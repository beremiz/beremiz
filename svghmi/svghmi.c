#include <pthread.h>
#include "iec_types_all.h"
#include "POUS.h"
#include "config.h"
#include "beremiz.h"

#define HMI_BUFFER_SIZE %(buffer_size)d

/* PLC reads from that buffer */
static char rbuf[HMI_BUFFER_SIZE];

/* PLC writes to that buffer */
static char wbuf[HMI_BUFFER_SIZE];

static pthread_mutex_t wbuf_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t rbuf_mutex = PTHREAD_MUTEX_INITIALIZER;

%(extern_variables_declarations)s

typedef const struct {
    void *ptr;
    __IEC_types_enum type;
    uint32_t buf_index;
    uint32_t flags;
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

/* TODO : deduplicate that code with plc_debug.c */

#define __Unpack_case_t(TYPENAME) \
        case TYPENAME##_ENUM :\
            *flags = ((__IEC_##TYPENAME##_t *)varp)->flags;\
            forced_value_p = *real_value_p = &((__IEC_##TYPENAME##_t *)varp)->value;\
            break;

#define __Unpack_case_p(TYPENAME)\
        case TYPENAME##_O_ENUM :\
            *flags = __IEC_OUTPUT_FLAG;\
        case TYPENAME##_P_ENUM :\
            *flags |= ((__IEC_##TYPENAME##_p *)varp)->flags;\
            *real_value_p = ((__IEC_##TYPENAME##_p *)varp)->value;\
            forced_value_p = &((__IEC_##TYPENAME##_p *)varp)->fvalue;\
            break;

static void* UnpackVar(hmi_tree_item_t *dsc, void **real_value_p, char *flags)
{
    void *varp = dsc->ptr;
    void *forced_value_p = NULL;
    *flags = 0;
    /* find data to copy*/
    switch(dsc->type){
        __ANY(__Unpack_case_t)
        __ANY(__Unpack_case_p)
    default:
        break;
    }
    if (*flags & __IEC_FORCE_FLAG)
        return forced_value_p;
    return *real_value_p;
}

void write_iterator(hmi_tree_item_t *dsc)
{
    void *dest_p = &wbuf[dsc->buf_index];
    void *real_value_p = NULL;
    char flags = 0;

    void *visible_value_p = UnpackVar(dsc, &real_value_p, &flags);

    memcpy(dest_p, visible_value_p, __get_type_enum_size(dsc->type));
}

void read_iterator(hmi_tree_item_t *dsc)
{
    void *src_p = &rbuf[dsc->buf_index];
    void *real_value_p = NULL;
    char flags = 0;

    void *visible_value_p = UnpackVar(dsc, &real_value_p, &flags);

    memcpy(visible_value_p, src_p, __get_type_enum_size(dsc->type));
}

int __init_svghmi()
{
    bzero(rbuf,sizeof(rbuf));
    bzero(wbuf,sizeof(wbuf));

    return 0;
}

void __cleanup_svghmi()
{
}

void __retrieve_svghmi()
{
    if(!pthread_mutex_lock(&rbuf_mutex)){
        traverse_hmi_tree(read_iterator);
        pthread_mutex_unlock(&rbuf_mutex);
    }
}

void __publish_svghmi()
{
    if(!pthread_mutex_lock(&wbuf_mutex)){
        pthread_mutex_unlock(&wbuf_mutex);
    }
}

