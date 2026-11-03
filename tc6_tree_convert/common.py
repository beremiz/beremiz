#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Definitions shared by TC6 XML <-> text conversion modules
"""

import re

from lxml import etree

TC6_NS = "http://www.plcopen.org/xml/tc6_0201"
XHTML_NS = "http://www.w3.org/1999/xhtml"
XSD_NS = "http://www.w3.org/2001/XMLSchema"
TREE_NS = "http://www.beremiz.org/tc6_tree"
NSMAP = {None: TC6_NS, "xhtml": XHTML_NS, "xsd": XSD_NS}

INDENT = "  "

_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_IEC_ESCAPES = {"$": "$$", "'": "$'", "\n": "$N", "\r": "$R", "\t": "$T", "\f": "$P"}
_IEC_UNESCAPES = {"$": "$", "'": "'", '"': '"', "L": "\n", "N": "\n", "P": "\f", "R": "\r",
                  "T": "\t"}


class ConversionError(Exception):
    """ Conversion failure, located in a file when known """

    def __init__(self, message, path=None, text=None, position=None):
        self.message = message
        self.path = path
        self.line = self.column = None
        if text is not None and position is not None:
            self.line = text.count("\n", 0, position) + 1
            self.column = position - text.rfind("\n", 0, position)
        Exception.__init__(self, message)

    def __str__(self):
        where = self.path or ""
        if self.line is not None:
            where += ":%d:%d" % (self.line, self.column)
        return "%s: %s" % (where, self.message) if where else self.message

    def locate(self, path, text=None, position=None):
        """ Add location to error that has none """
        if self.path is None:
            self.path = path
            if self.line is None and text is not None and position is not None:
                self.line = text.count("\n", 0, position) + 1
                self.column = position - text.rfind("\n", 0, position)
        return self


# XML

def tc6(name):
    return "{%s}%s" % (TC6_NS, name)


def localname(element):
    return etree.QName(element).localname


def sub(parent, name, attrib=None):
    """ New TC6 child element """
    element = etree.SubElement(parent, tc6(name))
    for key, value in (attrib or {}).items():
        if value is not None:
            element.set(key, value)
    return element


def elements(parent, name=None):
    """ Child elements, of given TC6 name if given """
    return [c for c in parent if isinstance(c.tag, str) and
            (name is None or c.tag == tc6(name))]


def formatted_text(element):
    """ Text of TC6 formattedText element (xhtml:p) """
    paragraph = element.find("{%s}p" % XHTML_NS)
    if paragraph is None or len(paragraph) or len(element) != 1:
        raise ConversionError("%s: only one paragraph of plain text is supported"
                              % localname(element))
    return paragraph.text or ""


def add_formatted_text(parent, name, text):
    """ New TC6 formattedText child element, as Beremiz writes them """
    element = sub(parent, name)
    paragraph = etree.SubElement(element, "{%s}p" % XHTML_NS)
    paragraph.text = etree.CDATA(text) if "]]>" not in text else text
    return element


# IEC literals

def iec_string(text):
    """ IEC single byte string literal """
    return "'%s'" % "".join(
        _IEC_ESCAPES.get(c) or ("$%02X" % ord(c) if ord(c) < 0x20 else c) for c in text)


def iec_unquote(literal):
    """ Text of IEC string literal """
    quote, content = literal[0], literal[1:-1]
    digits = 2 if quote == "'" else 4

    def unescape(match):
        escaped = match.group(1)
        if escaped.upper() in _IEC_UNESCAPES:
            return _IEC_UNESCAPES[escaped.upper()]
        return chr(int(escaped, 16))
    return re.sub(r"\$([0-9A-Fa-f]{%d}|.)" % digits, unescape, content)


def is_name(text):
    return _NAME_RE.match(text) is not None


def name_or_text(text):
    return text if is_name(text) else iec_string(text)


def is_true(value):
    return value in ("true", "1")


# Parse tree nodes : (name, start, end, children)

def kids(node):
    return node[3] or ()


def child(node, name):
    """ First direct child node with given name, or None """
    return next((c for c in kids(node) if c[0] == name), None)


def children(node, name):
    return [c for c in kids(node) if c[0] == name]


def find(node, name):
    """ First node with given name, depth first, or None """
    if node[0] == name:
        return node
    for c in kids(node):
        found = find(c, name)
        if found is not None:
            return found
    return None


def find_all(node, name, stop=()):
    """ Nodes with given name, depth first, not looking into names in stop """
    if node[0] == name:
        yield node
        return
    if node[0] in stop:
        return
    for c in kids(node):
        yield from find_all(c, name, stop)


def has_literal(node, literal):
    """ True if node has given literal as direct child """
    return any(c[0] == "'%s'" % literal for c in kids(node))


def source(text, node):
    return text[node[1]:node[2]]


def name_value(text, node):
    """ Text of TC6_Name_Or_Text like node """
    value = source(text, node)
    return iec_unquote(value) if value[:1] in "'\"" else value


def body_text(region, single_line=True):
    """ Body text from the text between its header and END keyword.
    Multiline : what is between the line of header and the line of END keyword.
    Single line : what is between one space after header and one space before END keyword.
    """
    if "\n" in region or not single_line:
        region = re.sub(r"^[ \t]*\n", "", region, count=1)
        return re.sub(r"\n[ \t]*$", "", region, count=1)
    if region.startswith(" "):
        region = region[1:]
    return region[:-1] if region.endswith(" ") else region


def body_region(text, single_line=True):
    """ Text between header and END keyword for body text """
    if "\n" in text or not single_line:
        return "\n" + text + "\n"
    return " " + text + " "
