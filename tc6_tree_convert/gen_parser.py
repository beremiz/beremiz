#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Generate a packrat PEG parser from W3C EBNF grammar

Generated module only depends on Python standard library re module.

Token rules (/* ws: explicit */) compile to regular expressions, rules they
refer to are inlined. Their end is guarded for maximal munch : a token ending
with a letter, digit or underscore is not followed by one, and a numeric token
ending with a digit is not followed by '.' and a digit, or by '#'. When a token rule is an
alternative, longest alternative wins. In token rules, A - B is A where B does
not match a whole word, and X* - (X* L X*) is X* not containing L.

Ignorable rules (/* ws: ignorable */) are skipped before tokens. Those that are
not only whitespace are recorded in parser trivia, by position.

Other rules compile to memoized methods. Alternatives are all tried, longest
match wins, first one in case of tie. Ignorable text after a match does not
count, so that a raw body is not longer than another body for its trailing
whitespace. Repetitions are greedy, they never give
back what they matched. A - B is A unless B matches the same text.
Literals made of letters, digits and underscores are keywords, they are not
followed by a letter, digit or underscore. Other literals are not followed by
what would make them a longer literal of the grammar, as ':' is not followed by
'='. Matching is case insensitive.

Parse tree nodes are (name, start, end, children) tuples, name being a rule name
or a quoted literal, children being None for tokens and literals.
"""

import argparse
import os
import re
import sys

import ebnf
from ebnf import Alt, Seq, Rep, Diff, Ref, Lit, CharClass, WS_IGNORABLE


WORD_CHARS = "A-Za-z0-9_"
WORD_GUARD = "(?:(?<![%s])|(?![%s]))" % (WORD_CHARS, WORD_CHARS)
NUMBER_GUARD = r"(?:(?<![0-9])|(?!\.[0-9]|#))"
_KEYWORD_RE = re.compile(r"[A-Za-z0-9_]+$")


class GeneratorError(Exception):
    pass


def class_regex(charclass):
    def char(code):
        c = chr(code)
        return "\\" + c if c in "\\]^-[" else c
    ranges = "".join(char(f) if f == l else char(f) + "-" + char(l) for f, l in charclass.ranges)
    return "[%s%s]" % ("^" if charclass.negated else "", ranges)


class TokenCompiler:
    """ Token rules as regular expressions """

    def __init__(self, grammar):
        self.grammar = grammar
        self.nullable = ebnf.nullables(grammar)[1]

    def regex(self, expr, stack=()):
        if isinstance(expr, Alt):
            return "(?:%s)" % "|".join(self.regex(i, stack) for i in expr.items)
        if isinstance(expr, Seq):
            return "".join(self.regex(i, stack) for i in expr.items)
        if isinstance(expr, Rep):
            return "(?:%s)%s" % (self.regex(expr.item, stack), expr.op)
        if isinstance(expr, Diff):
            left, right = expr.left, expr.right
            if isinstance(left, Rep) and left.op == "*" and isinstance(right, Seq) and \
               len(right.items) == 3 and right.items[0] == left == right.items[2]:
                return "(?:(?!%s)%s)*" % (self.regex(right.items[1], stack),
                                          self.regex(left.item, stack))
            return "(?!(?:%s)(?![%s]))(?:%s)" % (self.regex(right, stack), WORD_CHARS,
                                                 self.regex(left, stack))
        if isinstance(expr, Lit):
            return re.escape(expr.text)
        if isinstance(expr, CharClass):
            return class_regex(expr)
        if isinstance(expr, Ref):
            if expr.name in stack:
                raise GeneratorError("recursive token rule: " + " -> ".join(stack + (expr.name,)))
            return "(?:%s)" % self.regex(self.grammar[expr.name].expr, stack + (expr.name,))
        raise TypeError(expr)

    def first_chars(self, expr, stack=()):
        """ Characters a match may start with, approximated with ASCII """
        if isinstance(expr, Alt):
            return set().union(*(self.first_chars(i, stack) for i in expr.items))
        if isinstance(expr, Seq):
            result = set()
            for item in expr.items:
                result |= self.first_chars(item, stack)
                if not self.nullable(item):
                    break
            return result
        if isinstance(expr, Rep):
            return self.first_chars(expr.item, stack)
        if isinstance(expr, Diff):
            return self.first_chars(expr.left, stack)
        if isinstance(expr, Lit):
            return {expr.text[:1].upper()}
        if isinstance(expr, CharClass):
            chars = {chr(c) for f, l in expr.ranges for c in range(f, min(l, 127) + 1)}
            return {chr(c) for c in range(128)} - chars if expr.negated else chars
        if isinstance(expr, Ref):
            if expr.name in stack:
                return set()
            return self.first_chars(self.grammar[expr.name].expr, stack + (expr.name,))
        raise TypeError(expr)

    def token(self, name):
        """ Patterns of token rule : one per alternative, longest wins """
        expr = self.grammar[name].expr
        guard = WORD_GUARD
        if self.first_chars(expr) & set("0123456789"):
            guard += NUMBER_GUARD
        items = expr.items if isinstance(expr, Alt) else (expr,)
        return [self.regex(i, (name,)) + guard for i in items]


class ParserGenerator:

    def __init__(self, grammar):
        self.grammar = grammar
        self.tokens = TokenCompiler(grammar)
        self.rule_ids = {r.name: n for n, r in enumerate(grammar)}
        self.patterns = {}      # regex source -> constant name
        self.methods = []       # generated method sources
        self.count = 0
        literals = {e.text.upper() for r in grammar if not r.is_token()
                    for e in ebnf.walk(r.expr) if isinstance(e, Lit)}
        self.punctuation = [lit for lit in literals if not _KEYWORD_RE.match(lit)]

    def constant(self, source):
        if source not in self.patterns:
            self.patterns[source] = "_P%d" % len(self.patterns)
        return self.patterns[source]

    def literal_regex(self, text):
        if _KEYWORD_RE.match(text):
            return re.escape(text) + "(?![%s])" % WORD_CHARS
        longer = sorted({lit[len(text):] for lit in self.punctuation
                         if lit != text.upper() and lit.startswith(text.upper())})
        if longer:
            return re.escape(text) + "(?!%s)" % "|".join(re.escape(s) for s in longer)
        return re.escape(text)

    def call(self, expr, p="p"):
        """ Python expression matching expr at position p """
        if isinstance(expr, Ref):
            if expr.name not in self.grammar:
                raise GeneratorError("undefined rule " + expr.name)
            if self.grammar[expr.name].is_token():
                return "self._token(%s, %s, %r)" % (p, self.constant_token(expr.name), expr.name)
            return "self.r_%s(%s)" % (expr.name, p)
        if isinstance(expr, Lit):
            return "self._literal(%s, %s, %r)" % (
                p, self.constant(self.literal_regex(expr.text)), "'%s'" % expr.text)
        if isinstance(expr, CharClass):
            return "self._literal(%s, %s, %r)" % (
                p, self.constant(class_regex(expr)), ebnf.format_expr(expr))
        return "self.%s(%s)" % (self.method(expr), p)

    def constant_token(self, name):
        key = ("token", name)
        if key not in self.patterns:
            self.patterns[key] = "_T_%s" % name
        return self.patterns[key]

    def method(self, expr):
        self.count += 1
        name = "_e%d" % self.count
        lines = ["    def %s(self, p):" % name]
        if isinstance(expr, Seq):
            lines.append("        c = []")
            for item in expr.items:
                lines += ["        r = %s" % self.call(item),
                          "        if r is None:",
                          "            return None",
                          "        p = r[0]",
                          "        c.extend(r[1])"]
            lines.append("        return (p, c)")
        elif isinstance(expr, Alt):
            lines.append("        b = %s" % self.call(expr.items[0]))
            for item in expr.items[1:]:
                lines += ["        r = %s" % self.call(item),
                          "        if r is not None and (b is None or"
                          " self.skip(r[0]) > self.skip(b[0])):",
                          "            b = r"]
            lines.append("        return b")
        elif isinstance(expr, Rep) and expr.op == "?":
            lines += ["        r = %s" % self.call(expr.item),
                      "        return (p, ()) if r is None else r"]
        elif isinstance(expr, Rep):
            lines += ["        c = []",
                      "        n = 0",
                      "        while True:",
                      "            r = %s" % self.call(expr.item),
                      "            if r is None:",
                      "                break",
                      "            c.extend(r[1])",
                      "            n += 1",
                      "            if r[0] == p:",
                      "                break",
                      "            p = r[0]"]
            if expr.op == "+":
                lines += ["        if n == 0:",
                          "            return None"]
            lines.append("        return (p, c)")
        elif isinstance(expr, Diff):
            lines += ["        r = %s" % self.call(expr.left),
                      "        if r is None:",
                      "            return None",
                      "        s = %s" % self.call(expr.right),
                      "        if s is not None and s[0] == r[0]:",
                      "            return None",
                      "        return r"]
        else:
            raise TypeError(expr)
        self.methods.append("\n".join(lines))
        return name

    def rule(self, rule):
        body = self.call(rule.expr, "s")
        self.methods.append("\n".join([
            "    def r_%s(self, p):" % rule.name,
            "        k = p * %d + %d" % (len(self.rule_ids), self.rule_ids[rule.name]),
            "        if k in self.memo:",
            "            return self.memo[k]",
            "        s = self.skip(p)",
            "        r = %s" % body,
            "        if r is not None:",
            "            r = (r[0], [(%r, s, r[0], r[1])])" % rule.name,
            "        self.memo[k] = r",
            "        return r"]))

    def generate(self, source_name):
        for rule in self.grammar:
            if rule.is_token():
                self.constant_token(rule.name)
            else:
                self.rule(rule)
        ignorable = [r for r in self.grammar if r.annotated(WS_IGNORABLE)]
        blank = [r.name for r in ignorable
                 if self.tokens.first_chars(r.expr) <= set(" \t\r\n")]
        if not ignorable:
            raise GeneratorError("no ignorable rule")

        out = [HEADER % os.path.basename(source_name), "import re", "",
               "_FLAGS = re.IGNORECASE | re.ASCII", ""]
        for source, constant in sorted(self.patterns.items(), key=lambda i: i[1]):
            if isinstance(source, tuple):
                patterns = self.tokens.token(source[1])
                out.append("%s = (%s,)" % (constant, ", ".join(
                    "re.compile(%r, _FLAGS)" % p for p in patterns)))
            else:
                out.append("%s = re.compile(%r, _FLAGS)" % (constant, source))
        out.append("_BLANK = re.compile(%r, _FLAGS)" % ("(?:%s)+" % "|".join(
            self.tokens.regex(self.grammar[n].expr, (n,)) for n in blank)))
        out.append("_TRIVIA = re.compile(%r, _FLAGS)" % "|".join(
            "(?P<%s>%s)" % (r.name, self.tokens.regex(r.expr, (r.name,)))
            for r in ignorable if r.name not in blank))
        out.append("")
        out.append(PARSER_CLASS)
        out.append("\n\n".join(self.methods))
        out.append(FOOTER)
        return "\n".join(out)


HEADER = '''\
# Generated by gen_parser.py from %s, do not edit

"""
IEC 61131-3 and PLCopen TC6 textual forms parser, see gen_parser.py

