/*
 * Python Asynchronous execution code
 *
 * PLC put python commands in a fifo, respecting execution order
 * with the help of C pragmas inserted in python_eval FB code
 *
 * Buffer content is read asynchronously, (from non real time part),
 * commands are executed and result stored for later use by PLC.
 *
 * In this implementation, fifo is a list of pointer to python_eval
 * function blocks structures. Some local variables have been added in
 * python_eval interface. We use those local variables as buffer and state
 * flags.
 *
 * */

#include "iec_types_all.h"
#include "accessor.h"
#include "POUS.h"
#include <string.h>
#ifdef BEREMIZ_TEST_CYCLES
#include <time.h>
#endif

/* The fifo (fixed size, as number of FB is fixed) */
static PYTHON_EVAL_data__* EvalFBs[%(python_eval_fb_count)d];
/* Producer and consumer cursors */
static int Current_PLC_EvalFB;
static int Current_Python_EvalFB;

/* A global IEC-Python gateway state, for use inside python_eval FBs*/
static int PythonState;
#define PYTHON_LOCKED_BY_PYTHON 0
#define PYTHON_LOCKED_BY_PLC 1
#define PYTHON_MUSTWAKEUP 2
#define PYTHON_FINISHED 4

/* Hold back new requests, set by PLCObject around a logic hot-swap. */
static int PythonPurge;

/* Each python_eval FunctionBlock have it own state */
#define PYTHON_FB_FREE 0
#define PYTHON_FB_REQUESTED 1
#define PYTHON_FB_PROCESSING 2
#define PYTHON_FB_ANSWERED 3

int WaitPythonCommands(void);
void UnBlockPythonCommands(void);
int TryLockPython(void);
void UnLockPython(void);
void LockPython(void);

int __init_py_ext()
{
	int i;
	/* Initialize cursors */
	Current_Python_EvalFB = 0;
	Current_PLC_EvalFB = 0;
	PythonState = PYTHON_LOCKED_BY_PYTHON;
	PythonPurge = 0;
	for(i = 0; i < %(python_eval_fb_count)d; i++)
		EvalFBs[i] = NULL;
  return 0;
}

void __cleanup_py_ext()
{
	PythonState = PYTHON_FINISHED;
	UnBlockPythonCommands();
}

void __retrieve_py_ext()
{
	/* Defensive: an enqueue outside a retrieve/publish window would otherwise
	 * lose its wakeup here, PythonState being rewritten wholesale below. */
	int mustwakeup = PythonState & PYTHON_MUSTWAKEUP;
#ifdef BEREMIZ_TEST_CYCLES
	/* Emulated time: wait for python thread to answer all requests, as if
	 * it took no time, so that answers come at the next cycle, always */
	LockPython();
	while(EvalFBs[Current_Python_EvalFB] && !(PythonState & PYTHON_FINISHED)){
		struct timespec delay = {0, 100000};
		UnLockPython();
		nanosleep(&delay, NULL);
		LockPython();
	}
	PythonState = PYTHON_LOCKED_BY_PLC;
#else
	/* Check Python thread is not being
	 * modifying internal python_eval data */
	PythonState = TryLockPython() ?
	                PYTHON_LOCKED_BY_PLC :
	                PYTHON_LOCKED_BY_PYTHON;
#endif
	/* If python thread _is_ in, then PythonState remains PYTHON_LOCKED_BY_PYTHON
	 * and python_eval will no do anything */
	PythonState |= mustwakeup;
}

void __publish_py_ext()
{
	if(PythonState & PYTHON_LOCKED_BY_PLC){
		/* If runnig PLC did push something in the fifo*/
		if(PythonState & PYTHON_MUSTWAKEUP){
			/* WakeUp python thread */
			PythonState &= ~PYTHON_MUSTWAKEUP;
			UnBlockPythonCommands();
		}
		UnLockPython();
	}
}
/**
 * Called by the PLC, each time a python_eval
 * FB instance is executed
 */
