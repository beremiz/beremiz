/**
 * Linux specific code
 **/ 

#include <stdio.h>
#include <string.h>
#include <time.h>
#include <signal.h>
#include <stdlib.h>
#include <sys/mman.h>

#include <native/task.h>
#include <native/timer.h>
#include <native/mutex.h>
#include <native/sem.h>

unsigned int PLC_state = 0;
#define PLC_STATE_TASK_CREATED                  1
#define PLC_STATE_PYTHON_MUTEX_CREATED          2
#define PLC_STATE_PYTHON_WAIT_SEM_CREATED       4
#define PLC_STATE_DEBUG_MUTEX_CREATED           8
#define PLC_STATE_DEBUG_WAIT_SEM_CREATED       16

/* provided by POUS.C */
extern int common_ticktime__;

long AtomicCompareExchange(long* atomicvar,long compared, long exchange)
{
    return __sync_val_compare_and_swap(atomicvar, compared, exchange);
}

void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
    RTIME current_time = rt_timer_read();
    CURRENT_TIME->tv_sec = current_time / 1000000000;
    CURRENT_TIME->tv_nsec = current_time % 1000000000;
}

RT_TASK PLC_task;
RT_TASK WaitDebug_task;
RT_TASK WaitPythonCommand_task;
RT_TASK UnLockPython_task;
RT_TASK LockPython_task;
int PLC_shutdown = 0;

void PLC_SetTimer(long long next, long long period)
{
  RTIME current_time = rt_timer_read();
  rt_task_set_periodic(&PLC_task, current_time + next, rt_timer_ns2ticks(period));
}

void PLC_task_proc(void *arg)
{
    PLC_SetTimer(Ttick, Ttick);
  
    while (1) {
        PLC_GetTime(&__CURRENT_TIME);
        __run();
        if (PLC_shutdown) break;
        rt_task_wait_period(NULL);
    }
}

static int __debug_tick;

RT_SEM python_wait_sem;
RT_MUTEX python_mutex;
RT_SEM debug_wait_sem;
RT_MUTEX debug_mutex;

void PLC_cleanup_all(void)
{
    if (PLC_state & PLC_STATE_TASK_CREATED) {
        rt_task_delete(&PLC_task);
        PLC_state &= ~PLC_STATE_TASK_CREATED;
    }

    if (PLC_state & PLC_STATE_PYTHON_WAIT_SEM_CREATED) {
        rt_sem_delete(&python_wait_sem);
        PLC_state &= ~ PLC_STATE_PYTHON_WAIT_SEM_CREATED;
    }

    if (PLC_state & PLC_STATE_PYTHON_MUTEX_CREATED) {
        rt_mutex_delete(&python_mutex);
        PLC_state &= ~ PLC_STATE_PYTHON_MUTEX_CREATED;
    }
    
    if (PLC_state & PLC_STATE_DEBUG_WAIT_SEM_CREATED) {
        rt_sem_delete(&debug_wait_sem);
        PLC_state &= ~ PLC_STATE_DEBUG_WAIT_SEM_CREATED;
    }

    if (PLC_state & PLC_STATE_DEBUG_MUTEX_CREATED) {
        rt_mutex_delete(&debug_mutex);
        PLC_state &= ~ PLC_STATE_DEBUG_MUTEX_CREATED;
    }
}

int stopPLC()
{
    PLC_shutdown = 1;
    /* Stop the PLC */
    PLC_SetTimer(0, 0);
    PLC_cleanup_all();
    __cleanup();
    __debug_tick = -1;
    rt_sem_v(&debug_wait_sem);
    rt_sem_v(&python_wait_sem);
}

//
void catch_signal(int sig)
{
    stopPLC();
//  signal(SIGTERM, catch_signal);
    signal(SIGINT, catch_signal);
    printf("Got Signal %d\n",sig);
    exit(0);
}

