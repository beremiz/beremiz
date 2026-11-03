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
textual form of TC6 graphical elements (todo: syntax reference).

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
2. `extend_ebnf.py` (todo): `tc6_xml_v201.xsd` + fixed grammar →
   `iec61131-3-3rd_extended.ebnf` and `tc6_textmap.py`.
3. `gen_parser.py` (todo): extended grammar → `iec_parser.py`.

`ebnf.py` is the W3C EBNF model they share (reader, printer, validator).

IEC 61131-3 grammar is IEC copyrighted: `*.ebnf` files are not distributed (see
`.gitignore`), generated Python modules are. Regenerating needs a local copy of
`iec61131-3-3rd.ebnf`:

    make -C tc6_tree_convert generate PYTHON=/path/to/python

## Tests

    make -C tc6_tree_convert test PYTHON=/path/to/python

Tests that need IEC grammar are skipped when it is absent.
