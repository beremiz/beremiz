#include <stdio.h>
#include <sys/timeb.h>
#include <time.h>
#include <windows.h>

long AtomicCompareExchange(long* atomicvar,long exchange, long compared)
{
    return InterlockedCompareExchange(atomicvar, exchange, compared);
}

//long AtomicExchange(long* atomicvar,long exchange)
//{
//    return InterlockedExchange(atomicvar, exchange);    
//}

struct _timeb timetmp;
void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
	_ftime(&timetmp);
	
	(*CURRENT_TIME).tv_sec = timetmp.time;
	(*CURRENT_TIME).tv_nsec = timetmp.millitm * 1000000;
}

void PLC_timer_notify()
{
    PLC_GetTime(&__CURRENT_TIME);
    __run();
}

HANDLE PLC_timer = NULL;
void PLC_SetTimer(long long next, long long period)
{
	LARGE_INTEGER liDueTime;		
	/* arg 2 of SetWaitableTimer take 100 ns interval*/
	liDueTime.QuadPart =  next / (-100);
	
	/*
	printf("SetTimer(%lld,%lld)\n",next, period);
	*/
	
	if (!SetWaitableTimer(PLC_timer, &liDueTime, common_ticktime__, NULL, NULL, 0))
    {
        printf("SetWaitableTimer failed (%d)\n", GetLastError());
    }
	if (WaitForSingleObject(PLC_timer, INFINITE) != WAIT_OBJECT_0)
	{
		printf("WaitForSingleObject failed (%d)\n", GetLastError());
	}
	PLC_timer_notify();
}

int main(int argc,char **argv)
{
	/* Translate PLC's microseconds to Ttick nanoseconds */
	Ttick = 1000000 * maxval(common_ticktime__,1);

	/* Create a waitable timer */
    PLC_timer = CreateWaitableTimer(NULL, FALSE, "WaitableTimer");
    if(NULL == PLC_timer)
    {
        printf("CreateWaitableTimer failed (%d)\n", GetLastError());
        return 1;
    }

    if( __init(argc,argv) == 0 )
    {
    	printf("Tick Time : %d ms\n", common_ticktime__);
    	while(1)
    	{
    		// Set a timer
    		PLC_SetTimer(Ttick,Ttick);
    		if (kbhit())
    		{
    			printf("Finishing\n");
    		    break;
            }
    	}
    	PLC_SetTimer(0,0);
    }
    __cleanup();
    CloseHandle(PLC_timer);
    		
    return 0;
}