parse(text, start) returns parse tree and trivia (comments and pragmas) of text
matching start rule. Parse tree nodes are (name, start, end, children) tuples,
name being a rule name or a quoted literal, children being None for tokens and
literals. Trivia maps position of comments and pragmas to (rule name, end).
"""
'''

PARSER_CLASS = '''

class ParseError(Exception):

    def __init__(self, text, position, expected):
        self.position = position
        self.line = text.count("\\n", 0, position) + 1
        self.column = position - text.rfind("\\n", 0, position)
        self.expected = sorted(expected)
        found = text[position:position + 20].split("\\n")[0]
        Exception.__init__(self, "line %d, column %d: expected %s, found %s" % (
            self.line, self.column, ", ".join(self.expected[:8]) +
            (", ..." if len(self.expected) > 8 else ""),
            repr(found) if found else "end of line" if position < len(text) else "end of text"))


class Parser:

    def __init__(self, text):
        self.text = text
        self.memo = {}
        self.skipped = {}
        self.trivia = {}
        self.farthest = 0
        self.expected = set()

    def skip(self, p):
        """ Position after ignorable text, recording trivia """
        if p in self.skipped:
            return self.skipped[p]
        start, text = p, self.text
        while True:
            m = _BLANK.match(text, p)
            if m is not None:
                p = m.end()
            m = _TRIVIA.match(text, p)
            if m is None:
                break
            self.trivia[p] = (m.lastgroup, m.end())
            p = m.end()
        self.skipped[start] = p
        return p

    def fail(self, p, name):
        if p > self.farthest:
            self.farthest = p
            self.expected = {name}
        elif p == self.farthest:
            self.expected.add(name)

    def _literal(self, p, pattern, name):
        p = self.skip(p)
        m = pattern.match(self.text, p)
        if m is None:
            self.fail(p, name)
            return None
        return (m.end(), [(name, p, m.end(), None)])

    def _token(self, p, patterns, name):
        p = self.skip(p)
        end = -1
        for pattern in patterns:
            m = pattern.match(self.text, p)
            if m is not None and m.end() > end:
                end = m.end()
        if end < 0:
            self.fail(p, name)
            return None
        return (end, [(name, p, end, None)])

    def parse(self, start):
        """ Return parse tree of whole text, from start rule """
        method = getattr(self, "r_" + start, None)
        if method is not None:
            r = method(0)
        else:
            r = self._token(0, globals()["_T_" + start], start)
        if r is not None:
            end = self.skip(r[0])
            if end == len(self.text):
                return r[1][0]
            self.fail(end, "end of text")
        raise ParseError(self.text, self.farthest, self.expected)
'''

FOOTER = '''

def parse(text, start):
    """ Return (parse tree, trivia) of text, from start rule, raise ParseError """
    parser = Parser(text)
    return parser.parse(start), parser.trivia


def matches(text, rule):
    """ True if whole text matches rule """
    try:
        Parser(text).parse(rule)
    except ParseError:
        return False
    return True
'''


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("source", nargs="?",
                        default=os.path.join(here, "iec61131-3-3rd_extended.ebnf"))
    parser.add_argument("-o", "--output", default=os.path.join(here, "iec_parser.py"))
    args = parser.parse_args(argv)

    with open(args.source, encoding="utf-8") as f:
        grammar = ebnf.parse(f.read())
    try:
        code = ParserGenerator(grammar).generate(args.source)
    except GeneratorError as e:
        sys.exit("%s: %s" % (args.source, e))
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(code)
    print("%s: %d rules" % (args.output, len(grammar.rules)))


if __name__ == "__main__":
    main()
