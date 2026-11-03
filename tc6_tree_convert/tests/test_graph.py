#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tests for textual form of TC6 graphical bodies
"""

import glob
import os
import sys
import unittest

from lxml import etree

BEREMIZ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BEREMIZ_DIR)

from tc6_tree_convert.graph import GraphWriter, ConversionError, tc6  # noqa: E402

NAMESPACES = 'xmlns="http://www.plcopen.org/xml/tc6_0201" xmlns:xhtml="http://www.w3.org/1999/xhtml"'


def corpus():
    """ TC6 XML files of Beremiz test projects and examples """
    return sorted(glob.glob(os.path.join(BEREMIZ_DIR, "tests", "projects", "*", "plc.xml")) +
                  glob.glob(os.path.join(BEREMIZ_DIR, "exemples", "*", "plc.xml")))


def body(language, content):
    return etree.fromstring("<%s %s>%s</%s>" % (language, NAMESPACES, content, language))


class GraphWriterTest(unittest.TestCase):

    def write(self, language, content):
        return "\n".join(GraphWriter().graphical(body(language, content), 0))

    def test_block(self):
        self.assertEqual(self.write("FBD", """
            <block localId="7" typeName="TON" instanceName="TON0" executionOrderId="0" width="69" height="80">
              <position x="448" y="100"/>
              <inputVariables>
                <variable formalParameter="IN" negated="true">
                  <connectionPointIn><relPosition x="0" y="30"/>
                    <connection refLocalId="1"><position x="448" y="130"/><position x="415" y="130"/></connection>
                  </connectionPointIn>
                </variable>
                <variable formalParameter="PT"><connectionPointIn><relPosition x="0" y="50"/></connectionPointIn></variable>
              </inputVariables>
              <inOutVariables/>
              <outputVariables>
                <variable formalParameter="Q"><connectionPointOut><relPosition x="69" y="30"/></connectionPointOut></variable>
              </outputVariables>
            </block>"""), """\
BLOCK #7 TON0 : TON AT (448, 100) SIZE (69, 80)
  NOT IN AT (0, 30) := #1 VIA (448, 130), (415, 130);
  PT AT (0, 50);
  Q => AT (69, 30);
END_BLOCK""")

    def test_implied_and_default_attributes(self):
        self.assertEqual(self.write("FBD", """
            <inVariable localId="1" negated="false" height="30" width="61">
              <position x="321" y="58"/>
              <connectionPointOut><relPosition x="61" y="15"/></connectionPointOut>
              <expression>a.b[2]</expression>
            </inVariable>
            <outVariable localId="2" executionOrderId="3" negated="true">
              <position x="1" y="2"/>
              <connectionPointIn><connection refLocalId="1"/></connectionPointIn>
              <expression>x
y</expression>
            </outVariable>"""), """\
IN_VARIABLE #1 (executionOrderId := NULL) a.b[2] AT (321, 58) SIZE (61, 30)
  OUT => AT (61, 15);
END_IN_VARIABLE
OUT_VARIABLE #2 (executionOrderId := 3, negated := TRUE, expression := 'x$Ny') AT (1, 2)
  IN := #1;
END_OUT_VARIABLE""")

    def test_ld(self):
        self.assertEqual(self.write("LD", """
            <leftPowerRail localId="1" height="40" width="3">
              <position x="54" y="123"/>
              <connectionPointOut formalParameter=""><relPosition x="3" y="20"/></connectionPointOut>
              <connectionPointOut formalParameter="none"><relPosition x="3" y="30"/></connectionPointOut>
            </leftPowerRail>
            <coil localId="6" height="15" width="21" storage="reset">
              <position x="517" y="284"/>
              <connectionPointIn><relPosition x="0" y="8"/>
                <connection refLocalId="1"/><connection refLocalId="10" formalParameter="Q"/>
              </connectionPointIn>
              <variable>ORANGE_LIGHT</variable>
            </coil>"""), """\