void __PythonEvalFB(int poll, PYTHON_EVAL_data__* data__)
{
    if(!__GET_VAR(data__->TRIG)){
        /* ACK is False when TRIG is false, except a pulse when receiving result */
        __SET_VAR(data__->, ACK,, 0);
    }
	/* detect rising edge on TRIG to trigger evaluation */
	if(((__GET_VAR(data__->TRIG) && !__GET_VAR(data__->TRIGM1)) ||
	   /* polling is equivalent to trig on value rather than on rising edge*/
	    (poll && __GET_VAR(data__->TRIG) )) &&
	    /* trig only if not already trigged */
	    __GET_VAR(data__->TRIGGED) == 0){
		/* mark as trigged */
	    __SET_VAR(data__->, TRIGGED,, 1);
		/* make a safe copy of the code */
		__SET_VAR(data__->, PREBUFFER,, __GET_VAR(data__->CODE));
	}
	/* retain value for next rising edge detection */
	__SET_VAR(data__->, TRIGM1,, __GET_VAR(data__->TRIG));

	 /* enqueue if not purging and if python is already in */
	if(!PythonPurge && PythonState & PYTHON_LOCKED_BY_PLC) {
		/* Refresh the fifo entry of a request in flight.  A logic hot-swap
		 * copies SLOT over to the instance replacing this one and invalidates
		 * the entries it leaves behind, so claiming the entry here is what
		 * makes the answer land in the instance the PLC actually runs.  A
		 * cleared entry means the python thread gave up on it before we got
		 * here: ask again rather than wait for an answer that will not come. */
		if(__GET_VAR(data__->STATE) == PYTHON_FB_REQUESTED ||
		   __GET_VAR(data__->STATE) == PYTHON_FB_PROCESSING){
			int slot = (int)__GET_VAR(data__->SLOT);
			if(slot < 0){
				/* invalidated by a hot-swap, ~slot holds the entry index */
				slot = ~slot;
				__SET_VAR(data__->, SLOT,, slot);
			}
			if(EvalFBs[slot] == NULL)
				__SET_VAR(data__->, STATE,, PYTHON_FB_FREE);
			else if(EvalFBs[slot] != data__)
				EvalFBs[slot] = data__;
		}
		/* if some answer are waiting, publish*/
		if(__GET_VAR(data__->STATE) == PYTHON_FB_ANSWERED){
			/* Copy buffer content into result*/
			__SET_VAR(data__->, RESULT,, __GET_VAR(data__->BUFFER));
			/* signal result presence to PLC*/
			__SET_VAR(data__->, ACK,, 1);
			/* Mark as free */
			__SET_VAR(data__->, STATE,, PYTHON_FB_FREE);
			/* mark as not trigged */
			if(!poll)
			    __SET_VAR(data__->, TRIGGED,, 0);
			/*printf("__PythonEvalFB pop %%d - %%*s\n",Current_PLC_EvalFB, data__->BUFFER.len, data__->BUFFER.body);*/
		}else if(poll){
			/* when in polling, no answer == ack down */
		    __SET_VAR(data__->, ACK,, 0);
		}
		/* got the order to act ?*/
		if(__GET_VAR(data__->TRIGGED) == 1 &&
		   /* and not already being processed */
		   __GET_VAR(data__->STATE) == PYTHON_FB_FREE)
		{
			/* Enter the block in the fifo
			 * Don't have to check if fifo cell is free
			 * as fifo size == FB count, and a FB cannot
			 * be requested twice */
			/* remember where, so that an instance swapped in later can claim
			 * this entry back (see above) */
			__SET_VAR(data__->, SLOT,, Current_PLC_EvalFB);
			/* copy into BUFFER local*/
			__SET_VAR(data__->, BUFFER,, __GET_VAR(data__->PREBUFFER));
			/* Set ACK pin to low so that we can set a rising edge on result */
			if(!poll){
				/* when not polling, a new answer imply reseting ack*/
			    __SET_VAR(data__->, ACK,, 0);
			}else{
				/* when in polling, acting reset trigger */
			    __SET_VAR(data__->, TRIGGED,, 0);
			}
			/* Mark FB busy */
			__SET_VAR(data__->, STATE,, PYTHON_FB_REQUESTED);
			/* Only now publish the entry: the python thread drops entries that
			 * do not claim their index, so it must never see a half filled one
			 * (py_ext's own instances run outside the python mutex) */
			EvalFBs[Current_PLC_EvalFB] = data__;
			/* Have to wakeup python thread in case he was asleep */
			PythonState |= PYTHON_MUSTWAKEUP;
			/*printf("__PythonEvalFB push %%d - %%*s\n",Current_PLC_EvalFB, data__->BUFFER.len, data__->BUFFER.body);*/
			/* Get a new line */
			Current_PLC_EvalFB = (Current_PLC_EvalFB + 1) %% %(python_eval_fb_count)d;
		}
	}
}

