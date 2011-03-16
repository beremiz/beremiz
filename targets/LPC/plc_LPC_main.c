/**
 * Yagarto specific code
 **/

#include <string.h>
#include <app_glue.h>

/* provided by POUS.C */
extern unsigned long long common_ticktime__;
extern unsigned long __tick;

extern unsigned long idLen;
extern unsigned char *idBuf;

static unsigned char RetainedIdBuf[128] __attribute__((section (".nvolatile")));
static unsigned char retain_buffer[RETAIN_BUFFER_SIZE] __attribute__((section (".nvolatile")));

static int debug_locked = 0;
static int _DebugDataAvailable = 0;
static unsigned long __debug_tick;

void LPC_GetTime(IEC_TIME*);
void LPC_SetTimer(unsigned long long next, unsigned long long period);

long AtomicCompareExchange(long* atomicvar,long compared, long exchange)
{
	/* No need for real atomic op on LPC,
	 * no possible preemption between debug and PLC */
	long res = *atomicvar;
	if(res == compared){
		*atomicvar = exchange;
	}
	return res;
}

void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
	/* Call target GetTime function */
	LPC_GetTime(CURRENT_TIME);
}

void PLC_SetTimer(unsigned long long next, unsigned long long period)
{
	LPC_SetTimer(next, period);
}

int startPLC(int argc,char **argv)
{
	if(__init(argc,argv) == 0){
        /* sign retain buffer */
		PLC_SetTimer(0, common_ticktime__);
		return 0;
	}else{
		return 1;
	}
}

int TryEnterDebugSection(void)
{
    if(!debug_locked && __DEBUG){
        debug_locked = 1;
		return 1;
    }
    return 0;
}

void LeaveDebugSection(void)
{
        debug_locked = 0;
}

int stopPLC(void)
{
    __cleanup();
    return 0;
}

/* from plc_debugger.c */
int WaitDebugData(unsigned long *tick)
{
    /* no blocking call on LPC */
    if(_DebugDataAvailable && !debug_locked){
        /* returns 0 on success */
        *tick = __debug_tick;
        _DebugDataAvailable = 0;
        return 0;
    }
    return 1;
}

/* Called by PLC thread when debug_publish finished
 * This is supposed to unlock debugger thread in WaitDebugData*/
void InitiateDebugTransfer(void)
{
    /* remember tick */
    __debug_tick = __tick;
    _DebugDataAvailable = 1;
}

void suspendDebug(int disable)
{
    /* Prevent PLC to enter debug code */
    __DEBUG = !disable;
    debug_locked = !disable;
}

void resumeDebug(void)
{
    /* Let PLC enter debug code */
    __DEBUG = 1;
    debug_locked = 0;
}

void ValidateRetainBuffer(void)
{
        memcpy(RetainedIdBuf, idBuf, idLen);
}

void InValidateRetainBuffer(void)
{
    /* invalidate that buffer */
    RetainedIdBuf[0] = 0;
}

int CheckRetainBuffer(void)
{
	/* compare RETAIN ID buffer with MD5 */
    /* return true if identical */
    int res = memcmp(RetainedIdBuf, idBuf, idLen) == 0;
    return res;
}

void Retain(unsigned int offset, unsigned int count, void *p)
{
    if(offset + count < RETAIN_BUFFER_SIZE)
        /* write in RETAIN buffer at offset*/
        memcpy(&retain_buffer[offset], p, count);
}

void Remind(unsigned int offset, unsigned int count, void *p)
{
    if(offset + count < RETAIN_BUFFER_SIZE)
        /* read at offset in RETAIN buffer */
        memcpy(p, &retain_buffer[offset], count);
}
