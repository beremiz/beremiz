/*

Template C code used to produce target Ethercat C code

Copyright (C) 2011-2014: Laurent BESSARD, Edouard TISSERANT

Distributed under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

See COPYING file for copyrights details.

/* ------------------------------------------------------------------
 * EtherCAT C code template compatible con Xenomai o Linux estándar
 * ------------------------------------------------------------------ */
 #include <time.h>
#include <stdint.h>
#include <stdio.h>
 
#include "ecrt.h"

#include "beremiz.h"
#include "iec_types_all.h"

/* Selección de sistema: descomenta USE_XENOMAI para compilar con Xenomai */
// #define USE_XENOMAI

#ifdef USE_XENOMAI
#include <rtdm/rtdm.h>
#include <native/task.h>
#include <native/timer.h>
typedef RTIME RTIME_TYPE;
#else
typedef uint64_t RTIME_TYPE;
#endif

/* ---------------------- */
/* Variables de tiempo */
static int64_t system_time_base = 0LL;
static int64_t dc_adjust_ns = 0LL;

/* ---------------------- */
/* Funciones de tiempo */
#ifdef USE_XENOMAI
RTIME_TYPE system_time_ns(void)
{
    return rt_timer_read();
}

RTIME_TYPE system2count(uint64_t time)
{
    return rt_timer_ns2ticks(time + system_time_base);
}

#else
RTIME_TYPE system_time_ns(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    int64_t t = (int64_t)ts.tv_sec * 1000000000LL + ts.tv_nsec;
    return (RTIME_TYPE)(t - system_time_base);
}

RTIME_TYPE system2count(uint64_t time)
{
    return time + system_time_base;
}
#endif

/* ---------------------- */
/* Función portable de sign */
static inline int sign(int val) {
    return (val > 0) - (val < 0);
}

/* ---------------------- */
/* Logging seguro */
/*#ifndef USE_XENOMAI*/
/*#define SLOGF(level, format, args...) \*/
/*    do { printf(format "\n", ##args); } while(0)*/
/*#endif*/

#ifdef USE_XENOMAI

