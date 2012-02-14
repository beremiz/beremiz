/*
 * Ethercat DS402 node execution code
 *
 * */

#include "ecrt.h"

#ifdef _WINDOWS_H
  #include "iec_types.h"
#else
  #include "iec_std_lib.h"
#endif

%(MCL_includes)s

IEC_UINT __InactiveMask = 0x4f;
IEC_UINT __ActiveMask = 0x6f;

typedef enum {
	__Unknown,
	__NotReadyToSwitchOn,
	__SwitchOnDisabled,
	__ReadyToSwitchOn,
	__SwitchedOn,
	__OperationEnabled,
	__QuickStopActive,
	__FaultReactionActive,
	__Fault,
} __DS402NodeState;

typedef struct {
%(entry_variables)s
	__DS402NodeState state;
} __DS402Node;

static __DS402Node __DS402Node_%(location)s;

%(located_variables_declaration)s

extern uint8_t *domain1_pd;
%(extern_pdo_entry_configuration)s

int __init_%(location)s()
{
	return 0;
}

void __cleanup_%(location)s()
{
}

void __retrieve_%(location)s()
{
	IEC_UINT statusword_inactive = __DS402Node_%(location)s.StatusWord & __InactiveMask;
	IEC_UINT statusword_active = __DS402Node_%(location)s.StatusWord & __ActiveMask;

    // DS402 input entries extraction
%(retrieve_variables)s

	// DS402 node state computation
	__DS402Node_%(location)s.state = __Unknown;
	switch (statusword_inactive) {
		case 0x00:
			__DS402Node_%(location)s.state = __NotReadyToSwitchOn;
			break;
		case 0x40:
			__DS402Node_%(location)s.state = __SwitchOnDisabled;
			break;
		case 0x0f:
			__DS402Node_%(location)s.state = __FaultReactionActive;
			break;
		case 0x08:
			__DS402Node_%(location)s.state = __Fault;
			break;
		default:
			break;
	}
	switch (statusword_active) {
		case 0x21:
			__DS402Node_%(location)s.state = __ReadyToSwitchOn;
			break;
		case 0x23:
			__DS402Node_%(location)s.state = __SwitchedOn;
			break;
		case 0x27:
			__DS402Node_%(location)s.state = __OperationEnabled;
			break;
		case 0x07:
			__DS402Node_%(location)s.state = __QuickStopActive;
			break;
		default:
			break;
	}
	if (__DS402Node_%(location)s.state == __Unknown) {
		return;
	}

}

void __publish_%(location)s()
{
	// DS402 node state transition computation
	switch (__DS402Node_%(location)s.state) {
	    case __SwitchOnDisabled:
	    	__DS402Node_%(location)s.ControlWord = (__DS402Node_%(location)s.ControlWord & ~0x87) | 0x06;
	    	break;
	    case __ReadyToSwitchOn:
	    	__DS402Node_%(location)s.ControlWord = (__DS402Node_%(location)s.ControlWord & ~0x8f) | 0x07;
	    	break;
	    case __SwitchedOn:
	    	// if (POWER) {
	    	//      __DS402Node_%(location)s.ControlWord = (__DS402Node_%(location)s.ControlWord & ~0x8f) | 0x0f;
	    	// }
	    	break;
	    case __OperationEnabled:
	    	// if (!POWER) {
	        //      __DS402Node_%(location)s.ControlWord = (__DS402Node_%(location)s.ControlWord & ~0x8f) | 0x07;
	    	// }
	    	break;
	    case __Fault:
	    	__DS402Node_%(location)s.ControlWord = (__DS402Node_%(location)s.ControlWord & ~0x8f) | 0x80;
	    	break;
	    default:
	    	break;
	}

	// DS402 output entries setting
%(publish_variables)s
}
