#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Extend IEC 61131-3 grammar with textual forms of PLCopen TC6 XML

Reads fixed grammar and TC6 XML schema, writes extended grammar restricted to
what TC6 can represent, and tc6_textmap.py that maps TC6 graphical elements
to their textual form.
"""

import argparse
import os
import pprint
import re
import sys
from dataclasses import dataclass, field

from lxml import etree

import ebnf
from ebnf import Rule, RuleFix, FixError


# Start symbols, one per file extension, and project pragma content
ROOTS = ["TC6_ST_File", "TC6_IL_File", "TC6_FBD_File", "TC6_LD_File", "TC6_SFC_File",
         "TC6_Project_Pragma"]


# TC6 XML schema model

XSD = "{http://www.w3.org/2001/XMLSchema}"

# Named complex types that are handled as a whole
KNOWN_TYPES = ["body", "formattedText", "addData", "position",
               "connectionPointIn", "connectionPointOut"]

INTEGER_TYPES = ["unsignedLong", "unsignedInt", "nonNegativeInteger", "integer", "long", "int"]


@dataclass
class XAttr:
    name: str
    type: str                  # XSD type local name, "enum" for enumerations
    required: bool = False
    default: str = None
    values: tuple = ()         # enumeration values
    simple_type: str = None    # name of enumeration simple type, if named


@dataclass
class XElem:
    name: str
    kind: str                  # "element", "text", or one of KNOWN_TYPES
    attrs: list = field(default_factory=list)
    children: list = field(default_factory=list)
    min: int = 1
    max: int = 1               # None for unbounded

    def attr(self, name):
        return next((a for a in self.attrs if a.name == name), None)

    def child(self, name):
        return next((c for c in self.children if c.name == name), None)


class Schema:

    def __init__(self, path):
        root = etree.parse(path).getroot()
        self.complex_types = {t.get("name"): t for t in root.iterfind(XSD + "complexType")}
        self.simple_types = {t.get("name"): t for t in root.iterfind(XSD + "simpleType")}
        self.groups = {g.get("name"): g for g in root.iterfind(XSD + "group")}

    def group(self, name):
        """ Elements of a group of graphical objects """
        choice = self.groups[name].find(XSD + "choice")
        return [self.element(e) for e in choice.iterfind(XSD + "element")]

    def element(self, node, occurs=None):
        min_occurs, max_occurs = occurs or (1, 1)
        if node.get("minOccurs") is not None:
            min_occurs = int(node.get("minOccurs"))
        if node.get("maxOccurs") is not None:
            max_occurs = None if node.get("maxOccurs") == "unbounded" else int(node.get("maxOccurs"))
        elem = XElem(node.get("name"), "element", min=min_occurs, max=max_occurs)
        type_name = (node.get("type") or "").split(":")[-1]
        if type_name in KNOWN_TYPES:
            elem.kind = type_name
            self.content(self.complex_types[type_name], elem)
        elif type_name in self.complex_types:
            self.content(self.complex_types[type_name], elem)
        elif type_name:
            elem.kind = "text"
        else:
            self.content(node.find(XSD + "complexType"), elem)
        return elem

    def content(self, node, elem):
        """ Fill elem attributes and children from complexType node """
        if node is None:
            return
        extension = node.find(XSD + "complexContent/" + XSD + "extension")
        if extension is not None:
            base = extension.get("base").split(":")[-1]
            if base in KNOWN_TYPES:
                elem.kind = base
            self.content(self.complex_types[base], elem)
            node = extension
        for child in node:
            if child.tag == XSD + "attribute":
                elem.attrs.append(self.attribute(child))
            elif child.tag in (XSD + "sequence", XSD + "choice"):
                self.particle(child, elem.children, None)

    def particle(self, node, children, occurs):
        if node.tag == XSD + "element":
            children.append(self.element(node, occurs))
        elif node.tag in (XSD + "sequence", XSD + "choice"):
            if node.tag == XSD + "choice" or node.get("minOccurs") == "0":
                # optional and repeated choices make their elements optional and repeated
                max_occurs = None if node.get("maxOccurs") == "unbounded" else 1
                occurs = (0, max_occurs)
            for child in node:
                self.particle(child, children, occurs)

    def attribute(self, node):
        attr = XAttr(node.get("name"), (node.get("type") or "string").split(":")[-1],
                     node.get("use") == "required", node.get("default"))
        restriction = node.find(XSD + "simpleType/" + XSD + "restriction")
        if attr.type in self.simple_types:
            attr.simple_type = attr.type
            restriction = self.simple_types[attr.type].find(XSD + "restriction")
        if restriction is not None:
            attr.values = tuple(e.get("value") for e in restriction.iterfind(XSD + "enumeration"))
            attr.type = "enum" if attr.values else restriction.get("base").split(":")[-1]
        return attr


# Idioms : how TC6 elements fold into compact IEC like text

GROUPS = [("commonObjects", "Common_Element"), ("fbdObjects", "FBD_Object"),
          ("ldObjects", "LD_Object"), ("sfcObjects", "SFC_Object")]

LANGUAGES = {
    "FBD": ["commonObjects", "fbdObjects"],
    "LD": ["commonObjects", "fbdObjects", "ldObjects"],
    "SFC": ["commonObjects", "fbdObjects", "ldObjects", "sfcObjects"],
}

# Elements without textual form, rejected with given reason
EXCLUDED = {"vendorElement": "vendor specific element"}

# Element operand : what comes after the label and attributes
#   ("attr", name, syntax) or ("child", name, syntax) with syntax one of
#   "name" : name or string, "expression" : IEC expression, "variable" : IEC variable
OPERANDS = {
    "inVariable": ("child", "expression", "expression"),
    "outVariable": ("child", "expression", "expression"),
    "inOutVariable": ("child", "expression", "expression"),
    "contact": ("child", "variable", "variable"),
    "coil": ("child", "variable", "variable"),
    "connector": ("attr", "name", "name"),
    "continuation": ("attr", "name", "name"),
    "label": ("attr", "label", "name"),
    "jump": ("attr", "label", "name"),
    "step": ("attr", "name", "name"),
    "macroStep": ("attr", "name", "name"),
    "jumpStep": ("attr", "targetName", "name"),
    "simultaneousDivergence": ("attr", "name", "name"),
}

# Boolean attributes written as NOT before operand, when operand is not an expression
FLAGS = {"contact": "negated", "coil": "negated", "block/variable": "negated"}

# Boolean attribute selecting another keyword
VARIANTS = {"step": ("initialStep", "INITIAL_STEP")}

# Values written by Beremiz, implied when attribute is not given in text.
# NULL stands for an absent attribute.
IMPLIED = {
    ("block", "executionOrderId"): "0",
    ("inVariable", "executionOrderId"): "0",
    ("outVariable", "executionOrderId"): "0",
    ("inOutVariable", "executionOrderId"): "0",
    ("actionBlock/action", "localId"): "0",
    ("transition/condition/inline", "name"): "",
}

# Implied value of required formalParameter added to some connection points
PIN_IMPLIED = {"formalParameter": ""}

# Children with a dedicated syntax
SPECIALS = {
    "block": ["inputVariables", "inOutVariables", "outputVariables"],
    "actionBlock": ["action"],
    "transition": ["condition"],
    "comment": ["content"],
    "error": ["content"],
    "macroStep": ["body"],
}

# Action qualifiers followed by a duration
TIMED_QUALIFIERS = ["L", "D", "SD", "DS", "SL", "DL"]


def upper_snake(name):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).upper()


def rule_name(name):
    return "TC6_" + "_".join(w.capitalize() for w in upper_snake(name).split("_"))


def pin_name(child):
    return upper_snake(child.name.replace("connectionPoint", ""))


def value_kind(attr):
    if attr.values:
        return "enum"
    if attr.type == "boolean":
        return "boolean"
    if attr.type == "decimal":
        return "decimal"
    if attr.type in INTEGER_TYPES:
        return "unsigned"
    return "string"


def attr_map(attrs, path, folded=()):
    """ Textmap of attributes that are not folded into a dedicated syntax """
    result = {}
    for attr in attrs:
        if attr.name in folded:
            continue
        result[attr.name] = {"kind": value_kind(attr), "default": attr.default,
                             "implied": IMPLIED.get((path, attr.name))}
        if attr.values:
            result[attr.name]["values"] = list(attr.values)
    return result


class Extender:
    """ Builds graphical element rules and textmap from schema """

    def __init__(self, schema):
        self.schema = schema
        self.rules = []          # rule texts
        self.done = set()
        self.textmap = {}

    def add(self, text):
        name = text.split("::=")[0].strip()
        if name not in self.done:
            self.done.add(name)
            self.rules.append(text)

    # values and attributes

    def value_rule(self, attr, implied):
        if attr.values:
            if attr.simple_type:
                name = rule_name(attr.simple_type)
                self.add("%s ::= %s" % (name, " | ".join("'%s'" % v for v in attr.values)))
            else:
                name = "(%s)" % " | ".join("'%s'" % v for v in attr.values)
        else:
            name = {"boolean": "TC6_Boolean", "decimal": "TC6_Decimal",
                    "unsigned": "TC6_Unsigned", "string": "Char_Str"}[value_kind(attr)]
        return "(%s | 'NULL')" % name if implied is not None else name

    def attributes_rule(self, name, attrs, attr_specs):
        """ Return attribute list rule name, None if no attribute """
        if not attr_specs:
            return None
        by_name = {a.name: a for a in attrs}
        self.add("%s_Attributes ::= '(' %s_Attribute (',' %s_Attribute)* ')'" % (name, name, name))
        self.add("%s_Attribute ::= %s" % (name, " | ".join(
            "'%s' ':=' %s" % (a, self.value_rule(by_name[a], spec["implied"]))
            if a in by_name else "'%s' ':=' Char_Str" % a
            for a, spec in attr_specs.items())))
        return name + "_Attributes"

    # connection points

    def pin(self, child, element_path):
        attrs = {a.name: {"kind": value_kind(a), "default": a.default,
                          "implied": PIN_IMPLIED.get(a.name) if a.required else None}
                 for a in child.attrs}
        direction = "in" if child.kind == "connectionPointIn" else "out"
        spec = {"pin": pin_name(child), "direction": direction,
                "multiple": child.max is None, "attrs": attrs}
        attributes = self.attributes_rule(
            "TC6_Formal_Pin" if "formalParameter" in attrs else "TC6_Pin", child.attrs, attrs)
        tail = "TC6_Input_Tail" if direction == "in" else "TC6_Output_Tail"
        text = "'%s' %s%s" % (spec["pin"], attributes + "? " if attributes else "", tail)
        return spec, text

    # elements

    def element(self, x, path):
        """ Element textmap and grammar rule name """
        name = rule_name(path)
        first = len(self.rules)
        spec = {"keyword": upper_snake(x.name), "children": [c.name for c in x.children]}
        folded = []
        alternatives = ["'%s'" % spec["keyword"]]
        if path in VARIANTS:
            spec["variant"] = list(VARIANTS[path])
            folded.append(VARIANTS[path][0])
            alternatives.append("'%s'" % VARIANTS[path][1])
        head = ["(%s)" % " | ".join(alternatives) if len(alternatives) > 1 else alternatives[0]]

        local_id = x.attr("localId")
        if local_id is not None:
            spec["label"] = "localId"
            folded.append("localId")
            implied = IMPLIED.get((path, "localId"))
            head.append("TC6_Id" if local_id.required and implied is None else "TC6_Id?")
        if path in FLAGS:
            spec["flag"] = FLAGS[path]
            folded.append(FLAGS[path])
            head.append("'NOT'?")

        operand = OPERANDS.get(path)
        operand_rule = None
        if operand is not None:
            kind, operand_name, syntax = operand
            spec["operand"] = {"kind": kind, "name": operand_name, "syntax": syntax}
            optional = True
            if kind == "attr":
                folded.append(operand_name)
                optional = not x.attr(operand_name).required
            operand_rule = {"name": "TC6_Operand", "expression": "Expression",
                            "variable": "Variable_Access"}[syntax]
            if kind == "child":
                # child operand may also be given as attribute
                optional = True
            operand_rule += "?" if optional else ""
        if x.name == "block":
            spec["operand"] = {"kind": "block", "instance": "instanceName", "type": "typeName"}
            folded.extend(["instanceName", "typeName"])
            operand_rule = "TC6_Block_Instance? ':' TC6_Block_Type"

        at = x.child("position") or x.child("relPosition")
        if at is not None:
            spec["at"] = at.name
        if x.attr("width") is not None and x.attr("height") is not None:
            spec["size"] = ["width", "height"]
            folded.extend(["width", "height"])

        attrs = attr_map(x.attrs, path, folded)
        for child in x.children:
            if operand is not None and operand[0] == "child" and child.name == operand[1]:
                attrs[child.name] = {"kind": "string", "default": None, "implied": None}
        spec["attrs"] = attrs
        attributes = self.attributes_rule(name, x.attrs, attrs)
        if attributes:
            head.append(attributes + "?")
        if operand_rule:
            head.append(operand_rule)
        if at is not None:
            head.append("TC6_At" if at.min else "TC6_At?")
        if "size" in spec:
            head.append("TC6_Size" if x.attr("width").required else "TC6_Size?")

        items, spec["pins"] = [], {}
        for child in x.children:
            if child.kind in ("connectionPointIn", "connectionPointOut") and child is not at:
                spec["pins"][child.name], text = self.pin(child, path)
                items.append(text)
            elif child.name in SPECIALS.get(x.name, ()):
                items.extend(self.special(x, child, path))
            elif not (child is at or child.kind in ("addData",) or child.name == "documentation"
                      or operand is not None and child.name == operand[1]):
                raise FixError("%s: unhandled child %s" % (path, child.name))

        if x.name in ("comment", "error"):
            body = "(Char_Str ';' | 'END_%s')" % spec["keyword"]
        elif items:
            self.add("%s_Item ::= %s" % (name, " | ".join(items)))
            body = "(';' | %s_Item* 'END_%s')" % (name, spec["keyword"])
        else:
            body = "';'"
        spec["specials"] = SPECIALS.get(x.name, [])
        spec["end"] = bool(items) or x.name in ("comment", "error")
        # element rule first, then rules it uses
        self.add("%s ::= %s %s" % (name, " ".join(head), body))
        self.rules.insert(first, self.rules.pop())
        self.textmap[path] = spec
        return name

    def special(self, x, child, path):
        """ Item rules for children with dedicated syntax """
        if x.name == "block":
            if child.name == "inputVariables":
                variable = child.child("variable")
                self.block_variable(variable)
                return ["TC6_Block_Input", "TC6_Block_In_Out", "TC6_Block_Output"]
            return []
        if x.name == "actionBlock":
            self.action(child)
            return ["TC6_Action_Association", "TC6_Inline_Action"]
        if x.name == "transition":
            self.condition(child)
            return ["TC6_Condition"]
        if child.name == "content":
            return []
        if child.kind == "body":
            return ["TC6_Tagged_Body"]
        raise FixError("%s: no special syntax for %s" % (path, child.name))

    def block_variable(self, variable):
        path = "block/variable"
        attrs = attr_map(variable.attrs, path, ["formalParameter", FLAGS[path]])
        self.textmap[path] = {"name": "formalParameter", "flag": FLAGS[path], "attrs": attrs,
                              "groups": {"inputVariables": "in", "inOutVariables": "inout",
                                         "outputVariables": "out"},
                              "children": [c.name for c in variable.children]}
        attributes = self.attributes_rule("TC6_Block_Variable", variable.attrs, attrs)
        self.add("TC6_Block_Pin ::= 'NOT'? TC6_Name_Or_Text %s" % (attributes + "?"))
        self.add("TC6_Block_Input ::= TC6_Block_Pin TC6_Input_Tail")
        self.add("TC6_Block_In_Out ::= 'IN_OUT' TC6_Block_Pin TC6_At? (':=' TC6_Connection)?"
                 " TC6_Output_Tail")
        self.add("TC6_Block_Output ::= TC6_Block_Pin TC6_Output_Tail")
        self.add("TC6_Block_Instance ::= TC6_Name_Or_Text")
        self.add("TC6_Block_Type ::= TC6_Name_Or_Text")

    def action(self, action):
        path = "actionBlock/action"
        folded = ["localId", "qualifier", "duration", "indicator", "width", "height"]
        attrs = attr_map(action.attrs, path, folded)
        qualifiers = action.attr("qualifier").values
        self.textmap[path] = {"label": "localId", "at": "relPosition", "size": ["width", "height"],
                              "attrs": attrs, "implied": {"localId": "0", "relPosition": ["0", "0"]},
                              "timed": TIMED_QUALIFIERS,
                              "children": [c.name for c in action.children]}
        attributes = self.attributes_rule("TC6_Action", action.attrs, attrs)
        head = "TC6_Id? %s" % (attributes + "?")
        tail = "'(' TC6_Action_Qualifier? ')' TC6_At? TC6_Size?"
        self.add("TC6_Action_Association ::= %s TC6_Name_Or_Text %s ';'" % (head, tail))
        self.add("TC6_Inline_Action ::= 'ACTION' %s %s TC6_Action_Body 'END_ACTION'" % (head, tail))
        self.add("TC6_Action_Qualifier ::= TC6_Timed_Qualifier ',' TC6_Action_Time (',' TC6_Indicator)?"
                 " | TC6_Qualifier (',' TC6_Indicator)?")
        self.add("TC6_Timed_Qualifier ::= " + " | ".join("'%s'" % q for q in qualifiers
                                                         if q in TIMED_QUALIFIERS))
        self.add("TC6_Qualifier ::= " + " | ".join("'%s'" % q for q in qualifiers
                                                   if q not in TIMED_QUALIFIERS))
        self.add("TC6_Action_Time ::= Duration | Identifier | Char_Str")
        self.add("TC6_Indicator ::= TC6_Name_Or_Text")

    def condition(self, condition):
        path = "transition/condition"
        attrs = attr_map(condition.attrs, path)
        inline = condition.child("inline")
        self.textmap[path] = {"attrs": attrs, "inline": attr_map(inline.attrs, path + "/inline"),
                              "children": [c.name for c in condition.children]}
        attributes = self.attributes_rule("TC6_Condition", condition.attrs, attrs)
        self.add("TC6_Condition ::= 'CONDITION' %s TC6_At? (':=' (TC6_Sources | TC6_Raw_Expression)"
                 " ';' | TC6_Operand ';' | TC6_Tagged_Body)" % (attributes + "?"))

    def build(self):
        group_rules = []
        for group, suffix in GROUPS:
            names = []
            for x in self.schema.group(group):
                if x.name in EXCLUDED:
                    continue
                names.append(self.element(x, x.name))
                self.textmap[x.name]["group"] = group
            group_rules.append("TC6_%s ::= %s" % (suffix, " | ".join(names)))
        for text in group_rules:
            self.add(text)
        for language, groups in LANGUAGES.items():
            self.add("TC6_%s_Element ::= %s" % (language, " | ".join(
                "TC6_" + dict(GROUPS)[g] for g in groups)))


# Hand written textual forms of POUs, variables, configuration and nested bodies

TC6_RULES = r"""
/* TC6: start symbols, one per file extension, that gives POU bodies language */
TC6_ST_File ::= (Data_Type_Decl | TC6_Config_Decl | TC6_Text_POU)*
TC6_IL_File ::= TC6_Text_POU*
TC6_FBD_File ::= TC6_FBD_POU*
TC6_LD_File ::= TC6_LD_POU*
TC6_SFC_File ::= TC6_SFC_POU*

