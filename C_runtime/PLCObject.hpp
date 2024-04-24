/*
    Copyright Edouard TISSERANT 2024
    See COPYING for details
*/

#if !defined(_PLCObject_hpp_)
#define _PLCObject_hpp_

#include "erpc_PLCObject_interface.hpp"

using namespace erpcShim;

class PLCObject : public BeremizPLCObjectService_interface
{
    public:

        ~PLCObject(void);

        virtual uint32_t AppendChunkToBlob(const binary_t * data, const binary_t * blobID, binary_t * newBlobID);
        virtual uint32_t GetLogMessage(uint8_t level, uint32_t msgID, log_message * message);
        virtual uint32_t GetPLCID(PSKID * plcID);
        virtual uint32_t GetPLCstatus(PLCstatus * status);
        virtual uint32_t GetTraceVariables(uint32_t debugToken, TraceVariables * traces);
        virtual uint32_t MatchMD5(const char * MD5, bool * match);
        virtual uint32_t NewPLC(const char * md5sum, const binary_t * plcObjectBlobID, const list_extra_file_1_t * extrafiles, bool * success);
        virtual uint32_t PurgeBlobs(void);
        virtual uint32_t RepairPLC(void);
        virtual uint32_t ResetLogCount(void);
        virtual uint32_t SeedBlob(const binary_t * seed, binary_t * blobID);
        virtual uint32_t SetTraceVariablesList(const list_trace_order_1_t * orders, uint32_t * debugtoken);
        virtual uint32_t StartPLC(void);
        virtual uint32_t StopPLC(bool * success);
};

#endif