#define max_val(a,b) ((a>b)?a:b)
int startPLC(int argc,char **argv)
{
    int ret = 0;
    
    signal(SIGINT, catch_signal);
    
    /* ne-memory-swapping for this program */
    mlockall(MCL_CURRENT | MCL_FUTURE);
    
    /* Translate PLC's microseconds to Ttick nanoseconds */
    Ttick = 1000000 * max_val(common_ticktime__,1);
    
    /* create python_wait_sem */
    ret = rt_sem_create(&python_wait_sem, "python_wait_sem", 0, S_FIFO);
    if (ret) goto error;
    PLC_state |= PLC_STATE_PYTHON_WAIT_SEM_CREATED;
    
    /* create python_mutex */
    ret = rt_mutex_create(&python_mutex, "python_mutex");
    if (ret) goto error;
    PLC_state |= PLC_STATE_PYTHON_MUTEX_CREATED;
    
    /* create debug_wait_sem */
    ret = rt_sem_create(&debug_wait_sem, "debug_wait_sem", 0, S_FIFO);
    if (ret) goto error;
    PLC_state |= PLC_STATE_DEBUG_WAIT_SEM_CREATED;
    
    /* create debug_mutex */
    ret = rt_mutex_create(&debug_mutex, "debug_mutex");
    if (ret) goto error;
    PLC_state |= PLC_STATE_DEBUG_MUTEX_CREATED;
    
    /* create can_driver_task */
    ret = rt_task_create(&PLC_task, "PLC_task", 0, 50, 0);
    if (ret) goto error;
    PLC_state |= PLC_STATE_TASK_CREATED;
    
    ret = __init(argc,argv);
    if (ret) goto error;

    /* start can_driver_task */
    ret = rt_task_start(&PLC_task, &PLC_task_proc, NULL);
    if (ret) goto error;

    return 0;

error:
    PLC_cleanup_all();
    return 1;
}

int TryEnterDebugSection(void)
{
    return rt_mutex_acquire(&debug_mutex, TM_NONBLOCK) == 0;
}

void LeaveDebugSection(void)
{
    rt_mutex_release(&debug_mutex);
}

extern int __tick;
/* from plc_debugger.c */
int WaitDebugData()
{
    rt_task_shadow(&WaitDebug_task, "WaitDebug_task", 0, 0);
    /* Wait signal from PLC thread */
    rt_sem_p(&debug_wait_sem, TM_INFINITE);
    return __debug_tick;
}
 
/* Called by PLC thread when debug_publish finished
 * This is supposed to unlock debugger thread in WaitDebugData*/
void InitiateDebugTransfer()
{
    /* remember tick */
    __debug_tick = __tick;
    /* signal debugger thread it can read data */
    rt_sem_v(&debug_wait_sem);
}

void suspendDebug(void)
{
    __DEBUG = 0;
    /* Prevent PLC to enter debug code */
    rt_mutex_acquire(&debug_mutex, TM_INFINITE);
}

void resumeDebug(void)
{
    __DEBUG = 1;
    /* Let PLC enter debug code */
    rt_mutex_release(&debug_mutex);
}

/* from plc_python.c */
int WaitPythonCommands(void)
{
    rt_task_shadow(&WaitPythonCommand_task, "WaitPythonCommand_task", 0, 0);
    /* Wait signal from PLC thread */
    rt_sem_p(&python_wait_sem, TM_INFINITE);
}
 
/* Called by PLC thread on each new python command*/
void UnBlockPythonCommands(void)
{
    /* signal debugger thread it can read data */
    rt_sem_v(&python_wait_sem);
}

int TryLockPython(void)
{
    return rt_mutex_acquire(&python_mutex, TM_NONBLOCK) == 0;
}

void UnLockPython(void)
{
    rt_task_shadow(&UnLockPython_task, "UnLockPython_task", 0, 0);
    rt_mutex_release(&python_mutex);
}

void LockPython(void)
{
    rt_task_shadow(&LockPython_task, "LockPython_task", 0, 0);
    rt_mutex_acquire(&python_mutex, TM_INFINITE);
}
