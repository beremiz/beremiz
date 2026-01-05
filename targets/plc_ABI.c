/**
 * Init ABI and provide symbols to redirect calls from PLC code
 **/

#include "beremiz.h"

// Runtime -> PLC calls (plc_main_head.c)
unsigned int __run(unsigned int periods_passed);
int __init(int argc, char **argv);
void __cleanup(void);

#ifndef PLC_NO_DEBUG
int GetDebugData(unsigned int *tick, unsigned int *size, void **buffer);
void ResetDebugVariables(void);
void FreeDebugData(void);
int RegisterDebugVariable(uint32_t idx, void* force, size_t force_size);
#endif

static unsigned long long GetCommonTickTime() {
    return common_ticktime__;
}

beremiz_plc_ABI *beremiz_plc_interface_ptr;

void __init_ABI(beremiz_plc_ABI *interface) {
    beremiz_plc_interface_ptr = interface;
    beremiz_plc_interface_ptr->GetCommonTickTime = GetCommonTickTime;
    beremiz_plc_interface_ptr->__run = __run;
    beremiz_plc_interface_ptr->__init = __init;
    beremiz_plc_interface_ptr->__cleanup = __cleanup;
#ifndef PLC_NO_DEBUG
    beremiz_plc_interface_ptr->GetDebugData = GetDebugData;
    beremiz_plc_interface_ptr->ResetDebugVariables = ResetDebugVariables;
    beremiz_plc_interface_ptr->FreeDebugData = FreeDebugData;
    beremiz_plc_interface_ptr->RegisterDebugVariable = RegisterDebugVariable;
#endif
}

#ifndef PLC_NO_LOGGING
int LogMessage(uint8_t level, char* buf, uint32_t size)
{
    // note that we pass additional __tick when using ABI
    return beremiz_plc_interface_ptr->LogMessage(level, buf, size, __tick);
}
#endif

uint32_t AtomicCompareExchange(uint32_t *atomicvar, uint32_t compared, uint32_t exchange) {
    return beremiz_plc_interface_ptr->AtomicCompareExchange(atomicvar, compared, exchange);
}

void PLC_GetTime(IEC_TIME *CURRENT_TIME) {
    beremiz_plc_interface_ptr->PLC_GetTime(CURRENT_TIME);
}

int iec_lib_snprintf(char *__s, size_t __maxlen, const char *__format, ...)
{
	va_list args;
	va_start(args, __format);
	int ret = beremiz_plc_interface_ptr->iec_lib_vsnprintf(__s, __maxlen, __format, args);
	va_end(args);
	return ret;
}

double iec_lib_acos(double x) { return beremiz_plc_interface_ptr->iec_lib_acos(x); }
double iec_lib_asin(double x) { return beremiz_plc_interface_ptr->iec_lib_asin(x); }
double iec_lib_atan(double x) { return beremiz_plc_interface_ptr->iec_lib_atan(x); }
double iec_lib_cos(double x) { return beremiz_plc_interface_ptr->iec_lib_cos(x); }
double iec_lib_exp(double x) { return beremiz_plc_interface_ptr->iec_lib_exp(x); }
double iec_lib_fmod(double x, double y) { return beremiz_plc_interface_ptr->iec_lib_fmod(x, y); }
double iec_lib_log(double x) { return beremiz_plc_interface_ptr->iec_lib_log(x); }
double iec_lib_log10(double x) { return beremiz_plc_interface_ptr->iec_lib_log10(x); }
double iec_lib_pow(double x, double y) { return beremiz_plc_interface_ptr->iec_lib_pow(x, y); }
double iec_lib_sin(double x) { return beremiz_plc_interface_ptr->iec_lib_sin(x); }
double iec_lib_sqrt(double x) { return beremiz_plc_interface_ptr->iec_lib_sqrt(x); }
double iec_lib_tan(double x) { return beremiz_plc_interface_ptr->iec_lib_tan(x); }


void *create_RT_to_nRT_signal(char *name) {
    return beremiz_plc_interface_ptr->create_RT_to_nRT_signal(name);
}

void delete_RT_to_nRT_signal(void *handle) {
    beremiz_plc_interface_ptr->delete_RT_to_nRT_signal(handle);
}

int wait_RT_to_nRT_signal(void *handle) {
    return beremiz_plc_interface_ptr->wait_RT_to_nRT_signal(handle);
}

int unblock_RT_to_nRT_signal(void *handle) {
    return beremiz_plc_interface_ptr->unblock_RT_to_nRT_signal(handle);
}

void nRT_reschedule(void) {
    beremiz_plc_interface_ptr->nRT_reschedule();
}

#ifndef PLC_NO_DEBUG
int TryEnterDebugSection(void) {
    return beremiz_plc_interface_ptr->TryEnterDebugSection();
}

void InitiateDebugTransfer(int tick) {
    beremiz_plc_interface_ptr->InitiateDebugTransfer(tick);
}

void LeaveDebugSection(void) {
    beremiz_plc_interface_ptr->LeaveDebugSection();
}

int WaitDebugData(unsigned int *tick) {
    return beremiz_plc_interface_ptr->WaitDebugData(tick);
}
#endif

int CheckRetainBuffer(void) {
    return beremiz_plc_interface_ptr->CheckRetainBuffer();
}

void ValidateRetainBuffer(void) {
    beremiz_plc_interface_ptr->ValidateRetainBuffer();
}

void InValidateRetainBuffer(void) {
    beremiz_plc_interface_ptr->InValidateRetainBuffer();
}

void Retain(unsigned int offset, unsigned int count, void *p) {
    beremiz_plc_interface_ptr->Retain(offset, count, p);
}

void Remind(unsigned int offset, unsigned int count, void *p) {
    beremiz_plc_interface_ptr->Remind(offset, count, p);
}

void CleanupRetain(void) {
    beremiz_plc_interface_ptr->CleanupRetain();
}

int InitRetain(size_t buffer_size) {
    return beremiz_plc_interface_ptr->InitRetain(buffer_size);
}
