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

void read_iterator(hmi_tree_item_t *dsc){
    /* todo */
}

void write_iterator(hmi_tree_item_t *dsc){
    /* todo */
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
        pthread_mutex_unlock(&rbuf_mutex);
    }
}

void __publish_svghmi()
{
    if(!pthread_mutex_lock(&wbuf_mutex)){
        pthread_mutex_unlock(&wbuf_mutex);
    }
}