/* TC6: POUs, actions and transitions of POU come before body */
TC6_POU_Head ::= 'FUNCTION' Derived_Func_Name (':' TC6_Type_Spec)? | 'FUNCTION_BLOCK' Derived_FB_Name
               | 'PROGRAM' Prog_Type_Name
TC6_POU_End ::= 'END_FUNCTION' | 'END_FUNCTION_BLOCK' | 'END_PROGRAM'
TC6_Text_POU ::= TC6_POU_Head TC6_Var_Decls* TC6_POU_Member* TC6_POU_Raw_Body? TC6_POU_End
TC6_FBD_POU ::= TC6_POU_Head TC6_Var_Decls* TC6_POU_Member* TC6_FBD_Element* TC6_POU_End
TC6_LD_POU ::= TC6_POU_Head TC6_Var_Decls* TC6_POU_Member* TC6_LD_Element* TC6_POU_End
TC6_SFC_POU ::= TC6_POU_Head TC6_Var_Decls* TC6_POU_Member* TC6_SFC_Element* TC6_POU_End
TC6_POU_Member ::= 'ACTION' Action_Name ':' TC6_Action_Body 'END_ACTION'
                 | 'TRANSITION' Transition_Name ':' TC6_Transition_Body 'END_TRANSITION'

/* TC6: nested bodies are ST unless tagged with their language */
TC6_Action_Body ::= TC6_Tagged_Body | TC6_Action_Raw_Body?
TC6_Transition_Body ::= TC6_Tagged_Body | TC6_Transition_Raw_Body?
TC6_Tagged_Body ::= 'ST' TC6_ST_Raw_Body? 'END_ST' | 'IL' TC6_IL_Raw_Body? 'END_IL'
                  | 'FBD' TC6_FBD_Element* 'END_FBD' | 'LD' TC6_LD_Element* 'END_LD'
                  | 'SFC' TC6_SFC_Element* 'END_SFC'

