/*
 * DEBUGGER code
 * 
 * On "publish", when buffer is free, debugger stores arbitrary variables 
 * content into, and mark this buffer as filled
 * 
 * 
 * Buffer content is read asynchronously, (from non real time part), 
 * and then buffer marked free again.
 *  
 * 
 * */
#include "iec_types_all.h"
#include "POUS.h"
/*for memcpy*/
#include <string.h>
#include <stdio.h>

#define BUFFER_SIZE %(buffer_size)d
#define MAX_SUBSCRIBTION %(subscription_table_count)d

/* Atomically accessed variable for buffer state */
#define BUFFER_FREE 0
#define BUFFER_BUSY 1
static long buffer_state = BUFFER_FREE;

/* The buffer itself */
char debug_buffer[BUFFER_SIZE];

/* Buffer's cursor*/
static char* buffer_cursor = debug_buffer;

typedef struct{
    void* ptrvalue;
    __IEC_types_enum type;
}struct_plcvar;

/***
 * Declare programs 
 **/
%(programs_declarations)s

/***
 * Declare global variables from resources and conf 
 **/
%(extern_variables_declarations)s

static int subscription_table[MAX_SUBSCRIBTION];
static int* latest_subscription = subscription_table;
static int* subscription_cursor = subscription_table;

struct_plcvar variable_table[%(variables_pointer_type_table_count)d];

void __init_debug(void)
{
%(variables_pointer_type_table_initializer)s
    buffer_state = BUFFER_FREE;
}

void __cleanup_debug(void)
{
}

void __retrieve_debug(void)
{
}

extern int TryEnterDebugSection(void);
extern void LeaveDebugSection(void);
extern long AtomicCompareExchange(long*, long, long);
extern void InitiateDebugTransfer(void);

extern unsigned long __tick;
void __publish_debug(void)
{
    /* Check there is no running debugger re-configuration */
    if(TryEnterDebugSection()){
        /* Lock buffer */
        long latest_state = AtomicCompareExchange(
            &buffer_state,
            BUFFER_FREE,
            BUFFER_BUSY);
            
        /* If buffer was free */
        if(latest_state == BUFFER_FREE)
        {
            int* subscription;
            
            /* Reset buffer cursor */
            buffer_cursor = debug_buffer;
            
            /* iterate over subscriptions */
            for(subscription=subscription_table;
                subscription < latest_subscription;
                subscription++)
            {
                /* get variable descriptor */
                struct_plcvar* my_var = &variable_table[*subscription];
                char* next_cursor;
                /* get variable size*/
                USINT size = __get_type_enum_size(my_var->type);
                /* compute next cursor positon*/
                next_cursor = buffer_cursor + size;
                /* if buffer not full */
                if(next_cursor <= debug_buffer + BUFFER_SIZE)
                {
                    /* copy data to the buffer */
                    memcpy(buffer_cursor, my_var->ptrvalue, size);
                    /* increment cursor according size*/
                    buffer_cursor = next_cursor;
                }else{
                    /*TODO : signal overflow*/
                }
            }
    
            /* Reset buffer cursor again (for IterDebugData)*/
            buffer_cursor = debug_buffer;
            subscription_cursor = subscription_table;
            
            /* Leave debug section,
             * Trigger asynchronous transmission 
             * (returns immediately) */
            InitiateDebugTransfer(); /* size */
        }
        LeaveDebugSection();
    }
}

void RegisterDebugVariable(int idx)
{
    /*If subscription table not full */
    if(latest_subscription - subscription_table < MAX_SUBSCRIBTION)
    {
        *(latest_subscription++) = idx;
        /* TODO pre-calc buffer size and signal overflow*/
    }else{
        /*TODO : signal subscription overflow*/
    }
}

void ResetDebugVariables(void)
{
    latest_subscription = subscription_table;
}

void FreeDebugData(void)
{
    /* atomically mark buffer as free */
    long latest_state;
    latest_state = AtomicCompareExchange(
        &buffer_state,
        BUFFER_BUSY,
        BUFFER_FREE);
}

void* IterDebugData(int* idx, const char **type_name)
{
	struct_plcvar* my_var;
	USINT size;
    if(subscription_cursor < latest_subscription){
        char* old_cursor = buffer_cursor;
        *idx = *subscription_cursor;
        my_var = &variable_table[*(subscription_cursor++)];
        *type_name = __get_type_enum_name(my_var->type);
        /* get variable size*/
        size = __get_type_enum_size(my_var->type);
        /* compute next cursor position*/
        buffer_cursor = buffer_cursor + size;
        if(old_cursor < debug_buffer + BUFFER_SIZE)
        {
            return old_cursor;
        }else{
            //printf("%%d > %%d\n", old_cursor - debug_buffer, BUFFER_SIZE);
            return NULL;
        } 
    }
    *idx = -1;
    *type_name = NULL;
    return NULL;
}

