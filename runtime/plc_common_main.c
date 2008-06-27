/*
 * Prototypes for function provided by arch-specific code (main)
 * concatained after this template
 ** /


/*
 * Functions and variables provied by generated C softPLC
 **/ 
extern int common_ticktime__;

/*
 * Functions and variables provied by plc.c
 **/ 
void run(long int tv_sec, long int tv_nsec);

#define maxval(a,b) ((a>b)?a:b)

#include "iec_types.h"

/*
 * Functions and variables provied by generated C softPLC
 **/ 
void config_run__(int tick);
void config_init__(void);

/*
 *  Functions and variables to export to generated C softPLC
 **/
 
IEC_TIME __CURRENT_TIME;

static int tick = 0;
static int init_level=0;

/*
 * Prototypes of functions exported by plugins 
 **/
%(calls_prototypes)s

/*
 * Retrieve input variables, run PLC and publish output variables 
 **/
void __run()
{
    %(retrieve_calls)s
    
	/*
	printf("run tick = %%d\n", tick + 1);
	*/
    config_run__(tick++);
    
    %(publish_calls)s
}

/*
 * Initialize variables according to PLC's defalut values,
 * and then init plugins with that values  
 **/
int __init(int argc,char **argv)
{
    int res;
    config_init__();
    %(init_calls)s
    return 0;
}
/*
 * Calls plugin cleanup proc.
 **/
void __cleanup()
{
    %(cleanup_calls)s
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
 **/
void align_tick(int calibrate)
{
	/*
	printf("align_tick(%%d)\n", calibrate);
	*/
	if(calibrate){
		if(calibration_count == CALIBRATED)
			/* Re-calibration*/
			calibration_count = NOT_CALIBRATED;
		if(calibration_count == NOT_CALIBRATED)
			/* Calibration start, get time*/
			PLC_GetTime(&cal_begin);
		calibration_count++;
	}else{
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
				PhaseCorr = elapsed - (Ttick + FreqCorr/Nticks)*%(sync_align_ratio)d/100; /* to be divided by Nticks */
				Tcorr = Ttick + (PhaseCorr + FreqCorr) / Nticks;
				if(Nticks < 2){
					/* When Sync source period is near Tick time */
					/* PhaseCorr may not be applied to Periodic time given to timer */
					PeriodicTcorr = Ttick + FreqCorr / Nticks;
				}else{
					PeriodicTcorr = Tcorr; 
				}
			}else if(tick > last_tick){
				last_tick = tick;
				PhaseCorr = elapsed - (Tsync*%(sync_align_ratio)d/100);
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
