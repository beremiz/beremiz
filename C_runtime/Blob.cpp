#include "Blob.hpp"

Blob::Blob()
{
}

void Blob::Seed(uint8_t *seedData, size_t seedLength)
{
    // Seed the MD5 hash with the seed data
    md5.update(seedData, seedLength);
}

Blob::~Blob()
{
}

MD5::digest_t Blob::digest()
{
    return md5.digest();
}

uint32_t Blob::appendChunk(uint8_t *data, size_t length)
{

    // Update MD5 hash
    md5.update(data, length);

    return 0;
}
