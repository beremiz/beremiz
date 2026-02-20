/** 
 * LOGGING
 **/

#include "beremiz.h"
#include <string.h>
#include <time.h>
#include <stdio.h>

#ifndef LOG_BUFFER_SIZE
#define LOG_BUFFER_SIZE (1<<14) /*16Ko*/
#endif
#ifndef LOG_BUFFER_ATTRS
#define LOG_BUFFER_ATTRS
#endif

static char LogBuff[LOG_LEVELS][LOG_BUFFER_SIZE] LOG_BUFFER_ATTRS;

#define LOG_BUFFER_MASK (LOG_BUFFER_SIZE-1)

static void inline copy_to_log(uint8_t level, uint32_t buffpos, void* buf, uint32_t size){
    if(buffpos + size < LOG_BUFFER_SIZE){
        memcpy(&LogBuff[level][buffpos], buf, size);
    }else{
        uint32_t remaining = LOG_BUFFER_SIZE - buffpos; 
        memcpy(&LogBuff[level][buffpos], buf, remaining);
        memcpy(LogBuff[level], (char*)buf + remaining, size - remaining);
    }
}
static void inline copy_from_log(uint8_t level, uint32_t buffpos, void* buf, uint32_t size){
    if(buffpos + size < LOG_BUFFER_SIZE){
        memcpy(buf, &LogBuff[level][buffpos], size);
    }else{
        uint32_t remaining = LOG_BUFFER_SIZE - buffpos; 
        memcpy(buf, &LogBuff[level][buffpos], remaining);
        memcpy((char*)buf + remaining, LogBuff[level], size - remaining);
    }
}

/* Log buffer structure

 |<-Tail1.msgsize->|<-sizeof(mTail)->|<--Tail2.msgsize-->|<-sizeof(mTail)->|...
 |  Message1 Body  |      Tail1      |   Message2 Body   |      Tail2      |

*/
typedef struct {
    uint32_t msgidx;
    uint32_t msgsize;
    unsigned int tick;
    IEC_TIME time;
} mTail;

/* Log cursor : 32b index in log buffer, accessed atomically */
static uint32_t LogCursor[LOG_LEVELS] LOG_BUFFER_ATTRS = {0x0,0x0,0x0,0x0};
static uint32_t LogIndex[LOG_LEVELS] LOG_BUFFER_ATTRS = {0x0,0x0,0x0,0x0};

void __init_logging(void) {
	uint8_t level;
	for(level=0;level<LOG_LEVELS;level++){
		LogCursor[level] = 0;
        LogIndex[level] = 0;
	}
    memset(LogBuff, 0, sizeof(LogBuff));
}

void ResetLogCount(void) {
    __init_logging();
}

#ifdef PLC_USES_ABI
#define _sfx(fn) fn##_impl
void _sfx(PLC_GetTime)(IEC_TIME *CURRENT_TIME);
uint32_t _sfx(AtomicCompareExchange)(uint32_t *atomicvar, uint32_t compared, uint32_t exchange);

#else
#define _sfx(fn) fn
#endif

/* Store one log message of given size */
int _sfx(LogMessage)(uint8_t level, char* buf, uint32_t size
#ifdef PLC_USES_ABI
, unsigned int __tick
#endif
){
    if(size < LOG_BUFFER_SIZE - sizeof(mTail)){
        uint32_t new_cursor, old_cursor;
        uint32_t new_index, old_index;
        uint32_t result;

        mTail tail;
        tail.msgsize = size;
        tail.tick = __tick;
        _sfx(PLC_GetTime)(&tail.time);

        /* Try fetch and then increment "atomically" and loop if (unlikely) interrupted.*/
        do{
            old_cursor = LogCursor[level];
            new_cursor = ((old_cursor + size + sizeof(mTail)) & LOG_BUFFER_MASK);
            result = _sfx(AtomicCompareExchange)(
                (uint32_t*)&LogCursor[level],
                (uint32_t)old_cursor,
                (uint32_t)new_cursor);
        }while((result!=(uint32_t)old_cursor));

        /* Doesn't matter much if indices do not strictly follow */
        do{
            old_index = LogIndex[level];
            new_index = old_index + 1;
            result = _sfx(AtomicCompareExchange)(
                (uint32_t*)&LogIndex[level],
                (uint32_t)old_index,
                (uint32_t)new_index);
        }while((result!=(uint32_t)old_index));


        tail.msgidx = old_index;

        copy_to_log(level, old_cursor, buf, size);
        copy_to_log(level, (old_cursor + size) & LOG_BUFFER_MASK, &tail, sizeof(mTail));

        return 1; /* Success */
    }else{
    	char mstr[] = "Logging error : message too big";
        _sfx(LogMessage)(LOG_CRITICAL, mstr, sizeof(mstr)
        #ifdef PLC_USES_ABI
        , __tick
        #endif
        );
    }
    return 0;
}

