/**
 * Code common to all C targets
 **/

#include <locale.h>
#include "iec_types.h"
/*
 * Prototypes of functions provied by generated C softPLC
 **/
void config_run__(int tick);
void config_init__(void);

/*
 * Prototypes of functions provied by generated target C code
 * */
void __init_debug(void);
void __cleanup_debug(void);
/*void __retrieve_debug(void);*/
void __publish_debug(void);

void __init_python(void);
void __cleanup_python(void);
void __retrieve_python(void);
void __publish_python(void);

/*
 *  Variables used by generated C softPLC and plugins
 **/
IEC_TIME __CURRENT_TIME;
IEC_BOOL __DEBUG;
int __tick = -1;

/* Help to quit cleanly when init fail at a certain level */
static int init_level = 0;

/*
 * Prototypes of functions exported by plugins
 **/
%(calls_prototypes)s

/*
 * Retrieve input variables, run PLC and publish output variables
 **/
void __run()
{
    __tick++;

    %(retrieve_calls)s

    __retrieve_python();

    /*__retrieve_debug();*/

    config_run__(__tick);

    __publish_python();

    __publish_debug();

    %(publish_calls)s

}

/*
 * Initialize variables according to PLC's defalut values,
 * and then init plugins with that values
 **/
int __init(int argc,char **argv)
{
    int res;
    setlocale(LC_NUMERIC, "C");
    config_init__();
    __init_debug();
    __init_python();
    %(init_calls)s
    return 0;
}
/*
 * Calls plugin cleanup proc.
 **/
void __cleanup()
{
    %(cleanup_calls)s
    __cleanup_debug();
    __cleanup_python();
}


void PLC_GetTime(IEC_TIME *CURRENT_TIME);
void PLC_SetTimer(long long next, long long period);

#define CALIBRATED -2
#define NOT_CALIBRATED -1
static int calibration_count = NOT_CALIBRATED;
static IEC_TIME cal_begin;
static long long Tsync = 0;
static long long FreqCorr = 0;
static int Nticks = 0;
static int  last_tick = 0;
static long long Ttick = 0;
#define mod %%
/*
 * Call this on each external sync,
 * @param sync_align_ratio 0->100 : align ratio, < 0 : no align, calibrate period
 **/
void align_tick(int sync_align_ratio)
{
	/*
	printf("align_tick(%%d)\n", calibrate);
	*/
	if(sync_align_ratio < 0){ /* Calibration */
		if(calibration_count == CALIBRATED)
			/* Re-calibration*/
			calibration_count = NOT_CALIBRATED;
		if(calibration_count == NOT_CALIBRATED)
			/* Calibration start, get time*/
			PLC_GetTime(&cal_begin);
		calibration_count++;
	}else{ /* do alignment (if possible) */
		if(calibration_count >= 0){
			/* End of calibration */
			/* Get final time */
			IEC_TIME cal_end;
			PLC_GetTime(&cal_end);
			/*adjust calibration_count*/
			calibration_count++;
			/* compute mean of Tsync, over calibration period */
			Tsync = ((long long)(cal_end.tv_sec - cal_begin.tv_sec) * (long long)1000000000 +
					(cal_end.tv_nsec - cal_begin.tv_nsec)) / calibration_count;
			if( (Nticks = (Tsync / Ttick)) > 0){
				FreqCorr = (Tsync mod Ttick); /* to be divided by Nticks */
			}else{
				FreqCorr = Tsync - (Ttick mod Tsync);
			}
			/*
			printf("Tsync = %%ld\n", Tsync);
			printf("calibration_count = %%d\n", calibration_count);
			printf("Nticks = %%d\n", Nticks);
			*/
			calibration_count = CALIBRATED;
		}
		if(calibration_count == CALIBRATED){
			/* Get Elapsed time since last PLC tick (__CURRENT_TIME) */
			IEC_TIME now;
			long long elapsed;
			long long Tcorr;
			long long PhaseCorr;
			long long PeriodicTcorr;
			PLC_GetTime(&now);
			elapsed = (now.tv_sec - __CURRENT_TIME.tv_sec) * 1000000000 + now.tv_nsec - __CURRENT_TIME.tv_nsec;
			if(Nticks > 0){
				PhaseCorr = elapsed - (Ttick + FreqCorr/Nticks)*sync_align_ratio/100; /* to be divided by Nticks */
				Tcorr = Ttick + (PhaseCorr + FreqCorr) / Nticks;
				if(Nticks < 2){
					/* When Sync source period is near Tick time */
					/* PhaseCorr may not be applied to Periodic time given to timer */
					PeriodicTcorr = Ttick + FreqCorr / Nticks;
				}else{
					PeriodicTcorr = Tcorr;
				}
			}else if(__tick > last_tick){
				last_tick = __tick;
				PhaseCorr = elapsed - (Tsync*sync_align_ratio/100);
				PeriodicTcorr = Tcorr = Ttick + PhaseCorr + FreqCorr;
			}else{
				/*PLC did not run meanwhile. Nothing to do*/
				return;
			}
			/* DO ALIGNEMENT */
			PLC_SetTimer(Tcorr - elapsed, PeriodicTcorr);
		}
	}
}

/**
 * Prototypes for function provided by arch-specific code (main)
 * is concatained hereafter
 **/
