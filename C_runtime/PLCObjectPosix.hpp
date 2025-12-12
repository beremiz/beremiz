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

        virtual uint32_t LoadPLC(void);
        virtual uint32_t UnLoadPLC(void);
        virtual uint32_t PurgePLC(void);

        virtual void SaveBlobs(
            const char *md5sum,
            const binary_t *plcObjectBlobID,
            const list_extra_file_1_t *extrafiles);

    private:
        virtual uint32_t BlobAsFile(const binary_t * BlobID, std::filesystem::path filename);

};

#endif
