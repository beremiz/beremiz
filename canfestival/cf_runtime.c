
#include "canfestival.h"
#include "dcf.h"

/* CanFestival nodes generated OD headers*/
%(nodes_includes)s

#define BOARD_DECL(nodename, busname, baudrate)\
    s_BOARD nodename##Board = {busname, baudrate};

/* CAN channels declaration */
%(board_decls)s

/* Keep track of init level to cleanup correctly */
static int init_level=0;
/* Retrieve PLC cycle time */
extern unsigned long long common_ticktime__;

/* Per master node slavebootup callbacks. Checks that
 * every node have booted before calling Master_post_SlaveBootup */
%(slavebootups)s

/* One slave node post_sync callback.
 * Used to align PLC tick-time on CANopen SYNC
 */
%(post_sync)s

/* Triggers DCF transission
 */
%(pre_op)s

#define NODE_FORCE_SYNC(nodename) \
    /* Artificially force sync state to 1 so that it is not started */\
    nodename##_Data.CurrentCommunicationState.csSYNC = -1;\
    /* Force sync period to common_ticktime__ so that other node can read it*/\
    *nodename##_Data.COB_ID_Sync = 0x40000080;\
    *nodename##_Data.Sync_Cycle_Period = common_ticktime__ / 1000;

static void DeferedInitAlarm(CO_Data* d, UNS32 id){
    /* Node will start beeing active on the network after this */
    setState(d, Initialisation);
}

#define NODE_INIT(nodename, nodeid) \
    /* Defining the node Id */\
    setNodeId(&nodename##_Data, nodeid);\
    SetAlarm(&nodename##_Data,0,&DeferedInitAlarm,MS_TO_TIMEVAL(100),0);

#define NODE_MASTER_INIT(nodename, nodeid) \
    NODE_FORCE_SYNC(nodename) \
    NODE_INIT(nodename, nodeid)

#define NODE_SLAVE_INIT(nodename, nodeid) \
    NODE_INIT(nodename, nodeid)

static void InitNodes(CO_Data* d, UNS32 id)
{
    %(slavebootup_register)s
    %(post_sync_register)s
    %(pre_op_register)s
    %(nodes_init)s
}

#define NODE_STOP(nodename) \
    if(init_level-- > 0)\
    {\
        masterSendNMTstateChange(&nodename##_Data, 0, NMT_Reset_Node);\
        setState(&nodename##_Data, Stopped);\
    }

static void Exit(CO_Data* d, UNS32 id)
{
    %(nodes_stop)s
}

#define NODE_CLOSE(nodename) \
    if(init_level_c-- > 0)\
    {\
      canClose(&nodename##_Data);\
    }

void __cleanup_%(locstr)s(void)
{
    // Stop timer thread
    if(init_level-- > 0){
    int init_level_c = init_level;
        StopTimerLoop(&Exit);
        %(nodes_close)s
    }

    TimerCleanup();
}

#ifndef stderr
#define fprintf(...)
#define fflush(...)
#endif

#define NODE_OPEN(nodename)\
    if(!canOpen(&nodename##Board,&nodename##_Data)){\
        fprintf(stderr,"Cannot open CAN intefrace %%s at speed %%s\n for CANopen node \"" #nodename "\"",nodename##Board.busname, nodename##Board.baudrate);\
        fflush(stderr);\
        return -1;\
    }\
    init_level++;

/***************************  INIT  *****************************************/
int __init_%(locstr)s(int argc,char **argv)
{
#ifndef NOT_USE_DYNAMIC_LOADING
    if( !LoadCanDriver("%(candriver)s") ){
        fprintf(stderr, "Cannot load CAN interface library for CanFestival (%(candriver)s)\n");\
        fflush(stderr);\
        return -1;\
    }
#endif

    TimerInit();

    %(nodes_open)s

    // Start timer thread
    StartTimerLoop(&InitNodes);
    init_level++;
    return 0;
}

#define NODE_SEND_SYNC(nodename)\
    if(getState(&nodename##_Data)==Operational){\
        sendSYNCMessage(&nodename##_Data);\
    }

void __retrieve_%(locstr)s(void)
{
    /* Locks the stack, so that no changes occurs while PLC access variables
     * TODO : implement buffers to avoid such a big lock
     *  */
    EnterMutex();
    /* Send Sync */
    %(nodes_send_sync)s
}

#define NODE_PROCEED_SYNC(nodename)\
    proceedSYNC(&nodename##_Data);

void __publish_%(locstr)s(void)
{
    /* Process sync event */
    %(nodes_proceed_sync)s
    LeaveMutex();
}

/* Code placed here without a test to get it out of the way in plc_main_tail.c */
#define TARGET_EXT_SYNC_DISABLE
#ifndef TARGET_EXT_SYNC_DISABLE

#define CALIBRATED -2
#define NOT_CALIBRATED -1
static int calibration_count = NOT_CALIBRATED;
static IEC_TIME cal_begin;
static long long Tsync = 0;
static long long FreqCorr = 0;
static int Nticks = 0;
static unsigned int last_tick = 0;

/*
 * Called on each external periodic sync event
 * make PLC tick synchronous with external sync
 * ratio defines when PLC tick occurs between two external sync
 * @param sync_align_ratio 
 *          0->100 : align ratio
 *          < 0 : no align, calibrate period
 **/
void align_tick(int sync_align_ratio)
{
	/*
	printf("align_tick(%d)\n", calibrate);
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
			if( (Nticks = (Tsync / common_ticktime__)) > 0){
				FreqCorr = (Tsync % common_ticktime__); /* to be divided by Nticks */
			}else{
				FreqCorr = Tsync - (common_ticktime__ % Tsync);
			}
			/*
			printf("Tsync = %ld\n", Tsync);
			printf("calibration_count = %d\n", calibration_count);
			printf("Nticks = %d\n", Nticks);
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
				PhaseCorr = elapsed - (common_ticktime__ + FreqCorr/Nticks)*sync_align_ratio/100; /* to be divided by Nticks */
				Tcorr = common_ticktime__ + (PhaseCorr + FreqCorr) / Nticks;
				if(Nticks < 2){
					/* When Sync source period is near Tick time */
					/* PhaseCorr may not be applied to Periodic time given to timer */
					PeriodicTcorr = common_ticktime__ + FreqCorr / Nticks;
				}else{
					PeriodicTcorr = Tcorr;
				}
			}else if(__tick > last_tick){
				last_tick = __tick;
				PhaseCorr = elapsed - (Tsync*sync_align_ratio/100);
				PeriodicTcorr = Tcorr = common_ticktime__ + PhaseCorr + FreqCorr;
			}else{
				/*PLC did not run meanwhile. Nothing to do*/
				return;
			}
			/* DO ALIGNEMENT */
			PLC_SetTimer(Tcorr - elapsed, PeriodicTcorr);
		}
	}
}

#endif