#define SLOGF(level, format, args...) \
{ \
    char sbuf[256]; \
    int slen = snprintf(sbuf , sizeof(sbuf) , format , ##args); \
    LogMessage(level, sbuf, slen); \
}

#else

#define SLOGF(level, format, args...) \
    do { printf(format "\n", ##args); } while(0)

#endif


/* ------------------------------------------------------- */
/* Declaration of interface variables */
%(located_variables_declaration)s

/* Process data */
uint8_t *domain1_pd = NULL;
%(used_pdo_entry_offset_variables_declaration)s

/* PDO entry registration */
const static ec_pdo_entry_reg_t domain1_regs[] = {
%(used_pdo_entry_configuration)s
    {}
};

/* Distributed Clock variables */
%(dc_variable)s
unsigned long long comp_period_ns = 500000ULL;
int comp_count = 1;
int comp_count_max;
#define DC_FILTER_CNT 1024

static uint64_t dc_start_time_ns = 0LL;
static uint64_t dc_time_ns = 0;
static uint8_t  dc_started = 0;
static int32_t  dc_diff_ns = 0;
static int32_t  prev_dc_diff_ns = 0;
static int64_t  dc_diff_total_ns = 0LL;
static int64_t  dc_delta_total_ns = 0LL;
static int      dc_filter_idx = 0;
static uint64_t dc_first_app_time = 0LL;
unsigned long long frame_period_ns = 0ULL;

int debug_count = 0;
int slave_dc_used = 0;

/* ---------------------- */
/* Funciones de DC y temporización */
void dc_init(void);
void sync_distributed_clocks(void);
void update_master_clock(void);
RTIME_TYPE calculate_sleeptime(uint64_t wakeup_time);
uint64_t calculate_first(void);

/* ---------------------- */
/* PDO Configuration */
%(pdos_configuration_declaration)s

long long wait_period_ns = 100000LL;

/* ---------------------- */
/* EtherCAT master */
static ec_master_t *master = NULL;
static ec_domain_t *domain1 = NULL;
static int first_sent=0;
%(slaves_declaration)s

/*#define SLOGF(level, format, args...) \*/
/*{ \*/
/*    char sbuf[256]; \*/
/*    int slen = snprintf(sbuf , sizeof(sbuf) , format , ##args); \*/
/*    LogMessage(level, sbuf, slen); \*/
/*}*/

/* ---------------------- */
/* EtherCAT plugin functions */
int __init_%(location)s(int argc, void **argv)
{
    master = ecrt_request_master(%(master_number)d);
    if (!master) {
        SLOGF(LOG_CRITICAL, "EtherCAT master request failed!");
        return -1;
    }

    if (!(domain1 = ecrt_master_create_domain(master))) {
        SLOGF(LOG_CRITICAL, "EtherCAT Domain Creation failed!");
        goto ecat_failed;
    }

    /* slaves PDO configuration */
%(slaves_configuration)s

    if (ecrt_domain_reg_pdo_entry_list(domain1, domain1_regs)) {
        SLOGF(LOG_CRITICAL, "EtherCAT PDO registration failed!");
        goto ecat_failed;
    }

    ecrt_master_set_send_interval(master, common_ticktime__);

#if DC_ENABLE
    {
        int ret;
        ret = ecrt_master_select_reference_clock(master, slave0);
        if (ret <0) {
            fprintf(stderr, "Failed to select reference clock : %%s\n", strerror(-ret));
            return ret;
        }
    }
#endif

#if DC_ENABLE
    dc_init();
#endif

    if (ecrt_master_activate(master)) {
        SLOGF(LOG_CRITICAL, "EtherCAT Master activation failed");
        goto ecat_failed;
    }

    if (!(domain1_pd = ecrt_domain_data(domain1))) {
        SLOGF(LOG_CRITICAL, "Failed to map EtherCAT process data");
        goto ecat_failed;
    }

    SLOGF(LOG_INFO, "Master %(master_number)d activated.");
    first_sent = 0;
    return 0;

ecat_failed:
    ecrt_release_master(master);
    return -1;
}

void __cleanup_%(location)s(void)
{
    ecrt_release_master(master);
    first_sent = 0;
}

void __retrieve_%(location)s(void)
{
    if(first_sent){
        ecrt_master_receive(master);
        ecrt_domain_process(domain1);
%(retrieve_variables)s
    }
}

void __publish_%(location)s(void)
{
%(publish_variables)s
    ecrt_domain_queue(domain1);

#if DC_ENABLE
    if (comp_count == 0)
        sync_distributed_clocks();
#endif

    ecrt_master_send(master);
    first_sent = 1;

#if DC_ENABLE
    if (comp_count == 0)
        update_master_clock();
    comp_count++;
    if (comp_count == comp_count_max) comp_count = 0;
#endif
}

/* ---------------------- */
/* SDO functions */
int GetMasterData(void)
{
    master = ecrt_open_master(0);
    if (!master) {
        SLOGF(LOG_CRITICAL, "EtherCAT master request failed!");
        return -1;
    }
    return 0;
}

void ReleaseMasterData(void)
{
    ecrt_release_master(master);
}

uint32_t GetSDOData(uint16_t slave_pos, uint16_t idx, uint8_t subidx, int size)
{
    uint32_t abort_code, return_value;
    size_t result_size;
    uint8_t value[size];

    abort_code = 0;
    result_size = 0;

    if (ecrt_master_sdo_upload(master, slave_pos, idx, subidx, value, size, &result_size, &abort_code)) {
        SLOGF(LOG_CRITICAL, "EtherCAT failed to get SDO Value %d %d", idx, subidx);
    }

    return_value = EC_READ_S32(value);
    return return_value;
}

/* ---------------------- */
/* DC and clock functions */
void dc_init(void)
{
    slave_dc_used = 1;

    frame_period_ns = common_ticktime__;
    comp_count_max = (frame_period_ns <= comp_period_ns) ? (comp_period_ns / frame_period_ns) : 1;
    comp_count = 0;

    dc_start_time_ns = system_time_ns();
    dc_time_ns = dc_start_time_ns;
    dc_first_app_time = dc_start_time_ns;

    ecrt_master_application_time(master, dc_start_time_ns);
}

void sync_distributed_clocks(void)
{
    uint32_t ref_time = 0;
    RTIME_TYPE prev_app_time = dc_time_ns;

    if(!ecrt_master_reference_clock_time(master, &ref_time)) {
        dc_diff_ns = (uint32_t) prev_app_time - ref_time;
    }

    ecrt_master_sync_slave_clocks(master);
    dc_time_ns = system_time_ns();
    ecrt_master_application_time(master, dc_time_ns);
}

void update_master_clock(void)
{
    int32_t delta = dc_diff_ns - prev_dc_diff_ns;
    prev_dc_diff_ns = dc_diff_ns;

    dc_diff_ns = dc_diff_ns >= 0 ?
        ((dc_diff_ns + (int32_t)(frame_period_ns / 2)) % (int32_t)frame_period_ns) - (frame_period_ns / 2) :
        ((dc_diff_ns - (int32_t)(frame_period_ns / 2)) % (int32_t)frame_period_ns) - (frame_period_ns / 2);

    if (dc_started) {
        dc_diff_total_ns += dc_diff_ns;
        dc_delta_total_ns += delta;
        dc_filter_idx++;

        if (dc_filter_idx >= DC_FILTER_CNT) {
            dc_adjust_ns += (dc_delta_total_ns >= 0) ?
                ((dc_delta_total_ns + (DC_FILTER_CNT / 2)) / DC_FILTER_CNT) :
                ((dc_delta_total_ns - (DC_FILTER_CNT / 2)) / DC_FILTER_CNT);

            dc_adjust_ns += sign(dc_diff_total_ns / DC_FILTER_CNT);

            if (dc_adjust_ns < -1000) dc_adjust_ns = -1000;
            if (dc_adjust_ns > 1000) dc_adjust_ns = 1000;

            dc_diff_total_ns = 0LL;
            dc_delta_total_ns = 0LL;
            dc_filter_idx = 0;
        }

        system_time_base += dc_adjust_ns + sign(dc_diff_ns);
    } else {
        dc_started = (dc_diff_ns != 0);
        if (dc_started) dc_start_time_ns = dc_time_ns;
    }
}

RTIME_TYPE calculate_sleeptime(uint64_t wakeup_time)
{
    RTIME_TYPE wakeup_count = system2count(wakeup_time);
    RTIME_TYPE current_count = system_time_ns();

    if ((wakeup_count < current_count) || (wakeup_count > current_count + (50 * frame_period_ns))) {
        fprintf(stderr, "%s(): unexpected wake time! wc = %lld\tcc = %lld\n",
            __func__, (long long)wakeup_count, (long long)current_count);
    }

    return wakeup_count;
}

uint64_t calculate_first(void)
{
    uint64_t dc_remainder = 0LL;
    uint64_t dc_phase_set_time = 0LL;

    dc_phase_set_time = system_time_ns() + frame_period_ns * 10;
    dc_remainder = (dc_phase_set_time - dc_first_app_time) % frame_period_ns;

    return dc_phase_set_time + frame_period_ns - dc_remainder;
}

