
#include "canfestival.h"

%(nodes_includes)s

#define BOARD_DECL(nodename, busname, baudrate)\
    s_BOARD nodename##Board = {busname, baudrate};

%(board_decls)s

static int init_level=0;
extern int common_ticktime__;


static void ConfigureSlaveNode(CO_Data* d, UNS8 nodeId)
{
    /* Put the master in operational mode */
    setState(d, Operational);
      
    /* Ask slave node to go in operational mode */
    masterSendNMTstateChange (d, 0, NMT_Start_Node);
}

#define NODE_DECLARE(nodename, nodeid)\
void nodename##_preOperational()\
{\
    ConfigureSlaveNode(&nodename##_Data, nodeid);\
}\

%(nodes_declare)s


#define NODE_INIT(nodename, nodeid) \
    /* Artificially force sync state to 1 so that it is not started */\
    nodename##_Data.CurrentCommunicationState.csSYNC = -1;\
    /* Force sync period to common_ticktime__ so that other node can read it*/\
    *nodename##_Data.COB_ID_Sync = 0x40000080;\
    *nodename##_Data.Sync_Cycle_Period = common_ticktime__ * 1000;\
    /* Defining the node Id */\
    setNodeId(&nodename##_Data, nodeid);\
    /* init */\
    setState(&nodename##_Data, Initialisation);

void InitNodes(CO_Data* d, UNS32 id)
{
    %(nodes_init)s
}

#define NODE_CLOSE(nodename) \
    if(init_level-- > 0)\
    {\
        EnterMutex();\
        setState(&nodename##_Data, Stopped);\
        LeaveMutex();\
        canClose(&nodename##_Data);\
    }

void __cleanup_%(locstr)s()
{
    %(nodes_close)s
    
    // Stop timer thread
    if(init_level-- > 0)
        StopTimerLoop();

}

#define NODE_OPEN(nodename)\
    nodename##_Data.preOperational = nodename##_preOperational;\
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
    /*Send Sync */
    %(nodes_send_sync)s
}

#define NODE_PROCEED_SYNC(nodename)\
    proceedSYNC(&nodename##_Data);

void __publish_%(locstr)s()
{
    /*Call SendPDOEvent */
    %(nodes_proceed_sync)s
    LeaveMutex();
}

