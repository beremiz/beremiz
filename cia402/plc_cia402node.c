/*

Template C code used to produce target C CIA402 code. CiA402 being the drive
profile of the CANopen application layer, this is shared by every field bus
reusing that application layer : EtherCAT (CoE) and CANopen itself.

Copyright (C) 2011-2014: Laurent BESSARD
                         RTES Lab : CRKim, JBLee, youcu
                         Higen Motor : Donggu Kang
Copyright (C) 2011-2026: Edouard TISSERANT


Distributed under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

See COPYING file for copyrights details.

*/

%(fieldbus_includes)s

#include "beremiz.h"
#include "iec_types_all.h"

#include "accessor.h"
#include "POUS.h"

/* From CiA402, page 27

        Table 30 - State coding
    Statusword      |      PDS FSA state
xxxx xxxx x0xx 0000 | Not ready to switch on
xxxx xxxx x1xx 0000 | Switch on disabled
xxxx xxxx x01x 0001 | Ready to switch on
xxxx xxxx x01x 0011 | Switched on
xxxx xxxx x01x 0111 | Operation enabled
xxxx xxxx x00x 0111 | Quick stop active
xxxx xxxx x0xx 1111 | Fault reaction active
xxxx xxxx x0xx 1000 | Fault
*/


/* From CiA402, Page 63 Statusword for homing mode

		Table 106 - Definition of bit 10, bit 12, bit 13

xx00 x0xx xxxx xxxx | Homing procedure is in progress
xx00 x1xx xxxx xxxx | Homing procedure is interrupted or not started
xx01 x0xx xxxx xxxx | Homing is attained, but target is not reached
xx01 x1xx xxxx xxxx | Homing procedure is completed successfully
xx10 x0xx xxxx xxxx | Homing error occurred, velocity is not 0
xx10 x1xx xxxx xxxx | Homing error occurred, velocity is 0
xx11 xxxx xxxx xxxx | reserved
*/

#define FSAFromStatusWord(SW) (SW & 0x006f)

#define HomingStatusWord(SW) (SW & 0x3400)
#define FaultFromStatusWord(SW) (SW & 0x0008)
#define NotReadyToSwitchOn  0b00000000 FSA_sep 0b00100000
#define SwitchOnDisabled    0b01000000 FSA_sep 0b01100000
#define ReadyToSwitchOn     0b00100001
#define SwitchedOn          0b00100011
#define OperationEnabled    0b00100111
#define QuickStopActive     0b00000111
#define FaultReactionActive 0b00001111 FSA_sep 0b00101111
#define Fault               0b00001000 FSA_sep 0b00101000


#define HomingInProgress	0b0000000000000000
#define HomingNotRunning	0b0000010000000000
#define HomingNotReached	0b0001000000000000
#define Homing_Completed	0b0001010000000000
#define HomingErrorInVelo	0b0010000000000000
#define HomingErrorNotVelo	0b0010010000000000
#define HomingReserved		0b0011000000000000 FSA_sep 0b0011010000000000

// StatusWord bits :
#define SW_ReadyToSwitchOn     0x0001
#define SW_SwitchedOn          0x0002
#define SW_OperationEnabled    0x0004
#define SW_Fault               0x0008
#define SW_VoltageEnabled      0x0010
#define SW_QuickStop           0x0020
#define SW_SwitchOnDisabled    0x0040
#define SW_Warning             0x0080
#define SW_Remote              0x0200
#define SW_TargetReached       0x0400
#define SW_InternalLimitActive 0x0800


#define SW_HomingAttained		0x1000
#define SW_HomingError			0x2000

// ControlWord bits :
#define SwitchOn        0x0001
#define EnableVoltage   0x0002
#define QuickStop       0x0004
#define EnableOperation 0x0008
#define FaultReset      0x0080
#define Halt            0x0100


//#define Homing_OperationStart 0x0010
#define Homing_OperationStart_Origin 0x0010

IEC_INT beremiz%(axisref_symbol)s;
IEC_INT *%(axisref_symbol)s = &beremiz%(axisref_symbol)s;

%(MCL_headers)s

static IEC_BOOL __FirstTick = 1;

typedef struct {
%(entry_variables)s
    axis_s* axis;
} __CIA402Node;

#define AxsPub __CIA402Node_%(location)s

static __CIA402Node AxsPub;

