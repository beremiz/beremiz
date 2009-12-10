/**
 * Yagarto specific code
 **/

//#include <stdio.h>

/* provided by POUS.C */
extern int common_ticktime__;

void Target_GetTime(IEC_TIME*);

long AtomicCompareExchange(long* atomicvar,long compared, long exchange)
{
	return 0;
}

void PLC_GetTime(IEC_TIME *CURRENT_TIME)
{
	/* Call target GetTime function */
	Target_GetTime(CURRENT_TIME);
}

void PLC_SetTimer(long long next, long long period)
{
}

int startPLC(int argc,char **argv)
{
	if(__init(argc,argv) == 0)
		return 0;
	else
		return 1;
}

int TryEnterDebugSection(void)
{
    return __DEBUG;
}

void LeaveDebugSection(void)
{
}

int stopPLC(void)
{
    __cleanup();
    return 0;
}

extern unsigned long __tick;
int _DebugDataAvailable = 0;
/* from plc_debugger.c */
int WaitDebugData(unsigned long *tick)
{
    *tick = __tick;
    return _DebugDataAvailable;
}

/* Called by PLC thread when debug_publish finished
 * This is supposed to unlock debugger thread in WaitDebugData*/
void InitiateDebugTransfer(void)
{
    _DebugDataAvailable = 1;
}

void suspendDebug(int disable)
{
    __DEBUG = !disable;
}

void resumeDebug(void)
{
    __DEBUG = 1;
}

void Retain(unsigned int offset, unsigned int count, void *p)
{
}

void Remind(unsigned int offset, unsigned int count, void *p)
{
}
