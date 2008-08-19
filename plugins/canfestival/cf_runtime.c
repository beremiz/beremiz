
#include "canfestival.h"

/* CanFestival nodes generated OD headers*/
%(nodes_includes)s

#define BOARD_DECL(nodename, busname, baudrate)\
    s_BOARD nodename##Board = {busname, baudrate};

/* CAN channels declaration */
%(board_decls)s

/* Keep track of init level to cleanup correctly */
static int init_level=0;
/* Retrieve PLC cycle time */
extern int common_ticktime__;

/* Called once all NetworkEdit declares slaves have booted*/
static void Master_post_SlaveBootup(CO_Data* d, UNS8 nodeId)
{
    /* Put the master in operational mode */
    setState(d, Operational);
      
    /* Ask slave node to go in operational mode */
    masterSendNMTstateChange (d, 0, NMT_Start_Node);
}

/* Per master node slavebootup callbacks. Checks that
 * every node have booted before calling Master_post_SlaveBootup */
%(slavebootups)s

/* One slave node post_sync callback.
 * Used to align PLC tick-time on CANopen SYNC 
 */
%(post_sync)s

#define NODE_FORCE_SYNC(nodename) \
    /* Artificially force sync state to 1 so that it is not started */\
    nodename##_Data.CurrentCommunicationState.csSYNC = -1;\
    /* Force sync period to common_ticktime__ so that other node can read it*/\
    *nodename##_Data.COB_ID_Sync = 0x40000080;\
    *nodename##_Data.Sync_Cycle_Period = common_ticktime__ * 1000;

#define NODE_INIT(nodename, nodeid) \
    /* Defining the node Id */\
    setNodeId(&nodename##_Data, nodeid);\
    /* init */\
    setState(&nodename##_Data, Initialisation);

#define NODE_MASTER_INIT(nodename, nodeid) \
	NODE_FORCE_SYNC(nodename) \
	NODE_INIT(nodename, nodeid)

#define NODE_SLAVE_INIT(nodename, nodeid) \
	NODE_INIT(nodename, nodeid)

void InitNodes(CO_Data* d, UNS32 id)
{
	%(slavebootup_register)s
	%(post_sync_register)s
    %(nodes_init)s
}

void Exit(CO_Data* d, UNS32 id)
{
}

#define NODE_CLOSE(nodename) \
    if(init_level-- > 0)\
    {\
        EnterMutex();\
        masterSendNMTstateChange(&nodename##_Data, 0, NMT_Reset_Node);\
        setState(&nodename##_Data, Stopped);\
        LeaveMutex();\
        canClose(&nodename##_Data);\
    }

void __cleanup_%(locstr)s()
{
    // Stop timer thread
    if(init_level-- > 0){
        StopTimerLoop(&Exit);
        %(nodes_close)s
   }
    #if !defined(WIN32) || defined(__CYGWIN__)
   		TimerCleanup();
    #endif
}

#define NODE_OPEN(nodename)\
    if(!canOpen(&nodename##Board,&nodename##_Data)){\
        printf("Cannot open " #nodename " Board (%%s,%%s)\n",nodename##Board.busname, nodename##Board.baudrate);\
        return -1;\
    }\
    init_level++;

/***************************  INIT  *****************************************/
int __init_%(locstr)s(int argc,char **argv)
{
#ifndef NOT_USE_DYNAMIC_LOADING
    if( !LoadCanDriver("%(candriver)s") ){
        fprintf(stderr, "Cannot load CAN interface library for CanFestival (%(candriver)s)\n");\
        return -1;
    }
#endif      
	#if !defined(WIN32) || defined(__CYGWIN__)
		TimerInit();
	#endif
	
    %(nodes_open)s

    // Start timer thread
    StartTimerLoop(&InitNodes);
    init_level++;
    return 0;
}

#define NODE_SEND_SYNC(nodename)\
    sendSYNCMessage(&nodename##_Data);

void __retrieve_%(locstr)s()
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

void __publish_%(locstr)s()
{
    /* Process sync event */
    %(nodes_proceed_sync)s
    LeaveMutex();
}

