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

IEC_INT beremiz__IW%(location)s_0;
IEC_INT *__IW%(location)s_0 = &beremiz__IW%(location)s_0;

%(MCL_headers)s

IEC_UINT __InactiveMask = 0x4f;
IEC_UINT __ActiveMask = 0x6f;
IEC_UINT __PowerMask = 0x10;

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
	axis_s* axis;
} __DS402Node;

static __DS402Node __DS402Node_%(location)s;

%(extern_located_variables_declaration)s

int __init_%(location)s()
{
%(init_entry_variables)s;
*__IW%(location)s_0 = __MK_AllocAxis(&(__DS402Node_%(location)s.axis));
	return 0;
}

void __cleanup_%(location)s()
{
}

void __retrieve_%(location)s()
{
	IEC_UINT statusword_inactive = *(__DS402Node_%(location)s.StatusWord) & __InactiveMask;
	IEC_UINT statusword_active = *(__DS402Node_%(location)s.StatusWord) & __ActiveMask;

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

	__DS402Node_%(location)s.axis->PowerFeedback = __DS402Node_%(location)s.state == __OperationEnabled;
	__DS402Node_%(location)s.axis->ActualPosition = (IEC_REAL)(*(__DS402Node_%(location)s.ActualPosition)) * __DS402Node_%(location)s.axis->RatioDenominator / __DS402Node_%(location)s.axis->RatioNumerator;

	__MK_UpdateAxis(*__IW%(location)s_0);
}

void __publish_%(location)s()
{
	__MK_ComputeAxis(*__IW%(location)s_0);

	IEC_BOOL power = ((*(__DS402Node_%(location)s.StatusWord) & __PowerMask) > 0) && __DS402Node_%(location)s.axis->Power;

	// DS402 node state transition computation
	switch (__DS402Node_%(location)s.state) {
	    case __SwitchOnDisabled:
	    	*(__DS402Node_%(location)s.ControlWord) = (*(__DS402Node_%(location)s.ControlWord) & ~0x87) | 0x06;
	    	break;
	    case __ReadyToSwitchOn:
	    case __OperationEnabled:
	    	if (!power) {
	    		*(__DS402Node_%(location)s.ControlWord) = (*(__DS402Node_%(location)s.ControlWord) & ~0x8f) | 0x07;
	    		break;
	    	}
	    case __SwitchedOn:
	    	if (power) {
	    	    *(__DS402Node_%(location)s.ControlWord) = (*(__DS402Node_%(location)s.ControlWord) & ~0x8f) | 0x0f;
	    	}
	    	break;
	    case __Fault:
	    	*(__DS402Node_%(location)s.ControlWord) = (*(__DS402Node_%(location)s.ControlWord) & ~0x8f) | 0x80;
	    	break;
	    default:
	    	break;
	}

	if (__DS402Node_%(location)s.axis->CSP && *(__DS402Node_%(location)s.ModesOfOperationDisplay) == 0x08) {
		*(__DS402Node_%(location)s.TargetPosition) = (IEC_DINT)(__DS402Node_%(location)s.axis->PositionSetPoint * __DS402Node_%(location)s.axis->RatioNumerator / __DS402Node_%(location)s.axis->RatioDenominator);
	}
	else {
		*(__DS402Node_%(location)s.TargetPosition) = *(__DS402Node_%(location)s.ActualPosition);
	}
}
