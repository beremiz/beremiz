#ifndef _BEREMIZ_H_
#define _BEREMIZ_H_

/* Beremiz' definitions shared by PLC, runtime and extensions */

#include <stddef.h>
#include <stdarg.h>
#include "iec_types.h"

#define LOG_LEVELS 4
#define LOG_CRITICAL 0
#define LOG_WARNING 1
#define LOG_INFO 2
#define LOG_DEBUG 3

#ifndef PLC_NOT_LINKED
extern unsigned long long common_ticktime__;
extern unsigned int __tick;

// PROTOTYPES

// PLC -> Runtime calls
uint32_t AtomicCompareExchange(uint32_t *atomicvar, uint32_t compared, uint32_t exchange);
void PLC_GetTime(IEC_TIME *CURRENT_TIME);

int iec_lib_snprintf(char *__s, size_t __maxlen, const char *__format, ...);
double iec_lib_acos(double x);
double iec_lib_asin(double x);
double iec_lib_atan(double x);
double iec_lib_cos(double x);
double iec_lib_exp(double x);
double iec_lib_fmod(double x, double y);
double iec_lib_log(double x);
double iec_lib_log10(double x);
double iec_lib_pow(double x, double y);
double iec_lib_sin(double x);
double iec_lib_sqrt(double x);
double iec_lib_tan(double x);

void *create_RT_to_nRT_signal(char *name);
void delete_RT_to_nRT_signal(void *handle);
int wait_RT_to_nRT_signal(void *handle);
int unblock_RT_to_nRT_signal(void *handle);
void nRT_reschedule(void);

#ifndef PLC_NO_DEBUG
int TryEnterDebugSection(void);
void InitiateDebugTransfer(int tick);
#endif

int CheckRetainBuffer(void);
void ValidateRetainBuffer(void);
void InValidateRetainBuffer(void);
void Retain(unsigned int offset, unsigned int count, void *p);
void Remind(unsigned int offset, unsigned int count, void *p);
void CleanupRetain(void);
void InitRetain(void);

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

#endif // PLC_NOT_LINKED

#ifdef PLC_USES_ABI

// FUNCTION POINTERS TYPE DEFINITIONS

// PLC -> Runtime calls
typedef uint32_t (*AtomicCompareExchange_t)(uint32_t *atomicvar, uint32_t compared, uint32_t exchange);
typedef void (*PLC_GetTime_t)(IEC_TIME *CURRENT_TIME);
typedef int (*IEC_LibVsnprintf_t)(char *__s, size_t __maxlen, const char *__format, va_list args);

typedef double (*IEC_LibAcos_t)(double x);
typedef double (*IEC_LibAsin_t)(double x);
typedef double (*IEC_LibAtan_t)(double x);
typedef double (*IEC_LibCos_t)(double x);
typedef double (*IEC_LibExp_t)(double x);
typedef double (*IEC_LibFmod_t)(double x, double y);
typedef double (*IEC_LibLog_t)(double x);
typedef double (*IEC_LibLog10_t)(double x);
typedef double (*IEC_LibPow_t)(double x, double y);
typedef double (*IEC_LibSin_t)(double x);
typedef double (*IEC_LibSqrt_t)(double x);
typedef double (*IEC_LibTan_t)(double x);



typedef void *(*CreateRTtoNRTSignal_t)(char *name);
typedef void (*DeleteRTtoNRTSignal_t)(void *handle);
typedef int (*WaitRTtoNRTSignal_t)(void *handle);
typedef int (*UnblockRTtoNRTSignal_t)(void *handle);
typedef void (*NRTReschedule_t)(void);

#ifndef PLC_NO_DEBUG
typedef int (*TryEnterDebugSection_t)(void);
typedef void (*InitiateDebugTransfer_t)(int tick);
typedef void (*LeaveDebugSection_t)(void);
#endif

typedef int (*CheckRetainBuffer_t)(void);
typedef void (*ValidateRetainBuffer_t)(void);
typedef void (*InValidateRetainBuffer_t)(void);
typedef void (*Retain_t)(unsigned int offset, unsigned int count, void *p);
typedef void (*Remind_t)(unsigned int offset, unsigned int count, void *p);
typedef void (*CleanupRetain_t)(void);
typedef void (*InitRetain_t)(void);

typedef int (*LogMessage_t)(uint8_t level, char* buf, uint32_t size, unsigned int __tick);

// Runtime -> PLC calls
typedef unsigned long long (*GetCommonTickTime_t)(void);

typedef unsigned int (*Run_t)(unsigned int periods_passed);
typedef int (*Init_t)(int argc, char **argv);
typedef void (*Cleanup_t)(void);

// Beremiz PLC ABI structure
typedef struct {

    // PLC -> Runtime calls
    AtomicCompareExchange_t AtomicCompareExchange;
    PLC_GetTime_t PLC_GetTime;

    IEC_LibVsnprintf_t iec_lib_vsnprintf;

    IEC_LibAcos_t iec_lib_acos;
    IEC_LibAsin_t iec_lib_asin;
    IEC_LibAtan_t iec_lib_atan;
    IEC_LibCos_t iec_lib_cos;
    IEC_LibExp_t iec_lib_exp;
    IEC_LibFmod_t iec_lib_fmod;
    IEC_LibLog_t iec_lib_log;
    IEC_LibLog10_t iec_lib_log10;
    IEC_LibPow_t iec_lib_pow;
    IEC_LibSin_t iec_lib_sin;
    IEC_LibSqrt_t iec_lib_sqrt;
    IEC_LibTan_t iec_lib_tan;

    CreateRTtoNRTSignal_t create_RT_to_nRT_signal;
    DeleteRTtoNRTSignal_t delete_RT_to_nRT_signal;
    WaitRTtoNRTSignal_t wait_RT_to_nRT_signal;
    UnblockRTtoNRTSignal_t unblock_RT_to_nRT_signal;
    NRTReschedule_t nRT_reschedule;
#ifndef PLC_NO_DEBUG
    TryEnterDebugSection_t TryEnterDebugSection;
    InitiateDebugTransfer_t InitiateDebugTransfer;
    LeaveDebugSection_t LeaveDebugSection;
#endif
    CheckRetainBuffer_t CheckRetainBuffer;
    ValidateRetainBuffer_t ValidateRetainBuffer;
    InValidateRetainBuffer_t InValidateRetainBuffer;
    Retain_t Retain;
    Remind_t Remind;
    CleanupRetain_t CleanupRetain;
    InitRetain_t InitRetain;

#ifndef PLC_NO_LOGGING
    LogMessage_t LogMessage;
#endif

    // Runtime -> PLC calls

    GetCommonTickTime_t GetCommonTickTime;

    Run_t __run;
    Init_t __init;
    Cleanup_t __cleanup;   

    // private vendor data accessed by:
    // - C code generated by extensions
    // - FB libraries    
    int *argcs;
    void ***argvs;

} beremiz_plc_ABI;

#endif // PLC_USES_ABI

#endif
