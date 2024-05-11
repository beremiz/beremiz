
#include <string.h>
#include <filesystem>
#include <dlfcn.h>
#include <fstream>
#include <iostream>

#include "Logging.hpp"

#include "PLCObject.hpp"

#include "beremiz.h"


// File name of the last transferred PLC md5 hex digest
// with typo in the name, for compatibility with Python runtime
#define LastTransferredPLC "lasttransferedPLC.md5"

// File name of the extra files list
#define ExtraFilesList "extra_files.txt"



PLCObject::PLCObject(void)
{
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

    auto nh = m_mapBlobIDToBlob.extract(std::vector<uint8_t>(
        blobID->data, blobID->data + blobID->dataLength));
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

    nh.key() = std::vector<uint8_t>(
        (uint8_t)*digest.data, (uint8_t)*digest.data + MD5::digestsize);

    m_mapBlobIDToBlob.insert(std::move(nh));

    return 0;
}

#define LOG_READ_BUFFER_SIZE 1 << 10 // 1KB

uint32_t PLCObject::GetLogMessage(
    uint8_t level, uint32_t msgID, log_message *message)
{
    char buf[LOG_READ_BUFFER_SIZE];
    uint32_t tick;
    uint32_t tv_sec;
    uint32_t tv_nsec;

    uint32_t resultLen = m_PLCSyms.GetLogMessage(
        level, msgID, buf, LOG_READ_BUFFER_SIZE - 1,
        &tick, &tv_sec, &tv_nsec);

    if (resultLen == 0)
    {
        return ENOENT;
    }

    // Get log message with given msgID
    message->msg = (char *)malloc(resultLen);
    if (message->msg == NULL)
    {
        return ENOMEM;
    }
    // Copy the log message into eRPC message
    memcpy(message->msg, buf, resultLen);
    message->msg[resultLen + 1] = '\0';

    message->tick = tick;
    message->sec = tv_sec;
    message->nsec = tv_nsec;

    return 0;
}

uint32_t PLCObject::GetPLCID(PSKID *plcID)
{
    // Get PLC ID
    *plcID = m_plcID;
    return 0;
}

uint32_t PLCObject::GetPLCstatus(PLCstatus *status)
{
    // Get PLC status
    *status = m_status;
    return 0;
}

uint32_t PLCObject::GetTraceVariables(
    uint32_t debugToken, TraceVariables *traces)
{
    // XXX TODO
    return 0;
}

uint32_t PLCObject::MatchMD5(const char *MD5, bool *match)
{
    // Load the last transferred PLC md5 hex digest
    std::string md5sum;
    std::ifstream(std::string(LastTransferredPLC), std::ios::binary) >> md5sum;

    // Compare the given MD5 with the last transferred PLC md5
    *match = (md5sum == MD5);

    return 0;
}

#if defined(_WIN32) || defined(_WIN64)
// For Windows platform
#define SHARED_OBJECT_EXT ".dll"
#elif defined(__APPLE__) || defined(__MACH__)
// For MacOS platform
#define SHARED_OBJECT_EXT ".dylib"
#else
// For Linux/Unix platform
#define SHARED_OBJECT_EXT ".so"
#endif

uint32_t PLCObject::BlobAsFile(
    const binary_t *BlobID, std::filesystem::path filename)
{
    // Extract the blob from the map
    auto nh = m_mapBlobIDToBlob.extract(
        std::vector<uint8_t>(BlobID->data, BlobID->data + BlobID->dataLength));
    if (nh.empty())
    {
        return ENOENT;
    }
    Blob *blob = nh.mapped();

    // Realize the blob into a file
    uint32_t res = blob->asFile(filename);

    delete blob;

    if (res != 0)
    {
        return res;
    }
    return 0;
}

