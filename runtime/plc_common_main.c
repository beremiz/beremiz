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
static int init_level=0;

/*
 * Prototypes of funcions exported by plugins 
 **/
%(calls_prototypes)s

/*
 * Retrive input variables, run PLC and publish output variables 
 **/
void __run()
{
    %(retrive_calls)s
    
    config_run__(tick++);
    
    %(publish_calls)s
}

/*
 * Initialize variables according to PLC's defalut values,
 * and then init plugins with that values  
 **/
int __init(int argc,char **argv)
{
    int res;
    config_init__();
    %(init_calls)s
    return 0;
}
/*
 * Calls plugin cleanup proc.
 **/
void __cleanup()
{
    %(cleanup_calls)s
}