uint32_t GetLogCount(uint8_t level){
    return LogIndex[level];
}


// PLC execution statistics
#define STATS_EMA_ALPHA 0.2f  // Exponential moving average smoothing factor

// Macro to generate timing record functions
#define DEFINE_RECORD_TIME_FUNC(var_name)                                                             \
static uint32_t var_name = 0;                                                                         \
static int var_name##_valid = 0;                                                                      \
void record_##var_name(struct timespec *start, struct timespec *end) {                                \
    int32_t sec_diff = end->tv_sec - start->tv_sec;                                                   \
	uint32_t delta_ns;                                                                                \
    if (sec_diff == 0 && end->tv_nsec >= start->tv_nsec) {                                            \
        /* Same second, simple subtraction */                                                         \
        delta_ns = end->tv_nsec - start->tv_nsec;                                                     \
		var_name##_valid = 1;                                                                         \
    } else if (sec_diff == 1) {                                                                       \
        /* Crossed second boundary */                                                                 \
        delta_ns = (1000000000U - start->tv_nsec) + end->tv_nsec;                                     \
		var_name##_valid = 1;                                                                         \
    } else {                                                                                          \
        /* Overflow (> 1 second or negative time), mark stats invalid */                              \
        var_name##_valid = 0;                                                                         \
		var_name = 0;                                                                                 \
		return;                                                                                       \
    }                                                                                                 \
	if(var_name##_valid){                                                                             \
		var_name = (uint32_t)(STATS_EMA_ALPHA * delta_ns + (1.0f - STATS_EMA_ALPHA) * (var_name));    \
	} else {                                                                                          \
		var_name = delta_ns;                                                                          \
		var_name##_valid = 1;                                                                         \
	}                                                                                                 \
}

// Generate the three recording functions
DEFINE_RECORD_TIME_FUNC(run_time_ns_avg)

unsigned long long GetCommonTickTime();

/* Return message size and content */
uint32_t GetLogMessage(uint8_t level, uint32_t msgidx, char* buf, uint32_t max_size, uint32_t* tick, uint32_t* tv_sec, uint32_t* tv_nsec){
    if(!max_size || !buf || !tick || !tv_sec || !tv_nsec)
        return 0;

    if(level == 0xFF){ // Get stats
        uint64_t period_ns = GetCommonTickTime();
		if(run_time_ns_avg_valid){
            IEC_TIME now;
            _sfx(PLC_GetTime)(&now);
            *tv_sec = now.tv_sec; 
            *tv_nsec = now.tv_nsec; 
            *tick = 0; 

			return snprintf(buf, max_size,
					"PLC Cycle: %d%% of %dms", 
					(int)(((uint64_t)run_time_ns_avg*100)/period_ns),
					(int)(period_ns/1000000));
		} else {
			return snprintf(buf, max_size,
					"PLC Cycle: %dms",
					(int)(period_ns/1000000));
		}    
    }
    
    if(LogIndex[level] > 0){
        uint32_t cursor = LogCursor[level];
        uint32_t stailpos = (cursor - sizeof(mTail)) & LOG_BUFFER_MASK;
        uint32_t initial_stailpos = stailpos;
        uint32_t old_stailpos = stailpos;
        int found = 0;

        mTail tail = {0};

        /* Message search loop */
        do {
            copy_from_log(level, stailpos, &tail, sizeof(mTail));
            if(tail.msgsize == 0) break;
            if((found = (tail.msgidx == msgidx))) break;
            old_stailpos = stailpos;
            stailpos = (stailpos - sizeof(mTail) - tail.msgsize ) & LOG_BUFFER_MASK;
        }while(!((stailpos <= initial_stailpos) && (old_stailpos > initial_stailpos)) // don't cross start position
            && (stailpos != initial_stailpos));                           // don't loop forever

        if(found){
            uint32_t sbuffpos = (stailpos - tail.msgsize ) & LOG_BUFFER_MASK; 
            uint32_t totalsize = tail.msgsize;
            *tick = tail.tick; 
            *tv_sec = tail.time.tv_sec; 
            *tv_nsec = tail.time.tv_nsec; 
            copy_from_log(level, sbuffpos, buf, 
                          totalsize > max_size ? max_size : totalsize);
            return totalsize;
        }
    }
    return 0;
}

