#include <pthread.h>
#include <errno.h>
#include "iec_types_all.h"
#include "POUS.h"
#include "config.h"
#include "beremiz.h"

#define DEFAULT_REFRESH_PERIOD_MS 100
#define HMI_BUFFER_SIZE %(buffer_size)d
#define HMI_ITEM_COUNT %(item_count)d
#define HMI_HASH_SIZE 8
#define MAX_CONNECTIONS %(max_connections)d

static uint8_t hmi_hash[HMI_HASH_SIZE] = {%(hmi_hash_ints)s};

/* PLC reads from that buffer */
static char rbuf[HMI_BUFFER_SIZE];

/* PLC writes to that buffer */
static char wbuf[HMI_BUFFER_SIZE];

/* TODO change that in case of multiclient... */
/* worst biggest send buffer. FIXME : use dynamic alloc ? */
static char sbuf[HMI_HASH_SIZE +  HMI_BUFFER_SIZE + (HMI_ITEM_COUNT * sizeof(uint32_t))];
static unsigned int sbufidx;

%(extern_variables_declarations)s

#define ticktime_ns %(PLC_ticktime)d
static uint16_t ticktime_ms = (ticktime_ns>1000000)?
                     ticktime_ns/1000000:
                     1;

typedef enum {
    buf_free = 0,
    buf_new,
    buf_set,
    buf_tosend
} buf_state_t;

static int global_write_dirty = 0;
static long hmitree_rlock = 0;
static long hmitree_wlock = 0;

typedef struct {
    void *ptr;
    __IEC_types_enum type;
    uint32_t buf_index;

    /* publish/write/send */
    buf_state_t wstate[MAX_CONNECTIONS];

    /* zero means not subscribed */
    uint16_t refresh_period_ms[MAX_CONNECTIONS];
    uint16_t age_ms[MAX_CONNECTIONS];

    /* retrieve/read/recv */
    buf_state_t rstate;

} hmi_tree_item_t;

static hmi_tree_item_t hmi_tree_item[] = {
%(variable_decl_array)s
};

typedef int(*hmi_tree_iterator)(uint32_t, hmi_tree_item_t*);
static int traverse_hmi_tree(hmi_tree_iterator fp)
{
    unsigned int i;
    for(i = 0; i < sizeof(hmi_tree_item)/sizeof(hmi_tree_item_t); i++){
        hmi_tree_item_t *dsc = &hmi_tree_item[i];
        int res = (*fp)(i, dsc);
        if(res != 0){
            return res;
        }
    }
    return 0;
}

#define __Unpack_desc_type hmi_tree_item_t

%(var_access_code)s

static int write_iterator(uint32_t index, hmi_tree_item_t *dsc)
{
    {
        uint32_t session_index = 0;
        int value_changed = 0;
        void *dest_p = NULL;
        void *real_value_p = NULL;
        void *visible_value_p = NULL;
        USINT sz = 0;
        while(session_index < MAX_CONNECTIONS) {
            if(dsc->wstate[session_index] == buf_set){
                /* if being subscribed */
                if(dsc->refresh_period_ms[session_index]){
                    if(dsc->age_ms[session_index] + ticktime_ms < dsc->refresh_period_ms[session_index]){
                        dsc->age_ms[session_index] += ticktime_ms;
                    }else{
                        dsc->wstate[session_index] = buf_tosend;
                        global_write_dirty = 1;
                    }
                }
            }

            /* variable is sample only if just subscribed
               or already subscribed and having value change */
            int do_sample = 0;
            int just_subscribed = dsc->wstate[session_index] == buf_new;
            if(!just_subscribed){
                int already_subscribed = dsc->refresh_period_ms[session_index] > 0;
                if(already_subscribed){
                    if(!value_changed){
                        if(!visible_value_p){
                            char flags = 0;
                            visible_value_p = UnpackVar(dsc, &real_value_p, &flags);
                            if(__Is_a_string(dsc)){
                                sz = ((STRING*)visible_value_p)->len + 1;
                            } else {
                                sz = __get_type_enum_size(dsc->type);
                            }
                            dest_p = &wbuf[dsc->buf_index];
                        }
                        value_changed = memcmp(dest_p, visible_value_p, sz) != 0;
                        do_sample = value_changed;
                    }else{
                        do_sample = 1;
                    }
                }
            } else {
                do_sample = 1;
            }


            if(do_sample){
                if(dsc->wstate[session_index] != buf_set && dsc->wstate[session_index] != buf_tosend) {
                    if(dsc->wstate[session_index] == buf_new \
                       || ticktime_ms > dsc->refresh_period_ms[session_index]){
                        dsc->wstate[session_index] = buf_tosend;
                        global_write_dirty = 1;
                    } else {
                        dsc->wstate[session_index] = buf_set;
                    }
                    dsc->age_ms[session_index] = 0;
                }
            }

            session_index++;
        }
        /* copy value if changed (and subscribed) */
        if(value_changed)
            memcpy(dest_p, visible_value_p, sz);
    }
    // else ... : PLC can't wait, variable will be updated next turn
    return 0;
}

