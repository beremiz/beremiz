#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tests for generated IEC 61131-3 and TC6 textual forms parser
"""

import os
import sys
import unittest

from lxml import etree

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)
sys.path.insert(0, os.path.dirname(TOOL_DIR))

from tc6_tree_convert import iec_parser  # noqa: E402
from tc6_tree_convert.iec_parser import parse, matches, ParseError  # noqa: E402
from tc6_tree_convert.graph import GraphWriter, tc6, localname  # noqa: E402
from test_graph import corpus  # noqa: E402

EXTENDED = os.path.join(TOOL_DIR, "iec61131-3-3rd_extended.ebnf")


def find(node, name):
    """ Depth first nodes with given name """
    if node[0] == name:
        yield node
    for child in node[3] or ():
        yield from find(child, name)


def text_of(text, node):
    return text[node[1]:node[2]]


class TokenTest(unittest.TestCase):

    def test_constants(self):
        for text in ["T#1d2h", "T#1.5s", "t#100ms", "TIME#-5s", "T#1d_2h_3m", "16#FF",
                     "2#1010_1010", "INT#-5", "1.5E3", "-3", "''", "'café'", "'it$'s'",
                     '"wide"', "TRUE", "bool#0", "D#2024-01-02", "DT#2024-01-02-10:20:30.5",
                     "TOD#10:20:30", "STRING#'s'"]:
            self.assertTrue(matches(text, "Constant"), text)
        for text in ["T#", "1.", "'a", "16#"]:
            self.assertFalse(matches(text, "Constant"), text)

    def test_maximal_munch(self):
        tree, _trivia = parse("1.5 + x1.2", "Expression")
        self.assertEqual([text_of("1.5 + x1.2", n) for n in find(tree, "Constant")], ["1.5"])
        self.assertEqual([text_of("1.5 + x1.2", n) for n in find(tree, "Multibit_Part_Access")],
                         [".2"])
        self.assertTrue(matches("1..10", "Subrange"))
        self.assertTrue(matches("a := b", "Param_Assign"))

    def test_variables(self):
        for text in ["x1.2", "a.b.c", "a[1, i].b", "%IX0.1", "THIS.x"]:
            self.assertTrue(matches(text, "Variable_Access"), text)

    def test_identifiers(self):
        for text in ["Final", "Interface", "Position", "METHOD", "ref", "Null", "x1", "_a"]:
            self.assertTrue(matches(text, "Identifier"), text)
        for text in ["END_VAR", "int", "Var_Input", "1a"]:
            self.assertFalse(matches(text, "Identifier"), text)


class DeclarationTest(unittest.TestCase):

    def test_variables(self):
        text = """\
FUNCTION_BLOCK fb
  VAR_INPUT a, b : INT := 5; c AT %IX0.0 : BOOL; END_VAR
  VAR CONSTANT RETAIN
    t : ARRAY [0..9, 1..2] OF ARRAY [1..2] OF REAL := [10(0.0)];
    s : Point := (x := 1, y := [1, 2]);
    r : REF_TO INT;
    str : STRING[20] := 'abc';
    rng : INT (0..100) := 5;
    e : (Red, Green := 5) := Red;
    tm : TOD;
  END_VAR
  VAR_EXTERNAL x : MyType; END_VAR
END_FUNCTION_BLOCK
"""
        tree, _trivia = parse(text, "TC6_ST_File")
        declarations = list(find(tree, "TC6_Var_Decl"))
        self.assertEqual(len(declarations), 10)
        self.assertEqual([text_of(text, n) for n in find(tree, "TC6_Initial_Value")],
                         ["5", "[10(0.0)]", "(x := 1, y := [1, 2])", "'abc'", "5", "Red"])
        self.assertEqual([text_of(text, n) for n in find(tree, "TC6_Var_Qualifier")],
                         ["CONSTANT", "RETAIN"])

    def test_types(self):
        text = """\
TYPE
  Color : (Red, Green) := Red;
  S : STRUCT a : INT := 1; b : ARRAY [0..1] OF BOOL; END_STRUCT;
  Empty : STRUCT END_STRUCT;
  Str10 : STRING[10] := 'x';
  Ptr : REF_TO S;
