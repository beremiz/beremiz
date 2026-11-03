(* Counters written in ST, part of IEC 61131-3 language test,
   stored as text files *)

FUNCTION AverageVal : REAL
  VAR_INPUT
    Cnt1 : INT;
    Cnt2 : INT;
    Cnt3 : INT;
    Cnt4 : INT;
    Cnt5 : INT;
  END_VAR
  VAR
    (*Количество входных значений*)
    InputsNumber : REAL := 5.0;
  END_VAR
AverageVal := INT_TO_REAL(Cnt1+Cnt2+Cnt3+Cnt4+Cnt5)/InputsNumber;
END_FUNCTION

FUNCTION_BLOCK CounterST
  VAR_INPUT
    Reset : BOOL;
  END_VAR
  VAR
    Cnt : INT;
  END_VAR
  VAR_OUTPUT
    OUT : INT;
  END_VAR
  VAR_EXTERNAL CONSTANT
    ResetCounterValue : INT;
  END_VAR
IF Reset THEN
  Cnt := ResetCounterValue;
ELSE
  Cnt := Cnt + 1;
END_IF;

Out := Cnt;
END_FUNCTION_BLOCK
