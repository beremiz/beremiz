#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
W3C EBNF grammar model shared by fix_ebnf.py, extend_ebnf.py and gen_parser.py

Notation is the one of XML 1.0 specification, section 6 :
    Rule ::= expression
    A B         sequence
    A | B       alternative
    A? A* A+    optional, zero or more, one or more
    A - B       strings matching A but not B
    'x' "x"     literal
    [a-z#x20]   character class, [^...] negated, #xN character

Annotations are comments that follow a rule on its last line:
    /* ws: explicit */   token rule : no whitespace, comment or pragma between its parts
    /* ws: ignorable */  token rule skipped between tokens of other rules
"""

import re
from dataclasses import dataclass, field

WS_EXPLICIT = "ws: explicit"
WS_IGNORABLE = "ws: ignorable"


# Expressions

@dataclass(frozen=True)
class Alt:
    items: tuple


@dataclass(frozen=True)
class Seq:
    items: tuple


@dataclass(frozen=True)
class Rep:
    item: object
    op: str  # '?', '*' or '+'


@dataclass(frozen=True)
class Diff:
    left: object
    right: object


@dataclass(frozen=True)
class Ref:
    name: str


@dataclass(frozen=True)
class Lit:
    text: str


@dataclass(frozen=True)
class CharClass:
    ranges: tuple  # sorted, merged ((first, last), ...) code points
    negated: bool = False


def alt(*items):
    flat = []
    for item in items:
        flat.extend(item.items if isinstance(item, Alt) else [item])
    return flat[0] if len(flat) == 1 else Alt(tuple(flat))


def seq(*items):
    flat = []
    for item in items:
        flat.extend(item.items if isinstance(item, Seq) else [item])
    return flat[0] if len(flat) == 1 else Seq(tuple(flat))


def char_class(ranges, negated=False):
    merged = []
    for first, last in sorted(ranges):
        if merged and first <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(last, merged[-1][1]))
        else:
            merged.append((first, last))
    return CharClass(tuple(merged), negated)


def children(expr):
    if isinstance(expr, (Alt, Seq)):
        return expr.items
    if isinstance(expr, Rep):
        return (expr.item,)
    if isinstance(expr, Diff):
        return (expr.left, expr.right)
    return ()


def walk(expr):
    yield expr
    for child in children(expr):
        yield from walk(child)


def refs(expr):
    return {e.name for e in walk(expr) if isinstance(e, Ref)}


# Rules and grammar

@dataclass
class Rule:
    name: str
    expr: object
    leading: list = field(default_factory=list)   # comments on lines before the rule
    trailing: list = field(default_factory=list)  # comments after the rule, incl. annotations
    blank_before: bool = False

    def annotated(self, annotation):
        return annotation in self.trailing

    def is_token(self):
        return self.annotated(WS_EXPLICIT) or self.annotated(WS_IGNORABLE)


class Grammar:
    def __init__(self, rules=(), header=(), footer=()):
        self.header = list(header)
        self.footer = list(footer)
        self.rules = {}
        for rule in rules:
            self.add(rule)

    def __iter__(self):
        return iter(list(self.rules.values()))

    def __contains__(self, name):
        return name in self.rules

    def __getitem__(self, name):
        return self.rules[name]

    def add(self, rule, after=None):
        if rule.name in self.rules:
            raise ValueError("duplicate rule " + rule.name)
        if after is None:
            self.rules[rule.name] = rule
            return
        if after not in self.rules:
            raise KeyError(after)
        rules = list(self.rules.values())
        rules.insert(rules.index(self.rules[after]) + 1, rule)
        self.rules = {r.name: r for r in rules}

    def remove(self, name):
        return self.rules.pop(name)


# Reader

_TOKEN_RE = re.compile(r"""
    (?P<nl>\n)
  | (?P<ws>[ \t\r]+)
  | (?P<comment>/\*.*?\*/)
  | (?P<define>::=)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<lit>'[^']*'|"[^"]*")
  | (?P<cls>\[[^\]]*\])
  | (?P<code>\#x[0-9A-Fa-f]+)
  | (?P<op>[|()?*+-])
""", re.S | re.X)


class EbnfSyntaxError(Exception):
    pass


@dataclass
class Token:
    kind: str
    value: str
    line: int
    col: int
    end_line: int


def tokenize(text, token_re=_TOKEN_RE):
    """ Yield Token objects, skipping white space """
    pos, line, line_start = 0, 1, 0
    while pos < len(text):
        m = token_re.match(text, pos)
        if m is None:
            raise EbnfSyntaxError("line %d: unexpected %r" % (line, text[pos:pos + 20]))
        kind, value = m.lastgroup, m.group()
        end_line = line + value.count("\n")
        if kind not in ("ws", "nl"):
            yield Token(kind, value, line, pos - line_start, end_line)
        if end_line != line:
            line, line_start = end_line, pos + value.rindex("\n") + 1
        pos = m.end()


def comment_text(comment):
    text = comment[2:-2].rstrip()
    return text[1:] if text.startswith(" ") else text


def assemble(items):
    """ Attach comments to rules
    items: source ordered ("comment", Token) and ("rule", Rule, first_line, last_line)
    A comment on the last line of a rule, or indented on the next line, trails it.
    Other comments lead the next rule. Comments before the first rule and separated
    from it by a blank line make the header, comments after the last rule the footer.
    """
    header, rules, pending = [], [], []
    prev, prev_end = None, None
    for item in items:
        if item[0] == "comment":
            pending.append(item[1])
            continue
        _kind, rule, first, last = item
        rest, end = _trail(prev, prev_end, pending)
        if prev is None:
            # header is everything not glued to the first rule
            glued = len(rest)
            while glued > 0:
                below = rest[glued].line if glued < len(rest) else first
                if below - rest[glued - 1].end_line > 1:
                    break
                glued -= 1
            header = [comment_text(c.value) for c in rest[:glued]]
            rest = rest[glued:]
        else:
            top = rest[0].line if rest else first
            rule.blank_before = top - end > 1
        rule.leading.extend(comment_text(c.value) for c in rest)
        rules.append(rule)
        prev, prev_end, pending = rule, last, []
    footer = [comment_text(c.value) for c in _trail(prev, prev_end, pending)[0]]
    return header, rules, footer


def _trail(prev, prev_end, pending):
    """ Move trailing comments to prev rule, return remaining comments and new end line """
    end = prev_end
    for i, comment in enumerate(pending):
        if prev is not None and (comment.line == end or
                                 (comment.col > 0 and comment.line == end + 1)):
            prev.trailing.append(comment_text(comment.value))
            end = comment.end_line
        else:
            return pending[i:], end
    return [], end


class _Parser:
    """ Recursive descent over a token list, comments are kept apart """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.inner = []  # comments met inside current rule

    def peek(self, offset=0):
        pos = self.pos
        while pos < len(self.tokens):
            if self.tokens[pos].kind != "comment":
                if offset == 0:
                    return self.tokens[pos]
                offset -= 1
            pos += 1
        return None

    def next(self):
        while self.tokens[self.pos].kind == "comment":
            self.inner.append(self.tokens[self.pos])
            self.pos += 1
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def expect(self, value):
        token = self.peek()
        if token is None or token.value != value:
            self.error("expected %r" % value)
        return self.next()

    def error(self, message):
        token = self.peek()
        where = "line %d: " % token.line if token else "end of file: "
        raise EbnfSyntaxError(where + message + (", got %r" % token.value if token else ""))


class _W3CParser(_Parser):

    def at_rule_start(self):
        token, follow = self.peek(), self.peek(1)
        return (token is not None and token.kind == "name" and
                follow is not None and follow.kind == "define")

    def parse(self):
        items = []
        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            if token.kind == "comment":
                items.append(("comment", token))
                self.pos += 1
                continue
            if not self.at_rule_start():
                self.error("expected rule definition")
            name = self.next()
            self.next()
            self.inner = []
            expr = self.alternative()
            last = self.tokens[self.pos - 1].end_line
            rule = Rule(name.value, expr)
            rule.trailing.extend(comment_text(c.value) for c in self.inner)
            items.append(("rule", rule, name.line, last))
        return assemble(items)

    def alternative(self):
        items = [self.sequence()]
        while self.peek() is not None and self.peek().value == "|":
            self.next()
            items.append(self.sequence())
        return alt(*items)

    def sequence(self):
        items = []
        while True:
            token = self.peek()
            if (token is None or token.value in ("|", ")") or self.at_rule_start()):
                break
            items.append(self.difference())
        if not items:
            self.error("empty sequence")
        return seq(*items)

    def difference(self):
        left = self.postfix()
        if self.peek() is not None and self.peek().value == "-":
            self.next()
            return Diff(left, self.postfix())
        return left

    def postfix(self):
        expr = self.primary()
        while self.peek() is not None and self.peek().value in ("?", "*", "+"):
            expr = Rep(expr, self.next().value)
        return expr

    def primary(self):
        token = self.peek()
        if token is None:
            self.error("unexpected end of grammar")
        if token.value == "(":
            self.next()
            expr = self.alternative()
            self.expect(")")
            return expr
        self.next()
        if token.kind == "name":
            return Ref(token.value)
        if token.kind == "lit":
            return Lit(token.value[1:-1])
        if token.kind == "code":
            return char_class([(int(token.value[2:], 16),) * 2])
        if token.kind == "cls":
            return parse_class(token.value[1:-1])
        self.pos -= 1
        self.error("unexpected token")


def parse_class(content):
    negated = content.startswith("^")
    if negated:
        content = content[1:]
    raw = re.findall(r"#x[0-9A-Fa-f]+|.", content, re.S)
    chars = [int(c[2:], 16) if c.startswith("#x") else ord(c) for c in raw]
    ranges, i = [], 0
    while i < len(chars):
        if i + 2 < len(chars) and raw[i + 1] == "-":
            ranges.append((chars[i], chars[i + 2]))
            i += 3
        else:
            ranges.append((chars[i], chars[i]))
            i += 1
    return char_class(ranges, negated)


def parse(text):
    """ Parse W3C EBNF text into a Grammar """
    header, rules, footer = _W3CParser(list(tokenize(text))).parse()
    return Grammar(rules, header, footer)


# Printer

def _class_char(code, after_code=False):
    """ Printable ASCII as is, except class syntax characters, and hex digits after
    a #xN code that would read as part of it """
    char = chr(code)
    if 0x21 <= code <= 0x7E and char not in "[]^-\\#" and \
       not (after_code and char in "0123456789abcdefABCDEF"):
        return char
    return "#x%X" % code


def _class_text(charclass):
    text = "^" if charclass.negated else ""
    for first, last in charclass.ranges:
        for n, code in enumerate((first,) if first == last else (first, last)):
            text += ("-" if n else "") + _class_char(code, re.search(r"#x[0-9A-F]+$", text))
    return "[%s]" % text


def format_expr(expr, min_prec=0):
    """ Precedences: alternative 0, sequence 1, difference 2, postfix 3, primary 4
    Differences inside a sequence are always parenthesized for readability.
    """
    if isinstance(expr, Alt):
        text, prec = " | ".join(format_expr(i, 1) for i in expr.items), 0
    elif isinstance(expr, Seq):
        text, prec = " ".join(format_expr(i, 3) for i in expr.items), 1
    elif isinstance(expr, Diff):
        text, prec = format_expr(expr.left, 3) + " - " + format_expr(expr.right, 3), 2
    elif isinstance(expr, Rep):
        text, prec = format_expr(expr.item, 4) + expr.op, 3
    elif isinstance(expr, Ref):
        text, prec = expr.name, 4
    elif isinstance(expr, Lit):
        if "'" not in expr.text:
            text = "'%s'" % expr.text
        elif '"' not in expr.text:
            text = '"%s"' % expr.text
        else:
            raise ValueError("literal with both quotes: " + expr.text)
        prec = 4
    elif isinstance(expr, CharClass):
        first, last = expr.ranges[0]
        if not expr.negated and len(expr.ranges) == 1 and first == last \
           and _class_char(first).startswith("#x"):
            text = _class_char(first)
        else:
            text = _class_text(expr)
        prec = 4
    else:
        raise TypeError(expr)
    return "(%s)" % text if prec < min_prec else text


def format_rule(rule, width=100):
    prefix = rule.name + " ::= "
    lines = [prefix + format_expr(rule.expr)]
    if len(lines[0]) > width and isinstance(rule.expr, Alt):
        indent = " " * (len(rule.name) + 3) + "| "
        lines = [prefix]
        for item in (format_expr(i, 1) for i in rule.expr.items):
            if len(lines[-1]) + 3 + len(item) > width and lines[-1] not in (prefix, indent):
                lines.append(indent)
            elif lines[-1] not in (prefix, indent):
                lines[-1] += " | "
            lines[-1] += item
    if rule.trailing:
        lines[-1] += " " + " ".join(format_comment(c) for c in rule.trailing)
    return lines


def format_comment(text):
    if "*/" in text:
        raise ValueError("comment text contains '*/': " + text)
    return "/* %s */" % text


def format_grammar(grammar, width=100):
    out = [format_comment(c) for c in grammar.header]
    if out:
        out.append("")
    for rule in grammar:
        if rule.blank_before and out and out[-1] != "":
            out.append("")
        out.extend(format_comment(c) for c in rule.leading)
        out.extend(format_rule(rule, width))
    out.extend(format_comment(c) for c in grammar.footer)
    return "\n".join(out) + "\n"


# Validation

def nullables(grammar):
    result = set()

    def nullable(expr):
        if isinstance(expr, Alt):
            return any(nullable(i) for i in expr.items)
        if isinstance(expr, Seq):
            return all(nullable(i) for i in expr.items)
        if isinstance(expr, Rep):
            return expr.op != "+" or nullable(expr.item)
        if isinstance(expr, Diff):
            return nullable(expr.left)
        if isinstance(expr, Ref):
            return expr.name in result
        if isinstance(expr, Lit):
            return expr.text == ""
        return False

    changed = True
    while changed:
        changed = False
        for rule in grammar:
            if rule.name not in result and nullable(rule.expr):
                result.add(rule.name)
                changed = True
    return result, nullable


def reachable(grammar, roots):
    seen, todo = set(), list(roots)
    while todo:
        name = todo.pop()
        if name in seen or name not in grammar:
            continue
        seen.add(name)
        todo.extend(refs(grammar[name].expr))
    return seen


def left_recursions(grammar):
    """ Return cycles of rules reachable in leftmost position """
    _null, nullable = nullables(grammar)

    def left_refs(expr):
        if isinstance(expr, Alt):
            return set().union(*(left_refs(i) for i in expr.items))
        if isinstance(expr, Seq):
            result = set()
            for item in expr.items:
                result |= left_refs(item)
                if not nullable(item):
                    break
            return result
        if isinstance(expr, Rep):
            return left_refs(expr.item)
        if isinstance(expr, Diff):
            return left_refs(expr.left)
        if isinstance(expr, Ref):
            return {expr.name}
        return set()

    edges = {r.name: sorted(left_refs(r.expr) & set(grammar.rules)) for r in grammar}
    cycles, state = [], {}

    def visit(name, path):
        state[name] = "active"
        for target in edges[name]:
            if state.get(target) == "active":
                cycles.append(path[path.index(target):] + [target])
            elif target not in state:
                visit(target, path + [target])
        state[name] = "done"

    for name in edges:
        if name not in state:
            visit(name, [name])
    return cycles


def greedy_conflicts(grammar):
    """ PEG repetitions never give back what they matched :
    report X?, X* or X+ in syntactic rules when X can start like what follows.
    Token rules are terminals here. A word literal and Identifier overlap
    unless the word is a Keyword.
    """
    _null, nullable = nullables(grammar)
    tokens = {r.name for r in grammar if r.is_token()}
    keywords = set()
    if "Keyword" in grammar:
        keywords = {e.text.upper() for e in walk(grammar["Keyword"].expr) if isinstance(e, Lit)}
    first_sets = {r.name: set() for r in grammar if r.name not in tokens}

    def first(expr):
        if isinstance(expr, Alt):
            return set().union(*(first(i) for i in expr.items))
        if isinstance(expr, Seq):
            result = set()
            for item in expr.items:
                result |= first(item)
                if not nullable(item):
                    break
            return result
        if isinstance(expr, Rep):
            return first(expr.item)
        if isinstance(expr, Diff):
            return first(expr.left)
        if isinstance(expr, Ref):
            if expr.name in tokens:
                return {expr.name}
            return first_sets.get(expr.name, set())
        if isinstance(expr, Lit):
            return {"'%s'" % expr.text.upper()}
        return {format_expr(expr)}

    changed = True
    while changed:
        changed = False
        for name in first_sets:
            new = first(grammar[name].expr)
            if not new <= first_sets[name]:
                first_sets[name] |= new
                changed = True

    def overlap(set_a, set_b):
        common = set_a & set_b
        for a, b in ((a, b) for a in set_a for b in set_b):
            for word, other in ((a, b), (b, a)):
                if other == "Identifier" and re.match(r"^'[A-Z_][A-Z0-9_]*'$", word) \
                   and word[1:-1] not in keywords:
                    common.add(word)
        return common

    follow_sets = {name: set() for name in first_sets}
    conflicts = {}

    def visit(rule, expr, follow):
        """ Propagate follow sets, return True if one of them grew """
        grew = False
        if isinstance(expr, Alt):
            for item in expr.items:
                grew |= visit(rule, item, follow)
        elif isinstance(expr, Seq):
            for item in reversed(expr.items):
                grew |= visit(rule, item, follow)
                follow = first(item) | (follow if nullable(item) else set())
        elif isinstance(expr, Rep):
            common = overlap(first(expr.item), follow)
            if common:
                conflicts[(rule, format_expr(expr))] = sorted(common)
            inner = follow | (first(expr.item) if expr.op != "?" else set())
            grew |= visit(rule, expr.item, inner)
        elif isinstance(expr, Diff):
            grew |= visit(rule, expr.left, follow)
        elif isinstance(expr, Ref) and expr.name in follow_sets:
            if not follow <= follow_sets[expr.name]:
                follow_sets[expr.name] |= follow
                grew = True
        return grew

    grew = True
    while grew:
        conflicts.clear()
        grew = False
        for name in first_sets:
            grew |= visit(name, grammar[name].expr, follow_sets[name])
    return ["%s: %s may swallow %s" % (rule, expr, ", ".join(common[:4]))
            for (rule, expr), common in sorted(conflicts.items())]


def validate(grammar, start, conflicts=False):
    """ Return (errors, warnings) lists of messages """
    errors, warnings = [], []
    for rule in grammar:
        for name in sorted(refs(rule.expr) - set(grammar.rules)):
            errors.append("%s: undefined rule %s" % (rule.name, name))
    roots = [start] + [r.name for r in grammar if r.annotated(WS_IGNORABLE)]
    reached = reachable(grammar, roots)
    for rule in grammar:
        if rule.name not in reached:
            errors.append("%s: unreachable from %s" % (rule.name, start))
    for cycle in left_recursions(grammar):
        errors.append("left recursion: " + " -> ".join(cycle))
    if conflicts:
        warnings.extend(greedy_conflicts(grammar))
    return errors, warnings
