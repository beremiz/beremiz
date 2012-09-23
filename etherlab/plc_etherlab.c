/*
 * Etherlab execution code
 *
 * */

#include <rtdm/rtdm.h>
#include <native/task.h>
#include <native/timer.h>

#include "ecrt.h"
#include "ec_rtdm.h"

#ifdef _WINDOWS_H
  #include "iec_types.h"
#else
  #include "iec_std_lib.h"
#endif

extern unsigned long long common_ticktime__;

// declaration of interface variables
%(located_variables_declaration)s

// process data
uint8_t *domain1_pd = NULL;
%(used_pdo_entry_offset_variables_declaration)s

const static ec_pdo_entry_reg_t domain1_regs[] = {
%(used_pdo_entry_configuration)s
    {}
};
/*****************************************************************************/

%(pdos_configuration_declaration)s

int rt_fd = -1;
CstructMstrAttach MstrAttach;
char rt_dev_file[64];
long long wait_period_ns = 100000LL;

// EtherCAT
static ec_master_t *master = NULL;
static ec_domain_t *domain1 = NULL;
static int first_sent=0;
%(slaves_declaration)s

/* Beremiz plugin functions */
int __init_%(location)s(int argc,char **argv)
{
    uint32_t abort_code;
    size_t result_size;
    int i, rtstatus;
    
	MstrAttach.masterindex = %(master_number)d;

	master = ecrt_request_master(MstrAttach.masterindex);
	if (!master) return -1;

	domain1 = ecrt_master_create_domain(master);
	if (!domain1) return -1;

    // slaves PDO configuration
%(slaves_configuration)s

    if (ecrt_domain_reg_pdo_entry_list(domain1, domain1_regs)) {
        fprintf(stderr, "PDO entry registration failed!\n");
        return -1;
    }

	ecrt_master_set_send_interval(master, common_ticktime__);

    // slaves initialization
%(slaves_initialization)s

    // extracting default value for not mapped entry in output PDOs
%(slaves_output_pdos_default_values_extraction)s

    sprintf(&rt_dev_file[0],"%%s%%u",EC_RTDM_DEV_FILE_NAME,0);
    rt_fd = rt_dev_open( &rt_dev_file[0], 0);
    if (rt_fd < 0) {
        fprintf(stderr, "Can't open %%s\n", &rt_dev_file[0]);
        return -1;
    }

    // attach the master over rtdm driver
    MstrAttach.domainindex = ecrt_domain_index(domain1);
    rtstatus = ecrt_rtdm_master_attach(rt_fd, &MstrAttach);
    if (rtstatus < 0) {
        fprintf(stderr, "Cannot attach to master over rtdm\n");
        return -1;
    }

    if (ecrt_master_activate(master))
        return -1;

    if (!(domain1_pd = ecrt_domain_data(domain1))) {
        fprintf(stderr, "domain1_pd:  0x%%.6lx\n", (unsigned long)domain1_pd);
        return -1;
    }

    fprintf(stdout, "Master %(master_number)d activated...\n");
    
    first_sent = 0;

    return 0;
}

void __cleanup_%(location)s(void)
{
	if (rt_fd >= 0) {
		rt_dev_close(rt_fd);
	}
	//release master
	ecrt_release_master(master);
    first_sent = 0;
}

void __retrieve_%(location)s(void)
{
    // receive ethercat
    if(first_sent){
        ecrt_rtdm_master_recieve(rt_fd);
        ecrt_rtdm_domain_process(rt_fd);
%(retrieve_variables)s
    }

}

static RTIME _last_occur=0;
static RTIME _last_publish=0;
RTIME _current_lag=0;
RTIME _max_jitter=0;
static inline RTIME max(RTIME a,RTIME b){return a>b?a:b;}

void __publish_%(location)s(void)
{
%(publish_variables)s
    ecrt_rtdm_domain_queque(rt_fd);
    {
        RTIME current_time = rt_timer_read();
        // Limit spining max 1/5 of common_ticktime
        RTIME maxdeadline = current_time + (common_ticktime__ / 5);
        RTIME deadline = _last_occur ? 
            _last_occur + common_ticktime__ : 
            current_time + _max_jitter; 
        if(deadline > maxdeadline) deadline = maxdeadline;
        _current_lag = deadline - current_time;
        if(_last_publish != 0){
            RTIME period = current_time - _last_publish;
            if(period > common_ticktime__ )
                _max_jitter = max(_max_jitter, period - common_ticktime__);
            else
                _max_jitter = max(_max_jitter, common_ticktime__ - period);
        }
        _last_publish = current_time;
        _last_occur = current_time;
        while(current_time < deadline) {
            _last_occur = current_time; //Drift backward by default
            current_time = rt_timer_read();
        }
        if( _max_jitter * 10 < common_ticktime__ && _current_lag < _max_jitter){
            //Consuming security margin ?
            _last_occur = current_time; //Drift forward
        }
    }
    ecrt_rtdm_master_send(rt_fd);
    first_sent = 1;
}