uint32_t PLCObject::NewPLC(
    const char *md5sum, const binary_t *plcObjectBlobID,
    const list_extra_file_1_t *extrafiles, bool *success)
{
    // Concatenate md5sum and shared object extension to obtain filename
    std::filesystem::path filename =
        std::filesystem::path(md5sum) += SHARED_OBJECT_EXT;

    // Create the PLC object shared object file
    BlobAsFile(plcObjectBlobID, filename);

    // create "lasttransferedPLC.md5" file and Save md5sum in it
    std::ofstream(std::string(LastTransferredPLC), std::ios::binary) << md5sum;

    // create "extra_files.txt" file
    std::ofstream extra_files_log(std::string(ExtraFilesList), std::ios::binary);

    // Create extra files
    for (int i = 0; i < extrafiles->elementsCount; i++)
    {
        extra_file *extrafile = extrafiles->elements + i;

        BlobAsFile(plcObjectBlobID, extrafile->fname);

        // Save the extra file name in "extra_files.txt"
        extra_files_log << extrafile->fname << std::endl;
    }

    return 0;
}

#define DLSYM(sym)                                                      \
    do                                                                  \
    {                                                                   \
        m_PLCSyms.sym = (decltype(m_PLCSyms.sym))dlsym(m_handle, #sym); \
        if (m_PLCSyms.sym == NULL)                                      \
        {                                                               \
            return errno;                                               \
        }                                                               \
    } while (0);

uint32_t PLCObject::LoadPLC(void)
{
    // Load the last transferred PLC md5 hex digest
    std::string md5sum;
    std::ifstream(std::string(LastTransferredPLC), std::ios::binary) >> md5sum;

    // Concatenate md5sum and shared object extension to obtain filename
    std::filesystem::path filename = std::filesystem::path(md5sum) += SHARED_OBJECT_EXT;

    // Load the shared object file
    m_handle = dlopen(filename.c_str(), RTLD_NOW);
    if (m_handle == NULL)
    {
        return errno;
    }

    // Resolve shared object symbols
    FOR_EACH_PLC_SYMBOLS_DO(DLSYM);

    return 0;
}

#define ULSYM(sym)            \
    do                        \
    {                         \
        m_PLCSyms.sym = NULL; \
    } while (0);

uint32_t PLCObject::UnLoadPLC(void)
{
    // Unload the shared object file
    FOR_EACH_PLC_SYMBOLS_DO(ULSYM);
    dlclose(m_handle);
    
    return 0;
}

uint32_t PLCObject::PurgeBlobs(void)
{
    // Purge all blobs

    for (auto &blob : m_mapBlobIDToBlob)
    {
        delete blob.second;
    }
    m_mapBlobIDToBlob.clear();

    return 0;
}

uint32_t PLCObject::RepairPLC(void)
{
    // XXX TODO
    LogMessage(LOG_WARNING, "RepairPLC not implemented");
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
    try
    {
        blob = new Blob(seed->data, seed->dataLength);
    }
    catch (int e)
    {
        return e;
    }

    MD5::digest_t digest = blob->digest();

    m_mapBlobIDToBlob[std::vector<uint8_t>((uint8_t)*digest.data, (uint8_t)*digest.data + MD5::digestsize)] = blob;

    blobID->data = (uint8_t *)malloc(MD5::digestsize);
    if (blobID->data == NULL)
    {
        return ENOMEM;
    }
    memcpy(blobID->data, digest.data, MD5::digestsize);
    blobID->dataLength = MD5::digestsize;

    return 0;
}

uint32_t PLCObject::SetTraceVariablesList(
    const list_trace_order_1_t *orders, uint32_t *debugtoken)
{
    // XXX TODO
    LogMessage(LOG_WARNING, "SetTraceVariablesList not implemented");
    return 0;
}

uint32_t PLCObject::StartPLC(void)
{
    LogMessage(LOG_INFO, "Starting PLC");
    uint32_t res = m_PLCSyms.startPLC(m_argc, m_argv);
    if(res != 0)
    {
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
    if(res != 0)
    {
        m_status.PLCstatus = Broken;
        return res;
    }
    m_status.PLCstatus = Stopped;
    return 0;
}

uint32_t PLCObject::LogMessage(uint8_t level, std::string message)
{
    // Log std::string message with given level
    return m_PLCSyms.LogMessage(level, (char *)message.c_str(), message.size());
}
