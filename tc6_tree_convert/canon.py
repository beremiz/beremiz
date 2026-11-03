#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Canonical form of TC6 XML, equal for XML that mean the same to Beremiz

Ignores attribute order, attributes equal to their default, CDATA sections,
whitespace between elements, comments, empty actions, transitions and additional data,
modification date, schema location, tc6_tree additional data, and order of
data types and POUs that Beremiz sorts by dependency. Never changes text content.
"""

import copy
import hashlib

from lxml import etree

from .common import TREE_NS, tc6, localname
from .tc6_textmap import ATTRIBUTE_DEFAULTS


def _clean(element):
    for node in list(element.iter(etree.Comment, etree.ProcessingInstruction)):
        _remove(node)
    for data in list(element.iter(tc6("data"))):
        if data.get("name") == TREE_NS:
            add_data = data.getparent()
            add_data.remove(data)
            if not len(add_data):
                _remove(add_data)
    for name in ("dataTypes", "pous"):
        for parent in element.iter(tc6(name)):
            for item in sorted(parent, key=lambda e: e.get("name", "") if isinstance(e.tag, str)
                               else ""):
                parent.append(item)
    for name in ("actions", "transitions", "addData"):
        for empty in list(element.iter(tc6(name))):
            if not len(empty):
                _remove(empty)
    element.attrib.pop("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", None)
    for node in element.iter(etree.Element):
        if localname(node) == "contentHeader":
            node.attrib.pop("modificationDateTime", None)
        for attribute, default in ATTRIBUTE_DEFAULTS.items():
            value = node.get(attribute)
            if value is not None and (value == default or
                                      default == "false" and value == "0"):
                del node.attrib[attribute]
        if len(node) and node.text is not None and not node.text.strip():
            node.text = None
        if node.tail is not None and not node.tail.strip():
            node.tail = None


def _remove(node):
    """ Remove node, keeping its tail text """
    parent = node.getparent()
    if node.tail and node.tail.strip():
        previous = node.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + node.tail
        else:
            parent.text = (parent.text or "") + node.tail
    parent.remove(node)


def canonical(element):
    """ Canonical bytes of element """
    if isinstance(element, etree._ElementTree):
        element = element.getroot()
    element = copy.deepcopy(element)
    _clean(element)
    return etree.tostring(element, method="c14n", exclusive=True)


def digest(element):
    return hashlib.sha1(canonical(element)).hexdigest()


def difference(a, b):
    """ None if a and b are equal, otherwise a description of first difference """
    lines_a = canonical(a).decode().replace("><", ">\n<").split("\n")
    lines_b = canonical(b).decode().replace("><", ">\n<").split("\n")
    for n, (line_a, line_b) in enumerate(zip(lines_a, lines_b)):
        if line_a != line_b:
            return "element %d differs:\n- %s\n+ %s" % (n, line_a[:300], line_b[:300])
    if len(lines_a) != len(lines_b):
        return "%d elements instead of %d" % (len(lines_b), len(lines_a))
    return None
