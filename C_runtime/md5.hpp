/* MD5

    Modified in 2024 for use in Beremiz by Edouard Tisserant

    converted to C++ class by Frank Thilo (thilo@unix-ag.org)
    for bzflag (http://www.bzflag.org)

    based on:

    md5.h and md5.c
    reference implementation of RFC 1321

    Copyright (C) 1991-2, RSA Data Security, Inc. Created 1991. All
rights reserved.

License to copy and use this software is granted provided that it
is identified as the "RSA Data Security, Inc. MD5 Message-Digest
Algorithm" in all material mentioning or referencing this software
or this function.

License is also granted to make and use derivative works provided
that such works are identified as "derived from the RSA Data
Security, Inc. MD5 Message-Digest Algorithm" in all material
mentioning or referencing the derived work.

RSA Data Security, Inc. makes no representations concerning either
the merchantability of this software or the suitability of this
software for any particular purpose. It is provided "as is"
without express or implied warranty of any kind.

These notices must be retained in any copies of any part of this
documentation and/or software.

*/

#ifndef BZF_MD5_H
#define BZF_MD5_H

#include <cstdint>

// a small class for calculating MD5 hashes of strings or byte arrays
// it is not meant to be fast or secure
//
// usage: 1) feed it blocks of uchars with update()
//        2) get digest() data
//
// assumes that char is 8 bit and int is 32 bit
class MD5
{
public:
    typedef unsigned int size_type; // must be 32bit

    MD5();
    void update(const unsigned char *buf, size_type length);
    typedef struct {
        uint8_t data[16];
    } digest_t;
    digest_t digest();
    enum
    {
        blocksize = 64,
        digestsize = 16
    };    

private:
    void init();

    void transform(const uint8_t block[blocksize]);
    static void decode(uint32_t output[], const uint8_t input[], size_type len);
    static void encode(uint8_t output[], const uint32_t input[], size_type len);
    
    uint8_t buffer[blocksize]; // bytes that didn't fit in last 64 byte chunk
    uint32_t count[2];          // 64bit counter for number of bits (lo, hi)
    uint32_t state[4];          // digest so far

    // low level logic operations
    static inline uint32_t F(uint32_t x, uint32_t y, uint32_t z);
    static inline uint32_t G(uint32_t x, uint32_t y, uint32_t z);
    static inline uint32_t H(uint32_t x, uint32_t y, uint32_t z);
    static inline uint32_t I(uint32_t x, uint32_t y, uint32_t z);
    static inline uint32_t rotate_left(uint32_t x, int n);
    static inline void FF(uint32_t &a, uint32_t b, uint32_t c, uint32_t d, uint32_t x, uint32_t s, uint32_t ac);
    static inline void GG(uint32_t &a, uint32_t b, uint32_t c, uint32_t d, uint32_t x, uint32_t s, uint32_t ac);
    static inline void HH(uint32_t &a, uint32_t b, uint32_t c, uint32_t d, uint32_t x, uint32_t s, uint32_t ac);
    static inline void II(uint32_t &a, uint32_t b, uint32_t c, uint32_t d, uint32_t x, uint32_t s, uint32_t ac);
};

#endif