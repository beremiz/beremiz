/**
 * Head of code common to all C targets
 **/
 
#include "beremiz.h"
/*
 * Prototypes of functions provided by generated C softPLC
 **/
void config_run__(unsigned int tick);
void config_init__(void);

/*
 * Prototypes of functions provided by generated target C code
 * */

// Retain buffer handling
int CheckRetainBuffer(void);
void ValidateRetainBuffer(void);
void InValidateRetainBuffer(void);
void Retain(unsigned int offset, unsigned int count, void *p);
void Remind(unsigned int offset, unsigned int count, void *p);
void CleanupRetain(void);
int InitRetain(size_t buffer_size);

// Debug
#ifndef PLC_NO_DEBUG
int __init_debug(void);
void __cleanup_debug(void);
void __publish_debug(void);
int TryEnterDebugSection(void);
void InitiateDebugTransfer(int tick);
#endif

// Logging
#ifndef PLC_USES_ABI /* not on PLC side if using ABI */
#ifndef PLC_NO_LOGGING
void __init_logging(void);
#endif
#endif

/*
 *  Variables used by generated C softPLC and plugins
 **/
IEC_TIME __CURRENT_TIME = {0, 0};
unsigned int __tick = 0;
char *PLC_ID = 0;

/*
 *  __tick is the current tick count of the PLC, 
 *  meant to be incremented on each cycle.
 *  PLC scheduler uses it to determine tasks to be executed.
 **/
extern unsigned int greatest_tick_count__;

/* Help to quit cleanly when init fail at a certain level */
static int init_level = 0;

/*
 * Prototypes of functions exported by plugins
 **/
%(calls_prototypes)s


/*
 * Retrieve input variables, run PLC and publish output variables
 **/
unsigned int __run(unsigned int periods_passed)
{
	PLC_GetTime(&__CURRENT_TIME);

    __tick += periods_passed;

    // scheduler is periodic and this period doesn't align with MAX_INT
    // if __tick overflows naturally at MAX_INT, scheduler will not work correctly
    // therefore matiec computes greatest_tick_count__ to use as a modulus
    if (greatest_tick_count__)
        __tick %%= greatest_tick_count__;

    %(retrieve_calls)s

    /*__retrieve_debug();*/

    config_run__(__tick);

#ifndef PLC_NO_DEBUG
    __publish_debug();
#endif

    %(publish_calls)s

    return __tick;
}

/*
 * Initialize PLC and calls plugins init functions
 **/

#ifdef PLC_USES_ABI
// from plc_ABI.c
extern beremiz_plc_ABI *beremiz_plc_interface_ptr;
#define EXT_INIT_ARGS(index) beremiz_plc_interface_ptr->argcs[index],beremiz_plc_interface_ptr->argvs[index]
#else
#define EXT_INIT_ARGS(index) 0,NULL
#endif

int __init(int argc, char **argv)
{
    int res = 0;
    init_level = 0;
    
    /* Effective tick time with 1ms default value */
    if(!common_ticktime__)
        common_ticktime__ = 1000000;

#ifndef PLC_USES_ABI /* not on PLC side if using ABI */
#ifndef PLC_NO_LOGGING
    __init_logging();
#endif
#endif

    config_init__();

#ifndef PLC_NO_DEBUG
    if((res = __init_debug()) != 0)
        return res;
#endif

    %(init_calls)s
    return res;
}

/*
 * Calls plugin cleanup proc.
 **/
void __cleanup(void)
{
    %(cleanup_calls)s
#ifndef PLC_NO_DEBUG
    __cleanup_debug();
#endif
}

/*
 * Extensions requirements
 **/
#define EXTENSIONS_REQUIREMENTS \
%(extensions_requirements)s

/*
 * plc_${target_name}_main.c is concatenated verbatim after this
 **/