%(extern_located_variables_declaration)s

%(fieldbus_axis_network)s

int __init_%(location)s()
{
    __FirstTick = 1;
%(init_entry_variables)s
    return 0;
}

void __cleanup_%(location)s()
{
}

void __retrieve_%(location)s()
{
	if (__FirstTick) {
		*%(axisref_symbol)s = new_AXIS_REF();
		AxsPub.axis = 
            AXIS_REF_interface(*%(axisref_symbol)s);
%(fieldbus_axis_network_binding)s
%(init_axis_params)s
		__FirstTick = 0;
	}

	// Default variables retrieve
	AxsPub.axis->CommunicationReady = 
        *(AxsPub.StatusWord) != 0;
#define FSA_sep || FSA ==
    {
        uint16_t FSA = FSAFromStatusWord(*(AxsPub.StatusWord));
        AxsPub.axis->ReadyForPowerOn = FSA == ReadyToSwitchOn;
        AxsPub.axis->PowerFeedback = FSA == OperationEnabled;
    }
#undef FSA_sep 
%(default_variables_retrieve)s

	// Extra variables retrieve
%(extra_variables_retrieve)s
}

void __publish_%(location)s()
{
	/* MC_Power request. SW_VoltageEnabled can't take part in that decision :
	   CiA402 leaves it "don't care" in every PDS state, and drives typically
	   only report high voltage applied once the power stage has been switched
	   on, which is precisely what this request is about to ask for. */
	IEC_BOOL power = AxsPub.axis->Power;
    uint16_t CW = *(AxsPub.ControlWord);

#define FSA_sep : case
	// CIA402 node state transition computation
	switch (FSAFromStatusWord(*(AxsPub.StatusWord))) {
	    case SwitchOnDisabled :
            CW &= ~(SwitchOn | FaultReset);
            CW |= EnableVoltage | QuickStop;
	    	break;
	    case OperationEnabled :
	    	if (!power) {
                /* Disable operation first, so that the drive gets a chance to
                   stop as configured before its power stage is switched off */
                CW &= ~(FaultReset | EnableOperation);
                CW |= SwitchOn | EnableVoltage | QuickStop;
	    		break;
	    	}
	    case ReadyToSwitchOn :
	    case SwitchedOn :
	    	if (!power) {
                /* Wait for MC_Power : only it can switch the power stage on */
                CW &= ~(SwitchOn | FaultReset | EnableOperation);
                CW |= EnableVoltage | QuickStop;
	    		break;
	    	}
            CW &= ~(FaultReset);
            CW |= SwitchOn | EnableVoltage | QuickStop | EnableOperation;
	    	break;
			//ssh_check
//	    case Fault :
//            /* TODO reset fault only when MC_Reset */
//	    	AxsPub.axis->DriveFault = 1;
//            CW &= ~(SwitchOn | EnableVoltage | QuickStop | EnableOperation);
//            CW |= FaultReset;
//	    	break;
	    default:
	    	break;
	}

	if(FaultFromStatusWord(*(AxsPub.StatusWord)) == SW_Fault)
		AxsPub.axis->DriveFault = 1;
	else{
		AxsPub.axis->DriveFault = 0;
		AxsPub.axis->DriveFaultReset = 0;
	}
	if(AxsPub.axis->DriveFaultReset){
		CW &= ~(SwitchOn | EnableVoltage | QuickStop | EnableOperation);
		CW |= FaultReset;
	}


	switch (HomingStatusWord(*(AxsPub.StatusWord))) {
		case HomingInProgress:
			break;
		case HomingNotRunning:
			break;
		case HomingNotReached:
			break;
		case Homing_Completed:
			if(!AxsPub.axis->HomingCompleted)
				AxsPub.axis->HomingCompleted = 1;
			break;
		case HomingErrorInVelo:
		case HomingErrorNotVelo:
			if(!AxsPub.axis->HomingCompleted)
				AxsPub.axis->HomingCompleted = 1;
			break;
		case HomingReserved:
			break;
	}
#undef FSA_sep 


%(modeofop_homing_method)s

	*(AxsPub.ControlWord) = CW;


	// CIA402 node modes of operation computation according to axis motion mode
%(modeofop_computation_mode)s

	// Default variables publish
%(default_variables_publish)s

	// Extra variables publish
%(extra_variables_publish)s
}
