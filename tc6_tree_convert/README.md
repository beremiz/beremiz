# tc6_tree_convert

Converts PLC logic between PLCopen TC6 XML (`plc.xml`) and a tree of IEC 61131-3 text
files (a `plc/` directory). Beremiz keeps TC6 XML as its internal model; a project that
contains a `plc/` directory instead of `plc.xml` is converted when loaded and saved.

## `plc/` directory

Organization of files and sub-directories is free. File extension gives the content:

| Extension | Content |
|-----------|---------|
| `.st`  | TYPE declarations, the CONFIGURATION (one per project), POUs written in ST |
| `.il`  | POUs written in IL |
| `.sfc` | POUs written in SFC |
| `.fbd` | POUs written in FBD |
| `.ld`  | POUs written in LD |

Other files, and files starting with `.`, are ignored. A `.st` file looks like:

    {TC6 PROJECT(companyName := 'Beremiz', productName := 'demo',
        productVersion := '1', creationDateTime := '2026-11-03T10:00:00',
        name := 'demo', fbdScaling := (8, 8), ldScaling := (0, 0), sfcScaling := (0, 0))}

    TYPE
      Color : (Red, Green, Blue) := Green;
      Point : STRUCT
        x : REAL := 1.5;
        y : REAL;
      END_STRUCT;
    END_TYPE

    (* Counts rising edges of Pulse *)
    FUNCTION_BLOCK Counter
      VAR_INPUT
        Pulse : BOOL;
      END_VAR
      VAR CONSTANT
        Limit : DINT := 1000;
      END_VAR
      ACTION Clear : Count := 0; END_ACTION
    IF Pulse THEN Count := Count + 1; END_IF;
    END_FUNCTION_BLOCK

    CONFIGURATION config
      RESOURCE resource1 ON PLC
        TASK fast(INTERVAL := T#10ms, PRIORITY := 0);
        PROGRAM main0 WITH fast : Main;
      END_RESOURCE
    END_CONFIGURATION

`{TC6 PROJECT(...)}` pragma holds the project header (properties of the project in
Beremiz), it can be in any `.st` file. Without it, the project gets default properties.

ST and IL bodies are kept as is. A body text is what is between the line of what comes
before it (header, variables, actions) and the line of its END keyword. A nested body,
of an action or a transition, may also be on a single line, one space after its header
and one space before END keyword.

Data types are any TC6 data type: elementary, `STRING[n]`, arrays, enumerations, with
values and base type, structures, subranges and `REF_TO` pointers. Initial values are
split as Beremiz does: `[...]` is an array value, `n(...)` a repeated value, `(...)` a
structure value. Variable blocks have `CONSTANT`, `RETAIN` and `NON_RETAIN` qualifiers.

## Comments

A comment right before a declaration, on its own line and with no blank line before the
declaration, is its documentation: data types, POUs, actions and transitions of POUs,
variables, configuration, resources, tasks, program instances and graphical elements.

Other comments are kept with the whitespace around them, as XML comments in TC6
`addData` of the next declaration, or of the container they end. In POU bodies, they are
part of the body.

## Graphical languages

Each TC6 element is written as

    KEYWORD #localId [NOT] [(attribute := value, ...)] [operand] AT (x, y) [SIZE (w, h)]
      items...
    END_KEYWORD

or ends with `;` when it has no item. Keyword is the TC6 element name, `IN_VARIABLE`
for `inVariable`. Operand is the expression of a variable, the variable of a contact or
a coil, `instance : type` of a block, or the name of a step, connector or label. Items
are connection points, actions of an action block and condition of a transition:

    BLOCK #4 TON0 : TON AT (328, 115) SIZE (69, 80)
      IN AT (0, 35) := #6 VIA (328, 150), (275, 150);
      PT AT (0, 65) := #3.OUT;
      IN_OUT X := #2 => AT (69, 50);
      Q => AT (69, 35);
    END_BLOCK

An input `PIN AT (x, y) := #id[.output] [VIA (x, y), ...]` gives the relative position of
the connection point, and where it is connected from, with the points of the wire. An
output is written `PIN => AT (x, y)`. Attributes Beremiz writes by default are implied,
`(executionOrderId := NULL)` stands for an absent one.

SFC steps and actions use IEC keywords and action associations:

    INITIAL_STEP #1 Start AT (241, 14) SIZE (90, 34)
      OUT => AT (45, 34);
    END_STEP
    TRANSITION #3 AT (491, 132) SIZE (20, 2)
      IN AT (10, 0) := #2 VIA (501, 132), (501, 87);
      CONDITION := NOT Reset;
    END_TRANSITION
    ACTION_BLOCK #6 AT (641, 190) SIZE (254, 63)
      IN AT (0, 15) := #5;
      ACTION (N) Cnt := ResetCounterValue; END_ACTION
      STOP_CARS(D, T#2s);
    END_ACTION_BLOCK

A transition condition is an inline ST expression `CONDITION := expr;`, a named
transition `CONDITION name;`, a wire `CONDITION := #id;`, or a tagged body. Nested bodies
are ST unless tagged with their language: `LD ... END_LD`.

## Not supported

Conversion stops with an error on TC6 content Beremiz does not write: vendor elements,
additional data of other tools, POUs with several bodies, access and configuration
variables, named and persistent variable blocks, and text that can not be written back
as such, like documentation holding both `*)` and `*/`.

## Saving

File and position of each declaration are kept in TC6 `addData`, in namespace
`http://www.beremiz.org/tc6_tree`, so that a declaration is saved where it was.
Declarations without one go to `<pou>.<ext>`, `types.st` and `config.st`, at `plc/` root.

Declarations unchanged since loading keep their text, formatting included. Only changed
files are written, files left without declaration are removed. Saving is refused, and
nothing written, if one of the files changed on disk since loading.

## Command line

    python -m tc6_tree_convert to-tree plc.xml plc      # update plc/ from plc.xml
    python -m tc6_tree_convert to-xml plc plc.xml       # write plc.xml from plc/
    python -m tc6_tree_convert check plc.xml plc        # compare two projects

`check` compares canonical forms, that ignore what Beremiz does not use: attribute
order, default attributes, whitespace between elements, order of data types and POUs.

## Grammar pipeline

Parser is generated from IEC 61131-3 3rd edition Annex A grammar, extended with
TC6 graphical languages:

1. `fix_ebnf.py`: `iec61131-3-3rd.ebnf` (ANTLR like notation, as copy-pasted from the
   standard) → `iec61131-3-3rd_fixed.ebnf` (W3C EBNF). Each fix is listed in the
   generated file header and noted after the fixed rule.
2. `extend_ebnf.py`: fixed grammar + `tc6_xml_v201.xsd` → `iec61131-3-3rd_extended.ebnf`,
   restricted to what TC6 can represent, with POU, variable and configuration forms,
   raw ST and IL bodies, and graphical elements generated from the schema. Also writes
   `tc6_textmap.py`, the mapping of graphical elements `graph.py` follows.
3. `gen_parser.py`: extended grammar → `iec_parser.py`, a packrat PEG parser that only
   depends on Python `re` module. Token rules become regular expressions, other rules
   memoized methods where longest alternative wins. Comments and pragmas are kept
   apart, by position, for documentation and free comments.

`ebnf.py` is the W3C EBNF model they share (reader, printer, validator).

Conversion itself is in `decl.py` (declarations), `graph.py` (graphical elements),
`comments.py`, `tree.py` (files, loading and saving) and `canon.py` (canonical form).

IEC 61131-3 grammar is IEC copyrighted: `*.ebnf` files are not distributed (see
`.gitignore`), generated Python modules are. `tc6_textmap.py` only depends on TC6
schema. Regenerating needs a local copy of `iec61131-3-3rd.ebnf`:

    make -C tc6_tree_convert generate PYTHON=/path/to/python

## Tests

    make -C tc6_tree_convert test PYTHON=/path/to/python

All test projects and examples of Beremiz are converted to text and back. Tests that
need IEC grammar are skipped when it is absent.
