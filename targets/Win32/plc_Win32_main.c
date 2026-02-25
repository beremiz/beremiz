/**
 * Win32 specific code
 **/

#include <stdio.h>
#include <sys/timeb.h>
#include <time.h>
#include <windows.h>
#include <locale.h>
#include <math.h>
#include <stdarg.h>


uint32_t AtomicCompareExchange(uint32_t* atomicvar, uint32_t compared, uint32_t exchange)
{
    return InterlockedCompareExchange((volatile long int *)atomicvar, exchange, compared);
}

struct timeb timetmp;
void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
	ftime(&timetmp);

	(*CURRENT_TIME).tv_sec = timetmp.time;
	(*CURRENT_TIME).tv_nsec = timetmp.millitm * 1000000;
}

int iec_lib_snprintf(char *__s, size_t __maxlen, const char *__format, ...)
{
	va_list args;
	va_start(args, __format);
	int ret = vsnprintf(__s, __maxlen, __format, args);
	va_end(args);
	return ret;
}

double iec_lib_acos(double x) { return acos(x); }
double iec_lib_asin(double x) { return asin(x); }
double iec_lib_atan(double x) { return atan(x); }
double iec_lib_cos(double x) { return cos(x); }
double iec_lib_exp(double x) { return exp(x); }
double iec_lib_fmod(double x, double y) { return fmod(x, y); }
double iec_lib_log(double x) { return log(x); }
double iec_lib_log10(double x) { return log10(x); }
double iec_lib_pow(double x, double y) { return pow(x, y); }
double iec_lib_sin(double x) { return sin(x); }
double iec_lib_sqrt(double x) { return sqrt(x); }
double iec_lib_tan(double x) { return tan(x); }

HANDLE PLC_timer = NULL;
void PLC_SetTimer(unsigned long long next, unsigned long long period)
{
	LARGE_INTEGER liDueTime;
	/* arg 2 of SetWaitableTimer take 100 ns interval*/
	liDueTime.QuadPart =  next / (-100);

	if (!SetWaitableTimer(PLC_timer, &liDueTime, period<1000000?1:period/1000000, NULL, NULL, 0))
    {
        printf("SetWaitableTimer failed (%d)\n", GetLastError());
    }
}

int PLC_shutdown;

void record_run_time_ns_avg(struct timespec *start, struct timespec *end);

int ForceSaveRetainReq(void) {
    return PLC_shutdown;
}

unsigned long long GetCommonTickTime(){
	return common_ticktime__;
}

/* Variable used to stop plcloop thread */
void PlcLoop()
{
    PLC_shutdown = 0;
    while(!PLC_shutdown) {
        struct timespec plc_start_time, plc_end_time;
        if (WaitForSingleObject(PLC_timer, INFINITE) != WAIT_OBJECT_0){
            PLC_shutdown = 1;
            break;
        }
        clock_gettime(CLOCK_MONOTONIC, &plc_start_time);
        __run(1);
        clock_gettime(CLOCK_MONOTONIC, &plc_end_time);
		record_run_time_ns_avg(&plc_start_time, &plc_end_time);
    }
}

HANDLE PLC_thread;
HANDLE debug_sem;
HANDLE debug_wait_sem;
HANDLE python_sem;
HANDLE python_wait_sem;

#define maxval(a,b) ((a>b)?a:b)
int startPLC(int argc,char **argv)
{
	unsigned long thread_id = 0;
    BOOL tmp;

    debug_sem = CreateSemaphore(
                            NULL,           // default security attributes
                            1,  			// initial count
                            1,  			// maximum count
                            NULL);          // unnamed semaphore
    if (debug_sem == NULL)
    {
        printf("startPLC CreateSemaphore debug_sem error: %d\n", GetLastError());
        return 1;
    }

    debug_wait_sem = CreateSemaphore(
                            NULL,           // default security attributes
                            0,  			// initial count
                            1,  			// maximum count
                            NULL);          // unnamed semaphore

    if (debug_wait_sem == NULL)
    {
        printf("startPLC CreateSemaphore debug_wait_sem error: %d\n", GetLastError());
        return 1;
    }

    python_sem = CreateSemaphore(
                            NULL,           // default security attributes
                            1,  			// initial count
                            1,  			// maximum count
                            NULL);          // unnamed semaphore

    if (python_sem == NULL)
    {
        printf("startPLC CreateSemaphore python_sem error: %d\n", GetLastError());
        return 1;
    }
    python_wait_sem = CreateSemaphore(
                            NULL,           // default security attributes
                            0,  			// initial count
                            1,  			// maximum count
                            NULL);          // unnamed semaphore


    if (python_wait_sem == NULL)
    {
        printf("startPLC CreateSemaphore python_wait_sem error: %d\n", GetLastError());
        return 1;
    }


    /* Create a waitable timer */
    timeBeginPeriod(1);
    PLC_timer = CreateWaitableTimer(NULL, FALSE, "WaitableTimer");
    if(NULL == PLC_timer)
    {
        printf("CreateWaitableTimer failed (%d)\n", GetLastError());
        return 1;
    }
    if( __init(argc,argv) == 0 )
    {
        PLC_SetTimer(common_ticktime__,common_ticktime__);
        PLC_thread = CreateThread(NULL, 0, (LPTHREAD_START_ROUTINE)PlcLoop, NULL, 0, &thread_id);
    }
    else{
        return 1;
    }
    return 0;
}

