#include <string.h>
#include <stdio.h>
#include <vector>

#include "PLCObject.hpp"
#include "erpc_port.h"

#include "beremiz.h"

// File name of the last transferred PLC md5 hex digest
// with typo in the name, for compatibility with Python runtime
#define LastTransferredPLC "lasttransferedPLC.md5"

// File name of the extra files list
#define ExtraFilesList "extra_files.txt"
#define MAX_ERPC_PAYLOAD_SIZE 4096
#define DEBUGGER_TIMEOUT_S 3

PLCObject::PLCObject(void)
{
    m_status.PLCstatus = Empty;
    m_debugToken = 0;
    m_argc = 0;
    m_argv = NULL;
    m_PSK_ID = "";
    m_PSK_secret = "";
    m_trace_byte_size = 0;
}

PLCObject::~PLCObject(void)
{
}

uint32_t PLCObject::AppendChunkToBlob(
    const binary_t *data, const binary_t *blobID, binary_t *newBlobID)
{
    // Append data to blob with given blobID
    // Output new blob's md5 into newBlobID
    // Return 0 if success
    newBlobID->data = (uint8_t *)erpc_malloc(MD5::digestsize);
    if (newBlobID->data == NULL)
    {
        return ENOMEM;
    }

    std::vector<uint8_t> k(blobID->data, blobID->data + blobID->dataLength);

    auto nh = m_mapBlobIDToBlob.extract(k);
    if (nh.empty())
    {
        return ENOENT;
    }

    Blob *blob = nh.mapped();

    uint32_t res = blob->appendChunk(data->data, data->dataLength);
    if (res != 0)
    {
        return res;
    }

    MD5::digest_t digest = blob->digest();

    std::vector<uint8_t> nk((uint8_t*)digest.data, (uint8_t*)digest.data + MD5::digestsize);
    nh.key() = nk;

    m_mapBlobIDToBlob.insert(std::move(nh));

    memcpy(newBlobID->data, digest.data, MD5::digestsize);
    newBlobID->dataLength = MD5::digestsize;

    return 0;
}

uint32_t PLCObject::AutoLoad()
{
    // Load PLC object
    LogMessage(LOG_INFO, "Autoload PLC");

    uint32_t res = LoadPLC();
    if (res != 0)
    {
        m_status.PLCstatus = Empty;
        return res;
    }
    m_status.PLCstatus = Stopped;

    // Start PLC object
    res = StartPLC();
    if (res != 0)
    {
        return res;
    }

    return 0;
}


#define LOG_READ_BUFFER_SIZE (1 << 10) // 1KB

uint32_t PLCObject::GetLogMessage(
    uint8_t level, uint32_t msgID, log_message *message)
{
    char buf[LOG_READ_BUFFER_SIZE];
    uint32_t tick = 0;
    uint32_t tv_sec = 0;
    uint32_t tv_nsec = 0;

    uint32_t resultLen = 0;
    if(m_PLCSyms.GetLogMessage){
        resultLen = m_PLCSyms.GetLogMessage(
            level, msgID, buf, LOG_READ_BUFFER_SIZE - 1,
            &tick, &tv_sec, &tv_nsec);
    }

    // Get log message with given msgID
    message->msg = (char *)erpc_malloc(resultLen + 1);
    if (message->msg == NULL)
    {
        return ENOMEM;
    }
    // Copy the log message into eRPC message
    memcpy(message->msg, buf, resultLen);
    message->msg[resultLen] = '\0';

    message->tick = tick;
    message->sec = tv_sec;
    message->nsec = tv_nsec;

    return 0;
}

uint32_t PLCObject::GetPLCID(PSKID *plcID)
{
    //Start of connection between plc and beremiz

    // Get PSK ID
    plcID->ID = (char *)erpc_malloc(m_PSK_ID.size() + 1);
    if (plcID->ID == NULL)
    {
        return ENOMEM;
    }
    memcpy(plcID->ID, m_PSK_ID.c_str(), m_PSK_ID.size());
    plcID->ID[m_PSK_ID.size()] = '\0';

    // Get PSK secret
    plcID->PSK = (char *)erpc_malloc(m_PSK_secret.size() + 1);
    if (plcID->PSK == NULL)
    {
        erpc_free(plcID->ID);
        return ENOMEM;
    }
    memcpy(plcID->PSK, m_PSK_secret.c_str(), m_PSK_secret.size());
    plcID->PSK[m_PSK_secret.size()] = '\0';

    return 0;
}


