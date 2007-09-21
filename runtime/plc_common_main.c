/*
 * Functions and variables provied by generated C softPLC
 **/ 
extern int common_ticktime__;

/*
 * Functions and variables provied by plc.c
 **/ 
void run(long int tv_sec, long int tv_nsec);

#define maxval(a,b) ((a>b)?a:b)

#include "iec_types.h"

/*
 * Functions and variables provied by generated C softPLC
 **/ 
void config_run__(int tick);
void config_init__(void);

/*
 *  Functions and variables to export to generated C softPLC
 **/
 
IEC_TIME __CURRENT_TIME;

static int tick = 0;

%(calls_prototypes)s

void __run()
{
    %(retrive_calls)s
    config_run__(tick++);
    %(publish_calls)s
}

void __init()
{
    config_init__();
    %(init_calls)s
}

void __cleanup()
{
    %(cleanup_calls)s
}

