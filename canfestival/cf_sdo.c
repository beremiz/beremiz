/*

SDO client glue between the PLC and the CanFestival stack.

Copyright (C) 2026: Edouard TISSERANT

See COPYING file for copyrights details.

LOCKING : the function block bodies calling into this file run from
config_run__(), that is between __retrieve_<canfestival root>() which takes the
CanFestival mutex and __publish_<canfestival root>() which releases it. The
stack is therefore already locked, and EnterMutex() must NOT be called here.

A consequence is that the CanFestival timer thread, which dispatches received
SDO responses, only gets to run between PLC cycles. Every transfer thus spans
at least two cycles, which is what the function block state machines assume.

*/

#include "canfestival.h"
#include "sdo.h"

/* non static in src/sdo.c, but not declared by sdo.h */
extern UNS8 GetSDOClientFromNodeId(CO_Data* d, UNS8 nodeId);

/* One CANopen network per CanFestival node confnode, identified by its IEC
 * channel. Filled in by the generated runtime glue at init. */
#define CF_MAX_NETWORKS 16

static CO_Data *cf_networks[CF_MAX_NETWORKS];

void __CanOpen_RegisterNetwork(int network, CO_Data *d)
{
    if (network >= 0 && network < CF_MAX_NETWORKS)
        cf_networks[network] = d;
}

static CO_Data *GetNetwork(int network)
{
    if (network < 0 || network >= CF_MAX_NETWORKS)
        return NULL;
    return cf_networks[network];
}

/* Start reading an object of a distant node.
 * @return 0 when the request was sent, -1 otherwise */
int __CanOpen_SDORead(int network, UNS8 nodeid, UNS16 index, UNS8 subindex)
{
    CO_Data *d = GetNetwork(network);

    if (d == NULL)
        return -1;

    return readNetworkDict(d, nodeid, index, subindex, 0, 0) == 0 ? 0 : -1;
}

/* Start writing an object of a distant node. size is 1, 2 or 4 bytes.
 * writeNetworkDict copies the value before returning, so passing the address
 * of a caller local is safe.
 * @return 0 when the request was sent, -1 otherwise */
int __CanOpen_SDOWrite(int network, UNS8 nodeid, UNS16 index, UNS8 subindex,
                       UNS8 size, UNS32 value)
{
    CO_Data *d = GetNetwork(network);

    if (d == NULL)
        return -1;

    return writeNetworkDict(d, nodeid, index, subindex,
                            (UNS32)size, 0, &value, 0) == 0 ? 0 : -1;
}

/* Poll a transfer started by one of the two above.
 * @param isread non zero to poll a read, zero to poll a write
 * @return 1 when done, 0 while still in progress, -1 on failure */
int __CanOpen_SDOResult(int network, UNS8 nodeid, int isread,
                        UNS32 *value, UNS32 *abortcode)
{
    CO_Data *d = GetNetwork(network);
    UNS32 size = sizeof(UNS32);
    UNS8 res;

    *value = 0;
    *abortcode = 0;

    if (d == NULL)
        return -1;

    if (isread)
        res = getReadResultNetworkDict(d, nodeid, value, &size, abortcode);
    else
        res = getWriteResultNetworkDict(d, nodeid, abortcode);

    switch (res) {
        case SDO_FINISHED:
            /* both getters already reset the line */
            return 1;
        case SDO_UPLOAD_IN_PROGRESS:
        case SDO_DOWNLOAD_IN_PROGRESS:
            return 0;
        default:
            /* SDO_ABORTED_RCV, SDO_ABORTED_INTERNAL (which is also how a
             * timeout shows up), SDO_PROVIDED_BUFFER_TOO_SMALL, ... The line
             * stays allocated in those cases, free it. */
            closeSDOtransfer(d, GetSDOClientFromNodeId(d, nodeid), SDO_CLIENT);
            return -1;
    }
}

/* Give up on a transfer, so that a new one can be started for that node. */
void __CanOpen_SDOAbort(int network, UNS8 nodeid)
{
    CO_Data *d = GetNetwork(network);

    if (d != NULL)
        closeSDOtransfer(d, GetSDOClientFromNodeId(d, nodeid), SDO_CLIENT);
}