void PLCObject::SetPLCstatusEmpty()
{
    m_status.PLCstatus = Empty;
}

void PLCObject::GetLogCounts(void)
{
    if(m_status.PLCstatus == Empty){        
        for(int lvl = 0; lvl < 4; lvl++){
            m_status.logcounts[lvl] = 0;
        }
    } else {
        // Get log counts
        for(int lvl = 0; lvl < 4; lvl++){
            m_status.logcounts[lvl] = m_PLCSyms.GetLogCount(lvl);
        }
    }
}


uint32_t PLCObject::GetPLCstatus(PLCstatus *status)
{
    GetLogCounts();
    // Get PLC status
    *status = m_status;
    return 0;
}



uint32_t PLCObject::GetTraceVariables(
    uint32_t debugToken, TraceVariables *traces)
{
    if (m_status.PLCstatus == Started)
    {
        m_PLCSyms.PLC_GetTime(&last_uploaded_trace);
    }

    // Check if there are any traces
    TraceMutexLock();
    // Allocate memory for traces
    traces->traces.elements = (trace_sample *)erpc_malloc(count_array * sizeof(trace_sample));

    if(debugToken != m_debugToken)
    {
        LogMessage(LOG_CRITICAL, "Debug tokens desync");
        traces->PLCstatus = Broken;
        traces->traces.elementsCount = 0;
        TraceMutexUnlock();
        return 0;
    }

    if(count_array > 0)
    {

        if (traces->traces.elements == NULL) {
            traces->traces.elementsCount = 0;
            TraceMutexUnlock();
            return 0;
        }

        if (head_array > tail_array) {
            // Data is already linear
            memcpy(traces->traces.elements, &m_traces[tail_array], count_array * sizeof(trace_sample));
        }
        else
        {
            memcpy(traces->traces.elements, &m_traces[tail_array], (MAX_ELEMENTS_TRACE - tail_array) * sizeof(trace_sample));
            memcpy(traces->traces.elements + (MAX_ELEMENTS_TRACE - tail_array), &m_traces[0], head_array * sizeof(trace_sample));

        }

        // note that the data is not erpc_mallocd here, it is meant to be erpc_mallocd by eRPC server code
    }
     TraceMutexUnlock();

    traces->traces.elementsCount = count_array;
    traces->PLCstatus = m_status.PLCstatus;

    //Reset the array
    head_array = 0;
    tail_array = 0;
    count_array = 0;
    m_trace_byte_size = 0;

    return 0;
}

uint32_t PLCObject::MatchMD5(const char *MD5, bool *match)
{
    // an empty PLC is never considered to match
    if(m_status.PLCstatus == Empty)
    {
        *match = false;
        return 0;
    }

    std::string md5sum = GetLastTransferredPLC_MD5();

    // Compare the given MD5 with the last transferred PLC md5
    *match = (MD5 != nullptr && md5sum == MD5);

    return 0;
}

uint32_t PLCObject::NewPLC(
    const char *md5sum, const binary_t *plcObjectBlobID,
    const list_extra_file_1_t *extrafiles, bool *success)
{
    uint32_t res;

    LogMessage(LOG_INFO, "New PLC");

    if(m_status.PLCstatus == Started)
    {
        *success = false;
        return EBUSY;
    }

    if(m_status.PLCstatus == Broken)
    {
        *success = false;
        return EINVAL;
    }

    // Save blobs to files
    res = SaveBlobs(md5sum, plcObjectBlobID, extrafiles);
    if (res != 0)
    {
        LogMessage(LOG_CRITICAL, "Saves blobs failed");
        *success = false;
        return res;
    }

    // Load the PLC object
    res = LoadPLC();
    if (res != 0)
    {
        m_status.PLCstatus = Empty;
        *success = false;
        return res;
    }
    m_status.PLCstatus = Stopped;

    *success = true;
    return 0;
}

uint32_t PLCObject::PurgeBlobs(void)
{
    // Purge all blobs
    for (auto &blob : m_mapBlobIDToBlob)
    {
        DeleteBlob(blob.second);
    }
    m_mapBlobIDToBlob.clear();

    m_status.PLCstatus = Empty;

    return 0;
}

