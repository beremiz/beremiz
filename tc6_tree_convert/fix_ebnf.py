#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Fix IEC 61131-3 3rd edition Annex A grammar and convert it to W3C EBNF

Input is the grammar as copy-pasted from the standard, in its ANTLR like notation.
Each fix must apply exactly once, so that any change in input is noticed.
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass

import ebnf
from ebnf import Alt, Seq, Rep, Diff, Ref, Lit, CharClass, Rule, Grammar
from ebnf import WS_EXPLICIT, WS_IGNORABLE, alt, seq, char_class


START = "Library"


# Fixes applied on raw text before reading : (id, reason, old, new, count)
TEXT_FIXES = [
    ("F01", "unbalanced quote before VAR_TEMP", "Temp_Var_Decls : VAR_TEMP'", "Temp_Var_Decls : 'VAR_TEMP'", 1),
    ("F02", "trailing space in literal", "'ATAN2 '", "'ATAN2'", 1),
    ("F02", "trailing space in literal", "'MOVE '", "'MOVE'", 1),
    ("F02", "trailing space in literal", "'MUX '", "'MUX'", 1),
    ("F02", "trailing space in literal", "'THIS '", "'THIS'", 1),
    ("F03", "en dash in comments", "–", "-", 4),
]


@dataclass
class RuleFix:
    """ Replace rule expression when old is given, add rule otherwise (after given rule).
    Remove rule when new is None. Expressions are given in W3C notation. """
    fid: str
    name: str
    reason: str
    old: str = None
    new: str = None
    after: str = None


# Reserved words : tokens tagged as "Keyword" in matiec stage1_2/iec_flex.ll, without
# REF, DREF, REF_TO and NULL that matiec only reserves with -R option, not used by Beremiz.
# 3rd edition only keywords (CLASS, METHOD, ...) stay valid identifiers, as they are in matiec.
KEYWORDS = """
    ACTION ADD AND ANY ANY_BIT ANY_DATE ANY_DERIVED ANY_ELEMENTARY ANY_INT ANY_MAGNITUDE
    ANY_NUM ANY_REAL ANY_STRING ARRAY AT BOOL BY BYTE CASE CONFIGURATION CONSTANT CONTINUE
    DATE DATE_AND_TIME DINT DIV DO DT DWORD ELSE ELSIF EN END_ACTION END_CASE
    END_CONFIGURATION END_FOR END_FUNCTION END_FUNCTION_BLOCK END_IF END_PROGRAM END_REPEAT
    END_RESOURCE END_STEP END_STRUCT END_TRANSITION END_TYPE END_VAR END_WHILE ENO EQ EXIT
    FALSE F_EDGE FOR FROM FUNCTION FUNCTION_BLOCK GE GT IF INITIAL_STEP INT LE LINT LREAL LT
    LWORD MOD MUL NE NON_RETAIN NOT OF ON OR PROGRAM READ_ONLY READ_WRITE REAL R_EDGE REPEAT
    RESOURCE RETAIN RETURN SINT STEP STRING STRUCT SUB TASK THEN TIME TIME_OF_DAY TO TOD
    TRANSITION TRUE TYPE UDINT UINT ULINT UNTIL USINT VAR VAR_ACCESS VAR_CONFIG VAR_EXTERNAL
    VAR_GLOBAL VAR_IN_OUT VAR_INPUT VAR_OUTPUT VAR_TEMP WHILE WITH WORD WSTRING XOR
""".split()


