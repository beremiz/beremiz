#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tests for W3C EBNF model and IEC 61131-3 grammar fixing
"""

import os
import sys
import tempfile
import unittest

TOOL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOL_DIR)

import ebnf  # noqa: E402
import fix_ebnf  # noqa: E402
import extend_ebnf  # noqa: E402
from ebnf import Alt, Seq, Rep, Diff, Ref, Lit, CharClass  # noqa: E402

SOURCE = os.path.join(TOOL_DIR, "iec61131-3-3rd.ebnf")
FIXED = os.path.join(TOOL_DIR, "iec61131-3-3rd_fixed.ebnf")
EXTENDED = os.path.join(TOOL_DIR, "iec61131-3-3rd_extended.ebnf")
XSD = os.path.join(TOOL_DIR, "tc6_xml_v201.xsd")
TEXTMAP = os.path.join(TOOL_DIR, "tc6_textmap.py")


class W3CEbnfTest(unittest.TestCase):

    SAMPLE = """\
/* Header */

/* Section */
Start ::= Item* /* trailing */
Item ::= Name ':' Value? ';' | 'X'
Name ::= ([A-Z_] [0-9A-Z_]*) - Key /* ws: explicit */
Key ::= 'IF' | "THEN'S" /* ws: explicit */

Value ::= [^#xA#xD"$'] | #xA | Char* - (Char* '*)' Char*)
Char ::= [#x9-#xA#xD#x20-#xD7FF] /* ws: explicit */
"""

    def test_format_is_stable(self):
        self.assertEqual(ebnf.format_grammar(ebnf.parse(self.SAMPLE)), self.SAMPLE)

    def test_comments(self):
        grammar = ebnf.parse(self.SAMPLE)
        self.assertEqual(grammar.header, ["Header"])
        self.assertEqual(grammar["Start"].leading, ["Section"])
        self.assertEqual(grammar["Start"].trailing, ["trailing"])
        self.assertTrue(grammar["Name"].is_token())
        self.assertFalse(grammar["Item"].is_token())
        self.assertTrue(grammar["Value"].blank_before)

    def test_precedence(self):
        expr = ebnf.parse("A ::= x y - z | w*")["A"].expr
        self.assertEqual(expr, Alt((Seq((Ref("x"), Diff(Ref("y"), Ref("z")))),
                                    Rep(Ref("w"), "*"))))
        self.assertEqual(ebnf.format_expr(expr), "x (y - z) | w*")

    def test_char_class(self):
        expr = ebnf.parse("A ::= [^#xA#xD$a-c]")["A"].expr
        self.assertEqual(expr, CharClass(((0xA, 0xA), (0xD, 0xD), (0x24, 0x24), (0x61, 0x63)),
                                         negated=True))
        self.assertEqual(ebnf.format_expr(expr), "[^#xA#xD$a-c]")
        self.assertEqual(ebnf.format_expr(ebnf.char_class([(0x5D, 0x5D), (0x2D, 0x2D)])),
                         "[#x2D#x5D]")
        # hex digit after a code must not read as part of it
        expr = ebnf.char_class([(0xD, 0xD), (0x61, 0x61)])
        self.assertEqual(ebnf.format_expr(expr), "[#xD#x61]")
        self.assertEqual(ebnf.parse("A ::= [#xD#x61]")["A"].expr, expr)

    def test_literal_quotes(self):
        self.assertEqual(ebnf.format_expr(Lit("$'")), '"$\'"')
        self.assertEqual(ebnf.format_expr(Lit('$"')), "'$\"'")

    def test_validate(self):
        grammar = ebnf.parse("S ::= A 'x'\nA ::= A 'y' | B\nC ::= 'c'")
        errors, _warnings = ebnf.validate(grammar, "S")
        self.assertIn("A: undefined rule B", errors)
        self.assertIn("C: unreachable from S", errors)
        self.assertIn("left recursion: A -> A", errors)

    def test_greedy_conflicts(self):
        grammar = ebnf.parse("S ::= A* 'X' Id? Id\nA ::= 'X' | 'Y'\n"
                             "Id ::= [A-Z]+ - Keyword /* ws: explicit */\n"
                             "Keyword ::= 'K' /* ws: explicit */")
        self.assertEqual(ebnf.greedy_conflicts(grammar), [
            "S: A* may swallow 'X'",
            "S: Id? may swallow Id"])


@unittest.skipUnless(os.path.isfile(SOURCE), "IEC 61131-3 Annex A grammar is not distributed")
class FixEbnfTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(SOURCE, encoding="utf-8") as f:
            cls.grammar = fix_ebnf.fix(f.read())
        cls.text = ebnf.format_grammar(cls.grammar)

    def test_valid(self):
        errors, _warnings = ebnf.validate(self.grammar, fix_ebnf.START)
        self.assertEqual(errors, [])

    def test_reparse_is_stable(self):
        self.assertEqual(ebnf.format_grammar(ebnf.parse(self.text)), self.text)

    def test_tokens(self):
        for name in fix_ebnf.TOKEN_RULES + ["Comment", "WS", "Pragma"]:
            self.assertTrue(self.grammar[name].is_token(), name)
        for name in ["Comment", "WS", "Pragma"]:
            self.assertTrue(self.grammar[name].annotated(ebnf.WS_IGNORABLE), name)
        self.assertEqual(self.grammar["Identifier"].expr.right, Ref("Keyword"))

    def test_non_greedy_conversion(self):
        any_char = Rep(Ref("Char"), "*")
        self.assertEqual(self.grammar["Pragma"].expr, Seq((
            Lit("{"), Diff(any_char, Seq((any_char, Lit("}"), any_char))), Lit("}"))))

    def test_every_fix_noted(self):
        fixed = {fix.name for fix in fix_ebnf.RULE_FIXES if fix.new is not None}
        for name in fixed:
            self.assertTrue(any(c.startswith("fix F") for c in self.grammar[name].trailing),
                            name)

    @unittest.skipUnless(os.path.isfile(FIXED), "fixed grammar not generated")
    def test_generated_file_up_to_date(self):
        with open(FIXED, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.text, "run 'make -C tc6_tree_convert generate'")


@unittest.skipUnless(os.path.isfile(SOURCE), "IEC 61131-3 Annex A grammar is not distributed")
class ExtendEbnfTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(SOURCE, encoding="utf-8") as f:
            fixed = fix_ebnf.fix(f.read())
        cls.grammar, cls.textmap = extend_ebnf.extend(fixed, XSD)
        cls.grammar.header = extend_ebnf.header(fixed)
        cls.text = ebnf.format_grammar(cls.grammar)

    def test_valid(self):
        errors, _warnings = ebnf.validate(self.grammar, extend_ebnf.ROOTS)
        self.assertEqual(errors, [])

    def test_reparse_is_stable(self):
        self.assertEqual(ebnf.format_grammar(ebnf.parse(self.text)), self.text)

    def test_pruned(self):
        for name in ["Library", "Class_Decl", "Method_Decl", "Namespace_Decl", "Using_Directive",
                     "Stmt_List", "Instruction_List", "SFC", "Step", "Edge_Decl"]:
            self.assertNotIn(name, self.grammar, name)

    def test_elements(self):
        for group, _suffix in extend_ebnf.GROUPS:
            for element in extend_ebnf.Schema(XSD).group(group):
                name = extend_ebnf.rule_name(element.name)
                self.assertEqual(name in self.grammar, element.name not in extend_ebnf.EXCLUDED,
                                 name)

    @unittest.skipUnless(os.path.isfile(EXTENDED), "extended grammar not generated")
    def test_generated_file_up_to_date(self):
        with open(EXTENDED, encoding="utf-8") as f:
            self.assertEqual(f.read(), self.text, "run 'make -C tc6_tree_convert generate'")


class TextmapTest(unittest.TestCase):
    """ Textmap only depends on TC6 schema, it is distributed """

    def test_up_to_date(self):
        extender = extend_ebnf.Extender(extend_ebnf.Schema(XSD))
        extender.build()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "tc6_textmap.py")
            extend_ebnf.write_textmap(path, extender.textmap)
            with open(path, encoding="utf-8") as generated, \
                 open(TEXTMAP, encoding="utf-8") as distributed:
                self.assertEqual(distributed.read(), generated.read(),
                                 "run 'make -C tc6_tree_convert generate'")


if __name__ == "__main__":
    unittest.main()
