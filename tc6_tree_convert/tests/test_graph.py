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

from tc6_tree_convert import iec_parser  # noqa: E402
from tc6_tree_convert.canon import difference  # noqa: E402
from tc6_tree_convert.common import ConversionError, NSMAP, tc6  # noqa: E402
from tc6_tree_convert.decl import Writer, Builder  # noqa: E402

NAMESPACES = 'xmlns="http://www.plcopen.org/xml/tc6_0201" xmlns:xhtml="http://www.w3.org/1999/xhtml"'


def corpus():
    """ TC6 XML files of Beremiz test projects and examples """
    return sorted(glob.glob(os.path.join(BEREMIZ_DIR, "tests", "projects", "*", "plc.xml")) +
                  glob.glob(os.path.join(BEREMIZ_DIR, "exemples", "*", "plc.xml")))


def pou_xml(language, content):
    """ Program with given body """
    return etree.fromstring(
        '<pous %s><pou name="p" pouType="program"><interface/><body><%s>%s</%s></body></pou></pous>'
        % (NAMESPACES, language, content, language))[0]


def pou_text(pou):
    """ Text of POU with its documentation """
    writer = Writer()
    return writer.unit(pou, 0, writer.pou, "")


def pou_text_to_xml(text, language):
    """ POU XML from POU text in a file of given language """
    tree, trivia = iec_parser.parse(text, "TC6_%s_File" % language)
    parent = etree.Element(tc6("pous"), nsmap=NSMAP)
    return Builder(text, "test", trivia).pou(parent, tree[3][0], language, 0)


