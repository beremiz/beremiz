/*
 * Etherlab Asynchronous execution code
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

// declaration of interface variables
%(located_variables_declaration)s

// Optional features
#define CONFIGURE_PDOS  %(configure_pdos)d

// process data
static uint8_t *domain1_pd = NULL;
%(used_pdo_entry_offset_variables_declaration)s

const static ec_pdo_entry_reg_t domain1_regs[] = {
%(used_pdo_entry_configuration)s
    {}
};
/*****************************************************************************/

#if CONFIGURE_PDOS
%(pdos_configuration_declaration)s
#endif

int rt_fd = -1;
CstructMstrAttach MstrAttach;
char rt_dev_file[64];
long long wait_period_ns = 100000LL;

// EtherCAT
static ec_master_t *master = NULL;
static ec_domain_t *domain1 = NULL;
%(slaves_declaration)s

/* Beremiz plugin functions */
int __init_%(location)s(int argc,char **argv)
{
	int rtstatus;

	MstrAttach.masterindex = %(master_number)d;

	master = ecrt_request_master(MstrAttach.masterindex);
	if (!master) return -1;

	domain1 = ecrt_master_create_domain(master);
	if (!domain1) return -1;

#if CONFIGURE_PDOS
	%(slaves_configuration)s
#endif

    if (ecrt_domain_reg_pdo_entry_list(domain1, domain1_regs)) {
        fprintf(stderr, "PDO entry registration failed!\n");
        return -1;
    }

    sprintf(&rt_dev_file[0],"%%s%%u",EC_RTDM_DEV_FILE_NAME,0);
    rt_fd = rt_dev_open( &rt_dev_file[0], 0);
    if (rt_fd < 0) {
        printf("Can't open %%s\n", &rt_dev_file[0]);
        return -1;
    }

    // attach the master over rtdm driver
    MstrAttach.domainindex = ecrt_domain_index(domain1);
    rtstatus = ecrt_rtdm_master_attach(rt_fd, &MstrAttach);
    if (rtstatus < 0) {
        printf("Cannot attach to master over rtdm\n");
        return -1;
    }

    if (ecrt_master_activate(master))
        return -1;

    if (!(domain1_pd = ecrt_domain_data(domain1))) {
        fprintf(stderr, "domain1_pd:  0x%%.6lx\n", (unsigned long)domain1_pd);
        return -1;
    }

    fprintf(stdout, "Master %(master_number)d activated...\n");
    return 0;
}

void __cleanup_%(location)s(void)
{
	if (rt_fd >= 0) {
		rt_dev_close(rt_fd);
	}
}

void __retrieve_%(location)s(void)
{
    // receive ethercat
    ecrt_rtdm_master_recieve(rt_fd);
    ecrt_rtdm_domain_process(rt_fd);

    rt_task_sleep(rt_timer_ns2tsc(wait_period_ns));

    // send process data
    ecrt_rtdm_domain_queque(rt_fd);
    ecrt_rtdm_master_send(rt_fd);

%(retrieve_variables)s
}

void __publish_%(location)s(void)
{
%(publish_variables)s
}
