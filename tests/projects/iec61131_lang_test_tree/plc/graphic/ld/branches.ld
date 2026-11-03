FUNCTION_BLOCK LDNestedBranches
  VAR_INPUT
    A : BOOL;
    B : BOOL;
    C : BOOL;
  END_VAR
  VAR_OUTPUT
    Y : BOOL;
  END_VAR
  LEFT_POWER_RAIL #1 AT (20, 20) SIZE (10, 100)
    OUT (formalParameter := 'none') => AT (10, 20);
  END_LEFT_POWER_RAIL
  CONTACT #3 A AT (60, 30) SIZE (21, 15)
    IN AT (0, 10) := #1;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #4 A AT (60, 60) SIZE (21, 15)
    IN AT (0, 10) := #1;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #5 B AT (110, 60) SIZE (21, 15)
    IN AT (0, 10) := #4;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #6 A AT (60, 90) SIZE (21, 15)
    IN AT (0, 10) := #1;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #7 B AT (110, 90) SIZE (21, 15)
    IN AT (0, 10) := #6;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #8 C AT (160, 90) SIZE (21, 15)
    IN AT (0, 10) := #7;
    OUT => AT (21, 10);
  END_CONTACT
  COIL #9 Y AT (220, 30) SIZE (21, 15)
    IN AT (0, 10) := #3, #5, #8;
    OUT => AT (21, 10);
  END_COIL
END_FUNCTION_BLOCK

FUNCTION_BLOCK LDUnequalBranches
  VAR_INPUT
    A : BOOL;
    B : BOOL;
    C : BOOL;
  END_VAR
  VAR_OUTPUT
    Y : BOOL;
  END_VAR
  LEFT_POWER_RAIL #1 AT (20, 20) SIZE (10, 60)
    OUT (formalParameter := 'none') => AT (10, 20);
  END_LEFT_POWER_RAIL
  CONTACT #3 A AT (60, 30) SIZE (21, 15)
    IN AT (0, 10) := #1;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #4 NOT B AT (110, 30) SIZE (21, 15)
    IN AT (0, 10) := #3;
    OUT => AT (21, 10);
  END_CONTACT
  CONTACT #5 C AT (60, 70) SIZE (21, 15)
    IN AT (0, 10) := #1;
    OUT => AT (21, 10);
  END_CONTACT
  COIL #6 Y AT (180, 30) SIZE (21, 15)
    IN AT (0, 10) := #4, #5;
    OUT => AT (21, 10);
  END_COIL
END_FUNCTION_BLOCK
