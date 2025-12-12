#ifndef BLOB_HPP
#define BLOB_HPP

#include <string>
#include "md5.hpp"

class Blob
{
public:
    Blob(uint8_t *seedData, size_t seedLength);
    virtual ~Blob();
    MD5::digest_t digest();
    virtual uint32_t appendChunk(uint8_t *data, size_t length);

protected:
    MD5 md5;
};

#endif // BLOB_HPP
