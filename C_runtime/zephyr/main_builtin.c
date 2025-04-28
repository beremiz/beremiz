#include <stdio.h>
#include <zephyr/kernel.h>

/* 1000 msec = 1 sec */
#define SLEEP_TIME_MS   1000


int startPLC(int argc, char **argv);

int main(void)
{
	printf("Beremiz non-programmable runtime for Zephyr\n");

	// This create a thread for the PLC and starts the PLC
	int res = startPLC(0, NULL);
	printf("PLC started (startPLC = %d)\n", res);

	// Temporarily loop forever - TODO: answer basic tty cli instead
	while (1) {
        k_msleep(SLEEP_TIME_MS);
    }

	return 0;
}
