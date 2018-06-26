/*
  This file is part of Beremiz, a Integrated Development Environment for
  programming IEC 61131-3 automates supporting plcopen standard and CanFestival.

  See COPYING.runtime

  Copyright (C) 2018: Sergey Surkov <surkov.sv@summatechnology.ru>
  Copyright (C) 2018: Andrey Skvortsov <andrej.skvortzov@gmail.com>

*/

#ifndef HAVE_RETAIN
#include <stdio.h>
#include <stdint.h>
#include <unistd.h>
#include "iec_types.h"

int GetRetainSize(void);

/* Retain buffer.  */
FILE *retain_buffer;
const char rb_file[]      = "retain_buffer_file";
const char rb_file_bckp[] = "retain_buffer_file.bak";


/* Retain header struct.  */
struct retain_info_t {
	uint32_t retain_size;
	uint32_t hash_size;
	uint8_t* hash;
	uint32_t header_offset;
	uint32_t header_crc;
};

/* Init retain info structure.  */
struct retain_info_t retain_info;

/* CRC lookup table and initial state.  */
uint32_t crc32_table[256];
uint32_t retain_crc;


/* Generate CRC32 lookup table.  */
void GenerateCRC32Table(void)
{
	unsigned int i, j;
	/* Use CRC-32-IEEE 802.3 polynomial 0x04C11DB7 (bit reflected).  */
	uint32_t poly = 0xEDB88320;

	for (i = 0; i <= 0xFF; i++)
	{
		uint32_t c = i;
		for (j = 0 ; j < 8 ; j++)
			c = (c & 1) ? (c >> 1 ) ^ poly : (c >> 1);
		crc32_table[i] = c;
	}
}


/* Calculate CRC32 for len bytes from pointer buf with init starting value.  */
uint32_t GenerateCRC32Sum(const void* buf, unsigned int len, uint32_t init)
{
	uint32_t crc = ~init;
	unsigned char* current = (unsigned char*) buf;
	while (len--)
		crc = crc32_table[(crc ^ *current++) & 0xFF] ^ (crc >> 8);
	return ~crc;
}

/* Calc CRC32 for retain file byte by byte.  */
int CheckFileCRC(FILE* file_buffer)
{
	/* Set the magic constant for one-pass CRC calc according to ZIP CRC32.  */
	const uint32_t magic_number = 0x2144df1c;

	/* CRC initial state.  */
	uint32_t calc_crc32 = 0;
	char data_block = 0;

	while(!feof(file_buffer)){
		if (fread(&data_block, sizeof(data_block), 1, file_buffer))
			calc_crc32 = GenerateCRC32Sum(&data_block, sizeof(data_block), calc_crc32);
	}

	/* Compare crc result with a magic number.  */
	return (calc_crc32 == magic_number) ? 1 : 0;
}

/* Compare current hash with hash from file byte by byte.  */
int CheckFilehash(void)
{
	unsigned int k;
	int offset = sizeof(retain_info.retain_size);

	rewind(retain_buffer);
	fseek(retain_buffer, offset , SEEK_SET);

	uint32_t size;
	fread(&size, sizeof(size), 1, retain_buffer);
	if (size != retain_info.hash_size)
		return 0;

	for(k = 0; k < retain_info.hash_size; k++){
		uint8_t file_digit;
		fread(&file_digit, sizeof(file_digit), 1, retain_buffer);
		if (file_digit != *(retain_info.hash+k))
			return 0;
	}

	return 1;
}

void InitRetain(void)
{
	unsigned int i;

	/* Generate CRC32 lookup table.  */
	GenerateCRC32Table();

	/* Get retain size in bytes */
	retain_info.retain_size = GetRetainSize();

	/* Hash stored in retain file as array of char in hex digits
	   (that's why we divide strlen in two).  */
	retain_info.hash_size = PLC_ID ? strlen(PLC_ID)/2 : 0;
	//retain_info.hash_size = 0;
	retain_info.hash = malloc(retain_info.hash_size);

	/* Transform hash string into byte sequence.  */
	for (i = 0; i < retain_info.hash_size; i++) {
		int byte = 0;
		sscanf((PLC_ID + i*2), "%02X", &byte);
		retain_info.hash[i] = byte;
	}

	/* Calc header offset.  */
	retain_info.header_offset = sizeof(retain_info.retain_size) + \
		sizeof(retain_info.hash_size) + \
		retain_info.hash_size;

	/*  Set header CRC initial state.  */
	retain_info.header_crc = 0;

	/* Calc crc for header.  */
	retain_info.header_crc = GenerateCRC32Sum(
		&retain_info.retain_size,
		sizeof(retain_info.retain_size),
		retain_info.header_crc);

	retain_info.header_crc = GenerateCRC32Sum(
		&retain_info.hash_size,
		sizeof(retain_info.hash_size),
		retain_info.header_crc);

	retain_info.header_crc = GenerateCRC32Sum(
		retain_info.hash,
		retain_info.hash_size,
		retain_info.header_crc);
}