RULE_FIXES = [
    RuleFix("F10", "Unary_Expr", "operator precedence, unary operators are optional prefix",
            old="'-' | '+' | 'NOT'? Primary_Expr",
            new="('-' | '+' | 'NOT')? Primary_Expr"),
    RuleFix("F11", "Term", "operator precedence, operand follows any multiplicative operator",
            old="Power_Expr ('*' | '/' | 'MOD' Power_Expr)*",
            new="Power_Expr (('*' | '/' | 'MOD') Power_Expr)*"),
    RuleFix("F12", "IL_Return_Operator", "IL return operator is RET",
            old="'RT' | 'RETC' | 'RETCN'",
            new="'RET' | 'RETC' | 'RETCN'"),
    RuleFix("F13", "Var_Decl_Init", "Str_Var_Decl repeats Variable_List ':'",
            old="Variable_List ':' (Simple_Spec_Init | Str_Var_Decl | Ref_Spec_Init)"
                " | Array_Var_Decl_Init | Struct_Var_Decl_Init | FB_Decl_Init"
                " | Interface_Spec_Init",
            new="Variable_List ':' (Simple_Spec_Init | S_Byte_Str_Spec | D_Byte_Str_Spec"
                " | Ref_Spec_Init) | Array_Var_Decl_Init | Struct_Var_Decl_Init"
                " | FB_Decl_Init | Interface_Spec_Init"),
    RuleFix("F14", "Var_Decl", "Str_, Array_ and Struct_Var_Decl repeat Variable_List ':'",
            old="Variable_List ':' (Simple_Spec | Str_Var_Decl | Array_Var_Decl"
                " | Struct_Var_Decl)",
            new="Variable_List ':' (Simple_Spec | Array_Spec | Struct_Type_Access)"),
    RuleFix("F14", "Str_Var_Decl", "unreferenced after F13 and F14",
            old="S_Byte_Str_Var_Decl | D_Byte_Str_Var_Decl"),
    RuleFix("F14", "S_Byte_Str_Var_Decl", "unreferenced after F13 and F14",
            old="Variable_List ':' S_Byte_Str_Spec"),
    RuleFix("F14", "D_Byte_Str_Var_Decl", "unreferenced after F13 and F14",
            old="Variable_List ':' D_Byte_Str_Spec"),
    RuleFix("F14", "Array_Var_Decl", "unreferenced after F14",
            old="Variable_List ':' Array_Spec"),
    RuleFix("F14", "Struct_Var_Decl", "unreferenced after F14",
            old="Variable_List ':' Struct_Type_Access"),
    RuleFix("F15", "Interface_Spec_Init", "interface type is missing",
            old="Variable_List (':=' Interface_Value)?",
            new="Variable_List ':' Interface_Type_Access (':=' Interface_Value)?"),
    RuleFix("F16", "Str_Type_Decl", "declared type name must be an identifier",
            old="String_Type_Name ':' String_Type_Name (':=' Char_Str)?",
            new="Str_Type_Name ':' String_Type_Name (':=' Char_Str)?"),
    RuleFix("F16", "Str_Type_Name", "name of declared string type",
            new="Identifier", after="Str_Type_Decl"),
    RuleFix("F17", "S_Byte_Char_Str", "empty string is valid",
            old="\"'\" S_Byte_Char_Value+ \"'\"",
            new="\"'\" S_Byte_Char_Value* \"'\""),
    RuleFix("F17", "D_Byte_Char_Str", "empty string is valid",
            old="'\"' D_Byte_Char_Value+ '\"'",
            new="'\"' D_Byte_Char_Value* '\"'"),
    RuleFix("F18", "Common_Char_Value", "any printable character except $, \" and ',"
            " as stated by the comment, not only ASCII",
            old="[#x20!#x23%&(-/0-9:-@A-Z#x5B-`a-z{-~] | '$$' | '$L' | '$N' | '$P' | '$R'"
                " | '$T'",
            new="[^#x0-#x1F#x7F\"$'] | '$$' | '$L' | '$N' | '$P' | '$R' | '$T'"),
] + [
    RuleFix("F19", unit, "a duration unit cannot be empty",
            old="Fix_Point '%s' | (Unsigned_Int '%s' '_'?)? %s?" % (symbol, symbol, smaller),
            new="Fix_Point '%s' | Unsigned_Int '%s' '_'? %s?" % (symbol, symbol, smaller))
    for unit, symbol, smaller in [
        ("Days", "d", "Hours"), ("Hours", "h", "Minutes"), ("Minutes", "m", "Seconds"),
        ("Seconds", "s", "Milliseconds"), ("Milliseconds", "ms", "Microseconds"),
        ("Microseconds", "us", "Nanoseconds")]
] + [
    RuleFix("F20", "Interface_Name", "unreferenced", old="Identifier"),
    RuleFix("F21", START, "start symbol, programs and configurations were unreachable",
            new="(POU_Decl | Prog_Decl | Config_Decl)*", after="POU_Decl"),
    RuleFix("F22", "Keyword", "reserved words, as in matiec",
            new=" | ".join("'%s'" % k for k in KEYWORDS), after="Identifier"),
    RuleFix("F22", "Identifier", "keywords are not identifiers",
            old="Letter (Letter | Digit)*",
            new="(Letter (Letter | Digit)*) - Keyword"),
]