/* TC6: variables, one syntax for all variable blocks */
TC6_Var_Decls ::= TC6_Var_Kind TC6_Var_Qualifier* (TC6_Var_Decl ';')* 'END_VAR'
TC6_Var_Kind ::= 'VAR_INPUT' | 'VAR_OUTPUT' | 'VAR_IN_OUT' | 'VAR_EXTERNAL' | 'VAR_GLOBAL'
               | 'VAR_TEMP' | 'VAR'
TC6_Var_Qualifier ::= 'CONSTANT' | 'RETAIN' | 'NON_RETAIN'
TC6_Var_Decl ::= Variable_List Located_At? ':' TC6_Type_Spec (':=' TC6_Initial_Value)?

/* TC6: data types, any TC6 data type can be used in declarations */
TC6_Type_Spec ::= Elem_Type_Name | 'ARRAY' '[' Subrange (',' Subrange)* ']' 'OF' TC6_Type_Spec
                | 'REF_TO' TC6_Type_Spec | Int_Type_Name '(' Subrange ')'
                | Elem_Type_Name? '(' Enum_Value_Spec (',' Enum_Value_Spec)* ')' | Struct_Decl
                | TC6_Generic_Type | Identifier
TC6_Generic_Type ::= 'ANY' | 'ANY_DERIVED' | 'ANY_ELEMENTARY' | 'ANY_MAGNITUDE' | 'ANY_NUM'
                   | 'ANY_REAL' | 'ANY_INT' | 'ANY_BIT' | 'ANY_STRING' | 'ANY_DATE'
