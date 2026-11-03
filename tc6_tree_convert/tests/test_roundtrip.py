#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Round trip tests of TC6 XML <-> text tree conversion
"""

import filecmp
import os
import sys
import tempfile
import time
import unittest

from lxml import etree

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(TESTS_DIR)))
sys.path.insert(0, TESTS_DIR)

from tc6_tree_convert import tree_to_xml, xml_to_tree, ConversionError  # noqa: E402
from tc6_tree_convert import iec_parser  # noqa: E402
from tc6_tree_convert.tree import EXTENSIONS  # noqa: E402
from tc6_tree_convert.canon import difference  # noqa: E402
from tc6_tree_convert.common import tc6  # noqa: E402
from tc6_tree_convert.__main__ import read_xml  # noqa: E402
from test_graph import corpus  # noqa: E402


def write_tree(directory, files):
    for path, text in files.items():
        absolute = os.path.join(directory, path)
        os.makedirs(os.path.dirname(absolute), exist_ok=True)
        with open(absolute, "w", encoding="utf-8", newline="") as f:
            f.write(text)


def read_tree(directory):
    files = {}
    for root, _dirs, names in os.walk(directory):
        for name in names:
            path = os.path.join(root, name)
            with open(path, encoding="utf-8", newline="") as f:
                files[os.path.relpath(path, directory).replace(os.sep, "/")] = f.read()
    return files


def same_directories(a, b):
    comparison = filecmp.dircmp(a, b)

    def differences(c):
        return c.diff_files + c.left_only + c.right_only + \
            [d for s in c.subdirs.values() for d in differences(s)]
    return differences(comparison)


DECLARATIONS = {
    "types.st": """\
{TC6 PROJECT(companyName := 'Beremiz',
    productName := 'test$7D',
    productVersion := '1',
    creationDateTime := '2026-11-03T10:00:00',
    name := 'project',
    Comment := 'a comment',
    pageSize := (1050, 1485),
    fbdScaling := (8, 8),
    ldScaling := (0, 0),
    sfcScaling := (5, 5))}

TYPE
  Color : (Red, Green, Blue) := Green;
  Level : INT (Low := 1, High := 10);
  Percent : UINT (0..100) := 50;
  Signed : INT (-10..10);
  Name : STRING[20] := 'nobody';
  Wide : WSTRING;
  Matrix : ARRAY [0..2, 1..3] OF ARRAY [0..1] OF LREAL := [6(0.0), 3(1.0)];
  Ptr : REF_TO Point;
  Point : STRUCT
    x : REAL := 1.5;
    y : REAL;
    at_input AT %IX0.1 : BOOL;
    names : ARRAY [1..2] OF STRING := ['a', 'b'];
  END_STRUCT;
  Empty : STRUCT
  END_STRUCT;
  Line : Point := (x := 1.0, y := 2.0);
  Day : TOD;
  Stamp : DT := DT#2026-11-03-10:00:00;
END_TYPE
""",
    "pous/functions.st": """\
FUNCTION Average : REAL
  VAR_INPUT
    a : INT;
    b : INT := 2;
  END_VAR
  VAR_IN_OUT
    io : ARRAY [0..9] OF INT;
  END_VAR
  VAR_TEMP
    t : REAL;
  END_VAR
Average := (a + b) / 2;
END_FUNCTION

FUNCTION_BLOCK Counter
  VAR_INPUT
    Reset : BOOL;
  END_VAR
  VAR_OUTPUT
    Count : DINT;
  END_VAR
  VAR RETAIN
    Total : DINT;
  END_VAR
  VAR CONSTANT NON_RETAIN
    Limit : DINT := 1000;
  END_VAR
  VAR_EXTERNAL
    Global : INT;
  END_VAR
  ACTION Clear :
Count := 0;
Total := 0;
  END_ACTION
  ACTION Bump : Count := Count + 1; END_ACTION
IF Reset THEN Clear(); ELSE Bump(); END_IF;
IF a[b[i]]>0 THEN (* CDATA end ]]> *) x := ']]>'; END_IF;
END_FUNCTION_BLOCK
""",
    "pous/il.il": """\
FUNCTION_BLOCK Il
  VAR
    x : BOOL;
  END_VAR
  LD x
  ST x
END_FUNCTION_BLOCK
""",
    "config.st": """\