# Rules that would be lexer rules in ANTLR : their parts are not separated by whitespace
TOKEN_RULES = """
    Letter Digit Bit Octal_Digit Hex_Digit Identifier Keyword Char EOL
    Constant Numeric_Literal Int_Literal Unsigned_Int Signed_Int Binary_Int Octal_Int Hex_Int
    Real_Literal Bit_Str_Literal Bool_Literal
    Char_Literal Char_Str S_Byte_Char_Str D_Byte_Char_Str S_Byte_Char_Value D_Byte_Char_Value
    Common_Char_Value
    Time_Literal Duration Fix_Point Interval Days Hours Minutes Seconds Milliseconds
    Microseconds Nanoseconds Time_Of_Day Daytime Day_Hour Day_Minute Day_Second
    Date Date_Literal Year Month Day Date_And_Time
    Direct_Variable
""".split()


# XML 1.0 Char, replaces ANTLR '.' wildcard
CHAR_RULE = Rule("Char", char_class([(0x9, 0x9), (0xA, 0xA), (0xD, 0xD), (0x20, 0xD7FF),
                                     (0xE000, 0xFFFD), (0x10000, 0x10FFFF)]),
                 leading=["Any character, stands for ANTLR '.' wildcard"])


# ANTLR like notation reader

_ANTLR_TOKEN_RE = re.compile(r"""
    (?P<nl>\n)
  | (?P<ws>[ \t\r]+)
  | (?P<comment>//[^\n]*)
  | (?P<options>options\s*\{[^}]*\}\s*:)
  | (?P<action>\{[^}]*\})
  | (?P<lit>'(?:\\.|[^'\\])*')
  | (?P<range>\.\.)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>[:;|()?*+~.])
""", re.X)

_ESCAPES = {"n": "\n", "r": "\r", "t": "\t"}


@dataclass(frozen=True)
class _NonGreedy:
    expr: object


def _antlr_literal(token):
    text = re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), token[1:-1])
    if len(text) == 1 and ord(text) < 0x20:
        return char_class([(ord(text),) * 2])
    return Lit(text)


def _single_chars(expr):
    """ Ranges of a single character expression, None if not one """
    if isinstance(expr, CharClass) and not expr.negated:
        return list(expr.ranges)
    if isinstance(expr, Lit) and len(expr.text) == 1:
        return [(ord(expr.text),) * 2]
    if isinstance(expr, Alt):
        ranges = [_single_chars(i) for i in expr.items]
        if None not in ranges:
            return [r for rs in ranges for r in rs]
    return None


class _AntlrParser(ebnf._Parser):

    def parse(self):
        items = []
        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            if token.kind == "comment":
                items.append(("comment", token))
                self.pos += 1
                continue
            name = self.next()
            if name.kind != "name":
                self.pos -= 1
                self.error("expected rule name")
            self.expect(":")
            self.inner, self.hidden = [], False
            expr = self.alternative()
            self.expect(";")
            rule = Rule(name.value, expr)
            if self.hidden:
                rule.trailing.extend([WS_EXPLICIT, WS_IGNORABLE])
            rule.trailing.extend(ebnf.comment_text(c.value) for c in self.inner)
            items.append(("rule", rule, name.line, self.tokens[self.pos - 1].end_line))
        return ebnf.assemble(items)

    def alternative(self):
        items = [self.sequence()]
        while self.peek().value == "|":
            self.next()
            items.append(self.sequence())
        # character set definitions : merge single characters into one class
        if any(isinstance(i, CharClass) and (i.negated or any(f != l for f, l in i.ranges))
               for i in items):
            singles = [i for i in items if _single_chars(i) is not None]
            merged = char_class([r for i in singles for r in _single_chars(i)])
            first = items.index(singles[0])
            items = [merged if n == first else i
                     for n, i in enumerate(items) if n == first or i not in singles]
        return alt(*items)

    def sequence(self):
        items = []
        while self.peek().value not in ("|", ")", ";"):
            if self.peek().kind == "action":
                self.hidden |= "HIDDEN" in self.next().value
                continue
            items.append(self.postfix())
        # ( options{greedy=false;}: X )* 'end'  -->  (X* - (X* 'end' X*)) 'end'
        for n, item in enumerate(items[:-1]):
            if isinstance(item, Rep) and isinstance(item.item, _NonGreedy):
                any_x = Rep(item.item.expr, "*")
                items[n] = Diff(any_x, seq(any_x, items[n + 1], any_x))
        if not items:
            self.error("empty sequence")
        return seq(*items)

    def postfix(self):
        expr = self.primary()
        while self.peek().value in ("?", "*", "+"):
            expr = Rep(expr, self.next().value)
        return expr

    def primary(self):
        token = self.next()
        if token.kind == "name":
            return Ref(token.value)
        if token.kind == "lit":
            if self.peek().kind == "range":
                self.next()
                last = self.next()
                return char_class([(ord(_antlr_literal(token.value).text),
                                    ord(_antlr_literal(last.value).text))])
            return _antlr_literal(token.value)
        if token.value == "~":
            ranges = _single_chars(self.primary())
            if ranges is None:
                self.error("can only negate characters")
            return char_class(ranges, negated=True)
        if token.value == ".":
            return Ref("Char")
        if token.value == "(":
            nongreedy = self.peek().kind == "options"
            if nongreedy:
                self.next()
            expr = self.alternative()
            self.expect(")")
            return _NonGreedy(expr) if nongreedy else expr
        self.pos -= 1
        self.error("unexpected token")


