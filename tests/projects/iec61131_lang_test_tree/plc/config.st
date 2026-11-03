{TC6 PROJECT(companyName := 'Unknown',
    productName := 'Unnamed',
    productVersion := '1',
    creationDateTime := '2023-03-11T14:33:27',
    name := 'Unnamed',
    fbdScaling := (8, 8),
    ldScaling := (0, 0),
    sfcScaling := (0, 0))}

CONFIGURATION config
  VAR_GLOBAL CONSTANT
    ResetCounterValue : INT := 17;
  END_VAR
  VAR_GLOBAL
    GlobalArray : ARRAY [0..4] OF INT;
  END_VAR
  RESOURCE resourceA ON PLC
    VAR_GLOBAL
      ResourceGlobal : DINT := 1;
      ResourceGlobal0 : derived_dint := 1;
    END_VAR
    TASK plc_task(INTERVAL := T#100ms, PRIORITY := 1);
    PROGRAM instance0 WITH plc_task : main_test;
    PROGRAM plc_task_instance WITH plc_task : plc_prg;
  END_RESOURCE
  RESOURCE resourceB ON PLC
    VAR_GLOBAL
      ResourceGlobal : DINT := 2;
      ResourceGlobal0 : derived_dint := 2;
    END_VAR
    TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : main_test;
    PROGRAM instance1 WITH task0 : plc_prg;
  END_RESOURCE
END_CONFIGURATION
(* end of configuration *)