CONFIGURATION config
  VAR_GLOBAL
    Global : INT;
    Output AT %QX0.0 : BOOL;
  END_VAR
  RESOURCE resource1 ON PLC
    TASK fast(INTERVAL := T#10ms, PRIORITY := 0);
    TASK event(SINGLE := Output, PRIORITY := 1);
    PROGRAM counter0 WITH fast : Main;
    PROGRAM other0 WITH event : Main;
    PROGRAM free0 : Main;
  END_RESOURCE
END_CONFIGURATION
""",
    "main.st": """\
PROGRAM Main
  VAR
    c : Counter;
    il : Il;
  END_VAR
c(Reset := FALSE);
END_PROGRAM
""",
    "README.md": "not converted\n",
}


class DeclarationTest(unittest.TestCase):

    def test_declarations(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = os.path.join(tmp, "a")
            write_tree(source, DECLARATIONS)
            xml = tree_to_xml(source)
            root = etree.fromstring(xml.encode())
            types = {t.get("name"): t for t in root.iter(tc6("dataType"))}
            self.assertEqual(etree.QName(types["Percent"].find(tc6("baseType"))[0]).localname,
                             "subrangeUnsigned")
            self.assertEqual(types["Name"].find(".//" + tc6("string")).get("length"), "20")
            self.assertIsNotNone(types["Ptr"].find(".//" + tc6("pointer")))
            self.assertEqual(len(types["Matrix"].findall(".//" + tc6("arrayValue") + "/" +
                                                         tc6("value"))), 2)
            self.assertEqual(root.find(".//" + tc6("fileHeader")).get("productName"), "test}")
            self.assertEqual(len(root.findall(".//" + tc6("task") + "/" + tc6("pouInstance"))), 2)
            body = root.find(".//" + tc6("pou") + "[@name='Counter']/" + tc6("body"))
            self.assertIn("]]>' ; END_IF;".replace("' ;", "';"),
                          body.find(".//{http://www.w3.org/1999/xhtml}p").text)

            # written back as it was
            copy = os.path.join(tmp, "b")
            xml_to_tree(xml, copy)
            files = read_tree(copy)
            for path, text in DECLARATIONS.items():
                if path.endswith(".md"):
                    continue
                self.assertEqual(files.get(path), text, path)

    def test_rejected(self):
        for files in [
                {"a.st": "CONFIGURATION a END_CONFIGURATION\n",
                 "b.st": "CONFIGURATION b END_CONFIGURATION\n"},
                {"a.st": "{TC6 PROJECT(name := 'a')}\n", "b.st": "{TC6 PROJECT(name := 'b')}\n"},
                {"a.st": "PROGRAM p\n  VAR\n    x : BOOL R_EDGE;\n  END_VAR\nEND_PROGRAM\n"},
                {"a.st": "PROGRAM p\n  VAR\n    x : LTIME;\n  END_VAR\nEND_PROGRAM\n"},
                {"a.st": "PROGRAM p\nEND_FUNCTION\n"},
                {"a.il": "TYPE t : INT; END_TYPE\n"}]:
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ConversionError) as context:
                write_tree(tmp, files)
                tree_to_xml(tmp)
            self.assertIsNotNone(context.exception.path, files)

    def test_error_location(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(ConversionError) as context:
            write_tree(tmp, {"sub/a.st": "PROGRAM p\n  VAR\n    x : INT\n  END_VAR\nEND_PROGRAM\n"})
            tree_to_xml(tmp)
        self.assertEqual((context.exception.path, context.exception.line), ("sub/a.st", 4))


class CorpusTest(unittest.TestCase):

    def test_corpus(self):
        """ TC6 XML of Beremiz projects, converted to text and back, is the same, and text
        converted to XML and back is unchanged """
        start = time.time()
        for path in corpus():
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                xml = read_xml(path)
                xml_to_tree(xml, os.path.join(tmp, "a"))
                back = tree_to_xml(os.path.join(tmp, "a"))
                self.assertIsNone(difference(etree.fromstring(xml.encode()),
                                             etree.fromstring(back.encode())))
                xml_to_tree(back, os.path.join(tmp, "b"))
                self.assertEqual(same_directories(os.path.join(tmp, "a"), os.path.join(tmp, "b")),
                                 [])
        print("\n%d projects in %.1fs" % (len(corpus()), time.time() - start), file=sys.stderr)


def literals(node):
    if node[0].startswith("'"):
        yield node
    for item in node[3] or ():
        yield from literals(item)


def perturb(text, language):
    """ Same text with keywords in other case and more spaces, out of bodies and strings """
    tree, _trivia = iec_parser.parse(text, "TC6_%s_File" % language)
    for _name, start, end, _children in sorted(literals(tree), key=lambda n: -n[1]):
        literal = text[start:end]
        if literal in (";", ","):
            literal += " "
        text = text[:start] + literal.swapcase() + text[end:]
    return text


class PerturbationTest(unittest.TestCase):

    def test_corpus(self):
        """ Keyword case and spacing do not change XML """
        for path in corpus():
            with self.subTest(path=path), tempfile.TemporaryDirectory() as tmp:
                xml_to_tree(read_xml(path), os.path.join(tmp, "a"))
                files = read_tree(os.path.join(tmp, "a"))
                write_tree(os.path.join(tmp, "b"), {
                    name: perturb(text, EXTENSIONS[os.path.splitext(name)[1]])
                    for name, text in files.items()})
                self.assertIsNone(difference(
                    etree.fromstring(tree_to_xml(os.path.join(tmp, "a")).encode()),
                    etree.fromstring(tree_to_xml(os.path.join(tmp, "b")).encode())))


if __name__ == "__main__":
    unittest.main()