def read_antlr(text):
    tokens = list(ebnf.tokenize(text, _ANTLR_TOKEN_RE))
    for token in tokens:
        if token.kind == "comment":
            token.value = "/*" + token.value[2:] + "*/"
    header, rules, footer = _AntlrParser(tokens).parse()
    return Grammar(rules, header, footer)


# Fixing

class FixError(Exception):
    pass


def apply_text_fixes(text):
    for fid, reason, old, new, count in TEXT_FIXES:
        found = text.count(old)
        if found != count:
            raise FixError("%s (%s): expected %d occurrence(s) of %r, found %d"
                           % (fid, reason, count, old, found))
        text = text.replace(old, new)
    return text


def _expr(text):
    return ebnf.parse("X ::= " + text)["X"].expr


def apply_rule_fixes(grammar):
    for fix in RULE_FIXES:
        note = "fix %s: %s" % (fix.fid, fix.reason)
        if fix.old is None:
            grammar.add(Rule(fix.name, _expr(fix.new), trailing=[note]), after=fix.after)
            continue
        if fix.name not in grammar:
            raise FixError("%s: rule %s not found" % (fix.fid, fix.name))
        rule = grammar[fix.name]
        if rule.expr != _expr(fix.old):
            raise FixError("%s: rule %s is\n    %s\nexpected\n    %s" % (
                fix.fid, fix.name, ebnf.format_expr(rule.expr), fix.old))
        if fix.new is None:
            grammar.remove(fix.name)
        else:
            rule.expr = _expr(fix.new)
            rule.trailing.append(note)


def mark_tokens(grammar):
    for name in TOKEN_RULES:
        rule = grammar[name]
        if not rule.annotated(WS_EXPLICIT):
            rule.trailing.insert(0, WS_EXPLICIT)


def header(source):
    fixes = {}
    for fid, reason, *_ in TEXT_FIXES:
        fixes.setdefault(fid, ([], reason))
    for fix in RULE_FIXES:
        fixes.setdefault(fix.fid, ([], fix.reason))[0].append(fix.name)
    return [
        "IEC 61131-3:2013 Annex A grammar, fixed and converted to W3C EBNF (XML 1.0, section 6)",
        "Generated by fix_ebnf.py from %s, do not edit" % os.path.basename(source),
        "Start symbol is %s. Keywords and literals are case insensitive." % START,
        "  ws: explicit   token rule, no whitespace, comment or pragma between its parts",
        "  ws: ignorable  token rule, skipped between tokens of other rules",
        "Fixes, also noted after each fixed rule :",
    ] + ["  %s %s" % (fid, ", ".join(names) + ": " + reason if names else reason)
         for fid, (names, reason) in fixes.items()]


def fix(text, source="iec61131-3-3rd.ebnf"):
    """ Return fixed W3C EBNF Grammar from original ANTLR like text """
    grammar = read_antlr(apply_text_fixes(text))
    grammar.add(CHAR_RULE, after="Identifier")
    apply_rule_fixes(grammar)
    mark_tokens(grammar)
    grammar.header = header(source) + grammar.header
    return grammar


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("source", nargs="?", default=os.path.join(here, "iec61131-3-3rd.ebnf"))
    parser.add_argument("-o", "--output",
                        default=os.path.join(here, "iec61131-3-3rd_fixed.ebnf"))
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="list grammar warnings")
    args = parser.parse_args(argv)

    with open(args.source, encoding="utf-8") as f:
        text = f.read()
    try:
        grammar = fix(text, args.source)
    except (FixError, ebnf.EbnfSyntaxError) as e:
        sys.exit("%s: %s" % (args.source, e))

    errors, warnings = ebnf.validate(grammar, START, conflicts=True)
    for message in errors + (warnings if args.verbose else []):
        print(message, file=sys.stderr)
    if errors:
        sys.exit("%s: %d error(s)" % (args.output, len(errors)))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(ebnf.format_grammar(grammar))
    print("%s: %d rules, %d warning(s)" % (args.output, len(grammar.rules), len(warnings)))


if __name__ == "__main__":
    main()
