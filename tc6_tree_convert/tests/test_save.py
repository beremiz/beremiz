#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tests for saving TC6 XML to an existing text tree
"""

import copy
import os
import sys
import tempfile
import unittest

from lxml import etree

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(TESTS_DIR)))
sys.path.insert(0, TESTS_DIR)

import tc6_tree_convert  # noqa: E402
from tc6_tree_convert import TreeConflictError  # noqa: E402
from tc6_tree_convert.common import tc6, XHTML_NS, TREE_NS  # noqa: E402
from test_roundtrip import write_tree, read_tree  # noqa: E402

KEEP = "FUNCTION_BLOCK  Keep\n\tVAR_INPUT\n\t\tx :INT;\n\tEND_VAR\n\tVAR  y:BOOL ;END_VAR\n" \
       "x := 1;\nEND_FUNCTION_BLOCK"
CHANGE = "(*doc*)\nPROGRAM Change\n  VAR\n    v : INT;\n  END_VAR\n  VAR   (* odd *)  w :INT; " \
         "END_VAR\nv := 1;\nEND_PROGRAM"
FILES = {
    "a.st": (KEEP + "\n\n" + CHANGE + "\n").replace("\n", "\r\n"),
    "b.st": "PROGRAM Gone\nEND_PROGRAM\n",
    "c/d.fbd": "PROGRAM Fbd\nIN_VARIABLE  #1 a  AT (1,2);\nEND_PROGRAM\n",
    "types.st": "TYPE\n  T1 :INT;\nEND_TYPE\n",
    "notes.txt": "keep me\n",
}


def pou(root, name):
    return root.find(".//%s[@name='%s']" % (tc6("pou"), name))


class SaveTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.directory = os.path.join(self.tmp.name, "plc")
        write_tree(self.directory, FILES)
        self.root = etree.fromstring(tc6_tree_convert.load(self.directory).encode())

    def tearDown(self):
        self.tmp.cleanup()

    def save(self):
        tc6_tree_convert.save(etree.tostring(self.root).decode(), self.directory)
        return read_tree(self.directory)

    def test_unchanged(self):
        self.assertEqual(self.save(), FILES)

    def test_minimal_changes(self):
        # change a body, remove a POU, add a POU and a data type
        body = pou(self.root, "Change").find(".//{%s}p" % XHTML_NS)
        body.text = "v := 2;"
        pous = pou(self.root, "Gone").getparent()
        pous.remove(pou(self.root, "Gone"))
        added = copy.deepcopy(pou(self.root, "Fbd"))
        added.set("name", "Added")
        added.remove(added.find(tc6("addData")))
        pous.append(added)
        data_type = copy.deepcopy(self.root.find(".//" + tc6("dataType")))
        data_type.set("name", "T2")
        data_type.remove(data_type.find(tc6("addData")))
        self.root.find(".//" + tc6("dataTypes")).append(data_type)

        files = self.save()
        expected = dict(FILES)
        expected["a.st"] = expected["a.st"].replace("v := 1;", "v := 2;")
        del expected["b.st"]
        # unchanged element of copied POU gets the text it had
        expected["Added.fbd"] = FILES["c/d.fbd"].replace("PROGRAM Fbd", "PROGRAM Added")
        expected["types.st"] = "TYPE\n  T1 :INT;\n  T2 : INT;\nEND_TYPE\n"
        self.assertEqual(files, expected)

    def test_changed_parts(self):
        """ Unchanged variable blocks of a changed POU keep their text """
        variable = pou(self.root, "Keep").find(".//" + tc6("variable"))
        variable.set("name", "z")
        files = self.save()
        self.assertEqual(files["a.st"], FILES["a.st"].replace(
            "FUNCTION_BLOCK  Keep\r\n\tVAR_INPUT\r\n\t\tx :INT;\r\n\tEND_VAR",
            "FUNCTION_BLOCK Keep\r\n  VAR_INPUT\r\n    z : INT;\r\n  END_VAR"))

    def test_rename_keeps_place(self):
        pou(self.root, "Keep").set("name", "Kept")
        files = self.save()
        self.assertTrue(files["a.st"].startswith("FUNCTION_BLOCK Kept\r\n"))
        self.assertIn(CHANGE.replace("\n", "\r\n"), files["a.st"])

    def test_conflict(self):
        path = os.path.join(self.directory, "b.st")
        with open(path, "w", encoding="utf-8") as f:
            f.write("PROGRAM Gone\n(* edited *)\nEND_PROGRAM\n")
        pou(self.root, "Change").find(".//{%s}p" % XHTML_NS).text = "v := 2;"
        with self.assertRaises(TreeConflictError):
            self.save()
        files = read_tree(self.directory)
        self.assertEqual(files["a.st"], FILES["a.st"])
        self.assertIn("edited", files["b.st"])

    def test_paths_in_xml(self):
        paths = {e.getparent().getparent().getparent().getparent().get("name"): e.text
                 for e in self.root.iter("{%s}path" % TREE_NS)}
        self.assertEqual(paths, {"Keep": "a.st", "Change": "a.st", "Gone": "b.st",
                                 "Fbd": "c/d.fbd", "T1": "types.st"})


if __name__ == "__main__":
    unittest.main()
