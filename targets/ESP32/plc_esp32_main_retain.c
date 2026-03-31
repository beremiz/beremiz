/**
 * plc_esp32_main_retain.c
 * 
 * ESP32 equivalent of plc_linux_main_retain.c
 * Implements Retain variables persistence using NVS (non-volatile storage)
 **/

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "esp_log.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "iec_types.h"

static const char *TAG = "PLC_RETAIN";

static nvs_handle_t nvs_handle;
static uint32_t retain_crc = 0;   // CRC acumulativo
static double last_save_time_s = 0;
#ifndef FILE_RETAIN_SAVE_PERIOD_S
#define FILE_RETAIN_SAVE_PERIOD_S 1.0  // guarda cada 1 segundo
#endif

// Inicializa NVS y Retain
int InitRetain() {
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase();
        nvs_flash_init();
    }

    if (nvs_open("plc_retain", NVS_READWRITE, &nvs_handle) != ESP_OK) {
        ESP_LOGE(TAG, "No se pudo abrir NVS para Retain");
        return -1;
    }
    ESP_LOGI(TAG, "Retain inicializado");
    return 0;
}

// Cierra Retain
void CleanupRetain() {
    nvs_close(nvs_handle);
}

// Calcula CRC32 simple (idéntico al Linux)
static const uint32_t crc32_table[256] = {
    // tabla igual a plc_Linux_main_retain.c
    0x00000000, 0x77073096, 0xEE0E612C, 0x990951BA, 0x076DC419, 0x706AF48F, 0xE963A535, 0x9E6495A3,
    0x0EDB8832, 0x79DCB8A4, 0xE0D5E91E, 0x97D2D988, 0x09B64C2B, 0x7EB17CBD, 0xE7B82D07, 0x90BF1D91,
    0x1DB71064, 0x6AB020F2, 0xF3B97148, 0x84BE41DE, 0x1ADAD47D, 0x6DDDE4EB, 0xF4D4B551, 0x83D385C7,
    0x136C9856, 0x646BA8C0, 0xFD62F97A, 0x8A65C9EC, 0x14015C4F, 0x63066CD9, 0xFA0F3D63, 0x8D080DF5,
    0x3B6E20C8, 0x4C69105E, 0xD56041E4, 0xA2677172, 0x3C03E4D1, 0x4B04D447, 0xD20D85FD, 0xA50AB56B,
    0x35B5A8FA, 0x42B2986C, 0xDBBBC9D6, 0xACBCF940, 0x32D86CE3, 0x45DF5C75, 0xDCD60DCF, 0xABD13D59,
    0x26D930AC, 0x51DE003A, 0xC8D75180, 0xBFD06116, 0x21B4F4B5, 0x56B3C423, 0xCFBA9599, 0xB8BDA50F,
    0x2802B89E, 0x5F058808, 0xC60CD9B2, 0xB10BE924, 0x2F6F7C87, 0x58684C11, 0xC1611DAB, 0xB6662D3D,
    // restante de la tabla omitido por brevedad, incluir completa
};

uint32_t GenerateCRC32Sum(const void* buf, unsigned int len, uint32_t init) {
    uint32_t crc = ~init;
    const unsigned char* current = (const unsigned char*) buf;
    while (len--) {
        crc = crc32_table[(crc ^ *current++) & 0xFF] ^ (crc >> 8);
    }
    return ~crc;
}

// Guarda variable Retain (void *p, tamaño en bytes)
void Retain(unsigned int offset, unsigned int count, void *p) {
    char key[32];
    snprintf(key, sizeof(key), "var_%u", offset);

    // Actualiza CRC
    retain_crc = GenerateCRC32Sum(p, count, retain_crc);

    // Guardar bytes en NVS
    if (count == 1) {
        nvs_set_u8(nvs_handle, key, *(uint8_t*)p);
    } else if (count == 2) {
        nvs_set_u16(nvs_handle, key, *(uint16_t*)p);
    } else if (count == 4) {
        nvs_set_u32(nvs_handle, key, *(uint32_t*)p);
    } else {
        // bloques mayores, guardar byte a byte
        for (unsigned int i = 0; i < count; i++) {
            char bkey[36];
            snprintf(bkey, sizeof(bkey), "%s_%u", key, i);
            nvs_set_u8(nvs_handle, bkey, ((uint8_t*)p)[i]);
        }
    }
    nvs_commit(nvs_handle);
}

// Recupera variable Retain
void Remind(unsigned int offset, unsigned int count, void *p) {
    char key[32];
    snprintf(key, sizeof(key), "var_%u", offset);

    esp_err_t err;
    if (count == 1) {
        uint8_t val;
        err = nvs_get_u8(nvs_handle, key, &val);
        if (err == ESP_OK) *(uint8_t*)p = val;
    } else if (count == 2) {
        uint16_t val;
        err = nvs_get_u16(nvs_handle, key, &val);
        if (err == ESP_OK) *(uint16_t*)p = val;
    } else if (count == 4) {
        uint32_t val;
        err = nvs_get_u32(nvs_handle, key, &val);
        if (err == ESP_OK) *(uint32_t*)p = val;
    } else {
        for (unsigned int i = 0; i < count; i++) {
            char bkey[36];
            snprintf(bkey, sizeof(bkey), "%s_%u", key, i);
            uint8_t val;
            err = nvs_get_u8(nvs_handle, bkey, &val);
            if (err == ESP_OK) ((uint8_t*)p)[i] = val;
        }
    }
}

// Verifica si es momento de guardar Retain
int RetainSaveNeeded(double current_time_s, int force) {
    if ((current_time_s - last_save_time_s) > FILE_RETAIN_SAVE_PERIOD_S || force) {
        last_save_time_s = current_time_s;
        return 1;
    }
    return 0;
}

