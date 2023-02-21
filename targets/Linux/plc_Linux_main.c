/**
 * Linux specific code
 **/

#include <stdio.h>
#include <string.h>
#include <time.h>
#include <signal.h>
#include <stdlib.h>
#include <errno.h>
#include <pthread.h>
#include <locale.h>
#include <semaphore.h>
#ifdef REALTIME_LINUX
#include <sys/mman.h>
#endif

static unsigned long __debug_tick;

static pthread_t PLC_thread;
static pthread_mutex_t python_wait_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t python_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t debug_wait_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t debug_mutex = PTHREAD_MUTEX_INITIALIZER;

static int PLC_shutdown = 0;

long AtomicCompareExchange(long* atomicvar,long compared, long exchange)
{
    return __sync_val_compare_and_swap(atomicvar, compared, exchange);
}
long long AtomicCompareExchange64(long long* atomicvar, long long compared, long long exchange)
{
    return __sync_val_compare_and_swap(atomicvar, compared, exchange);
}

void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
    struct timespec tmp;
    clock_gettime(CLOCK_REALTIME, &tmp);
    CURRENT_TIME->tv_sec = tmp.tv_sec;
    CURRENT_TIME->tv_nsec = tmp.tv_nsec;
}

static long long period_ns = 0;
struct timespec next_abs_time;

static void inc_timespec(struct timespec *ts, unsigned long long value_ns)
{
    long long next_ns = ((long long) ts->tv_sec * 1000000000) + ts->tv_nsec + value_ns;
#ifdef __lldiv_t_defined
    lldiv_t next_div = lldiv(next_ns, 1000000000);
    ts->tv_sec = next_div.quot;
    ts->tv_nsec = next_div.rem;
#else
    ts->tv_sec = next_ns / 1000000000;
    ts->tv_nsec = next_ns % 1000000000;
#endif
}

void PLC_SetTimer(unsigned long long next, unsigned long long period)
{
    /*
    printf("SetTimer(%lld,%lld)\n",next, period);
    */
    period_ns = period;
    clock_gettime(CLOCK_MONOTONIC, &next_abs_time);
    inc_timespec(&next_abs_time, next);
    // interrupt clock_nanpsleep
    pthread_kill(PLC_thread, SIGUSR1);
}

void catch_signal(int sig)
{
//  signal(SIGTERM, catch_signal);
  signal(SIGINT, catch_signal);
  printf("Got Signal %d\n",sig);
  exit(0);
}

void PLCThreadSignalHandler(int sig)
{
    if (sig == SIGUSR2)
        pthread_exit(NULL);
}

int ForceSaveRetainReq(void) {
    return PLC_shutdown;
}

void PLC_thread_proc(void *arg)
{
    while (!PLC_shutdown) {
        // Sleep until next PLC run
        // TODO check result of clock_nanosleep and wait again or exit eventually
        int res = clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next_abs_time, NULL);
        if(res==EINTR){
            continue;
        }
        if(res!=0){
            printf("PLC thread died with error %d \n", res);
            return;
        }
        PLC_GetTime(&__CURRENT_TIME);
        __run();
        inc_timespec(&next_abs_time, period_ns);
    }
    pthread_exit(0);
}

