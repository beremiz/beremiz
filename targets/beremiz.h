/* Beremiz' header file for use by extensions */

#include "iec_types.h"

#define LOG_LEVELS 4
#define LOG_CRITICAL 0
#define LOG_WARNING 1
#define LOG_INFO 2
#define LOG_DEBUG 3

extern unsigned long long common_ticktime__;
int LogMessage(uint8_t level, char* buf, uint32_t size);
long AtomicCompareExchange(long* atomicvar,long compared, long exchange);

