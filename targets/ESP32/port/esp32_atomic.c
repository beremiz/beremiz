#include <stdint.h>
#include <stdbool.h>

uint32_t AtomicCompareExchange(uint32_t *addr,
                               uint32_t compare,
                               uint32_t exchange)
{
    __atomic_compare_exchange_n(
        addr,
        &compare,
        exchange,
        false,
        __ATOMIC_SEQ_CST,
        __ATOMIC_SEQ_CST
    );
    return compare;
}