static uint32_t send_session_index;
static int send_iterator(uint32_t index, hmi_tree_item_t *dsc)
{
    if(dsc->wstate[send_session_index] == buf_tosend)
    {
        uint32_t sz = __get_type_enum_size(dsc->type);
        if(sbufidx + sizeof(uint32_t) + sz <=  sizeof(sbuf))
        {
            void *src_p = &wbuf[dsc->buf_index];
            void *dst_p = &sbuf[sbufidx];
            if(__Is_a_string(dsc)){
                sz = ((STRING*)src_p)->len + 1;
            }
            /* TODO : force into little endian */
            memcpy(dst_p, &index, sizeof(uint32_t));
            memcpy(dst_p + sizeof(uint32_t), src_p, sz);
            dsc->wstate[send_session_index] = buf_free;
            sbufidx += sizeof(uint32_t) /* index */ + sz;
        }
        else
        {
            printf("BUG!!! %%d + %%ld + %%d >  %%ld \n", sbufidx, sizeof(uint32_t), sz,  sizeof(sbuf));
            return EOVERFLOW;
        }
    }

    return 0;
}

static int read_iterator(uint32_t index, hmi_tree_item_t *dsc)
{
    if(dsc->rstate == buf_set)
    {
        void *src_p = &rbuf[dsc->buf_index];
        void *real_value_p = NULL;
        char flags = 0;
        void *visible_value_p = UnpackVar(dsc, &real_value_p, &flags);
        memcpy(real_value_p, src_p, __get_type_enum_size(dsc->type));
        dsc->rstate = buf_free;
    }
    return 0;
}

void update_refresh_period(hmi_tree_item_t *dsc, uint32_t session_index, uint16_t refresh_period_ms)
{
    if(refresh_period_ms) {
        if(!dsc->refresh_period_ms[session_index])
        {
            dsc->wstate[session_index] = buf_new;
        }
    } else {
        dsc->wstate[session_index] = buf_free;
    }
    dsc->refresh_period_ms[session_index] = refresh_period_ms;
}

static uint32_t reset_session_index;
static int reset_iterator(uint32_t index, hmi_tree_item_t *dsc)
{
    update_refresh_period(dsc, reset_session_index, 0);
    return 0;
}

static void *svghmi_handle;

void SVGHMI_SuspendFromPythonThread(void)
{
    wait_RT_to_nRT_signal(svghmi_handle);
}

void SVGHMI_WakeupFromRTThread(void)
{
    unblock_RT_to_nRT_signal(svghmi_handle);
}

int svghmi_continue_collect;

int __init_svghmi()
{
    memset(rbuf,0,sizeof(rbuf));
    memset(wbuf,0,sizeof(wbuf));

    svghmi_continue_collect = 1;

    /* create svghmi_pipe */
    svghmi_handle = create_RT_to_nRT_signal("SVGHMI_pipe");

    if(!svghmi_handle) 
        return 1;

    return 0;
}

void __cleanup_svghmi()
{
    svghmi_continue_collect = 0;
    SVGHMI_WakeupFromRTThread();
    delete_RT_to_nRT_signal(svghmi_handle);
}

void __retrieve_svghmi()
{
    if(AtomicCompareExchange(&hmitree_rlock, 0, 1) == 0) {
        traverse_hmi_tree(read_iterator);
        AtomicCompareExchange(&hmitree_rlock, 1, 0);
    }
}

void __publish_svghmi()
{
    global_write_dirty = 0;
    if(AtomicCompareExchange(&hmitree_wlock, 0, 1) == 0) {
        traverse_hmi_tree(write_iterator);
        AtomicCompareExchange(&hmitree_wlock, 1, 0);
    }
    if(global_write_dirty) {
        SVGHMI_WakeupFromRTThread();
    }
}

/* PYTHON CALLS */
int svghmi_wait(void){

    SVGHMI_SuspendFromPythonThread();
}

int svghmi_send_collect(uint32_t session_index, uint32_t *size, char **ptr){

    if(svghmi_continue_collect) {
        int res;
        sbufidx = HMI_HASH_SIZE;
        send_session_index = session_index;

        while(AtomicCompareExchange(&hmitree_wlock, 0, 1)){
            nRT_reschedule();
        }

        if((res = traverse_hmi_tree(send_iterator)) == 0)
        {
            if(sbufidx > HMI_HASH_SIZE){
                memcpy(&sbuf[0], &hmi_hash[0], HMI_HASH_SIZE);
                *ptr = &sbuf[0];
                *size = sbufidx;
                AtomicCompareExchange(&hmitree_wlock, 1, 0);
                return 0;
            }
            AtomicCompareExchange(&hmitree_wlock, 1, 0);
            return ENODATA;
        }
        // printf("collected BAD result %%d\n", res);
        AtomicCompareExchange(&hmitree_wlock, 1, 0);
        return res;
    }
    else
    {
        return EINTR;
    }
}

