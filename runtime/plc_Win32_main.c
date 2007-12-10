#include <stdio.h>
#include <sys/timeb.h>
#include <time.h>
#include <windows.h>

void timer_notify()
{
   struct _timeb timebuffer;
   printf(".");

   _ftime( &timebuffer );
   __CURRENT_TIME.tv_sec = timebuffer.time;
   __CURRENT_TIME.tv_nsec = timebuffer.millitm * 1000000;
   __run();
}

int main(int argc,char **argv)
{
    HANDLE hTimer = NULL;
    LARGE_INTEGER liDueTime;

    liDueTime.QuadPart = -10000 * maxval(common_ticktime__,1);

    // Create a waitable timer.
    hTimer = CreateWaitableTimer(NULL, FALSE, "WaitableTimer");
    if (NULL == hTimer)
    {
        printf("CreateWaitableTimer failed (%d)\n", GetLastError());
        return 1;
    }

    if( __init(argc,argv) == 0 ){

    	printf("Tick Time : %d ms\n", common_ticktime__);
        // Set a timer
        if (!SetWaitableTimer(hTimer, &liDueTime, common_ticktime__, NULL, NULL, 0))
        {
            printf("SetWaitableTimer failed (%d)\n", GetLastError());
            return 2;
        }
    
        while(1){
        // Wait for the timer.
            if (WaitForSingleObject(hTimer, INFINITE) != WAIT_OBJECT_0)
            {
                printf("WaitForSingleObject failed (%d)\n", GetLastError());
                break;
            }
            if (kbhit())
            {
                printf("Finishing\n");
                break;
            }
            timer_notify();
        }
    }
    __cleanup();

    return 0;
}
