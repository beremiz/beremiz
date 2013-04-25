/*
 * Ethercat CIA402 node execution code
 *
 * */

#include "ecrt.h"

#include "beremiz.h"
#include "iec_types_all.h"

#include "accessor.h"
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

#define AXIS_UNIT_TO_USER_UNIT(param, type, name)\
(IEC_##type)(param) * __CIA402Node_%(location)s.axis->name##RatioDenominator / __CIA402Node_%(location)s.axis->name##RatioNumerator
#define USER_UNIT_TO_AXIS_UNIT(param, type, name)\
(IEC_##type)(param * __CIA402Node_%(location)s.axis->name##RatioNumerator / __CIA402Node_%(location)s.axis->name##RatioDenominator)

#define DEFAULT_AXIS_UNIT_TO_USER_UNIT(param) AXIS_UNIT_TO_USER_UNIT(param, LREAL,)
#define DEFAULT_USER_UNIT_TO_AXIS_UNIT(param) USER_UNIT_TO_AXIS_UNIT(param, DINT,)
#define TORQUE_AXIS_UNIT_TO_USER_UNIT(param) AXIS_UNIT_TO_USER_UNIT(param, LREAL, Torque)
#define TORQUE_USER_UNIT_TO_AXIS_UNIT(param) USER_UNIT_TO_AXIS_UNIT(param, INT, Torque)

static __CIA402Node __CIA402Node_%(location)s;

%(extern_located_variables_declaration)s

%(fieldbus_interface_declaration)s

int __init_%(location)s()
{
    __FirstTick = 1;
%(init_entry_variables)s
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
		*__IW%(location)s_0 = __MK_Alloc_AXIS_REF();
		__CIA402Node_%(location)s.axis = __MK_GetPublic_AXIS_REF(*__IW%(location)s_0);
		__CIA402Node_%(location)s.axis->NetworkPosition = %(slave_pos)d;
%(init_axis_params)s
%(fieldbus_interface_definition)s
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
	__CIA402Node_%(location)s.axis->CommunicationReady = *(__CIA402Node_%(location)s.StatusWord) != 0;
	__CIA402Node_%(location)s.axis->ReadyForPowerOn = __CIA402Node_%(location)s.state == __SwitchedOn || __OperationEnabled;
	__CIA402Node_%(location)s.axis->PowerFeedback = __CIA402Node_%(location)s.state == __OperationEnabled;
	__CIA402Node_%(location)s.axis->ActualPosition = DEFAULT_AXIS_UNIT_TO_USER_UNIT(*(__CIA402Node_%(location)s.ActualPosition));
	__CIA402Node_%(location)s.axis->ActualVelocity = DEFAULT_AXIS_UNIT_TO_USER_UNIT(*(__CIA402Node_%(location)s.ActualVelocity));
	__CIA402Node_%(location)s.axis->ActualTorque = TORQUE_AXIS_UNIT_TO_USER_UNIT(*(__CIA402Node_%(location)s.ActualTorque));

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

	// CIA402 node modes of operation computation according to axis motion mode
	switch (__CIA402Node_%(location)s.axis->AxisMotionMode) {
		case mc_mode_cst:
			*(__CIA402Node_%(location)s.ModesOfOperation) = 0x0a;
			break;
		case mc_mode_csv:
			*(__CIA402Node_%(location)s.ModesOfOperation) = 0x09;
			break;
		default:
			*(__CIA402Node_%(location)s.ModesOfOperation) = 0x08;
			break;
	}

	// Default variables publish
	*(__CIA402Node_%(location)s.TargetPosition) = DEFAULT_USER_UNIT_TO_AXIS_UNIT(__CIA402Node_%(location)s.axis->PositionSetPoint);
	*(__CIA402Node_%(location)s.TargetVelocity) = DEFAULT_USER_UNIT_TO_AXIS_UNIT(__CIA402Node_%(location)s.axis->VelocitySetPoint);
	*(__CIA402Node_%(location)s.TargetTorque) = TORQUE_USER_UNIT_TO_AXIS_UNIT(__CIA402Node_%(location)s.axis->TorqueSetPoint);

	// Extra variables publish
%(extra_variables_publish)s
}