typedef enum {
    unset = -1,
    setval = 0,
    reset = 1,
    subscribe = 2
} cmd_from_JS;

int svghmi_reset(uint32_t session_index){
    reset_session_index = session_index;
    traverse_hmi_tree(reset_iterator);
    return 1;
}

// Returns :
//   0 is OK, <0 is error, 1 is heartbeat
int svghmi_recv_dispatch(uint32_t session_index, uint32_t size, const uint8_t *ptr){
    const uint8_t* cursor = ptr + HMI_HASH_SIZE;
    const uint8_t* end = ptr + size;

    int was_hearbeat = 0;

    /* match hmitree fingerprint */
    if(size <= HMI_HASH_SIZE || memcmp(ptr, hmi_hash, HMI_HASH_SIZE) != 0)
    {
        printf("svghmi_recv_dispatch MISMATCH !!\n");
        return -EINVAL;
    }

    int ret;
    int got_wlock = 0;
    int got_rlock = 0;
    cmd_from_JS cmd_old = unset;
    cmd_from_JS cmd = unset;

    while(cursor < end)
    {
        uint32_t progress;

        cmd_old = cmd;
        cmd = *(cursor++);

        if(cmd_old != cmd){
            if(got_wlock){
                AtomicCompareExchange(&hmitree_wlock, 1, 0);
                got_wlock = 0;
            }
            if(got_rlock){
                AtomicCompareExchange(&hmitree_rlock, 1, 0);
                got_rlock = 0;
            }
        }
        switch(cmd)
        {
            case setval:
            {
                uint32_t index = *(uint32_t*)(cursor);
                uint8_t const *valptr = cursor + sizeof(uint32_t);

                if(index == heartbeat_index)
                    was_hearbeat = 1;

                if(index < HMI_ITEM_COUNT)
                {
                    hmi_tree_item_t *dsc = &hmi_tree_item[index];
                    void *real_value_p = NULL;
                    char flags = 0;
                    void *visible_value_p = UnpackVar(dsc, &real_value_p, &flags);
                    void *dst_p = &rbuf[dsc->buf_index];
                    uint32_t sz = __get_type_enum_size(dsc->type);

                    if(__Is_a_string(dsc)){
                        sz = ((STRING*)valptr)->len + 1;
                    }

                    if((valptr + sz) <= end)
                    {
                        // rescheduling spinlock until free
                        if(!got_rlock){
                            while(AtomicCompareExchange(&hmitree_rlock, 0, 1)){
                                nRT_reschedule();
                            }
                            got_rlock=1;
                        }

                        memcpy(dst_p, valptr, sz);
                        dsc->rstate = buf_set;

                        progress = sz + sizeof(uint32_t) /* index */;
                    }
                    else
                    {
                        ret = -EINVAL;
                        goto exit_free;
                    }
                }
                else
                {
                    ret = -EINVAL;
                    goto exit_free;
                }
            }
            break;

            case reset:
            {
                progress = 0;
                reset_session_index = session_index;
                if(!got_wlock){
                    while(AtomicCompareExchange(&hmitree_wlock, 0, 1)){
                        nRT_reschedule();
                    }
                    got_wlock = 1;
                }
                traverse_hmi_tree(reset_iterator);
            }
            break;

            case subscribe:
            {
                uint32_t index = *(uint32_t*)(cursor);
                uint16_t refresh_period_ms = *(uint32_t*)(cursor + sizeof(uint32_t));

                if(index < HMI_ITEM_COUNT)
                {
                    if(!got_wlock){
                        while(AtomicCompareExchange(&hmitree_wlock, 0, 1)){
                            nRT_reschedule();
                        }
                        got_wlock = 1;
                    }
                    hmi_tree_item_t *dsc = &hmi_tree_item[index];
                    update_refresh_period(dsc, session_index, refresh_period_ms);
                }
                else
                {
                    ret = -EINVAL;
                    goto exit_free;
                }

                progress = sizeof(uint32_t) /* index */ +
                           sizeof(uint16_t) /* refresh period */;
            }
            break;
            default:
                printf("svghmi_recv_dispatch unknown %%d\n",cmd);

        }
        cursor += progress;
    }
    ret = was_hearbeat;

exit_free:
    if(got_wlock){
        AtomicCompareExchange(&hmitree_wlock, 1, 0);
        got_wlock = 0;
    }
    if(got_rlock){
        AtomicCompareExchange(&hmitree_rlock, 1, 0);
        got_rlock = 0;
    }
    return ret;
}

