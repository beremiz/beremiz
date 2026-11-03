TYPE
  struct_type_0 : STRUCT
    a_var : DINT;
    an_array : ARRAY [0..9] OF DINT;
    a_table : ARRAY [0..9, 0..9] OF DINT;
  END_STRUCT;
  array_type_0 : ARRAY [0..9] OF DINT;
  struct_type_1 : STRUCT
    a_var : DINT;
    a_typed_array : array_type_0;
    an_array_of_struct : ARRAY [0..9] OF struct_type_0;
  END_STRUCT;
  derived_dint : DINT;
END_TYPE
