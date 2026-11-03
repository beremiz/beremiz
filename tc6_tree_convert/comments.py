#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Comments of text files : documentation of declarations, and free comments

A comment right before a declaration, starting its line and separated from the
declaration by whitespace without blank line, is its documentation. Text between
declarations that holds other comments is kept verbatim as a gap, before next
declaration, or before END keyword of a container. Gaps are kept as XML comments
in tc6_tree additional data of declarations, that also hold file path and index
of top level declarations.
"""

from lxml import etree

from .common import TREE_NS, ConversionError, tc6, localname, sub, elements

_DECL = "{%s}decl" % TREE_NS


def comment_text(comment):
    """ Documentation text of IEC comment """
    if comment.startswith("//"):
        return comment[2:].rstrip("\r\n")
    return comment[2:-2]


def doc_comment(text):
    """ IEC comment of documentation text """
    if "*)" not in text:
        return "(*" + text + "*)"
    if "*/" not in text:
        return "/*" + text + "*/"
    raise ConversionError("documentation contains both *) and */: %r" % text[:40])


def significant(gap):
    return gap is not None and gap.strip() != ""


class Trivia:
    """ Comments and pragmas of a text, out of raw bodies """

    def __init__(self, text, trivia):
        self.text = text
        self.items = sorted((start, end, kind) for start, (kind, end) in trivia.items())
        self.excluded = []

    def exclude(self, start, end):
        """ Comments between start and end are part of a body, or are a header """
        self.excluded.append((start, end))

    def within(self, start, end):
        return [(s, e, k) for s, e, k in self.items if start <= s and e <= end and
                not any(a <= s and e <= b for a, b in self.excluded)]

    def gap(self, start, end):
        """ Text between start and end, without excluded parts """
        text, position = "", start
        for a, b in sorted(self.excluded):
            if position <= a and b <= end:
                text += self.text[position:a]
                position = b
        return text + self.text[position:end]

    def leading(self, start, end):
        """ Gap, and documentation start and text, of a declaration starting at end
        after a previous token ending at start """
        comments = self.within(start, end)
        if comments:
            comment_start, comment_end, kind = comments[-1]
            between = self.text[comment_end:end]
            # documentation starts its line, a comment after previous token is not
            own_line = start == 0 or "\n" in self.text[start:comment_start]
            if kind == "Comment" and own_line and not between.strip() and \
               between.count("\n") <= 1:
                text = comment_text(self.text[comment_start:comment_end])
                return self.gap(start, comment_start), comment_start, text
        return self.gap(start, end), end, None


# tc6_tree additional data

def _decl(element, create=False):
    add_data = element.find(tc6("addData"))
    if add_data is not None:
        for data in elements(add_data, "data"):
            if data.get("name") == TREE_NS:
                return data.find(_DECL)
    if not create:
        return None
    if add_data is None:
        add_data = etree.Element(tc6("addData"))
        documentation = element.find(tc6("documentation"))
        if documentation is not None:
            documentation.addprevious(add_data)
        else:
            element.append(add_data)
    data = sub(add_data, "data", {"name": TREE_NS, "handleUnknown": "preserve"})
    # namespace is declared here, with no attribute after it, so that Beremiz keeps it
    # when copying an element (see xmlclass DefaultElementClass.tostring)
    return etree.SubElement(data, _DECL, nsmap={"tree": TREE_NS})


def check_add_data(element):
    """ Raise if element has additional data other than tc6_tree one """
    add_data = element.find(tc6("addData"))
    if add_data is not None:
        for data in elements(add_data, "data"):
            if data.get("name") != TREE_NS:
                raise ConversionError("%s %s: additional data %s is not supported" % (
                    localname(element), element.get("name", ""), data.get("name")))


def _escape(text):
    return text.replace("\\", "\\\\").replace("-", "\\-")


def _unescape(text):
    result, escaped = [], False
    for c in text:
        if escaped or c != "\\":
            result.append(c)
            escaped = False
        else:
            escaped = True
    return "".join(result)


def _set(element, name, text=None, comment=None):
    decl = _decl(element, True)
    item = decl.find("{%s}%s" % (TREE_NS, name))
    if item is None:
        item = etree.SubElement(decl, "{%s}%s" % (TREE_NS, name))
    if comment is not None:
        item.append(etree.Comment(_escape(comment)))
    elif text is not None:
        item.text = text


def _get(element, name):
    decl = _decl(element)
    if decl is None:
        return None
    return decl.find("{%s}%s" % (TREE_NS, name))


def set_location(element, path, index):
    _set(element, "path", path)
    _set(element, "index", str(index))


def location(element):
    """ (path, index) of top level declaration, (None, None) if unknown """
    path, index = _get(element, "path"), _get(element, "index")
    try:
        return (path.text if path is not None else None,
                int(index.text) if index is not None else None)
    except ValueError:
        return path.text, None


def set_block(element, gap):
    """ Mark data type starting a TYPE block, keeping gap before TYPE if it holds comments """
    _set(element, "block", comment=gap if significant(gap) else None)


def block(element):
    """ None if data type does not start a TYPE block, gap before TYPE otherwise """
    item = _get(element, "block")
    if item is None:
        return None
    return "".join(_unescape(c.text or "") for c in item if isinstance(c, etree._Comment))


def set_gap(element, which, gap):
    """ Keep gap holding comments, which is "before" or "after" element """
    if significant(gap):
        _set(element, which, comment=gap)


def gap(element, which):
    item = _get(element, which)
    if item is None:
        return None
    return "".join(_unescape(c.text or "") for c in item if isinstance(c, etree._Comment))
