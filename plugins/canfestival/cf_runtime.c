
#include "canfestival.h"

%(nodes_includes)s

#define BOARD_DECL(nodename, busname, baudrate)\
    s_BOARD nodename##Board = {busname, baudrate};

%(board_decls)s

static int init_level=0;

#define NODE_INIT(nodename, nodeid) \
    /* Defining the node Id */\
    setNodeId(&nodename##_Data, nodeid);\
    /* init */\
    setState(&nodename##_Data, Initialisation);

void InitNodes(CO_Data* d, UNS32 id)
{
    %(nodes_init)s
}

#define NODE_CLOSE(nodename) \
    if(init_level--)\
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
    StopTimerLoop();

}

#define NODE_OPEN(nodename)\
    if(!canOpen(&nodename##Board,&nodename##_Data)){\
        printf("Cannot open " #nodename " Board (%%s,%%s)\n",nodename##Board.busname, nodename##Board.baudrate);\
        __cleanup_%(locstr)s();\
        return -1;\
    }\
    init_level++;

/***************************  INIT  *****************************************/
int __init_%(locstr)s(int argc,char **argv)
{

    %(nodes_open)s

#ifndef NOT_USE_DYNAMIC_LOADING
    LoadCanDriver("libcanfestival_can_%(candriver)s.so");
#endif      
    // Start timer thread
    StartTimerLoop(&InitNodes);
    return 0;
}

void __retrive_%(locstr)s()
{
    /*TODO: Send Sync */
    EnterMutex();
}

void __publish_%(locstr)s()
{
    /*TODO: Call SendPDOEvent */
    LeaveMutex();
}

