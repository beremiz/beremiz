#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tests for documentation and free comments of text tree
"""

import os
import sys
import tempfile
import unittest

from lxml import etree

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(TESTS_DIR)))
sys.path.insert(0, TESTS_DIR)

from tc6_tree_convert import tree_to_xml, xml_to_tree  # noqa: E402
from tc6_tree_convert.common import tc6, XHTML_NS, TREE_NS  # noqa: E402
from test_roundtrip import write_tree, read_tree  # noqa: E402

TEXT = """\
(* file header comment *)

(* not documentation of a TYPE block *)
TYPE
  (* doc of T1 *)
  T1 : INT;
  T2 : BOOL; (* trailing T2 *)
END_TYPE

// free comment -- with dashes -
(* another one, \\ backslash *)

(* POU doc,
   on two lines *)
PROGRAM p
  VAR (* after VAR *)
    (* x doc *)
    x : INT; (* trailing x *)
    y : INT;

    (* separated by a blank line, not documentation *)

    z : INT;
    (* free before END_VAR *)
  END_VAR
(* in body *)
x := 1;
END_PROGRAM
(* end of file *)
"""


def documentation(element):
    doc = element.find(tc6("documentation"))
    return doc.find("{%s}p" % XHTML_NS).text if doc is not None else None


class CommentTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        write_tree(os.path.join(self.tmp.name, "a"), {"p.st": TEXT})
        self.xml = tree_to_xml(os.path.join(self.tmp.name, "a"))
        self.root = etree.fromstring(self.xml.encode())

    def tearDown(self):
        self.tmp.cleanup()

    def test_documentation(self):
        names = {e.get("name"): e for e in self.root.iter(tc6("dataType"), tc6("pou"),
                                                           tc6("variable"))}
        self.assertEqual(documentation(names["T1"]), " doc of T1 ")
        self.assertIsNone(documentation(names["T2"]))
        self.assertEqual(documentation(names["p"]), " POU doc,\n   on two lines ")
        self.assertEqual(documentation(names["x"]), " x doc ")
        self.assertIsNone(documentation(names["y"]))
        self.assertIsNone(documentation(names["z"]))
        body = self.root.find(".//" + tc6("ST") + "/{%s}p" % XHTML_NS).text
        self.assertEqual(body, "(* in body *)\nx := 1;")

    def test_xml_comments(self):
        comments = list(self.root.iter(etree.Comment))
        texts = [c.text for c in comments]
        self.assertTrue(any("free comment \\-\\- with dashes \\-" in t for t in texts), texts)
        self.assertTrue(all("--" not in t and not t.endswith("-") for t in texts))
        for comment in comments:
            # comments only are in tc6_tree additional data, never among TC6 elements
            self.assertEqual(etree.QName(comment.getparent()).namespace, TREE_NS)

    def test_from_xml_only(self):
        """ Comments come back from XML, without text of loaded files """
        directory = os.path.join(self.tmp.name, "b")
        xml_to_tree(self.xml, directory)
        self.assertEqual(read_tree(directory), {"p.st": TEXT})


if __name__ == "__main__":
    unittest.main()
