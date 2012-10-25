#include "iec_types_all.h"

#define FREE 0
#define ACQUIRED 1
#define ANSWERED 2

long SDOLock = FREE;
extern long AtomicCompareExchange(long* atomicvar,long compared, long exchange);

int AcquireSDOLock() {
	return AtomicCompareExchange(&SDOLock, FREE, ACQUIRED) == FREE;
}

void SDOAnswered() {
	AtomicCompareExchange(&SDOLock, ACQUIRED, ANSWERED);
}

int HasAnswer() {
	return SDOLock == ANSWERED;
}

void ReleaseSDOLock() {
	AtomicCompareExchange(&SDOLock, ANSWERED, FREE);
}

int __init_etherlab_ext()
{
    SDOLock = FREE;
    return 0;
}

void __cleanup_etherlab_ext()
{
}

void __retrieve_etherlab_ext()
{
}

void __publish_etherlab_ext()
{
}
