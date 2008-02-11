#include <stdio.h>
#include <string.h>
#include <time.h>
#include <signal.h>


void PLC_timer_notify(sigval_t val)
{
    clock_gettime(CLOCK_REALTIME, &__CURRENT_TIME);
    __run();
}

void catch_signal(int sig)
{
  signal(SIGTERM, catch_signal);
  signal(SIGINT, catch_signal);
  printf("Got Signal %d\n",sig);
}

int main(int argc,char **argv)
{
    timer_t timer;
    struct sigevent sigev;
    long tv_nsec = 1000000 * (maxval(common_ticktime__,1)%1000);
    time_t tv_sec = common_ticktime__/1000;
    struct itimerspec timerValues;
    
    memset (&sigev, 0, sizeof (struct sigevent));
    memset (&timerValues, 0, sizeof (struct itimerspec));
    sigev.sigev_value.sival_int = 0;
    sigev.sigev_notify = SIGEV_THREAD;
    sigev.sigev_notify_attributes = NULL;
    sigev.sigev_notify_function = PLC_timer_notify;
    timerValues.it_value.tv_sec = tv_sec;
    timerValues.it_value.tv_nsec = tv_nsec;
    timerValues.it_interval.tv_sec = tv_sec;
    timerValues.it_interval.tv_nsec = tv_nsec;

    if(  __init(argc,argv) == 0 ){
        timer_create (CLOCK_REALTIME, &sigev, &timer);
        timer_settime (timer, 0, &timerValues, NULL);
        
        /* install signal handler for manual break */
        signal(SIGTERM, catch_signal);
        signal(SIGINT, catch_signal);
        
        pause();
        
        timer_delete (timer);
    }
    __cleanup();
    
    return 0;
}
