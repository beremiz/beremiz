#include <pthread.h>
#include "iec_types_all.h"
#include "POUS.h"
#include "config.h"
#include "beremiz.h"

#define DEFAULT_REFRESH_PERIOD_MS 100
#define HMI_BUFFER_SIZE %(buffer_size)d

/* PLC reads from that buffer */
static char rbuf[HMI_BUFFER_SIZE];

/* PLC writes to that buffer */
static char wbuf[HMI_BUFFER_SIZE];

%(extern_variables_declarations)s

#define ticktime_ns %(PLC_ticktime)d
uint16_t ticktime_ms = (ticktime_ns>1000000)?
                     ticktime_ns/1000000:
                     1;

typedef enum {
    buf_free = 0,
    buf_set,
    buf_tosend
} buf_state_t;

int global_write_dirty = 0;

typedef struct {
    void *ptr;
    __IEC_types_enum type;
    uint32_t buf_index;

    /* publish/write/send */
    long wlock;
    /* zero means not subscribed */
    uint16_t refresh_period_ms;
    uint16_t age_ms;

    buf_state_t wstate;

    /* retrieve/read/recv */
    long rlock;
    buf_state_t rstate;

} hmi_tree_item_t;

static hmi_tree_item_t hmi_tree_item[] = {
%(variable_decl_array)s
};

typedef void(*hmi_tree_iterator)(hmi_tree_item_t*);
void traverse_hmi_tree(hmi_tree_iterator fp)
{
    unsigned int i;
    for(i = 0; i < sizeof(hmi_tree_item)/sizeof(hmi_tree_item_t); i++){
        hmi_tree_item_t *dsc = &hmi_tree_item[i];
        if(dsc->type != UNKNOWN_ENUM) 
            (*fp)(dsc);
    }
}

#define __Unpack_desc_type hmi_tree_item_t

%(var_access_code)s

void write_iterator(hmi_tree_item_t *dsc)
{
    void *dest_p = &wbuf[dsc->buf_index];
    void *real_value_p = NULL;
    char flags = 0;

    void *visible_value_p = UnpackVar(dsc, &real_value_p, &flags);

    /* Try take lock */
    long was_locked = AtomicCompareExchange(&dsc->wlock, 0, 1);

    if(was_locked) {
        /* was locked. give up*/
        return;
    }

    if(dsc->wstate == buf_set){
        /* if being subscribed */
        if(dsc->refresh_period_ms){
            if(dsc->age_ms + ticktime_ms < dsc->refresh_period_ms){
                dsc->age_ms += ticktime_ms;
            }else{
                dsc->wstate = buf_tosend;
            }
        }
    }
    
    /* if new value differs from previous one */
    if(memcmp(dest_p, visible_value_p, __get_type_enum_size(dsc->type)) != 0){
        /* copy and flag as set */
        memcpy(dest_p, visible_value_p, __get_type_enum_size(dsc->type));
        if(dsc->wstate == buf_free) {
            dsc->wstate = buf_set;
            dsc->age_ms = 0;
        }
        global_write_dirty = 1;
    }

    /* unlock - use AtomicComparExchange to have memory barrier */
    AtomicCompareExchange(&dsc->wlock, 1, 0);
}

struct timespec sending_now;
struct timespec next_sending;
void send_iterator(hmi_tree_item_t *dsc)
{
    while(AtomicCompareExchange(&dsc->wlock, 0, 1)) sched_yield();

    // check for variable being modified
    if(dsc->wstate == buf_tosend){
        // send 

        // TODO pack data in buffer

        dsc->wstate = buf_free;
    }

    AtomicCompareExchange(&dsc->wlock, 1, 0);
}

void read_iterator(hmi_tree_item_t *dsc)
{
    void *src_p = &rbuf[dsc->buf_index];
    void *real_value_p = NULL;
    char flags = 0;

    void *visible_value_p = UnpackVar(dsc, &real_value_p, &flags);


    memcpy(visible_value_p, src_p, __get_type_enum_size(dsc->type));
}

static pthread_cond_t UART_WakeCond = PTHREAD_COND_INITIALIZER;
static pthread_mutex_t UART_WakeCondLock = PTHREAD_MUTEX_INITIALIZER;

int __init_svghmi()
{
    bzero(rbuf,sizeof(rbuf));
    bzero(wbuf,sizeof(wbuf));
    continue_collect = 1;

    return 0;
}

void __cleanup_svghmi()
{
    pthread_mutex_lock(&UART_WakeCondLock);
    continue_collect = 0;
    pthread_cond_signal(&UART_WakeCond);
    pthread_mutex_unlock(&UART_WakeCondLock);
}

void __retrieve_svghmi()
{
    traverse_hmi_tree(read_iterator);
}

void __publish_svghmi()
{
    global_write_dirty = 0;
    traverse_hmi_tree(write_iterator);
    if(global_write_dirty) {
        pthread_cond_signal(&UART_WakeCond);
    }
}

/* PYTHON CALLS */
int svghmi_send_collect(uint32_t *size, void *ptr){

    pthread_mutex_lock(&UART_WakeCondLock);
    do_collect = continue_collect;
    if do_collect;
        pthread_cond_wait(&UART_WakeCond, &UART_WakeCondLock);
        do_collect = continue_collect;
    pthread_mutex_unlock(&UART_WakeCondLock);


    if(do_collect) {
        traverse_hmi_tree(send_iterator);
        /* TODO set ptr and size to something  */
        return 0;
    }
    else
    {
        return EINTR;
    }
}

int svghmi_recv_dispatch(uint32_t size, void* ptr){
    /* TODO something with ptr and size
        - subscribe
         or
        - spread values
    */
}