void CleanupRetain(void)
{
	/* Free hash memory.  */
	free(retain_info.hash);
}

int CheckRetainFile(const char * file)
{
	retain_buffer = fopen(file, "rb");
	if (retain_buffer) {
		/* Check CRC32 and hash.  */
		if (CheckFileCRC(retain_buffer))
			if (CheckFilehash())
				return 1;
		fclose(retain_buffer);
		retain_buffer = NULL;
	}
	return 0;
}

int CheckRetainBuffer(void)
{
	retain_buffer = NULL;
	if (!retain_info.retain_size)
		return 1;

	/* Check latest retain file.  */
	if (CheckRetainFile(rb_file))
		return 1;

	/* Check if we have backup.  */
	if (CheckRetainFile(rb_file_bckp))
		return 1;

	/* We don't have any valid retain buffer - nothing to remind.  */
	return 0;
}

#ifndef FILE_RETAIN_SAVE_PERIOD_S
#define FILE_RETAIN_SAVE_PERIOD_S 1.0
#endif

static double CalcDiffSeconds(IEC_TIME* t1, IEC_TIME *t2)
{
	IEC_TIME dt ={
		t1->tv_sec  - t2->tv_sec,
		t1->tv_nsec - t2->tv_nsec
	};

	if ((dt.tv_nsec < -1000000000) || ((dt.tv_sec > 0) && (dt.tv_nsec < 0))){
		dt.tv_sec--;
		dt.tv_nsec += 1000000000;
	}
	if ((dt.tv_nsec > +1000000000) || ((dt.tv_sec < 0) && (dt.tv_nsec > 0))){
		dt.tv_sec++;
		dt.tv_nsec -= 1000000000;
	}
	return dt.tv_sec + 1e-9*dt.tv_nsec;
}


int RetainSaveNeeded(void)
{
	int ret = 0;
	static IEC_TIME last_save;
	IEC_TIME now;
	double diff_s;

	/* no retain */
	if (!retain_info.retain_size)
		return 0;

	/* periodic retain flush to avoid high I/O load */
	PLC_GetTime(&now);

	diff_s = CalcDiffSeconds(&now, &last_save);

	if ((diff_s > FILE_RETAIN_SAVE_PERIOD_S) || ForceSaveRetainReq()) {
		ret = 1;
		last_save = now;
	}
	return ret;
}

void ValidateRetainBuffer(void)
{
	if (!retain_buffer)
		return;

	/* Add retain data CRC to the end of buffer file.  */
	fseek(retain_buffer, 0, SEEK_END);
	fwrite(&retain_crc, sizeof(retain_crc), 1, retain_buffer);

	/* Sync file buffer and close file.  */
#ifdef __WIN32
	fflush(retain_buffer);
#else
	fsync(fileno(retain_buffer));
#endif

	fclose(retain_buffer);
	retain_buffer = NULL;
}

void InValidateRetainBuffer(void)
{
	if (!RetainSaveNeeded())
		return;

	/* Rename old retain file into *.bak if it exists.  */
	rename(rb_file, rb_file_bckp);

	/* Set file CRC initial value.  */
	retain_crc = retain_info.header_crc;

	/* Create new retain file.  */
	retain_buffer = fopen(rb_file, "wb+");
	if (!retain_buffer) {
		fprintf(stderr, "Failed to create retain file : %s\n", rb_file);
		return;
	}

	/* Write header to the new file.  */
	fwrite(&retain_info.retain_size,
		sizeof(retain_info.retain_size), 1, retain_buffer);
	fwrite(&retain_info.hash_size,
		sizeof(retain_info.hash_size),   1, retain_buffer);
	fwrite(retain_info.hash ,
		sizeof(char), retain_info.hash_size, retain_buffer);
}

void Retain(unsigned int offset, unsigned int count, void *p)
{
	if (!retain_buffer)
		return;

	/* Generate CRC 32 for each data block.  */
	retain_crc = GenerateCRC32Sum(p, count, retain_crc);

	/* Save current var in file.  */
	fseek(retain_buffer, retain_info.header_offset+offset, SEEK_SET);
	fwrite(p, count, 1, retain_buffer);
}

void Remind(unsigned int offset, unsigned int count, void *p)
{
	/* Remind variable from file.  */
	fseek(retain_buffer, retain_info.header_offset+offset, SEEK_SET);
	fread((void *)p, count, 1, retain_buffer);
}
#endif // !HAVE_RETAIN
