#include "iec_types_all.h"
#include "POUS.h"
#include "config.h"
#include "beremiz.h"

%(extern_variables_declarations)s

typedef const struct {
    void *ptr;
    __IEC_types_enum type;
    /* TODO : w/r buffer, flags, locks */
} hmi_tree_item_t;

static hmi_tree_item_t hmi_tree_item[] = {
%(variable_decl_array)s
};

int __init_svghmi()
{
    %(varinit)s
    return 0;
}

void __cleanup_svghmi()
{
}

void __retrieve_svghmi()
{
%(varret)s
}

void __publish_svghmi()
{
%(varpub)s
}