uint32_t PLCObject::RepairPLC(void)
{
    // Repair the PLC object
    if(m_status.PLCstatus == Broken)
    {
        // Unload the PLC object
        UnLoadPLC();

        // Purge the PLC object
        PurgePLC();

        m_status.PLCstatus = Empty;

    }

   
    return 0;
}

uint32_t PLCObject::ResetLogCount(void)
{
    m_PLCSyms.ResetLogCount();
    return 0;
}


uint32_t PLCObject::SeedBlob(const binary_t *seed, binary_t *blobID)
{
    // Create a blob with given seed
    // Output new blob's md5 into blobID
    // Return 0 if success

    Blob *blob = NULL;
    blob = NewBlob();
    if(blob == NULL)
    {
        return ENOMEM;
    }

    blob->Seed(seed->data, seed->dataLength);

    MD5::digest_t digest = blob->digest();

    std::vector<uint8_t> k((uint8_t*)digest.data, (uint8_t*)digest.data + MD5::digestsize);

    m_mapBlobIDToBlob[k] = blob;

    blobID->data = (uint8_t *)erpc_malloc(MD5::digestsize);
    if (blobID->data == NULL)
    {
        return ENOMEM;
    }
    memcpy(blobID->data, digest.data, MD5::digestsize);
    blobID->dataLength = MD5::digestsize;

    m_status.PLCstatus = Empty;

    return 0;
}
void PLCObject::PurgeTraceBuffer(void)
{
    // Free trace buffer
    TraceMutexLock();
    while (count_array > 0) {
        trace_sample& s =  m_traces[tail_array];
        erpc_free(s.TraceBuffer.data);

        tail_array = (tail_array + 1) % MAX_ELEMENTS_TRACE;
        count_array--;
    }
    head_array = tail_array = m_trace_byte_size = 0;
    TraceMutexUnlock();
}

uint32_t PLCObject::SetTraceVariablesList(
    const list_trace_order_1_t *orders, int32_t *debugtoken)
{   
    if(m_status.PLCstatus == Empty)
    {
        LogMessage(LOG_WARNING, "Could not set trace variable: PLC empty");
        return 0;
    }

    m_PLCSyms.PLC_GetTime(&last_uploaded_trace);

    // increment debug token
    m_debugToken++;

    if(orders->elementsCount == 0)
    {
        // actually disables debug
        m_PLCSyms.suspendDebug(1);
        *debugtoken = -5; // DEBUG_SUSPENDED
        return 0;
    }

    // suspend debug before any operation
    int res = m_PLCSyms.suspendDebug(0);

    if(res == 0)
    {
        // forget about all previous debug variables
        m_PLCSyms.ResetDebugVariables();

        // call RegisterTraceVariables for each trace order
        for (unsigned int i = 0; i < orders->elementsCount; i++)
        {

            trace_order *order = orders->elements + i;
            res = m_PLCSyms.RegisterDebugVariable(order->idx, order->force.data, order->force.dataLength);
            if(res != 0)
            {
                // if any error, disable debug
                // since debug is already suspended, resume it first
                m_PLCSyms.resumeDebug();
                m_PLCSyms.suspendDebug(1);
                *debugtoken = -res;
                return EINVAL;
            }
        }
        // old traces are not valid anymore
        PurgeTraceBuffer();

        // Start debug thread if not already started
        EnsureDebugThread();

        m_PLCSyms.resumeDebug();
        *debugtoken = m_debugToken;
        return 0;
    }
    return 0;
}

uint32_t PLCObject::StartPLC(void)
{
    LogMessage(LOG_INFO, "Starting PLC");
    uint32_t res = m_PLCSyms.startPLC(m_argc, m_argv);
    if(res != 0)
    {
        LogMessage(LOG_CRITICAL, "Failed to start PLC");
        m_status.PLCstatus = Broken;
        return res;
    }
    m_status.PLCstatus = Started;

    return 0;
}

uint32_t PLCObject::StopPLC(bool *success)
{
    LogMessage(LOG_INFO, "Stopping PLC");
    uint32_t res = m_PLCSyms.stopPLC();
    if(res == 0)
    {
        m_status.PLCstatus = Stopped;
        *success = true;
    } else {
        m_status.PLCstatus = Broken;
        *success = false;
    }

    // Stop debug thread
    StopDebugThread();

    return res;
}

