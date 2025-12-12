/*
    Copyright Edouard TISSERANT 2024
    See COPYING for details
*/

#if !defined(_PLCObjectPosix_hpp_)
#define _PLCObjectPosix_hpp_

#include <filesystem>
#include "PLCObject.hpp"

class PLCObjectPosix : public PLCObject
{
    public:
        PLCObjectPosix(void);
        virtual ~PLCObjectPosix(void);

    protected:
        // PLC object library handle
        void * m_handle;

        // Shared object mutex
        std::mutex m_PLClibMutex;

        // Trace thread
        std::thread m_traceThread;

        // Trace thread mutex
        std::mutex m_tracesMutex;

        virtual uint32_t LoadPLC(void);
        virtual uint32_t UnLoadPLC(void);
        virtual uint32_t PurgePLC(void);

        virtual void SaveBlobs(
            const char *md5sum,
            const binary_t *plcObjectBlobID,
            const list_extra_file_1_t *extrafiles);
        virtual void EnsureDebugThread(void);
        virtual void StopDebugThread(void);
        virtual void TraceMutexLock(void);
        virtual void TraceMutexUnlock(void);
        virtual void PLCLibMutexLock(void);
        virtual void PLCLibMutexUnlock(void);

    private:
        virtual uint32_t BlobAsFile(const binary_t * BlobID, std::filesystem::path filename);
        void ThreadTrampoline(void);

};

#endif
