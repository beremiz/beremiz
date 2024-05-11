
#include <stdlib.h>
#include <errno.h>

#include "blob.hpp"
#include <unistd.h>

Blob::Blob(uint8_t *seedData, size_t seedLength)
{
    // Create a temporary file to store blob data
    // not using tmpfile() because we need to know the filename
    // for later renaming and avoid deletion on close
    
    // Assume that a tmp directory exists in the current directory
    uint8_t template_name[] = "tmp/blobXXXXXX";
    int fd = mkstemp((char *)template_name);
    if (fd == -1) {
        throw errno;
    }

    // Open file for stdlib I/O
    m_file = fdopen(fd, "w+");
    if (m_file == NULL) {
        throw errno;
    }

    // Save a copy of the filename
    m_filename = (char *)template_name;

    // Seed the MD5 hash with the seed data
    md5.update(seedData, seedLength);
}

Blob::~Blob() {
    if (m_file != NULL) {
        std::fclose(m_file);
        std::remove(m_filename.c_str());
    }
}

MD5::digest_t Blob::digest() {
    return md5.digest();
}

uint32_t Blob::appendChunk(uint8_t *data, size_t length) {
    // Write data to file
    if (std::fwrite(data, 1, length, m_file) != length) {
        return errno;
    }

    // Update MD5 hash
    md5.update(data, length);

    return 0;
}

uint32_t Blob::asFile(std::filesystem::path &filename)
{
    // Flush file
    if (std::fflush(m_file) != 0) {
        return errno;
    }

    // Sync file to disk
    if (fsync(fileno(m_file)) != 0) {
        return errno;
    }

    // Close file
    if (std::fclose(m_file) != 0) {
        return errno;
    }

    m_file = NULL;

    // Rename temp file to final file
    if (std::rename(m_filename.c_str(), filename.c_str()) != 0) {
        return errno;
    }

    return 0;
}