LEFT_POWER_RAIL #1 AT (54, 123) SIZE (3, 40)
  OUT => AT (3, 20);
  OUT (formalParameter := 'none') => AT (3, 30);
END_LEFT_POWER_RAIL
COIL #6 (storage := reset) ORANGE_LIGHT AT (517, 284) SIZE (21, 15)
  IN AT (0, 8) := #1, #10.Q;
END_COIL""")

    def test_sfc(self):
        self.assertEqual(self.write("SFC", """
            <step localId="1" name="Start" initialStep="true" height="34" width="90">
              <position x="241" y="14"/>
              <connectionPointOut formalParameter=""><relPosition x="45" y="34"/></connectionPointOut>
            </step>
            <transition localId="3" height="2" width="20" priority="2">
              <position x="491" y="132"/>
              <condition><inline name=""><ST><xhtml:p><![CDATA[NOT Reset]]></xhtml:p></ST></inline></condition>
            </transition>
            <transition localId="4"><position x="1" y="2"/><condition><reference name="STOP"/></condition></transition>
            <transition localId="5"><position x="1" y="2"/>
              <condition><connectionPointIn><connection refLocalId="35" formalParameter="OUT"/></connectionPointIn></condition>
            </transition>
            <actionBlock localId="6">
              <position x="641" y="190"/>
              <action localId="0"><relPosition x="0" y="0"/>
                <inline><ST><xhtml:p><![CDATA[Cnt := ResetCounterValue;]]></xhtml:p></ST></inline></action>
              <action localId="0" qualifier="D" duration="T#2s" indicator="ind"><relPosition x="0" y="0"/>
                <reference name="STOP_CARS"/></action>
              <action localId="0"><relPosition x="0" y="0"/>
                <inline><ST><xhtml:p><![CDATA[a := 1;
b := 2;]]></xhtml:p></ST></inline></action>
            </actionBlock>
            <jumpStep localId="12" targetName="Start"><position x="280" y="317"/></jumpStep>
            <comment localId="9" height="52" width="318"><position x="51" y="11"/>
              <content><xhtml:p><![CDATA[This makes
the light blink]]></xhtml:p></content></comment>"""), """\
INITIAL_STEP #1 Start AT (241, 14) SIZE (90, 34)
  OUT => AT (45, 34);
END_STEP
TRANSITION #3 (priority := 2) AT (491, 132) SIZE (20, 2)
  CONDITION := NOT Reset;
END_TRANSITION
TRANSITION #4 AT (1, 2)
  CONDITION STOP;
END_TRANSITION
TRANSITION #5 AT (1, 2)
  CONDITION := #35.OUT;
END_TRANSITION
ACTION_BLOCK #6 AT (641, 190)
  ACTION (N) Cnt := ResetCounterValue; END_ACTION
  STOP_CARS(D, T#2s, ind);
  ACTION (N)
a := 1;
b := 2;
  END_ACTION
END_ACTION_BLOCK
JUMP_STEP #12 Start AT (280, 317);
COMMENT #9 AT (51, 11) SIZE (318, 52)
  (*This makes
the light blink*)
END_COMMENT""")

    def test_rejected(self):
        for content in [
                '<vendorElement localId="1"><position x="0" y="0"/></vendorElement>',
                '<label localId="1" label="L"><position x="0" y="0"/><addData/></label>']:
            with self.assertRaises(ConversionError):
                self.write("FBD", content)

    def test_corpus(self):
        writer = GraphWriter()
        for path in corpus():
            with open(path, "rb") as f:
                root = etree.fromstring(f.read().replace(b"tc6.xsd", b"tc6_0201"))
            for language in root.iter(tc6("FBD"), tc6("LD"), tc6("SFC")):
                with self.subTest(path=path, line=language.sourceline):
                    writer.graphical(language, 0)


if __name__ == "__main__":
    unittest.main()