END_TYPE
"""
        tree, _trivia = parse(text, "TC6_ST_File")
        self.assertEqual([text_of(text, n[3][0]) for n in find(tree, "Type_Decl")],
                         ["Color", "S", "Empty", "Str10", "Ptr"])

    def test_configuration(self):
        text = """\
CONFIGURATION config
  VAR_GLOBAL x : INT; END_VAR
  VAR_GLOBAL CONSTANT k : INT := 3; END_VAR
  RESOURCE res1 ON PLC
    VAR_GLOBAL y AT %QX0.1 : BOOL; END_VAR
    TASK fast(INTERVAL := T#10ms, PRIORITY := 0);
    TASK event(SINGLE := trigger, PRIORITY := 1);
    PROGRAM main0 WITH fast : main;
    PROGRAM other0 : other;
  END_RESOURCE
  RESOURCE empty ON PLC
  END_RESOURCE
END_CONFIGURATION
"""
        tree, _trivia = parse(text, "TC6_ST_File")
        self.assertEqual(len(list(find(tree, "TC6_Resource_Decl"))), 2)
        self.assertEqual(len(list(find(tree, "TC6_Program_Config"))), 2)

    def test_project_pragma(self):
        self.assertTrue(matches("TC6 PROJECT(name := 'p', companyName := 'Beremiz', "
                                "creationDateTime := '2016-10-24T18:09:22', "
                                "pageSize := (1050, 1485), fbdScaling := (10, 10))",
                                "TC6_Project_Pragma"))


class RawBodyTest(unittest.TestCase):

    def body(self, text, rule="TC6_POU_Raw_Body"):
        tree, _trivia = parse(text, "TC6_ST_File")
        return [text_of(text, n) for n in find(tree, rule)]

    def test_end_keyword_in_strings_comments_pragmas(self):
        text = """\
PROGRAM p
VAR x : STRING; END_VAR
x := 'END_PROGRAM';  (* END_PROGRAM *)
{ END_PROGRAM }
{{ char c = '}'; /* (*p) END_PROGRAM */ }}
x := "END_PROGRAM";
end_program
"""
        self.assertEqual(self.body(text), [text[text.index("x :="):text.index("end_program")]])

    def test_actions_and_transitions(self):
        text = """\
PROGRAM p
ACTION a1 : x := 1; END_ACTION
ACTION a2 :
LD
  LEFT_POWER_RAIL #1 AT (0, 0) SIZE (3, 40);
END_LD
END_ACTION
TRANSITION t1 : IL LD x END_IL END_TRANSITION
x := 2;
END_PROGRAM
"""
        self.assertEqual(self.body(text, "TC6_Action_Raw_Body"), ["x := 1; "])
        self.assertEqual(self.body(text, "TC6_IL_Raw_Body"), ["LD x "])
        self.assertEqual(self.body(text), ["x := 2;\n"])

    def test_broken_declaration(self):
        text = "PROGRAM p\nVAR x : INT END_VAR\nx := 1;\nEND_PROGRAM\n"
        with self.assertRaises(ParseError) as context:
            parse(text, "TC6_ST_File")
        self.assertEqual((context.exception.line, context.exception.column), (2, 13))
        self.assertIn("';'", context.exception.expected)

    def test_trivia(self):
        text = "(* doc *)\nPROGRAM p\nx := 1; (* in body *)\nEND_PROGRAM\n// end\n"
        _tree, trivia = parse(text, "TC6_ST_File")
        self.assertEqual(trivia, {0: ("Comment", 9), text.index("//"): ("Comment", len(text))})


class GraphicalTest(unittest.TestCase):

    def test_sfc(self):
        text = """\
FUNCTION_BLOCK f
INITIAL_STEP #1 Start AT (241, 14) SIZE (90, 34)
  OUT => AT (45, 34);
END_STEP
TRANSITION #3 (priority := 2) AT (491, 132) SIZE (20, 2)
  IN := #1;
  CONDITION := a; b;
END_TRANSITION
TRANSITION #4 AT (1, 2)
  CONDITION STOP;
END_TRANSITION
TRANSITION #5 AT (1, 2) CONDITION := #35.OUT VIA (1, 2); END_TRANSITION
TRANSITION #6 AT (1, 2)
  CONDITION ST a; b; END_ST
END_TRANSITION
ACTION_BLOCK #6 AT (641, 190)
  ACTION (N) Cnt := Cnt + 1; END_ACTION
  STOP_CARS(D, T#2s, ind);
  #3 (executionOrderId := 1) GO(P1) AT (0, 15) SIZE (10, 10);
END_ACTION_BLOCK
JUMP_STEP #12 Start AT (280, 317);
COMMENT #9 AT (51, 11) SIZE (318, 52)
  (* comment *)
END_COMMENT
END_FUNCTION_BLOCK
"""
        with self.assertRaises(ParseError):
            # inline condition is an expression, up to ;
            parse(text, "TC6_SFC_File")
        text = text.replace("CONDITION := a; b;", "CONDITION := a AND b;")
        tree, _trivia = parse(text, "TC6_SFC_File")
        self.assertEqual([text_of(text, n) for n in find(tree, "TC6_Raw_Expression")], ["a AND b"])
        self.assertEqual([text_of(text, n) for n in find(tree, "TC6_Sources")], ["#1", "#35.OUT VIA (1, 2)"])
        self.assertEqual([text_of(text, n) for n in find(tree, "TC6_Action_Raw_Body")],
                         ["Cnt := Cnt + 1; "])

    def test_fbd_ld(self):
        text = """\
PROGRAM p
BLOCK #7 (executionOrderId := NULL) TON0 : TON AT (448, 100) SIZE (69, 80)
  NOT IN AT (0, 30) := #1 VIA (448, 130), (415, 130), #2.Q;
  PT AT (0, 50);
  IN_OUT X AT (0, 70) := #3 => AT (69, 70);
  Q => AT (69, 30);
END_BLOCK
IN_VARIABLE #1 (expression := 'a$Nb') AT (1, 2);
IN_VARIABLE #2 a.b[2] + f(x) AT (1, 2) SIZE (3, 4)
  OUT => AT (3, 2);
END_IN_VARIABLE
END_PROGRAM
"""
        tree, _trivia = parse(text, "TC6_FBD_File")
        self.assertEqual(len(list(find(tree, "TC6_Block_Input"))), 2)
        self.assertEqual(len(list(find(tree, "TC6_Block_In_Out"))), 1)
        self.assertEqual(len(list(find(tree, "TC6_Block_Output"))), 1)
        self.assertEqual(text_of(text, next(find(tree, "Expression"))), "a.b[2] + f(x)")
        text = text.replace("IN_VARIABLE #1 (expression := 'a$Nb')", "CONTACT #1 NOT a")
        with self.assertRaises(ParseError):
            # contacts are LD only
            parse(text, "TC6_FBD_File")
        parse(text, "TC6_LD_File")

    def test_corpus(self):
        """ All graphical POUs of Beremiz projects, as written by graph.py, parse """
        writer = GraphWriter()
        for path in corpus():
            with open(path, "rb") as f:
                root = etree.fromstring(f.read().replace(b"tc6.xsd", b"tc6_0201"))
            for pou in root.iter(tc6("pou")):
                language = pou.find(tc6("body"))[0]
                if localname(language) not in ("FBD", "LD", "SFC"):
                    continue
                lines = ["PROGRAM " + pou.get("name")]
                for kind in ("action", "transition"):
                    for member in pou.iterfind("%ss/%s" % (tc6(kind), tc6(kind))):
                        head = "%s %s :" % (kind.upper(), member.get("name"))
                        body = writer.body(member.find(tc6("body")), 0, tag_st=False)
                        lines += writer.text_body(head, body, "END_" + kind.upper()) \
                            if isinstance(body, str) else [head] + body + ["END_" + kind.upper()]
                lines += writer.graphical(language, 0) + ["END_PROGRAM"]
                with self.subTest(path=path, pou=pou.get("name")):
                    parse("\n".join(lines), "TC6_%s_File" % localname(language))


@unittest.skipUnless(os.path.isfile(EXTENDED), "extended grammar not generated")
class GeneratedParserTest(unittest.TestCase):

    def test_up_to_date(self):
        import gen_parser
        import ebnf
        with open(EXTENDED, encoding="utf-8") as f:
            code = gen_parser.ParserGenerator(ebnf.parse(f.read())).generate(EXTENDED)
        with open(iec_parser.__file__, encoding="utf-8") as f:
            self.assertEqual(f.read(), code, "run 'make -C tc6_tree_convert generate'")


if __name__ == "__main__":
    unittest.main()
