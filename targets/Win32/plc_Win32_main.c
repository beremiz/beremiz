/**
 * Win32 specific code
 **/

#include <stdio.h>
#include <sys/timeb.h>
#include <time.h>
#include <windows.h>
#include <locale.h>
#include <stdint.h>

static CRITICAL_SECTION event_lock;
static CONDITION_VARIABLE event_cond;
static uint32_t event_bits = 0;
static uint8_t events_initialized = 0;

void set_event_bits(uint32_t bits) {
    EnterCriticalSection(&event_lock);
    event_bits |= bits;
    WakeAllConditionVariable(&event_cond);
    LeaveCriticalSection(&event_lock);
}

void clear_event_bits(uint32_t bits) {
    EnterCriticalSection(&event_lock);
    event_bits &= ~bits;
    LeaveCriticalSection(&event_lock);
}

uint32_t wait_event_bits(uint32_t mask) {
    EnterCriticalSection(&event_lock);
    while ((event_bits & mask) == 0) {
        SleepConditionVariableCS(&event_cond, &event_lock, INFINITE);
    }
    uint32_t bits = event_bits & mask;
    LeaveCriticalSection(&event_lock);
    return bits;
}

static volatile uint8_t is_debug = 0;
#define RUN_STATE   (1 << 0)
#define STEP_STATE  (1 << 1)
#define DEBUG_BIT_MASK    (RUN_STATE | STEP_STATE)
#define START_DEBUG     0
#define DBG_STEP        1
#define DBG_PAUSE       2
#define DBG_RESUME      3
#define END_DEBUG       4
#define UNKNOWN_KEY     5

int DebugControl(uint8_t key) {
    if (! events_initialized){
        InitializeCriticalSection(&event_lock);
        InitializeConditionVariable(&event_cond);
        events_initialized = 1;
    }

    switch (key) {
        case START_DEBUG:   
            is_debug = 1;
            clear_event_bits(DEBUG_BIT_MASK);
            LogMessage(LOG_INFO, "START_DEBUG\n", strlen("START_DEBUG\n") );
            return 0;
        case DBG_STEP:
            is_debug = 1;
            clear_event_bits(DEBUG_BIT_MASK);
            set_event_bits(STEP_STATE);    
            LogMessage(LOG_INFO, "STEP\n", strlen("STEP\n") );
            return 0;
        case DBG_PAUSE:
            is_debug = 1;
            clear_event_bits(DEBUG_BIT_MASK);
            LogMessage(LOG_INFO, "PAUSE\n", strlen("PAUSE\n") );
            return 0;
        case DBG_RESUME:
            set_event_bits(RUN_STATE);
            LogMessage(LOG_INFO, "DBG_RESUME\n", strlen("DBG_RESUME\n") );    
            return 0;
        case END_DEBUG:
            is_debug = 0;
            set_event_bits(RUN_STATE);
            LogMessage(LOG_INFO, "END_DEBUG\n", strlen("END_DEBUG\n") );    
            return 0;
    }
    LogMessage(LOG_CRITICAL, "END_DEBUG\n", strlen("END_DEBUG\n") );    
    return UNKNOWN_KEY; 
}

long AtomicCompareExchange(long* atomicvar, long compared, long exchange)
{
    return InterlockedCompareExchange(atomicvar, exchange, compared);
}
CRITICAL_SECTION Atomic64CS; 
long long AtomicCompareExchange64(long long* atomicvar, long long compared, long long exchange)
{
    long long res;
    EnterCriticalSection(&Atomic64CS);
    res=*atomicvar;
    if(*atomicvar == compared){
        *atomicvar = exchange;
    }
    LeaveCriticalSection(&Atomic64CS);
    return res;
}

struct timeb timetmp;
void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
	ftime(&timetmp);

	(*CURRENT_TIME).tv_sec = timetmp.time;
	(*CURRENT_TIME).tv_nsec = timetmp.millitm * 1000000;
}

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

int ForceSaveRetainReq(void) {
    return PLC_shutdown;
}

/* Variable used to stop plcloop thread */
void PlcLoop()
{
    PLC_shutdown = 0;
    while(!PLC_shutdown) {
        if (WaitForSingleObject(PLC_timer, INFINITE) != WAIT_OBJECT_0){
            PLC_shutdown = 1;
            break;
        }
        if (is_debug){
            uint32_t bits = wait_event_bits(DEBUG_BIT_MASK);
            switch (bits) {
                case RUN_STATE:
                    break;
                case STEP_STATE:
                    clear_event_bits(DEBUG_BIT_MASK);
                    break;
            }
        }
        PLC_GetTime(&__CURRENT_TIME);
        __run();
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
 	__tick = 0;
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
void InitiateDebugTransfer()
{
    /* remember tick */
    __debug_tick = __tick;
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

static void __attribute__((constructor))
beremiz_dll_init(void)
{
    InitializeCriticalSection(&Atomic64CS);

}

static void __attribute__((destructor))
beremiz_dll_destroy(void)
{
    DeleteCriticalSection(&Atomic64CS);
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

