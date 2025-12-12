#include <string.h>
#include <filesystem>
#include <dlfcn.h>
#include <fstream>
#include <iostream>

#include "Logging.hpp"
#include "PLCObjectPosix.hpp"
#include "BlobPosix.hpp"

// File name of the last transferred PLC md5 hex digest
// with typo in the name, for compatibility with Python runtime
#define LastTransferredPLC "lasttransferedPLC.md5"

// File name of the extra files list
#define ExtraFilesList "extra_files.txt"

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

PLCObjectPosix::PLCObjectPosix(void) : PLCObject()
{
    m_handle = NULL;
}

PLCObjectPosix::~PLCObjectPosix(void)
{
}

const char* SharedObjectExtension = SHARED_OBJECT_EXT;

uint32_t PLCObjectPosix::BlobAsFile(
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
    uint32_t res = dynamic_cast<BlobPosix*>(blob)->asFile(filename);

    DeleteBlob(blob);

    if (res != 0)
    {
        return res;
    }
    return 0;
}

uint32_t PLCObjectPosix::SaveBlobs(
    const char *md5sum,
    const binary_t *plcObjectBlobID,
    const list_extra_file_1_t *extrafiles)
{
    uint32_t res;

    // Create the PLC object shared object file
    res = BlobAsFile(plcObjectBlobID, std::string(md5sum) + SharedObjectExtension);
    if (res != 0)
    {
        return res;
    }

    // create "lasttransferedPLC.md5" file and Save md5sum in it
    std::ofstream(std::string(LastTransferredPLC), std::ios::binary) << md5sum;

    // create "extra_files.txt" file
    std::ofstream extra_files_log(std::string(ExtraFilesList), std::ios::binary);

    // Create extra files
    for (int i = 0; i < extrafiles->elementsCount; i++)
    {
        extra_file *extrafile = extrafiles->elements + i;

        res = BlobAsFile(plcObjectBlobID, extrafile->fname);
        if (res != 0)
        {
            return res;
        }

        // Save the extra file name in "extra_files.txt"
        extra_files_log << extrafile->fname << std::endl;
    }

    return 0;
}

uint32_t PLCObjectPosix::PurgePLC(void)
{
    // Open the extra files list
    std::ifstream extra_files_log(std::string(ExtraFilesList), std::ios::binary);

    // Remove extra files
    std::string extra_file;
    while (std::getline(extra_files_log, extra_file))
    {
        std::filesystem::remove(extra_file);
    }

    // Load the last transferred PLC md5 hex digest
    std::string md5sum;
    try {
        std::ifstream(std::string(LastTransferredPLC), std::ios::binary) >> md5sum;

        // Remove the PLC object shared object file
        std::filesystem::remove(md5sum + SHARED_OBJECT_EXT);
    } catch (std::exception e) {
        // ignored
    }

    try {
        // Remove the last transferred PLC md5 hex digest
        std::filesystem::remove(std::string(LastTransferredPLC));

        // Remove the extra files list
        std::filesystem::remove(std::string(ExtraFilesList));
    } catch (std::exception e) {
        // ignored
    }

    return 0;
}

#define DLSYM(sym)                                                           \
    do                                                                       \
    {                                                                        \
        m_PLCSyms.sym = (decltype(m_PLCSyms.sym))dlsym(m_handle, #sym);      \
        if (m_PLCSyms.sym == NULL)                                           \
        {                                                                    \
            /* TODO: use log instead */                                      \
            std::cout << "Error dlsym " #sym ": " << dlerror() << std::endl; \
            return errno;                                                    \
        }                                                                    \
    } while (0);

uint32_t PLCObjectPosix::LoadPLC(void)
{
    // TODO use PLCLibMutex

    // Load the last transferred PLC md5 hex digest
    std::string md5sum;
    try {
        std::ifstream(std::string(LastTransferredPLC), std::ios::binary) >> md5sum;
    } catch (std::exception e) {
        return ENOENT;
    }

    // Concatenate md5sum and shared object extension to obtain filename
    std::filesystem::path filename(md5sum + SHARED_OBJECT_EXT);

    // Load the shared object file
    m_handle = dlopen(std::filesystem::absolute(filename).c_str(), RTLD_NOW);
    if (m_handle == NULL)
    {
        std::cout << "Error: " << dlerror() << std::endl;
        return errno;
    }

    // Resolve shared object symbols
    FOR_EACH_PLC_SYMBOLS_DO(DLSYM);

    // Set content of PLC_ID to md5sum
    m_PLCSyms.PLC_ID = (uint8_t *)malloc(md5sum.size() + 1);
    if (m_PLCSyms.PLC_ID == NULL)
    {
        return ENOMEM;
    }
    memcpy(m_PLCSyms.PLC_ID, md5sum.c_str(), md5sum.size());
    m_PLCSyms.PLC_ID[md5sum.size()] = '\0';

    return 0;
}

#define ULSYM(sym)            \
    do                        \
    {                         \
        m_PLCSyms.sym = NULL; \
    } while (0);

uint32_t PLCObjectPosix::UnLoadPLC(void)
{
    // Unload the shared object file
    FOR_EACH_PLC_SYMBOLS_DO(ULSYM);
    if(m_handle != NULL)
    {
        dlclose(m_handle);
        m_handle = NULL;
    }
    return 0;
}

void PLCObjectPosix::ThreadTrampoline(void){
    // Call the PLCObject::TraceThreadProc method
    PLCObject::TraceThreadProc();
}


void PLCObjectPosix::EnsureDebugThread(void)
{
    // Start debug thread if not already started
    if(!m_traceThread.joinable())
    {
        m_traceThread = std::thread(&PLCObjectPosix::ThreadTrampoline, this);
    }
}

void PLCObjectPosix::StopDebugThread(void)
{
    // Stop debug thread
    if(m_traceThread.joinable())
    {
        m_traceThread.join();
    }
}

void PLCObjectPosix::TraceMutexLock(void)
{
    m_tracesMutex.lock();
}

void PLCObjectPosix::TraceMutexUnlock(void)
{
    m_tracesMutex.unlock();
}

void PLCObjectPosix::PLCLibMutexLock(void)
{
    m_PLClibMutex.lock();
}

void PLCObjectPosix::PLCLibMutexUnlock(void)
{
    m_PLClibMutex.unlock();
}

Blob *PLCObjectPosix::NewBlob()
{
    return new BlobPosix();
}

void PLCObjectPosix::DeleteBlob(Blob *blob)
{
    delete dynamic_cast<BlobPosix*>(blob);
}