TC6_Initial_Value ::= Array_Init | Struct_Init | Constant_Expr

/* TC6: configuration, several global variable blocks, resources without program */
TC6_Config_Decl ::= 'CONFIGURATION' Config_Name TC6_Var_Decls* TC6_Resource_Decl* 'END_CONFIGURATION'
TC6_Resource_Decl ::= 'RESOURCE' Resource_Name 'ON' Resource_Type_Name TC6_Var_Decls*
                      (Task_Config ';')* (TC6_Program_Config ';')* 'END_RESOURCE'
TC6_Program_Config ::= 'PROGRAM' Prog_Name ('WITH' Task_Name)? ':' Prog_Type_Name

/* TC6: project pragma content, {TC6 PROJECT(...)} */
TC6_Project_Pragma ::= 'TC6' 'PROJECT' '(' TC6_Project_Attribute (',' TC6_Project_Attribute)* ')'

/* TC6: raw bodies, kept as is, scanned as matiec does to find their end */
TC6_POU_Raw_Body ::= (TC6_POU_Raw_Item - TC6_Raw_Start) TC6_POU_Raw_Item* /* ws: explicit */
TC6_POU_Raw_Item ::= TC6_Raw_Item | TC6_Raw_Word - TC6_POU_End /* ws: explicit */
TC6_Raw_Start ::= TC6_Var_Kind | 'END_VAR' | 'ACTION' | 'TRANSITION' /* ws: explicit */
TC6_Action_Raw_Body ::= (TC6_Raw_Item | TC6_Raw_Word - 'END_ACTION')+ /* ws: explicit */
TC6_Transition_Raw_Body ::= (TC6_Raw_Item | TC6_Raw_Word - 'END_TRANSITION')+ /* ws: explicit */
TC6_ST_Raw_Body ::= (TC6_Raw_Item | TC6_Raw_Word - 'END_ST')+ /* ws: explicit */
TC6_IL_Raw_Body ::= (TC6_Raw_Item | TC6_Raw_Word - 'END_IL')+ /* ws: explicit */
TC6_Raw_Expression ::= (TC6_Raw_Pragma | TC6_Raw_Comment | TC6_Raw_String | [^;'"({] | '(' | '{')+ /* ws: explicit */
TC6_Raw_Item ::= TC6_Raw_Pragma | TC6_Raw_Comment | TC6_Raw_String | [^A-Za-z_'"({] | '(' | '{' /* ws: explicit */
TC6_Raw_Pragma ::= '{{' (Char* - (Char* '}}' Char*)) '}}' | '{' [^}]* '}' /* ws: explicit */
TC6_Raw_Comment ::= '(*' (Char* - (Char* '*)' Char*)) '*)' /* ws: explicit */
TC6_Raw_String ::= "'" ([^'$] | '$' Char)* "'" | '"' ([^"$] | '$' Char)* '"' /* ws: explicit */
TC6_Raw_Word ::= [A-Za-z_] [A-Za-z0-9_]* /* ws: explicit */

/* TC6: graphical elements common parts */
TC6_Id ::= '#' [0-9]+ /* ws: explicit */
TC6_Unsigned ::= [0-9]+ /* ws: explicit */
TC6_Decimal ::= [+-]? ([0-9]+ ('.' [0-9]*)? | '.' [0-9]+) /* ws: explicit */
TC6_Name ::= Letter (Letter | Digit)* /* ws: explicit */
TC6_Name_Or_Text ::= TC6_Name | Char_Str
TC6_Operand ::= TC6_Name_Or_Text
TC6_Boolean ::= 'TRUE' | 'FALSE'
TC6_Point ::= '(' TC6_Decimal ',' TC6_Decimal ')'
TC6_At ::= 'AT' TC6_Point
TC6_Size ::= 'SIZE' TC6_Point
TC6_Source ::= TC6_Id ('.' TC6_Name_Or_Text)? ('VIA' TC6_Point (',' TC6_Point)*)?
TC6_Sources ::= TC6_Source (',' TC6_Source)*
TC6_Connection ::= TC6_Sources | Char_Str
TC6_Input_Tail ::= TC6_At? (':=' TC6_Connection)? ';'
TC6_Output_Tail ::= '=>' TC6_At? Char_Str? ';'
"""

# Changes to standard rules
OVERRIDES = [
    RuleFix("T01", "Pragma", "matiec C code pragmas {{ }} may contain }",
            old="'{' (Char* - (Char* '}' Char*)) '}'",
            new="'{{' (Char* - (Char* '}}' Char*)) '}}' | '{' (Char* - (Char* '}' Char*)) '}'"),
    RuleFix("T02", "Type_Decl", "any TC6 data type, with initial value",
            old="Simple_Type_Decl | Subrange_Type_Decl | Enum_Type_Decl | Array_Type_Decl"
                " | Struct_Type_Decl | Str_Type_Decl | Ref_Type_Decl",
            new="Identifier ':' TC6_Type_Spec (':=' TC6_Initial_Value)?"),
    RuleFix("T03", "Struct_Decl", "TC6 structures do not overlap, and can be empty",
            old="'STRUCT' 'OVERLAP'? (Struct_Elem_Decl ';')+ 'END_STRUCT'",
            new="'STRUCT' (Struct_Elem_Decl ';')* 'END_STRUCT'"),
    RuleFix("T04", "Struct_Elem_Decl", "TC6 structure members are variables",
            old="Struct_Elem_Name (Located_At Multibit_Part_Access?)? ':' (Simple_Spec_Init"
                " | Subrange_Spec_Init | Enum_Spec_Init | Array_Spec_Init | Struct_Spec_Init)",
            new="Struct_Elem_Name Located_At? ':' TC6_Type_Spec (':=' TC6_Initial_Value)?"),
    RuleFix("T05", "Symbolic_Variable", "no namespace in TC6, a.b is a structure member,"
            " and x.0 a bit",
            old="('THIS' '.' | (Namespace_Name '.')+)? (Var_Access | Multi_Elem_Var)",
            new="('THIS' '.')? (Var_Access | Multi_Elem_Var)"),
    RuleFix("T06", "Func_Access", "no namespace in TC6",
            old="(Namespace_Name '.')* Func_Name",
            new="Func_Name"),
    RuleFix("T07", "Ref_Addr", "no class in TC6, function block instances are variables",
            old="'REF' '(' (Symbolic_Variable | FB_Instance_Name | Class_Instance_Name) ')'",
            new="'REF' '(' Symbolic_Variable ')'"),
]


def attribute_defaults(xsd_path):
    """ Default value of attributes, by name, the same everywhere in TC6 schema """
    defaults = {}
    for attribute in etree.parse(xsd_path).getroot().iter(XSD + "attribute"):
        name, default = attribute.get("name"), attribute.get("default")
        if default is None:
            continue
        if defaults.setdefault(name, default) != default:
            raise FixError("attribute %s has several default values" % name)
    return dict(sorted(defaults.items()))


def header_attributes(xsd_path):
    root = etree.parse(xsd_path).getroot()
    project = root.find(XSD + "element[@name='project']")
    names = []
    for header in ("fileHeader", "contentHeader"):
        node = project.find(".//%selement[@name='%s']" % (XSD, header))
        names.extend(a.get("name") for a in node.iter(XSD + "attribute")
                     if a.get("name") != "modificationDateTime"
                     and a.getparent().getparent().get("name") in (None, header))
    return names


def extend(fixed, xsd_path):
    """ Return extended Grammar and textmap from fixed grammar """
    schema = Schema(xsd_path)
    grammar = fixed
    ebnf.apply_rule_fixes(grammar, OVERRIDES, "TC6")

    for rule in ebnf.parse(TC6_RULES):
        grammar.add(rule)
    grammar.add(Rule("TC6_Project_Attribute", ebnf.parse_expr(
        "(%s) ':=' Char_Str | ('Comment' | 'pageSize' | 'fbdScaling' | 'ldScaling' | 'sfcScaling')"
        " ':=' (TC6_Point | Char_Str)" % " | ".join("'%s'" % n for n in header_attributes(xsd_path)))),
        after="TC6_Project_Pragma")

    extender = Extender(schema)
    extender.build()
    for n, text in enumerate(extender.rules):
        rule = ebnf.parse(text).rules.popitem()[1]
        if n == 0:
            rule.leading = ["TC6: graphical elements, generated from TC6 XML schema"]
            rule.blank_before = True
        grammar.add(rule)

    # keep what TC6 files need, and section comments of removed rules
    reached = ebnf.reachable(grammar, ROOTS + [r.name for r in grammar
                                              if r.annotated(ebnf.WS_IGNORABLE)])
    leading, blank = [], False
    for rule in list(grammar):
        if rule.name not in reached:
            grammar.remove(rule.name)
            leading.extend(rule.leading)
            blank |= rule.blank_before
        elif leading or blank:
            # section title of removed rules, unless kept rule starts another section
            if not rule.leading:
                rule.leading = leading
            rule.blank_before |= blank
            leading, blank = [], False
    return grammar, extender.textmap


def header(grammar):
    fixed = [line for line in grammar.header if line.startswith("  F")]
    return [
        "IEC 61131-3:2013 Annex A grammar extended with PLCopen TC6 XML textual forms",
        "Generated by extend_ebnf.py from iec61131-3-3rd_fixed.ebnf and tc6_xml_v201.xsd,"
        " do not edit",
        "Start symbols are %s," % ", ".join(ROOTS[:-1]),
        "  depending on file extension, and %s for {TC6 ...} pragma content." % ROOTS[-1],
        "Only rules reachable from start symbols are kept.",
        "Keywords and literals are case insensitive.",
        "  ws: explicit   token rule, no whitespace, comment or pragma between its parts",
        "  ws: ignorable  token rule, skipped between tokens of other rules",
        "Fixes of standard grammar, also noted after each fixed rule :",
    ] + fixed + [
        "Changes for TC6, also noted after each changed rule :",
    ] + ["  %s %s: %s" % (o.fid, o.name, o.reason) for o in OVERRIDES]


TEXTMAP_HEADER = '''\
# Generated by extend_ebnf.py from tc6_xml_v201.xsd, do not edit

"""
Textual form of PLCopen TC6 graphical elements, see extend_ebnf.py idioms

ELEMENTS maps element path to its textual form :
  keyword   keyword starting the element, "variant" gives boolean attribute
            selecting another keyword
  label     attribute written as #n
  flag      boolean attribute written as NOT
  operand   attribute or child written after label and attributes
  at        position child written as AT (x, y)
  size      width and height attributes written as SIZE (w, h)
  attrs     other attributes, written as (name := value, ...) : value kind,
            default, and implied value (written by Beremiz, implied when
            attribute is not given, NULL standing for absent attribute)
  pins      connection points written as PIN AT (x, y) := sources or PIN => AT (x, y)
  specials  children with a dedicated syntax
  end       element may have items and end with END_<keyword>, ; ends it otherwise
  children  XML children in schema order
LANGUAGES gives XML schema groups of elements allowed in each graphical language.
ATTRIBUTE_DEFAULTS gives default values of TC6 attributes, the same wherever they are.
"""

'''


def write_textmap(path, textmap, defaults):
    content = TEXTMAP_HEADER
    content += "LANGUAGES = %s\n\n" % pprint.pformat(LANGUAGES, width=100, sort_dicts=False)
    content += "EXCLUDED = %s\n\n" % pprint.pformat(EXCLUDED, width=100, sort_dicts=False)
    content += "ATTRIBUTE_DEFAULTS = %s\n\n" % pprint.pformat(defaults, width=100)
    content += "ELEMENTS = %s\n" % pprint.pformat(textmap, width=100, sort_dicts=False)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("fixed", nargs="?", default=os.path.join(here, "iec61131-3-3rd_fixed.ebnf"))
    parser.add_argument("xsd", nargs="?", default=os.path.join(here, "tc6_xml_v201.xsd"))
    parser.add_argument("-o", "--output",
                        default=os.path.join(here, "iec61131-3-3rd_extended.ebnf"))
    parser.add_argument("-t", "--textmap", default=os.path.join(here, "tc6_textmap.py"))
    parser.add_argument("-v", "--verbose", action="store_true", help="list grammar warnings")
    args = parser.parse_args(argv)

    with open(args.fixed, encoding="utf-8") as f:
        fixed = ebnf.parse(f.read())
    try:
        grammar, textmap = extend(fixed, args.xsd)
    except (FixError, ebnf.EbnfSyntaxError, ValueError) as e:
        sys.exit("%s: %s" % (args.fixed, e))
    grammar.header = header(fixed)

    errors, warnings = ebnf.validate(grammar, ROOTS, conflicts=True)
    for message in errors + (warnings if args.verbose else []):
        print(message, file=sys.stderr)
    if errors:
        sys.exit("%s: %d error(s)" % (args.output, len(errors)))

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(ebnf.format_grammar(grammar))
    write_textmap(args.textmap, textmap, attribute_defaults(args.xsd))
    print("%s: %d rules, %d warning(s)" % (args.output, len(grammar.rules), len(warnings)))


if __name__ == "__main__":
    main()