static unsigned int __debug_tick;
IEC_BOOL __DEBUG = 0;

int TryEnterDebugSection(void)
{
	//printf("TryEnterDebugSection\n");
    if(WaitForSingleObject(debug_sem, 0) == WAIT_OBJECT_0){
        /* Only enter if debug active */
        if(__DEBUG){
            return 1;
        }
        ReleaseSemaphore(debug_sem, 1, NULL);
    }
    return 0;
}

void LeaveDebugSection(void)
{
	ReleaseSemaphore(debug_sem, 1, NULL);
    //printf("LeaveDebugSection\n");
}

int stopPLC()
{
 	
    PLC_shutdown = 1;
    // force last wakeup of PLC thread
    SetWaitableTimer(PLC_timer, 0, 0, NULL, NULL, 0);
    // wait end of PLC thread
    WaitForSingleObject(PLC_thread, INFINITE);

    __cleanup();

    CloseHandle(PLC_timer);
    CloseHandle(debug_wait_sem);
    CloseHandle(debug_sem);
    CloseHandle(python_wait_sem);
    CloseHandle(python_sem);
    CloseHandle(PLC_thread);
}

/* from plc_debugger.c */
int WaitDebugData(unsigned int *tick)
{
	DWORD res;
	res = WaitForSingleObject(debug_wait_sem, INFINITE);
    *tick = __debug_tick;
    /* Wait signal from PLC thread */
	return res != WAIT_OBJECT_0;
}

/* Called by PLC thread when debug_publish finished
 * This is supposed to unlock debugger thread in WaitDebugData*/
void InitiateDebugTransfer(int tick)
{
    /* remember tick */
    __debug_tick = tick;
    /* signal debugger thread it can read data */
    ReleaseSemaphore(debug_wait_sem, 1, NULL);
}

int suspendDebug(int disable)
{
    /* Prevent PLC to enter debug code */
    WaitForSingleObject(debug_sem, INFINITE);
    __DEBUG = !disable;
    if(disable)
        ReleaseSemaphore(debug_sem, 1, NULL);
    return 0;
}

void resumeDebug()
{
	__DEBUG = 1;
    /* Let PLC enter debug code */
	ReleaseSemaphore(debug_sem, 1, NULL);
}

/* from plc_python.c */
int WaitPythonCommands(void)
{
    /* Wait signal from PLC thread */
	return WaitForSingleObject(python_wait_sem, INFINITE);
}

/* Called by PLC thread on each new python command*/
void UnBlockPythonCommands(void)
{
    /* signal debugger thread it can read data */
	ReleaseSemaphore(python_wait_sem, 1, NULL);
}

int TryLockPython(void)
{
	return WaitForSingleObject(python_sem, 0) == WAIT_OBJECT_0;
}

void UnLockPython(void)
{
	ReleaseSemaphore(python_sem, 1, NULL);
}

void LockPython(void)
{
	WaitForSingleObject(python_sem, INFINITE);
}

struct RT_to_nRT_signal_s {
    HANDLE sem;
};

typedef struct RT_to_nRT_signal_s RT_to_nRT_signal_t;

#define _LogAndReturnNull(text) \
    {\
    	char mstr[256] = text " for ";\
        strncat(mstr, name, 255);\
        LogMessage(LOG_CRITICAL, mstr, strlen(mstr));\
        return NULL;\
    }

void *create_RT_to_nRT_signal(char* name){
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)malloc(sizeof(RT_to_nRT_signal_t));

    if(!sig) 
    	_LogAndReturnNull("Failed allocating memory for RT_to_nRT signal");

    sig->sem = CreateSemaphore(
                            NULL,           // default security attributes
                            1,  			// initial count
                            1,  			// maximum count
                            NULL);          // unnamed semaphore

    if(sig->sem == NULL)
    {
    	char mstr[256];
        snprintf(mstr, 255, "startPLC CreateSemaphore %s error: %d\n", name, GetLastError());
        LogMessage(LOG_CRITICAL, mstr, strlen(mstr));
        return NULL;
    }

    return (void*)sig;
}

void delete_RT_to_nRT_signal(void* handle){
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)handle;

    CloseHandle(python_sem);

    free(sig);
}

int wait_RT_to_nRT_signal(void* handle){
    int ret;
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)handle;
	return WaitForSingleObject(sig->sem, INFINITE);
}

int unblock_RT_to_nRT_signal(void* handle){
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)handle;
	return ReleaseSemaphore(sig->sem, 1, NULL);
}

void nRT_reschedule(void){
    SwitchToThread();
}

