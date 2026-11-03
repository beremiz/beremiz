FUNCTION_BLOCK CounterIL
  VAR
    Cnt : INT;
  END_VAR
  VAR_INPUT
    Reset : BOOL;
  END_VAR
  VAR_OUTPUT
    OUT : INT;
  END_VAR
  VAR_EXTERNAL CONSTANT
    ResetCounterValue : INT;
  END_VAR
LD Reset
JMPC ResetCnt

(* increment counter *)
LD Cnt
ADD 1
JMP QuitFb

ResetCnt:
(* reset counter *)
LD ResetCounterValue

QuitFb:
(* save results *)
ST Cnt
ST Out

END_FUNCTION_BLOCK
