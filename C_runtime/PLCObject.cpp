
#include <stdlib.h>

#include "Logging.hpp"

#include "PLCObject.hpp"

PLCObject::~PLCObject(void)
{
}

uint32_t PLCObject::AppendChunkToBlob(const binary_t * data, const binary_t * blobID, binary_t * newBlobID)
{
    return 0;
}

uint32_t PLCObject::GetLogMessage(uint8_t level, uint32_t msgID, log_message * message)
{
    return 0;
}

uint32_t PLCObject::GetPLCID(PSKID * plcID)
{
    return 0;
}

uint32_t PLCObject::GetPLCstatus(PLCstatus * status)
{
    return 0;
}

uint32_t PLCObject::GetTraceVariables(uint32_t debugToken, TraceVariables * traces)
{
    return 0;
}

uint32_t PLCObject::MatchMD5(const char * MD5, bool * match)
{
    return 0;
}

uint32_t PLCObject::NewPLC(const char * md5sum, const binary_t * plcObjectBlobID, const list_extra_file_1_t * extrafiles, bool * success)
{
    return 0;
}

uint32_t PLCObject::PurgeBlobs(void)
{
    return 0;
}

uint32_t PLCObject::RepairPLC(void)
{
    return 0;
}

uint32_t PLCObject::ResetLogCount(void)
{
    return 0;
}

uint32_t PLCObject::SeedBlob(const binary_t * seed, binary_t * blobID)
{
    return 0;
}

uint32_t PLCObject::SetTraceVariablesList(const list_trace_order_1_t * orders, uint32_t * debugtoken)
{
    return 0;
}

uint32_t PLCObject::StartPLC(void)
{
    return 0;
}

uint32_t PLCObject::StopPLC(bool * success)
{
    return 0;
}
