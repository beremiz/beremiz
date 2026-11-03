# tc6_tree_convert

Converts PLC logic between PLCopen TC6 XML (`plc.xml`) and a tree of IEC 61131-3 text
files (a `plc/` directory). Beremiz keeps TC6 XML as its internal model; a project that
contains a `plc/` directory instead of `plc.xml` is converted when loaded and saved.

*Draft: sections marked (todo) are completed along with the corresponding step.*

## `plc/` directory

Organization of files and sub-directories is free. File extension gives the content:

| Extension | Content |
|-----------|---------|
| `.st`  | TYPE declarations, the CONFIGURATION (one per project), POUs written in ST |
| `.il`  | POUs written in IL |
| `.sfc` | POUs written in SFC |
| `.fbd` | POUs written in FBD |
| `.ld`  | POUs written in LD |

Other files are ignored. ST and IL bodies are kept as is. SFC, FBD and LD bodies use a
textual form of TC6 graphical elements.

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

Nested bodies, of actions and transitions, are ST unless tagged with their language,
`LD ... END_LD`. Body text is what is between the line of its header and the line of
its END keyword, or between them separated by one space when it fits on one line.

Comments (todo):
- a comment right before a declaration is its documentation,
- other comments are kept, as XML comments in TC6 `addData`.

File of each declaration is kept in TC6 `addData`, in namespace
`http://www.beremiz.org/tc6_tree`. Declarations without one go to `<pou>.<ext>`,
`types.st` and `config.st`.

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

IEC 61131-3 grammar is IEC copyrighted: `*.ebnf` files are not distributed (see
`.gitignore`), generated Python modules are. `tc6_textmap.py` only depends on TC6
schema. Regenerating needs a local copy of `iec61131-3-3rd.ebnf`:

    make -C tc6_tree_convert generate PYTHON=/path/to/python

## Tests

    make -C tc6_tree_convert test PYTHON=/path/to/python

Tests that need IEC grammar are skipped when it is absent.
