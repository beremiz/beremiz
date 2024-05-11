#ifndef BLOB_HPP
#define BLOB_HPP

#include <string>
#include <filesystem>

#include "md5.hpp"

class Blob
{
public:
    Blob(uint8_t *seedData, size_t seedLength);
    ~Blob();
    MD5::digest_t digest();
    uint32_t appendChunk(uint8_t *data, size_t length);
    uint32_t asFile(std::filesystem::path &filename);

private:
    MD5 md5;
    std::FILE * m_file;
    std::filesystem::path m_filename;
};

#endif // BLOB_HPP
