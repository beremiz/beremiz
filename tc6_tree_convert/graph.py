#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Textual form of TC6 graphical bodies (FBD, LD and SFC), driven by tc6_textmap

Nested bodies are ST, untagged, or tagged with their language. Their text is
what is between the line of their header and the line of their END keyword,
or, on a single line, between one space after header and one space before END.
"""

import re

from . import iec_parser
from .common import ConversionError, INDENT, tc6, localname, sub, elements, formatted_text
from .common import add_formatted_text, iec_string, iec_unquote, name_or_text, is_true
from .common import child, children, kids, has_literal, source, name_value
from .common import body_text, body_region
from .tc6_textmap import ELEMENTS, EXCLUDED

_NUMBER_RE = re.compile(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$")


def where(element):
    return "%s #%s" % (localname(element), element.get("localId", "?"))


def rule_name(tag):
    """ Grammar rule of element, see extend_ebnf.rule_name """
    return "TC6_" + "_".join(w.capitalize() for w in
                             re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", tag).upper().split("_"))


_TAGS = {rule_name(tag): tag for tag in ELEMENTS if "/" not in tag}


def check_body(body):
    """ Raise if body has what textual form can not hold """
    if body.get("WorksheetName") is not None or body.find(tc6("addData")) is not None or \
       body.find(tc6("documentation")) is not None:
        raise ConversionError("body worksheet name, additional data and documentation"
                              " are not supported")
    return elements(body)[0]


class GraphWriter:
    """ TC6 XML to text, writer giving units, documentation and gaps of elements """

    def __init__(self, writer):
        self.writer = writer

    # values

    def value(self, value, spec, element):
        kind = spec["kind"]
        if kind == "boolean":
            return "TRUE" if is_true(value) else "FALSE"
        if kind in ("unsigned", "decimal"):
            if not _NUMBER_RE.match(value) or kind == "unsigned" and not value.isdigit():
                raise ConversionError("%s: invalid number %r" % (where(element), value))
            return value
        if kind == "enum":
            return value
        return iec_string(value)

    def attributes(self, element, specs, values=None):
        """ (name := value, ...) of attributes not written otherwise, or "" """
        items = []
        for name, spec in specs.items():
            value = (values or {}).get(name, element.get(name))
            implied = spec["implied"]
            if value is None:
                if implied is not None:
                    items.append("%s := NULL" % name)
                continue
            if value == implied:
                continue
            default = spec["default"]
            if default is not None and (value == default or spec["kind"] == "boolean" and
                                        is_true(value) == is_true(default)):
                continue
            items.append("%s := %s" % (name, self.value(value, spec, element)))
        return "(%s)" % ", ".join(items) if items else ""

    def point(self, position):
        return "(%s, %s)" % (position.get("x"), position.get("y"))

    # connection points

    def sources(self, point_in):
        expression = point_in.find(tc6("expression"))
        if expression is not None:
            return iec_string(expression.text or "")
        texts = []
        for connection in point_in.iterfind(tc6("connection")):
            if connection.find(tc6("addData")) is not None or connection.get("globalId"):
                raise ConversionError("connection to #%s: additional data and global id"
                                      " are not supported" % connection.get("refLocalId"))
            text = "#" + connection.get("refLocalId")
            formal = connection.get("formalParameter")
            if formal is not None:
                text += "." + name_or_text(formal)
            points = connection.findall(tc6("position"))
            if points:
                text += " VIA " + ", ".join(self.point(p) for p in points)
            texts.append(text)
        return ", ".join(texts)

    def input_tail(self, point_in):
        """ AT (x, y) := sources """
        text = ""
        position = point_in.find(tc6("relPosition"))
        if position is not None:
            text += " AT " + self.point(position)
        sources = self.sources(point_in)
        if sources:
            text += " := " + sources
        return text

    def output_tail(self, point_out):
        """ => AT (x, y) """
        text = " =>"
        position = point_out.find(tc6("relPosition"))
        if position is not None:
            text += " AT " + self.point(position)
        expression = point_out.find(tc6("expression"))
        if expression is not None:
            text += " " + iec_string(expression.text or "")
        return text

    def pin(self, point, spec):
        if point.find(tc6("addData")) is not None:
            raise ConversionError("%s: additional data is not supported" % localname(point))
        attributes = self.attributes(point, spec["attrs"])
        head = spec["pin"] + (" " + attributes if attributes else "")
        if spec["direction"] == "in":
            return head + self.input_tail(point) + ";"
        return head + self.output_tail(point) + ";"

    # bodies

    def tagged_body(self, body, depth):
        """ LANGUAGE ... END_LANGUAGE """
        language = check_body(body)
        name = localname(language)
        if name in ("ST", "IL"):
            text = formatted_text(language)
            return name + body_region(text) + (INDENT * depth if "\n" in text else "") + \
                "END_" + name
        return name + self.writer.graphical(language, depth + 1) + "\n" + INDENT * depth + \
            "END_" + name

    def nested_body(self, body, depth, head, end):
        """ head ... end, with ST body untagged """
        language = check_body(body)
        if localname(language) == "ST":
            text = formatted_text(language)
            return head + body_region(text) + (INDENT * depth if "\n" in text else "") + end
        return head + "\n" + INDENT * (depth + 1) + self.tagged_body(body, depth + 1) + \
            "\n" + INDENT * depth + end

    # elements

    def element(self, element, depth):
        """ Text of graphical element, without documentation """
        tag = localname(element)
        if tag in EXCLUDED:
            raise ConversionError("%s: %s is not supported" % (tag, EXCLUDED[tag]))
        spec = ELEMENTS.get(tag)
        if spec is None or "/" in tag:
            raise ConversionError("unknown element " + tag)
        head = self.head(element, spec)
        items = []
        for child_name, pin_spec in spec["pins"].items():
            items.extend(self.pin(point, pin_spec) for point in element.iterfind(tc6(child_name)))
        special = getattr(self, "special_" + tag, None)
        if special is not None:
            items = special(element, items, depth)
        if tag in ("comment", "error"):
            text = formatted_text(element.find(tc6("content")))
            if "*)" in text:
                return head + " " + iec_string(text) + ";"
            items = ["(*" + text + "*)"]
        if not items:
            return head + ";"
        pad = "\n" + INDENT * (depth + 1)
        return head + "".join(pad + item for item in items) + "\n" + INDENT * depth + \
            "END_" + spec["keyword"]

    def head(self, element, spec):
        keyword = spec["keyword"]
        if "variant" in spec and is_true(element.get(spec["variant"][0])):
            keyword = spec["variant"][1]
        parts = [keyword]
        if "label" in spec:
            parts.append("#" + element.get(spec["label"]))
        if "flag" in spec and is_true(element.get(spec["flag"])):
            parts.append("NOT")
        operand, values = self.operand(element, spec)
        attributes = self.attributes(element, spec["attrs"], values)
        if attributes:
            parts.append(attributes)
        if operand is not None:
            parts.append(operand)
        if "at" in spec:
            parts.append("AT " + self.point(element.find(tc6(spec["at"]))))
        if "size" in spec and element.get(spec["size"][0]) is not None:
            parts.append("SIZE (%s, %s)" % tuple(element.get(a) for a in spec["size"]))
        return " ".join(parts)

    def operand(self, element, spec):
        """ Operand text, and values of attributes standing for child operand """
        operand = spec.get("operand")
        if operand is None:
            return None, {}
        if operand["kind"] == "block":
            instance = element.get(operand["instance"])
            text = ": " + name_or_text(element.get(operand["type"]))
            return (name_or_text(instance) + " " + text if instance is not None else text), {}
        if operand["kind"] == "attr":
            value = element.get(operand["name"])
            return (None if value is None else name_or_text(value)), {}
        node = element.find(tc6(operand["name"]))
        text = node.text or "" if node is not None else None
        rule = {"expression": "Expression", "variable": "Variable_Access"}[operand["syntax"]]
        if text is not None and text.strip() == text and iec_parser.matches(text, rule):
            return text, {}
        return None, {operand["name"]: text}

    def special_block(self, element, items, depth):
        spec = ELEMENTS["block/variable"]
        for group, direction in spec["groups"].items():
            for variable in element.find(tc6(group)).iterfind(tc6("variable")):
                if variable.find(tc6("documentation")) is not None:
                    raise ConversionError("%s: pin documentation is not supported"
                                          % where(element))
                pin = name_or_text(variable.get(spec["name"]))
                if is_true(variable.get(spec["flag"])):
                    pin = "NOT " + pin
                attributes = self.attributes(variable, spec["attrs"])
                if attributes:
                    pin += " " + attributes
                point_in = variable.find(tc6("connectionPointIn"))
                point_out = variable.find(tc6("connectionPointOut"))
                if (point_in is None) != (direction == "out") or \
                   (point_out is None) != (direction == "in"):
                    raise ConversionError("%s: pin %s must have connection points of its"
                                          " direction" % (where(element), variable.get(spec["name"])))
                line = pin
                if direction == "inout":
                    line = "IN_OUT " + line
                if point_in is not None:
                    line += self.input_tail(point_in)
                if point_out is not None:
                    line += self.output_tail(point_out)
                items.append(line + ";")
        return items

    def special_actionBlock(self, element, items, depth):
        spec = ELEMENTS["actionBlock/action"]
        for action in element.iterfind(tc6("action")):
            if action.find(tc6("connectionPointOut")) is not None or \
               action.find(tc6("addData")) is not None or \
               action.find(tc6("documentation")) is not None:
                raise ConversionError("%s: action output, additional data and documentation"
                                      " are not supported" % where(element))
            parts = []
            if action.get("localId") != spec["implied"]["localId"]:
                parts.append("#" + action.get("localId"))
            attributes = self.attributes(action, spec["attrs"])
            if attributes:
                parts.append(attributes)
            qualifier = self.qualifier(action, spec, element)
            tail = ""
            position = action.find(tc6("relPosition"))
            if [position.get("x"), position.get("y")] != spec["implied"]["relPosition"]:
                tail += " AT " + self.point(position)
            if action.get("width") is not None:
                tail += " SIZE (%s, %s)" % (action.get("width"), action.get("height"))
            reference = action.find(tc6("reference"))
            if reference is not None:
                parts.append(name_or_text(reference.get("name")) + qualifier + tail + ";")
                items.append(" ".join(parts))
            else:
                head = " ".join(["ACTION"] + parts + [qualifier]) + tail
                items.append(self.nested_body(action.find(tc6("inline")), depth + 1, head,
                                              "END_ACTION"))
        return items

    def qualifier(self, action, spec, element):
        qualifier = action.get("qualifier", "N")
        duration, indicator = action.get("duration"), action.get("indicator")
        text = qualifier
        if qualifier in spec["timed"]:
            if duration is None:
                raise ConversionError("%s: %s action has no duration" % (where(element), qualifier))
            text += ", " + (duration if iec_parser.matches(duration, "TC6_Action_Time") and
                            duration[:1] not in "'\"" else iec_string(duration))
        elif duration is not None:
            raise ConversionError("%s: %s action has a duration" % (where(element), qualifier))
        if indicator is not None:
            text += ", " + name_or_text(indicator)
        return "(%s)" % text

    def special_transition(self, element, items, depth):
        condition = element.find(tc6("condition"))
        if condition is None:
            return items
        spec = ELEMENTS["transition/condition"]
        line = "CONDITION"
        attributes = self.attributes(condition, spec["attrs"])
        if attributes:
            line += " " + attributes
        reference = condition.find(tc6("reference"))
        point_in = condition.find(tc6("connectionPointIn"))
        inline = condition.find(tc6("inline"))
        if reference is not None:
            items.append(line + " " + name_or_text(reference.get("name")) + ";")
        elif point_in is not None:
            items.append(line + self.input_tail(point_in) + ";")
        else:
            if inline.get("name") != spec["inline"]["name"]["implied"]:
                raise ConversionError("%s: named inline condition is not supported"
                                      % where(element))
            language = check_body(inline)
            text = formatted_text(language) if localname(language) == "ST" else None
            if text is not None and iec_parser.matches(text, "TC6_Raw_Expression") or text == "":
                items.append(line + " := " + text + ";")
            else:
                items.append(line + " " + self.tagged_body(inline, depth + 1))
        return items

    def special_macroStep(self, element, items, depth):
        body = element.find(tc6("body"))
        if body is not None:
            items.append(self.tagged_body(body, depth + 1))
        return items


class GraphBuilder:
    """ Parse tree to TC6 XML of graphical elements, for a declaration builder """

    def __init__(self, builder):
        self.builder = builder

    @property
    def text(self):
        return self.builder.text

    def error(self, message, node):
        return self.builder.error(message, node)

    # values

    def value(self, node, spec):
        text = source(self.text, node)
        if text.upper() == "NULL":
            return None
        kind = spec["kind"]
        if kind == "boolean":
            return "true" if text.upper() == "TRUE" else "false"
        if kind == "enum":
            return next(v for v in spec["values"] if v.upper() == text.upper())
        if kind == "string":
            return iec_unquote(text)
        return text

    def attributes(self, element, node, specs):
        """ Set attributes of (name := value, ...) node, and implied ones """
        given = {}
        if node is not None:
            for attribute in children(node, node[0][:-1]):
                name_node, value_node = kids(attribute)[0], kids(attribute)[2]
                name = next(n for n in specs if n.upper() == source(self.text, name_node).upper())
                if name in given:
                    raise self.error("attribute %s given twice" % name, attribute)
                given[name] = self.value(value_node, specs[name])
        for name, spec in specs.items():
            if name in given:
                value = given[name]
            else:
                value = spec["implied"]
            if value is not None:
                element.set(name, value)
        return given

    def point(self, parent, name, node):
        x, y = children(node, "TC6_Decimal")
        sub(parent, name, {"x": source(self.text, x), "y": source(self.text, y)})

    # connection points

    def connection(self, point, node):
        """ Connections or expression of TC6_Connection node """
        sources = child(node, "TC6_Sources")
        if sources is None:
            expression = sub(point, "expression")
            expression.text = iec_unquote(source(self.text, child(node, "Char_Str")))
            return
        for source_node in children(sources, "TC6_Source"):
            connection = sub(point, "connection", {
                "refLocalId": source(self.text, child(source_node, "TC6_Id"))[1:]})
            formal = child(source_node, "TC6_Name_Or_Text")
            if formal is not None:
                connection.set("formalParameter", name_value(self.text, formal))
            for position in children(source_node, "TC6_Point"):
                self.point(connection, "position", position)

    def input_point(self, parent, name, nodes, attributes=None):
        """ connectionPointIn from nodes of AT (x, y) := sources """
        point = sub(parent, name)
        if attributes is not None:
            for key, value in attributes.items():
                point.set(key, value)
        at = next((n for n in nodes if n[0] == "TC6_At"), None)
        if at is not None:
            self.point(point, "relPosition", child(at, "TC6_Point"))
        connection = next((n for n in nodes if n[0] == "TC6_Connection"), None)
        if connection is not None:
            self.connection(point, connection)
        return point

    def output_point(self, parent, name, nodes):
        """ connectionPointOut from nodes of => AT (x, y) 'expression' """
        point = sub(parent, name)
        at = next((n for n in nodes if n[0] == "TC6_At"), None)
        if at is not None:
            self.point(point, "relPosition", child(at, "TC6_Point"))
        expression = next((n for n in nodes if n[0] == "Char_Str"), None)
        if expression is not None:
            sub(point, "expression").text = iec_unquote(source(self.text, expression))
        return point

    # bodies

    def tagged_body(self, parent, name, node):
        """ Body element from TC6_Tagged_Body node """
        body = sub(parent, name)
        language = source(self.text, kids(node)[0]).upper()
        if language in ("ST", "IL"):
            start, end = kids(node)[0][2], kids(node)[-1][1]
            self.builder.exclude(start, end)
            add_formatted_text(body, language, body_text(self.text[start:end]))
        else:
            graphical = sub(body, language)
            self.elements(graphical, kids(node)[1:-1], kids(node)[0][2], kids(node)[-1][1])
        return body

    def nested_body(self, parent, name, node, start, end):
        """ Body element from TC6_Action_Body like node, between start and end positions """
        tagged = child(node, "TC6_Tagged_Body") if node is not None else None
        if tagged is not None:
            return self.tagged_body(parent, name, tagged)
        body = sub(parent, name)
        self.builder.exclude(start, end)
        add_formatted_text(body, "ST", body_text(self.text[start:end]))
        return body

    def elements(self, language, nodes, start, end, container=None):
        """ Graphical elements of language element, from nodes found between start and end.
        Gap before end goes to container, if any """
        previous = start
        for node in nodes:
            self.element(language, node, previous)
            previous = node[2]
        if container is not None:
            self.builder.end(container, previous, end)

    # elements

    def element(self, parent, node, previous):
        """ Graphical element from its node, after token ending at previous """
        while node[0] not in _TAGS:
            node = kids(node)[0]
        tag = _TAGS[node[0]]
        spec = ELEMENTS[tag]
        element = sub(parent, tag)
        head = kids(node)
        if "variant" in spec:
            element.set(spec["variant"][0], "true" if source(self.text, head[0]).upper() ==
                        spec["variant"][1] else "false")
            if element.get(spec["variant"][0]) == "false":
                del element.attrib[spec["variant"][0]]
        label = child(node, "TC6_Id")
        if label is not None:
            element.set(spec["label"], source(self.text, label)[1:])
        if "flag" in spec and has_literal(node, "NOT"):
            element.set(spec["flag"], "true")
        self.attributes(element, child(node, node[0] + "_Attributes"), spec["attrs"])
        self.operand(element, node, spec)
        at = child(node, "TC6_At")
        if at is not None:
            self.point(element, spec["at"], child(at, "TC6_Point"))
        size = child(node, "TC6_Size")
        if size is not None:
            width, height = children(child(size, "TC6_Point"), "TC6_Decimal")
            element.set("width", source(self.text, width))
            element.set("height", source(self.text, height))
        for item in children(node, node[0] + "_Item"):
            self.item(element, spec, tag, kids(item))
        if tag in ("comment", "error"):
            self.content(element, node)
        if tag == "block":
            for group in ELEMENTS["block/variable"]["groups"]:
                if element.find(tc6(group)) is None:
                    sub(element, group)
        order = spec["children"]
        for item in sorted(elements(element), key=lambda e: order.index(localname(e))):
            element.append(item)
        self.builder.unit(element, node, previous)
        return element

    def operand(self, element, node, spec):
        operand = spec.get("operand")
        if operand is None:
            return
        if operand["kind"] == "block":
            instance = child(node, "TC6_Block_Instance")
            if instance is not None:
                element.set(operand["instance"], name_value(self.text, kids(instance)[0]))
            element.set(operand["type"], name_value(self.text, kids(child(node, "TC6_Block_Type"))[0]))
        elif operand["kind"] == "attr":
            value = child(node, "TC6_Operand")
            if value is not None:
                element.set(operand["name"], name_value(self.text, kids(value)[0]))
        else:
            value = child(node, {"expression": "Expression",
                                 "variable": "Variable_Access"}[operand["syntax"]])
            # child operand may be given as attribute, that attributes() set
            fallback = element.attrib.pop(operand["name"], None)
            if (value is None) == (fallback is None):
                raise self.error("%s needs %s, once" % (spec["keyword"], operand["name"]), node)
            sub(element, operand["name"]).text = \
                source(self.text, value) if value is not None else fallback

    def item(self, element, spec, tag, nodes):
        first = nodes[0]
        if first[0].startswith("'"):
            pin = first[0][1:-1].upper()
            for child_name, pin_spec in spec["pins"].items():
                if pin_spec["pin"] == pin:
                    attributes = next((n for n in nodes if n[0].endswith("Pin_Attributes")), None)
                    tail = nodes[-1]
                    if pin_spec["direction"] == "in":
                        point = self.input_point(element, child_name, kids(tail))
                    else:
                        point = self.output_point(element, child_name, kids(tail))
                    self.attributes(point, attributes, pin_spec["attrs"])
                    return
            raise self.error("unknown connection point %s" % pin, first)
        getattr(self, "item_" + first[0])(element, first)

    def content(self, element, node):
        text = child(node, "Char_Str")
        if text is not None:
            add_formatted_text(element, "content", iec_unquote(source(self.text, text)))
            return
        head_end, end = kids(node)[-2][2], kids(node)[-1][1]
        comments = self.builder.trivia.within(head_end, end)
        if len(comments) != 1 or comments[0][2] != "Comment" or \
           not self.text.startswith("(*", comments[0][0]):
            raise self.error("%s holds one (* comment *)" % localname(element).upper(), node)
        self.builder.exclude(head_end, end)
        start, stop, _kind = comments[0]
        add_formatted_text(element, "content", self.text[start + 2:stop - 2])

    # block pins

    def block_pin(self, element, node, group):
        spec = ELEMENTS["block/variable"]
        parent = element.find(tc6(group))
        if parent is None:
            parent = sub(element, group)
        pin = child(node, "TC6_Block_Pin")
        variable = sub(parent, "variable", {
            spec["name"]: name_value(self.text, child(pin, "TC6_Name_Or_Text"))})
        if has_literal(pin, "NOT"):
            variable.set(spec["flag"], "true")
        self.attributes(variable, child(pin, "TC6_Block_Variable_Attributes"), spec["attrs"])
        return variable

    def item_TC6_Block_Input(self, element, node):
        variable = self.block_pin(element, node, "inputVariables")
        self.input_point(variable, "connectionPointIn", kids(child(node, "TC6_Input_Tail")))

    def item_TC6_Block_Output(self, element, node):
        variable = self.block_pin(element, node, "outputVariables")
        self.output_point(variable, "connectionPointOut", kids(child(node, "TC6_Output_Tail")))

    def item_TC6_Block_In_Out(self, element, node):
        variable = self.block_pin(element, node, "inOutVariables")
        self.input_point(variable, "connectionPointIn", kids(node))
        self.output_point(variable, "connectionPointOut", kids(child(node, "TC6_Output_Tail")))

    # actions

    def action(self, element, node):
        spec = ELEMENTS["actionBlock/action"]
        action = sub(element, "action")
        label = child(node, "TC6_Id")
        action.set("localId", source(self.text, label)[1:] if label is not None
                   else spec["implied"]["localId"])
        self.attributes(action, child(node, "TC6_Action_Attributes"), spec["attrs"])
        qualifier = child(node, "TC6_Action_Qualifier")
        if qualifier is not None:
            name = child(qualifier, "TC6_Timed_Qualifier") or child(qualifier, "TC6_Qualifier")
            action.set("qualifier", source(self.text, name).upper())
            duration = child(qualifier, "TC6_Action_Time")
            if duration is not None:
                action.set("duration", name_value(self.text, duration)
                           if child(duration, "Char_Str") else source(self.text, duration))
            indicator = child(qualifier, "TC6_Indicator")
            if indicator is not None:
                action.set("indicator", name_value(self.text, kids(indicator)[0]))
        at = child(node, "TC6_At")
        if at is not None:
            self.point(action, "relPosition", child(at, "TC6_Point"))
        else:
            x, y = spec["implied"]["relPosition"]
            sub(action, "relPosition", {"x": x, "y": y})
        size = child(node, "TC6_Size")
        if size is not None:
            width, height = children(child(size, "TC6_Point"), "TC6_Decimal")
            action.set("width", source(self.text, width))
            action.set("height", source(self.text, height))
        return action

    def item_TC6_Action_Association(self, element, node):
        action = self.action(element, node)
        sub(action, "reference", {"name": name_value(self.text, child(node, "TC6_Name_Or_Text"))})

    def item_TC6_Inline_Action(self, element, node):
        action = self.action(element, node)
        body = child(node, "TC6_Action_Body")
        start = kids(node)[kids(node).index(body) - 1][2] if body is not None else kids(node)[-2][2]
        self.nested_body(action, "inline", body, start, kids(node)[-1][1])

    # transition condition

    def item_TC6_Condition(self, element, node):
        spec = ELEMENTS["transition/condition"]
        condition = sub(element, "condition")
        self.attributes(condition, child(node, "TC6_Condition_Attributes"), spec["attrs"])
        nodes = kids(node)
        operand = child(node, "TC6_Operand")
        tagged = child(node, "TC6_Tagged_Body")
        if operand is not None:
            sub(condition, "reference", {"name": name_value(self.text, kids(operand)[0])})
        elif tagged is not None:
            self.tagged_body(condition, "inline", tagged).set(
                "name", spec["inline"]["name"]["implied"])
        elif child(node, "TC6_Sources") is not None:
            point = self.input_point(condition, "connectionPointIn", nodes)
            self.connection(point, ("TC6_Connection", 0, 0, [child(node, "TC6_Sources")]))
        else:
            assign = next(n for n in nodes if n[0] == "':='")
            start, end = assign[2], nodes[-1][1]
            self.builder.exclude(start, end)
            text = self.text[start:end]
            inline = sub(condition, "inline", {"name": spec["inline"]["name"]["implied"]})
            add_formatted_text(inline, "ST", text[1:] if text.startswith(" ") else text)

    def item_TC6_Tagged_Body(self, element, node):
        self.tagged_body(element, "body", node)
