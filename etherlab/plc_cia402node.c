/*
 * Ethercat CIA402 node execution code
 *
 * */

#include "ecrt.h"

#ifdef _WINDOWS_H
  #include "iec_types.h"
#else
  #include "iec_std_lib.h"
#endif

#include "POUS.h"

IEC_INT beremiz__IW%(location)s_0;
IEC_INT *__IW%(location)s_0 = &beremiz__IW%(location)s_0;

%(MCL_headers)s

static IEC_UINT __InactiveMask = 0x4f;
static IEC_UINT __ActiveMask = 0x6f;
static IEC_UINT __PowerMask = 0x10;
static IEC_BOOL __FirstTick = 1;

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
} __CIA402NodeState;

typedef struct {
%(entry_variables)s
    __CIA402NodeState state;
    axis_s* axis;
} __CIA402Node;

#define AXIS_UNIT_TO_USER_UNIT(param)\
(IEC_LREAL)(param) * __CIA402Node_%(location)s.axis->RatioDenominator / __CIA402Node_%(location)s.axis->RatioNumerator
#define USER_UNIT_TO_AXIS_UNIT(param)\
(IEC_DINT)(param * __CIA402Node_%(location)s.axis->RatioNumerator / __CIA402Node_%(location)s.axis->RatioDenominator)

static __CIA402Node __CIA402Node_%(location)s;

%(extern_located_variables_declaration)s

%(fieldbus_interface_declaration)s

int __init_%(location)s()
{
%(init_entry_variables)s
	*__IW%(location)s_0 = __MK_Alloc_AXIS_REF();
	__CIA402Node_%(location)s.axis = __MK_GetPublic_AXIS_REF(*__IW%(location)s_0);
%(fieldbus_interface_definition)s
	__MK_Set_AXIS_REF_Pos(*__IW%(location)s_0, %(slave_pos)d);
	*(__CIA402Node_%(location)s.ModesOfOperation) = 0x08;
    return 0;
}

void __cleanup_%(location)s()
{
}

void __retrieve_%(location)s()
{
	IEC_UINT statusword_inactive = *(__CIA402Node_%(location)s.StatusWord) & __InactiveMask;
	IEC_UINT statusword_active = *(__CIA402Node_%(location)s.StatusWord) & __ActiveMask;

	if (__FirstTick) {
%(init_axis_params)s
		__FirstTick = 0;
	}

	// CIA402 node state computation
	__CIA402Node_%(location)s.state = __Unknown;
	switch (statusword_inactive) {
		case 0x00:
			__CIA402Node_%(location)s.state = __NotReadyToSwitchOn;
			break;
		case 0x40:
			__CIA402Node_%(location)s.state = __SwitchOnDisabled;
			break;
		case 0x0f:
			__CIA402Node_%(location)s.state = __FaultReactionActive;
			break;
		case 0x08:
			__CIA402Node_%(location)s.state = __Fault;
			break;
		default:
			break;
	}
	switch (statusword_active) {
		case 0x21:
			__CIA402Node_%(location)s.state = __ReadyToSwitchOn;
			break;
		case 0x23:
			__CIA402Node_%(location)s.state = __SwitchedOn;
			break;
		case 0x27:
			__CIA402Node_%(location)s.state = __OperationEnabled;
			break;
		case 0x07:
			__CIA402Node_%(location)s.state = __QuickStopActive;
			break;
		default:
			break;
	}
	if (__CIA402Node_%(location)s.state == __Unknown) {
		return;
	}

	// Default variables retrieve
	__CIA402Node_%(location)s.axis->PowerFeedback = __CIA402Node_%(location)s.state == __OperationEnabled;
	__CIA402Node_%(location)s.axis->ActualPosition = AXIS_UNIT_TO_USER_UNIT(*(__CIA402Node_%(location)s.ActualPosition));
	__CIA402Node_%(location)s.axis->ActualVelocity = AXIS_UNIT_TO_USER_UNIT(*(__CIA402Node_%(location)s.ActualVelocity));

	// Extra variables retrieve
%(extra_variables_retrieve)s
}

void __publish_%(location)s()
{
	IEC_BOOL power = ((*(__CIA402Node_%(location)s.StatusWord) & __PowerMask) > 0) && __CIA402Node_%(location)s.axis->Power;

	// CIA402 node state transition computation
	switch (__CIA402Node_%(location)s.state) {
	    case __SwitchOnDisabled:
	    	*(__CIA402Node_%(location)s.ControlWord) = (*(__CIA402Node_%(location)s.ControlWord) & ~0x87) | 0x06;
	    	break;
	    case __ReadyToSwitchOn:
	    case __OperationEnabled:
	    	if (!power) {
	    		*(__CIA402Node_%(location)s.ControlWord) = (*(__CIA402Node_%(location)s.ControlWord) & ~0x8f) | 0x07;
	    		break;
	    	}
	    case __SwitchedOn:
	    	if (power) {
	    	    *(__CIA402Node_%(location)s.ControlWord) = (*(__CIA402Node_%(location)s.ControlWord) & ~0x8f) | 0x0f;
	    	}
	    	break;
	    case __Fault:
	    	*(__CIA402Node_%(location)s.ControlWord) = (*(__CIA402Node_%(location)s.ControlWord) & ~0x8f) | 0x80;
	    	break;
	    default:
	    	break;
	}

	// Default variables publish
	if (__CIA402Node_%(location)s.axis->CSP && *(__CIA402Node_%(location)s.ModesOfOperationDisplay) == 0x08) {
		*(__CIA402Node_%(location)s.TargetPosition) = USER_UNIT_TO_AXIS_UNIT(__CIA402Node_%(location)s.axis->PositionSetPoint);
	}
	else {
		*(__CIA402Node_%(location)s.TargetPosition) = *(__CIA402Node_%(location)s.ActualPosition);
	}

	// Extra variables publish
%(extra_variables_publish)s
}
