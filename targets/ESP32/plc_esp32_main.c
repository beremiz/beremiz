/**
 * plc_esp32_main.c
 * 
 * ESP32/FreeRTOS specific PLC runtime for Beremiz
 * Skeleton version
 **/

#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_timer.h"
#include "esp_log.h"

#include "iec_types.h"    // Definiciones de IEC de Beremiz

static const char* TAG = "PLC_ESP32";

static TaskHandle_t PLC_task_handle = NULL;
static SemaphoreHandle_t python_mutex;
static SemaphoreHandle_t debug_mutex;
static SemaphoreHandle_t debug_wait_mutex;
static SemaphoreHandle_t python_wait_mutex;

static int PLC_shutdown = 0;
static unsigned int __debug_tick = 0;
static unsigned long long period_ns = 1000000; // 1 ms por defecto
static IEC_TIME __CURRENT_TIME;

// ---------------- Math functions ----------------
double iec_lib_acos(double x) { return acos(x); }
double iec_lib_asin(double x) { return asin(x); }
double iec_lib_atan(double x) { return atan(x); }
double iec_lib_cos(double x) { return cos(x); }
double iec_lib_exp(double x) { return exp(x); }
double iec_lib_fmod(double x, double y) { return fmod(x,y); }
double iec_lib_log(double x) { return log(x); }
double iec_lib_log10(double x) { return log10(x); }
double iec_lib_pow(double x, double y) { return pow(x,y); }
double iec_lib_sin(double x) { return sin(x); }
double iec_lib_sqrt(double x) { return sqrt(x); }
double iec_lib_tan(double x) { return tan(x); }

// ---------------- Timing ----------------
static void update_current_time() {
    int64_t us = esp_timer_get_time();
    __CURRENT_TIME.tv_sec = us / 1000000;
    __CURRENT_TIME.tv_nsec = (us % 1000000) * 1000;
}

static void PLC_cycle_wait() {
    static int64_t last_wakeup_us = 0;
    int64_t now = esp_timer_get_time();

    int64_t period_us = period_ns / 1000;

    if (last_wakeup_us == 0) last_wakeup_us = now;

    int64_t sleep_us = period_us - (now - last_wakeup_us);
    if (sleep_us > 0) {
        ets_delay_us(sleep_us);
    } else {
        ESP_LOGW(TAG, "PLC overrun! Missed cycle by %lld us", -sleep_us);
    }
    last_wakeup_us += period_us;
    update_current_time();
}

// ---------------- PLC main task ----------------
static void PLC_task(void *arg) {
    int periods_passed = 0;

    while (!PLC_shutdown) {
        // Aquí va la ejecución del PLC
        __run(periods_passed);

        PLC_cycle_wait();
        periods_passed++;
    }

    vTaskDelete(NULL);
}

// ---------------- Control functions ----------------
int startPLC(int period_ns_input) {
    PLC_shutdown = 0;
    period_ns = period_ns_input;

    python_mutex = xSemaphoreCreateMutex();
    debug_mutex = xSemaphoreCreateMutex();
    debug_wait_mutex = xSemaphoreCreateMutex();
    python_wait_mutex = xSemaphoreCreateMutex();

    xTaskCreate(PLC_task, "PLC_Task", 4096, NULL, 5, &PLC_task_handle);
    ESP_LOGI(TAG, "PLC Task started");
    return 0;
}

int stopPLC() {
    PLC_shutdown = 1;
    // Espera a que el task termine
    vTaskDelay(pdMS_TO_TICKS(10));
    ESP_LOGI(TAG, "PLC Task stopped");
    return 0;
}

// ---------------- Debug / Python ----------------
int TryEnterDebugSection(void) {
    if (xSemaphoreTake(debug_mutex, 0) == pdTRUE) {
        return 1;
    }
    return 0;
}

void LeaveDebugSection(void) {
    xSemaphoreGive(debug_mutex);
}

int TryLockPython(void) {
    if (xSemaphoreTake(python_mutex, 0) == pdTRUE) {
        return 1;
    }
    return 0;
}

void UnLockPython(void) {
    xSemaphoreGive(python_mutex);
}

void LockPython(void) {
    xSemaphoreTake(python_mutex, portMAX_DELAY);
}

// ---------------- Current time ----------------
void PLC_GetTime(IEC_TIME *CURRENT_TIME) {
    *CURRENT_TIME = __CURRENT_TIME;
}

