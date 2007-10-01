#include <stdio.h>
#include <sys/timeb.h>
#include <time.h>
#include <windows.h>

void timer_notify()
{
   struct _timeb timebuffer;

   _ftime( &timebuffer );
   CURRENT_TIME.tv_sec = timebuffer.time;
   CURRENT_TIME.tv_nsec = timebuffer.millitm * 1000000
   __run();
}

int main(int argc,char **argv)
{
    HANDLE hTimer = NULL;
    LARGE_INTEGER liDueTime;

    liDueTime.QuadPart = -10000 * maxval(common_ticktime__,1);;

    // Create a waitable timer.
    hTimer = CreateWaitableTimer(NULL, TRUE, "WaitableTimer");
    if (NULL == hTimer)
    {
        printf("CreateWaitableTimer failed (%d)\n", GetLastError());
        return 1;
    }

    if( __init(argc,argv) == 0 ){

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
            timer_notify();
        }
    }
    __cleanup();

    return 0;
}
