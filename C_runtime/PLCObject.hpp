/*
    Copyright Edouard TISSERANT 2024
    See COPYING for details
*/

#if !defined(_PLCObject_hpp_)
#define _PLCObject_hpp_

#include <map>
#include <vector>
#include <mutex>
#include <thread>
#include <array>
#include "Blob.hpp"

#include "erpc_PLCObject_interface.hpp"

#include "iec_types.h"

using namespace erpcShim;

#define MAX_ELEMENTS_TRACE 10

// #define LOG_DEBUG_ERPC

#define FOR_EACH_PLC_SYMBOLS_DO(ACTION) \
    ACTION(PLC_ID)\
    ACTION(startPLC)\
    ACTION(stopPLC)\
    ACTION(ResetDebugVariables)\
    ACTION(RegisterDebugVariable)\
    ACTION(FreeDebugData)\
    ACTION(GetDebugData)\
    ACTION(suspendDebug)\
    ACTION(resumeDebug)\
    ACTION(ResetLogCount)\
    ACTION(GetLogCount)\
    ACTION(LogMessage)\
    ACTION(GetLogMessage)\
    ACTION(PLC_GetTime)

extern "C" {   
    typedef struct s_PLCSyms{
        uint8_t *PLC_ID;
        int (*startPLC)(int argc,char **argv);
        int (*stopPLC)(void);
        void (*ResetDebugVariables)(void);
        int (*RegisterDebugVariable)(uint32_t idx, void* force, size_t force_size);
        void (*FreeDebugData)(void);
        int (*GetDebugData)(unsigned int *tick, unsigned int *size, void **buffer);
        int (*suspendDebug)(int disable);
        void (*resumeDebug)(void);
        void (*ResetLogCount)(void);
        uint32_t (*GetLogCount)(uint8_t level);
        int (*LogMessage)(uint8_t level, char* buf, uint32_t size);
        uint32_t (*GetLogMessage)(uint8_t level, uint32_t msgidx, char* buf, uint32_t max_size, uint32_t* tick, uint32_t* tv_sec, uint32_t* tv_nsec);
        void (*PLC_GetTime)(IEC_TIME *CURRENT_TIME);
    } PLCSyms;
}
class PLCObject : public BeremizPLCObjectService_interface
{
    public:

        PLCObject(void);
        virtual ~PLCObject(void);

        // ERPC interface
        uint32_t AppendChunkToBlob(const binary_t * data, const binary_t * blobID, binary_t * newBlobID);
        uint32_t GetLogMessage(uint8_t level, uint32_t msgID, log_message * message);
        uint32_t GetPLCID(PSKID * plcID);
        uint32_t GetPLCstatus(PLCstatus * status);
        uint32_t GetTraceVariables(uint32_t debugToken, TraceVariables * traces);
        uint32_t MatchMD5(const char * MD5, bool * match);
        uint32_t NewPLC(const char * md5sum, const binary_t * plcObjectBlobID, const list_extra_file_1_t * extrafiles, bool * success);
        uint32_t PurgeBlobs(void);
        uint32_t ResetLogCount(void);
        uint32_t SeedBlob(const binary_t * seed, binary_t * blobID);
        uint32_t SetTraceVariablesList(const list_trace_order_1_t * orders, int32_t * debugtoken);
        uint32_t ExtendedCall(const char * method, const binary_t * argument, binary_t * answer);

        // Public interface used by runtime
        uint32_t AutoLoad();
        uint32_t LogMessage(uint8_t level, std::string message);
        uint32_t StartPLC(void);
        uint32_t StopPLC(bool * success);
        uint32_t RepairPLC(void);
        void SetPLCstatusEmpty();

    protected:

        // used to monitor presence de beremiz debugger
        IEC_TIMESPEC last_uploaded_trace;

        // A map of all the blobs
        std::map<std::vector<uint8_t>, Blob*> m_mapBlobIDToBlob;

        // Symbols resolved from the PLC object
        PLCSyms m_PLCSyms = {0};

        // argc and argv for the PLC object
        int m_argc;
        char ** m_argv;

        // PLC status
        PLCstatus m_status;

        // PSK
        std::string m_PSK_ID;
        std::string m_PSK_secret;

        // Debug token, used for consistency check of traces
        uint32_t m_debugToken;

        // Trace double buffer
        std::array <trace_sample, MAX_ELEMENTS_TRACE> m_traces;
        uint8_t count_array = 0;
        uint8_t tail_array = 0;
        uint8_t head_array = 0;
        uint32_t m_trace_byte_size;

        virtual uint32_t LoadPLC(void) = 0;
        virtual uint32_t UnLoadPLC(void) = 0;
        virtual uint32_t PurgePLC(void) = 0;
        virtual uint32_t SaveBlobs(
            const char *md5sum,
            const binary_t *plcObjectBlobID,
            const list_extra_file_1_t *extrafiles) = 0;
        virtual void EnsureDebugThread(void) = 0;
        virtual void StopDebugThread(void) = 0;
        virtual void TraceMutexLock(void) = 0;
        virtual void TraceMutexUnlock(void) = 0;
        virtual void PLCLibMutexLock(void) = 0;
        virtual void PLCLibMutexUnlock(void) = 0;
        virtual Blob *NewBlob() = 0;
        virtual void DeleteBlob(Blob *blob) = 0;
        virtual std::string GetLastTransferredPLC_MD5(void) = 0;
        
        virtual void GetLogCounts(void);

        void PurgeTraceBuffer(void);
        void TraceThreadProc(void);

};

#endif