class GraphTest(unittest.TestCase):

    def check(self, language, content, expected):
        """ XML content of body is written as expected text, that is read back as XML """
        pou = pou_xml(language, content)
        text = pou_text(pou)
        lines = text.split("\n")
        self.assertEqual("\n".join(line[2:] if line.startswith("  ") else line
                                   for line in lines[1:-1]), expected)
        self.assertIsNone(difference(pou, pou_text_to_xml(text, language)))

    def test_block(self):
        self.check("FBD", """
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
              <inOutVariables>
                <variable formalParameter="X">
                  <connectionPointIn><connection refLocalId="2" formalParameter="Q"/></connectionPointIn>
                  <connectionPointOut><relPosition x="69" y="50"/></connectionPointOut>
                </variable>
              </inOutVariables>
              <outputVariables>
                <variable formalParameter="Q"><connectionPointOut><relPosition x="69" y="30"/></connectionPointOut></variable>
              </outputVariables>
            </block>""", """\
BLOCK #7 (executionOrderId := 0) TON0 : TON AT (448, 100) SIZE (69, 80)
  NOT IN AT (0, 30) := #1 VIA (448, 130), (415, 130);
  PT AT (0, 50);
  IN_OUT X := #2.Q => AT (69, 50);
  Q => AT (69, 30);
END_BLOCK""")

    def test_implied_and_default_attributes(self):
        self.check("FBD", """
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
            </outVariable>""", """\
IN_VARIABLE #1 a.b[2] AT (321, 58) SIZE (61, 30)
  OUT => AT (61, 15);
END_IN_VARIABLE
OUT_VARIABLE #2 (executionOrderId := 3, negated := TRUE, expression := 'x$Ny') AT (1, 2)
  IN := #1;
END_OUT_VARIABLE""")

    def test_ld(self):
        self.check("LD", """
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
            </coil>
            <contact localId="7" negated="true" edge="rising"><position x="1" y="2"/>
              <variable>%IX0.1</variable></contact>""", """\
LEFT_POWER_RAIL #1 AT (54, 123) SIZE (3, 40)
  OUT => AT (3, 20);
  OUT (formalParameter := 'none') => AT (3, 30);
END_LEFT_POWER_RAIL
COIL #6 (storage := reset) ORANGE_LIGHT AT (517, 284) SIZE (21, 15)
  IN AT (0, 8) := #1, #10.Q;
END_COIL
CONTACT #7 NOT (edge := rising) %IX0.1 AT (1, 2);""")

    def test_sfc(self):
        self.check("SFC", """
            <step localId="1" name="Start" initialStep="true" height="34" width="90">
              <position x="241" y="14"/>
              <connectionPointOut formalParameter=""><relPosition x="45" y="34"/></connectionPointOut>
            </step>
            <transition localId="3" height="2" width="20" priority="2">
              <position x="491" y="132"/>
              <condition><inline name=""><ST><xhtml:p><![CDATA[NOT Reset]]></xhtml:p></ST></inline></condition>
            </transition>
            <transition localId="4"><position x="1" y="2"/>
              <condition negated="true"><reference name="STOP"/></condition></transition>
            <transition localId="5"><position x="1" y="2"/>
              <condition><connectionPointIn><connection refLocalId="35" formalParameter="OUT"/></connectionPointIn></condition>
            </transition>
            <transition localId="8"><position x="1" y="2"/>
              <condition><inline name=""><ST><xhtml:p><![CDATA[a;
b]]></xhtml:p></ST></inline></condition>
            </transition>
            <actionBlock localId="6">
              <position x="641" y="190"/>
              <action localId="0"><relPosition x="0" y="0"/>
                <inline><ST><xhtml:p><![CDATA[Cnt := ResetCounterValue;]]></xhtml:p></ST></inline></action>
              <action localId="0" qualifier="D" duration="T#2s" indicator="ind"><relPosition x="0" y="0"/>
                <reference name="STOP_CARS"/></action>
              <action localId="3" qualifier="P1"><relPosition x="0" y="15"/>
                <reference name="GO"/></action>
              <action localId="0"><relPosition x="0" y="0"/>
                <inline><ST><xhtml:p><![CDATA[a := 1;
b := 2;]]></xhtml:p></ST></inline></action>
            </actionBlock>
            <jumpStep localId="12" targetName="Start"><position x="280" y="317"/></jumpStep>
            <simultaneousDivergence localId="13" name="sd"><position x="1" y="2"/>
              <connectionPointIn><connection refLocalId="12"/></connectionPointIn>
              <connectionPointOut formalParameter=""/><connectionPointOut formalParameter=""/>
            </simultaneousDivergence>
            <macroStep localId="14" name="m"><position x="1" y="2"/>
              <body><SFC><step localId="1" name="inner"><position x="1" y="2"/></step></SFC></body>
            </macroStep>
            <comment localId="9" height="52" width="318"><position x="51" y="11"/>
              <content><xhtml:p><![CDATA[This makes
the light blink]]></xhtml:p></content></comment>
            <comment localId="10" height="1" width="1"><position x="1" y="1"/>
              <content><xhtml:p><![CDATA[a *) b]]></xhtml:p></content></comment>""", """\
INITIAL_STEP #1 Start AT (241, 14) SIZE (90, 34)
  OUT => AT (45, 34);
END_STEP
TRANSITION #3 (priority := 2) AT (491, 132) SIZE (20, 2)
  CONDITION := NOT Reset;
END_TRANSITION
TRANSITION #4 AT (1, 2)
  CONDITION (negated := TRUE) STOP;
END_TRANSITION
TRANSITION #5 AT (1, 2)
  CONDITION := #35.OUT;
END_TRANSITION
TRANSITION #8 AT (1, 2)
  CONDITION ST
a;
b
  END_ST
END_TRANSITION
ACTION_BLOCK #6 AT (641, 190)
  ACTION (N) Cnt := ResetCounterValue; END_ACTION
  STOP_CARS(D, T#2s, ind);
  #3 GO(P1) AT (0, 15);
  ACTION (N)
a := 1;
b := 2;
  END_ACTION
END_ACTION_BLOCK
JUMP_STEP #12 Start AT (280, 317);
SIMULTANEOUS_DIVERGENCE #13 sd AT (1, 2)
  IN := #12;
  OUT =>;
  OUT =>;
END_SIMULTANEOUS_DIVERGENCE
MACRO_STEP #14 m AT (1, 2)
  SFC
    STEP #1 inner AT (1, 2);
  END_SFC
END_MACRO_STEP
COMMENT #9 AT (51, 11) SIZE (318, 52)
  (*This makes
the light blink*)
END_COMMENT
COMMENT #10 AT (1, 1) SIZE (1, 1) 'a *) b';""")

    def test_fbd_labels(self):
        self.check("FBD", """
            <label localId="1" label="L1"><position x="1" y="2"/></label>
            <jump localId="2" label="L1"><position x="1" y="2"/>
              <connectionPointIn><expression>a AND b</expression></connectionPointIn></jump>
            <return localId="3"><position x="1" y="2"/></return>
            <connector localId="4" name="c"><position x="1" y="2"/>
              <connectionPointIn><connection refLocalId="1"/></connectionPointIn></connector>
            <continuation localId="5" name="c"><position x="1" y="2"/>
              <connectionPointOut><relPosition x="1" y="1"/></connectionPointOut></continuation>
            <error localId="6" height="1" width="1"><position x="1" y="1"/>
              <content><xhtml:p><![CDATA[oops]]></xhtml:p></content></error>""", """\
LABEL #1 L1 AT (1, 2);
JUMP #2 L1 AT (1, 2)
  IN := 'a AND b';
END_JUMP
RETURN #3 AT (1, 2);
CONNECTOR #4 c AT (1, 2)
  IN := #1;
END_CONNECTOR
CONTINUATION #5 c AT (1, 2)
  OUT => AT (1, 1);
END_CONTINUATION
ERROR #6 AT (1, 1) SIZE (1, 1)
  (*oops*)
END_ERROR""")

    def test_rejected(self):
        for content in [
                '<vendorElement localId="1"><position x="0" y="0"/></vendorElement>',
                '<label localId="1" label="L"><position x="0" y="0"/>'
                '<addData><data name="other" handleUnknown="preserve"><x/></data></addData></label>']:
            with self.assertRaises(ConversionError):
                pou_text(pou_xml("FBD", content))

    def test_corpus(self):
        """ All graphical POUs of Beremiz projects read back as written """
        for path in corpus():
            with open(path, "rb") as f:
                root = etree.fromstring(f.read().replace(b"tc6.xsd", b"tc6_0201"))
            for pou in root.iter(tc6("pou")):
                language = etree.QName(pou.find(tc6("body"))[0]).localname
                if language in ("FBD", "LD", "SFC"):
                    with self.subTest(path=path, pou=pou.get("name")):
                        self.assertIsNone(difference(pou, pou_text_to_xml(pou_text(pou), language)))


if __name__ == "__main__":
    unittest.main()