#define _LogError(text,...) \
    {\
        char mstr[256];\
        snprintf(mstr, 255, text, ##__VA_ARGS__);\
        LogMessage(LOG_CRITICAL, mstr, strlen(mstr));\
    }
#define maxval(a,b) ((a>b)?a:b)
int startPLC(int argc,char **argv)
{

    int ret;
	pthread_attr_t *pattr = NULL;

#ifdef REALTIME_LINUX
	struct sched_param param;
	pthread_attr_t attr;

    /* Lock memory */
    ret = mlockall(MCL_CURRENT|MCL_FUTURE);
    if(ret == -1) {
		_LogError("mlockall failed: %m\n");
		return ret;
    }

	/* Initialize pthread attributes (default values) */
	ret = pthread_attr_init(&attr);
	if (ret) {
		_LogError("init pthread attributes failed\n");
		return ret;
	}

	/* Set scheduler policy and priority of pthread */
	ret = pthread_attr_setschedpolicy(&attr, SCHED_FIFO);
	if (ret) {
		_LogError("pthread setschedpolicy failed\n");
		return ret;
	}
	param.sched_priority = PLC_THREAD_PRIORITY;
	ret = pthread_attr_setschedparam(&attr, &param);
	if (ret) {
		_LogError("pthread setschedparam failed\n");
		return ret;
	}

	/* Use scheduling parameters of attr */
	ret = pthread_attr_setinheritsched(&attr, PTHREAD_EXPLICIT_SCHED);
	if (ret) {
		_LogError("pthread setinheritsched failed\n");
		return ret;
	}

	pattr = &attr;
#endif

    PLC_shutdown = 0;

    pthread_mutex_init(&debug_wait_mutex, NULL);
    pthread_mutex_init(&debug_mutex, NULL);
    pthread_mutex_init(&python_wait_mutex, NULL);
    pthread_mutex_init(&python_mutex, NULL);

    pthread_mutex_lock(&debug_wait_mutex);
    pthread_mutex_lock(&python_wait_mutex);

    if((ret = __init(argc,argv)) == 0 ){

        /* Signal to wakeup PLC thread when period changes */
        signal(SIGUSR1, PLCThreadSignalHandler);
        /* Signal to end PLC thread */
        signal(SIGUSR2, PLCThreadSignalHandler);
        /* install signal handler for manual break */
        signal(SIGINT, catch_signal);

        /* initialize next occurence and period */
        period_ns = common_ticktime__;
        clock_gettime(CLOCK_MONOTONIC, &next_abs_time);

        ret = pthread_create(&PLC_thread, pattr, (void*) &PLC_thread_proc, NULL);
		if (ret) {
			_LogError("create pthread failed\n");
			return ret;
		}
    }else{
        return ret;
    }
    return 0;
}

int TryEnterDebugSection(void)
{
    if (pthread_mutex_trylock(&debug_mutex) == 0){
        /* Only enter if debug active */
        if(__DEBUG){
            return 1;
        }
        pthread_mutex_unlock(&debug_mutex);
    }
    return 0;
}

void LeaveDebugSection(void)
{
    pthread_mutex_unlock(&debug_mutex);
}

int stopPLC()
{
    /* Stop the PLC */
    PLC_shutdown = 1;
    /* Order PLCThread to exit */
    pthread_kill(PLC_thread, SIGUSR2);
    pthread_join(PLC_thread, NULL);
    __cleanup();
    pthread_mutex_destroy(&debug_wait_mutex);
    pthread_mutex_destroy(&debug_mutex);
    pthread_mutex_destroy(&python_wait_mutex);
    pthread_mutex_destroy(&python_mutex);
    return 0;
}

extern unsigned long __tick;

int WaitDebugData(unsigned long *tick)
{
    int res;
    if (PLC_shutdown) return 1;
    /* Wait signal from PLC thread */
    res = pthread_mutex_lock(&debug_wait_mutex);
    *tick = __debug_tick;
    return res;
}

/* Called by PLC thread when debug_publish finished
 * This is supposed to unlock debugger thread in WaitDebugData*/
void InitiateDebugTransfer()
{
    /* remember tick */
    __debug_tick = __tick;
    /* signal debugger thread it can read data */
    pthread_mutex_unlock(&debug_wait_mutex);
}

int suspendDebug(int disable)
{
    /* Prevent PLC to enter debug code */
    pthread_mutex_lock(&debug_mutex);
    /*__DEBUG is protected by this mutex */
    __DEBUG = !disable;
    if (disable)
        pthread_mutex_unlock(&debug_mutex);
    return 0;
}

void resumeDebug(void)
{
    __DEBUG = 1;
    /* Let PLC enter debug code */
    pthread_mutex_unlock(&debug_mutex);
}

/* from plc_python.c */
int WaitPythonCommands(void)
{
    /* Wait signal from PLC thread */
    return pthread_mutex_lock(&python_wait_mutex);
}

/* Called by PLC thread on each new python command*/
void UnBlockPythonCommands(void)
{
    /* signal python thread it can read data */
    pthread_mutex_unlock(&python_wait_mutex);
}

int TryLockPython(void)
{
    return pthread_mutex_trylock(&python_mutex) == 0;
}

void UnLockPython(void)
{
    pthread_mutex_unlock(&python_mutex);
}

void LockPython(void)
{
    pthread_mutex_lock(&python_mutex);
}

struct RT_to_nRT_signal_s {
    int used;
    pthread_cond_t WakeCond;
    pthread_mutex_t WakeCondLock;
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

    sig->used = 1;
    pthread_cond_init(&sig->WakeCond, NULL);
    pthread_mutex_init(&sig->WakeCondLock, NULL);

    return (void*)sig;
}

void delete_RT_to_nRT_signal(void* handle){
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)handle;

    pthread_mutex_lock(&sig->WakeCondLock);
    sig->used = 0;
    pthread_cond_signal(&sig->WakeCond);
    pthread_mutex_unlock(&sig->WakeCondLock);
}

int wait_RT_to_nRT_signal(void* handle){
    int ret;
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)handle;
    pthread_mutex_lock(&sig->WakeCondLock);
    ret = pthread_cond_wait(&sig->WakeCond, &sig->WakeCondLock);
    if(!sig->used) ret = -EINVAL;
    pthread_mutex_unlock(&sig->WakeCondLock);

    if(!sig->used){
        pthread_cond_destroy(&sig->WakeCond);
        pthread_mutex_destroy(&sig->WakeCondLock);
        free(sig);
    }
    return ret;
}

int unblock_RT_to_nRT_signal(void* handle){
    RT_to_nRT_signal_t *sig = (RT_to_nRT_signal_t*)handle;
    return pthread_cond_signal(&sig->WakeCond);
}

void nRT_reschedule(void){
    sched_yield();
}
