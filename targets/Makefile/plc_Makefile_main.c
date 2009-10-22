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
    return 0;
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
/* from plc_debugger.c */
int WaitDebugData(void)
{
    return 0;
}

/* Called by PLC thread when debug_publish finished
 * This is supposed to unlock debugger thread in WaitDebugData*/
void InitiateDebugTransfer(void)
{
}

void suspendDebug(void)
{
}

void resumeDebug(void)
{
}

/* from plc_python.c */
int WaitPythonCommands(void)
{
    return 0;
}

/* Called by PLC thread on each new python command*/
void UnBlockPythonCommands(void)
{
}

int TryLockPython(void)
{
	return 0;
}

void UnLockPython(void)
{
}

void LockPython(void)
{
}
