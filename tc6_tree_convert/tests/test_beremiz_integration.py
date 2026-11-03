#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tests of Beremiz projects with PLC program in plc/ directory, without GUI as Beremiz CLI
"""

import os
import shutil
import sys
import tempfile
import unittest

from lxml import etree

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
BEREMIZ_DIR = os.path.dirname(os.path.dirname(TESTS_DIR))
sys.path.insert(0, BEREMIZ_DIR)
sys.path.insert(0, TESTS_DIR)

import fake_wx  # noqa: E402,F401  wx stub, as Beremiz CLI uses
from ProjectController import ProjectController  # noqa: E402
from PLCControler import PLCControler  # noqa: E402
from plcopen.types_enums import ComputePouName  # noqa: E402

from tc6_tree_convert import tree_to_xml  # noqa: E402
from tc6_tree_convert.canon import difference  # noqa: E402
from tc6_tree_convert.common import tc6  # noqa: E402
from test_roundtrip import read_tree, write_tree  # noqa: E402

PROJECTS = os.path.join(BEREMIZ_DIR, "tests", "projects")
TREE_PROJECT = os.path.join(PROJECTS, "iec61131_lang_test_tree")
XML_PROJECT = os.path.join(PROJECTS, "iec61131_lang_test")
LEGACY_PROJECT = os.path.join(PROJECTS, "legacy_execution_order")


class Log:

    def __init__(self):
        self.messages = []

    def write(self, message):
        self.messages.append(("info", message))

    def write_warning(self, message):
        self.messages.append(("warning", message))

    def write_error(self, message):
        self.messages.append(("error", message))

    def of(self, level):
        return [m for l, m in self.messages if l == level]


def xml_of(path):
    with open(path, encoding="utf-8") as f:
        return etree.fromstring(f.read().encode())


class TreeProjectTest(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = os.path.join(self.tmp.name, "project")
        shutil.copytree(TREE_PROJECT, self.project)
        self.plc = os.path.join(self.project, "plc")
        self.files = read_tree(self.plc)

    def tearDown(self):
        self.tmp.cleanup()

    def controller(self):
        controller = ProjectController()
        controller.logger = Log()
        return controller

    def load(self):
        controller = self.controller()
        self.assertEqual(controller.LoadProject(self.project), (None, False))
        self.assertEqual(controller.logger.messages, [])
        return controller

    def changed(self):
        files = read_tree(self.plc)
        return sorted(p for p in set(files) | set(self.files) if files.get(p) != self.files.get(p))

    def test_same_as_xml_project(self):
        """ Tree project is iec61131_lang_test one, organized in files """
        self.assertIsNone(difference(xml_of(os.path.join(XML_PROJECT, "plc.xml")),
                                     etree.fromstring(tree_to_xml(self.plc).encode())))

    def test_load_and_save_unchanged(self):
        controller = self.load()
        self.assertTrue(controller.PLCTreeFormat)
        self.assertEqual(len(controller.GetProjectPouNames()), 14)
        controller.SaveProject()
        self.assertEqual(controller.logger.of("error"), [])
        self.assertEqual(self.changed(), [])

    def test_edits(self):
        controller = self.load()
        controller.ChangePouName("CounterST", "CounterST2")
        controller.SetPouDescription("CounterFBD", "Counts in FBD")
        pou = controller.Project.getpou("CounterIL")
        variables = controller.GetPouInterfaceVars(pou)
        next(v for v in variables if v.Name == "Reset").Documentation = "reset counter"
        controller.SetPouInterfaceVars("CounterIL", variables)
        controller.ProjectChangePouType("AverageVal", "functionBlock")
        self.assertIsInstance(controller.PastePou(None, controller.GetPouXml("CounterLD")), tuple)
        controller.ProjectAddDataType("new_type")
        controller.SaveProject()
        self.assertEqual(controller.logger.of("error"), [])
        self.assertEqual(self.changed(), ["graphic/fbd/CounterFBD.fbd", "graphic/fbd/plc_prg.fbd",
                                          "graphic/ld/CounterLD.ld", "il/CounterIL.il",
                                          "st/counters.st", "types/types.st"])
        files = read_tree(self.plc)
        self.assertIn("FUNCTION_BLOCK CounterST2\n", files["st/counters.st"])
        self.assertIn("FUNCTION_BLOCK AverageVal_functionBlock\n", files["st/counters.st"])
        self.assertTrue(files["graphic/fbd/CounterFBD.fbd"].startswith("(*Counts in FBD*)\n"))
        self.assertIn("(*reset counter*)\n    Reset : BOOL;", files["il/CounterIL.il"])
        self.assertEqual(files["graphic/ld/CounterLD.ld"].count("FUNCTION_BLOCK CounterLD"), 2)
        self.assertIn("new_type : BOOL;", files["types/types.st"])

        # saved project loads with edits
        controller = self.load()
        self.assertIn("CounterLD1", controller.GetProjectPouNames())

    def test_conflict(self):
        controller = self.load()
        controller.ChangePouName("CounterST", "CounterST2")
        path = os.path.join(self.plc, "st", "counters.st")
        with open(path, "a", encoding="utf-8") as f:
            f.write("(* edited *)\n")
        controller.SaveProject()
        self.assertEqual(len(controller.logger.of("error")), 1)
        self.assertIn("st/counters.st", controller.logger.of("error")[0])
        self.assertTrue(controller.ProjectTestModified())
        self.assertEqual(self.changed(), ["st/counters.st"])

    def test_storage_switch(self):
        controller = self.load()
        controller.SetPLCTreeFormat(False)
        self.assertTrue(controller.ProjectTestModified())
        controller.SaveProject()
        self.assertTrue(os.path.isfile(os.path.join(self.project, "plc.xml")))
        self.assertEqual(read_tree(self.plc), {"README.md": self.files["README.md"]})
        self.assertEqual(len(controller.logger.of("warning")), 1)

        controller = self.load()
        self.assertFalse(controller.PLCTreeFormat)
        controller.SetPLCTreeFormat(True)
        controller.SaveProject()
        self.assertFalse(os.path.exists(os.path.join(self.project, "plc.xml")))
        self.assertIsNone(difference(xml_of(os.path.join(XML_PROJECT, "plc.xml")),
                                     etree.fromstring(tree_to_xml(self.plc).encode())))
        self.assertTrue(self.load().PLCTreeFormat)

    def test_errors(self):
        # syntax error stops loading, with file and line
        write_tree(self.plc, {"il/CounterIL.il": "FUNCTION_BLOCK CounterIL\n  VAR x END_VAR\n"})
        message, _error = self.controller().LoadProject(self.project)
        self.assertIn("il/CounterIL.il:2:", message)

        # validation error gives its file and declaration line
        write_tree(self.plc, {"il/CounterIL.il": self.files["il/CounterIL.il"],
                              "config.st": self.files["config.st"].replace(
                                  "PRIORITY := 1)", "PRIORITY := 70000)")})
        controller = self.controller()
        self.assertEqual(controller.LoadProject(self.project), (None, False))
        warnings = controller.logger.of("warning")
        self.assertEqual(len(warnings), 1)
        self.assertIn("plc/config.st", warnings[0])

        # both plc.xml and plc/ directory
        shutil.copy(os.path.join(XML_PROJECT, "plc.xml"), self.project)
        message, error = self.controller().LoadProject(self.project)
        self.assertTrue(error)


def execution_orders(pou):
    return [e.get("executionOrderId") for e in pou.iter() if e.get("executionOrderId") is not None]


class LegacyExecutionOrderTest(unittest.TestCase):
    """ Beremiz used to write executionOrderId="0" for unspecified execution order.
    legacy_execution_order project is iec61131_lang_test one, saved that way """

    def test_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "project")
            shutil.copytree(LEGACY_PROJECT, project)
            controller = ProjectController()
            controller.logger = Log()
            self.assertEqual(controller.LoadProject(project), (None, False))
            controller.SaveProject()
            self.assertEqual(controller.logger.of("error"), [])
            saved = xml_of(os.path.join(project, "plc.xml"))
        self.assertIsNone(difference(xml_of(os.path.join(XML_PROJECT, "plc.xml")), saved))
        self.assertEqual(execution_orders(saved), [])

    def test_mixed_kept(self):
        """ POU with other execution orders than 0 keeps all of them """
        with open(os.path.join(LEGACY_PROJECT, "plc.xml"), encoding="utf-8") as f:
            xml = f.read().replace('executionOrderId="0"', 'executionOrderId="1"', 1)
        pous = etree.fromstring(xml.encode()).iter(tc6("pou"))
        mixed = next(p for p in pous if "1" in execution_orders(p))
        controller = PLCControler()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plc.xml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(xml)
            self.assertIsNone(controller.OpenXMLFile(path))
        for pou in controller.Project.iter(tc6("pou")):
            expected = execution_orders(mixed) if pou.get("name") == mixed.get("name") else []
            self.assertEqual(execution_orders(pou), expected)

        # as shown in editor, 0 is an execution order, absent one is None
        for name, expected in [(mixed.get("name"), {0, 1}), ("CounterFBD", {None})]:
            infos = controller.GetEditedElementInstancesInfos(ComputePouName(name))
            self.assertEqual({i.specific_values.execution_order for i in infos.values()
                              if hasattr(i.specific_values, "execution_order")}, expected)


if __name__ == "__main__":
    unittest.main()