uint32_t PLCObject::LogMessage(uint8_t level, std::string message)
{
    // if PLC isn't loaded, log to stdout
    if(m_PLCSyms.LogMessage == NULL)
    {
        fprintf(stderr, "%d: %s\n", level, message.c_str());
        return ENOSYS;
    }

    // Log std::string message with given level
    return m_PLCSyms.LogMessage(level, (char *)message.c_str(), message.size());
}

void PLCObject::TraceThreadProc(void)
{
    uint32_t err = 0;
    m_PLCSyms.resumeDebug();

    while(m_status.PLCstatus == Started)
    {
        unsigned int tick;
        unsigned int size;
        void * buff;

        int res;

        if((res = m_PLCSyms.GetDebugData(&tick, &size, &buff)) == 0){
            // Data allocated here is meant to be erpc_mallocd by eRPC server code
            uint8_t* ourData = NULL;

            ourData = (uint8_t *)erpc_malloc(size);
            if(ourData == NULL){
                err = ENOMEM;
                break;
            }

            memcpy(ourData, buff, size);

            m_PLCSyms.FreeDebugData();

            IEC_TIMESPEC now;
            m_PLCSyms.PLC_GetTime(&now);

            if(now.tv_sec - last_uploaded_trace.tv_sec >= DEBUGGER_TIMEOUT_S)
            {
                //release lock before suspending debug
                m_PLCSyms.resumeDebug();
                m_PLCSyms.suspendDebug(1);
                erpc_free(ourData);
                break;
            }
            else
            {
                // exact size of the trace_sample without the pointer on buffer and taking the buffer instead
                // because size is limited regarding of the max erpc payload
                // size of trace_sample struct + buffer + tick + datalength
                std::size_t new_sample_size = sizeof(trace_sample) + size + sizeof(uint32_t) + sizeof(uint32_t);

                TraceMutexLock();

                // if payload size would become too large we cant put newest sample, so we keep droping oldest ones
                while (((m_trace_byte_size + new_sample_size) > MAX_ERPC_PAYLOAD_SIZE) && (count_array > 0))
                {
                    auto& oldest = m_traces[tail_array];
                    std::size_t removed_size = sizeof(trace_sample) + oldest.TraceBuffer.dataLength + sizeof(uint32_t) + sizeof(uint32_t);
                    m_trace_byte_size -= removed_size;
                    erpc_free(oldest.TraceBuffer.data);

                    tail_array = (tail_array + 1) % MAX_ELEMENTS_TRACE;
                    count_array--;
                }

                // oldest sample is dropped before inserting a new one if ring buffer is full
                if (count_array == MAX_ELEMENTS_TRACE)
                {
                    trace_sample& overwritten = m_traces[tail_array];
                    std::size_t overwritten_size = sizeof(trace_sample) + overwritten.TraceBuffer.dataLength + sizeof(uint32_t) + sizeof(uint32_t);
                    m_trace_byte_size -= overwritten_size;
                    erpc_free(overwritten.TraceBuffer.data);

                    tail_array = (tail_array + 1) % MAX_ELEMENTS_TRACE;
                    count_array--;
                }

                // insert the new sample
                m_traces[head_array] = (trace_sample{tick, binary_t{ourData, size}});
                m_trace_byte_size = m_trace_byte_size + new_sample_size;
                head_array = (head_array + 1) % MAX_ELEMENTS_TRACE;
                count_array ++;

                TraceMutexUnlock();
                
                m_PLCSyms.resumeDebug();
            }
        } else {
            // PLC shutdown
            err = 0;
            break;
        }

    }
    m_PLCSyms.FreeDebugData();

    PurgeTraceBuffer();

    LogMessage(err ? LOG_CRITICAL : LOG_INFO,
        err == ENOMEM ? "Out of memory in TraceThreadProc" :
        err ? "TraceThreadProc ended because of error" :
        "TraceThreadProc ended normally");
    StopDebugThread();
}

uint32_t PLCObject::ExtendedCall(const char * method, const binary_t * argument, binary_t * answer)
{
    // TODO
    answer->data = (uint8_t *)erpc_malloc(0);
    answer->dataLength = 0;

    return 0;
}