char* PythonIterator(char* result, void** id, int* is_last)
{
	char* next_command;
	PYTHON_EVAL_data__* data__;
	//printf("PythonIterator result %%s\n", result);
    /*emergency exit*/
    if(PythonState & PYTHON_FINISHED) return NULL;
	/* take python mutex to prevent changing PLC data while PLC running */
	LockPython();
	/* Get current FB */
	data__ = EvalFBs[Current_Python_EvalFB];
	if(data__ && /* may be null at first run */
	    __GET_VAR(data__->SLOT) == Current_Python_EvalFB && /* still its entry */
	    __GET_VAR(data__->STATE) == PYTHON_FB_PROCESSING){ /* some answer awaited*/
	   	/* If result not None */
	   	if(result){
			/* Get results len */
	   	    __SET_VAR(data__->, BUFFER, .len, strlen(result));
			/* prevent results overrun */
			if(__GET_VAR(data__->BUFFER, .len) > STR_MAX_LEN)
			{
			    __SET_VAR(data__->, BUFFER, .len, STR_MAX_LEN);
				/* TODO : signal error */
			}
			/* Copy results to buffer */
			strncpy((char*)__GET_VAR(data__->BUFFER, .body), result, __GET_VAR(data__->BUFFER,.len));
	   	}else{
	   	    __SET_VAR(data__->, BUFFER, .len, 0);
	   	}
		/* remove block from fifo*/
		EvalFBs[Current_Python_EvalFB] = NULL;
		/* Mark block as answered */
		__SET_VAR(data__->, STATE,, PYTHON_FB_ANSWERED);
		/* Get a new line */
		Current_Python_EvalFB = (Current_Python_EvalFB + 1) %% %(python_eval_fb_count)d;
		//printf("PythonIterator ++ Current_Python_EvalFB %%d\n", Current_Python_EvalFB);
	}
	/* look for the next command to eval */
	while(1)
	{
		data__ = EvalFBs[Current_Python_EvalFB];
		if(data__ &&
		   /* an entry the FB no longer claims was left behind by a hot-swap,
		    * or has already been dealt with: drop it and move on, or we would
		    * wait on it forever */
		   (__GET_VAR(data__->SLOT) != Current_Python_EvalFB ||
		    __GET_VAR(data__->STATE) != PYTHON_FB_REQUESTED))
		{
			EvalFBs[Current_Python_EvalFB] = NULL;
			Current_Python_EvalFB = (Current_Python_EvalFB + 1) %% %(python_eval_fb_count)d;
			continue;
		}
		/* slot holds a command */
		if(data__) break;
		/* slot is empty */
		UnLockPython();
		/* wait next FB to eval */
		//printf("PythonIterator wait\n");
		if(WaitPythonCommands()) return NULL;
		/*emergency exit*/
		if(PythonState & PYTHON_FINISHED) return NULL;
		LockPython();
	}
	/* Mark block as processing */
	__SET_VAR(data__->, STATE,, PYTHON_FB_PROCESSING);
	//printf("PythonIterator\n");
	/* make BUFFER a null terminated string */
	__SET_VAR(data__->, BUFFER, .body[__GET_VAR(data__->BUFFER, .len)], 0);
	/* next command is BUFFER */
	next_command = (char*)__GET_VAR(data__->BUFFER, .body);
	*id=data__;
    /*check if last command in the queue */
	*is_last = EvalFBs[(Current_Python_EvalFB + 1) %% %(python_eval_fb_count)d] == NULL;
	/* free python mutex */
	UnLockPython();
	/* return the next command to eval */
	return next_command;
}

void PythonSetPurge(int value){
	PythonPurge = value;
}

/* Logic lifecycle hook (see plc_ios_main_head.c): the logic .so became active.
 * Called by the PLC thread right after instance state was copied over, so the
 * fifo may still refer to instances of the .so being replaced.  Invalidate
 * every entry: whichever instance the PLC actually runs claims its own back on
 * its next execution (~i keeps the index so it knows which), and what no
 * execution refreshes gets dropped by PythonIterator instead of stalling it.
 * Then re-enable Python eval FB processing, purged around a hot-swap by
 * PLCObject.py. */
void __logic_active_py_ext(void){
	int i;
	for(i = 0; i < %(python_eval_fb_count)d; i++)
		if(EvalFBs[i])
			__SET_VAR(EvalFBs[i]->, SLOT,, ~i);
	PythonSetPurge(0);
}