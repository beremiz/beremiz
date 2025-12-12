#ifndef BLOBPOSIX_HPP
#define BLOBPOSIX_HPP

#include <filesystem>

#include "Blob.hpp"

class BlobPosix : public Blob
{
public:
    BlobPosix(uint8_t *seedData, size_t seedLength);
    virtual ~BlobPosix();
    
    uint32_t asFile(std::filesystem::path &filename);
    virtual uint32_t appendChunk(uint8_t *data, size_t length) override;

private:
    std::FILE * m_file;
    std::filesystem::path m_filename;
};

#endif // BLOBPOSIX_HPP
