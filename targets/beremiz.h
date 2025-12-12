#ifndef _BEREMIZ_H_
#define _BEREMIZ_H_

/* Beremiz' definitions file shared with extensions */

#include "iec_types.h"

#define LOG_LEVELS 4
#define LOG_CRITICAL 0
#define LOG_WARNING 1
#define LOG_INFO 2
#define LOG_DEBUG 3

#ifndef PLC_NOT_LINKED
extern unsigned long long common_ticktime__;
extern unsigned int __tick;
#endif

#define __PLC_LOG_FUNCTION \
int     LogMessage(uint8_t level, char* buf, uint32_t size)

#ifdef PLC_NO_LOGGING
#ifdef PLC_OWN_LOGGING
__PLC_LOG_FUNCTION;
#else
static inline __PLC_LOG_FUNCTION
{
	(void)level;
	(void)buf;
	(void)size;
	return 0;
}
#endif
#else
__PLC_LOG_FUNCTION;
#endif

uint32_t AtomicCompareExchange(uint32_t* atomicvar,uint32_t compared, uint32_t exchange);
void PLC_GetTime(IEC_TIME *CURRENT_TIME);
void *create_RT_to_nRT_signal(char* name);
void delete_RT_to_nRT_signal(void* handle);
int wait_RT_to_nRT_signal(void* handle);
int unblock_RT_to_nRT_signal(void* handle);
void nRT_reschedule(void);

#endif
