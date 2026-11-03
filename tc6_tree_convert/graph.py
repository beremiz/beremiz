#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Textual form of TC6 graphical bodies (FBD, LD and SFC), driven by tc6_textmap

Nested bodies, either untagged ST or tagged with their language, and bodies
of POUs follow the same layout rule : body text is what is between the line
of its header and the line of its END keyword. A body without line break is
written on header line, separated by one space from header and END keyword.
"""

import re

from lxml import etree

from .tc6_textmap import ELEMENTS, EXCLUDED

TC6_NS = "http://www.plcopen.org/xml/tc6_0201"
XHTML_NS = "http://www.w3.org/1999/xhtml"
INDENT = "  "

_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_NUMBER_RE = re.compile(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)$")
_DURATION_RE = re.compile(r"(T|TIME|LT|LTIME)#[+-]?[0-9][0-9_.dhmsun]*$", re.I)
_IEC_ESCAPES = {"$": "$$", "'": "$'", "\n": "$N", "\r": "$R", "\t": "$T", "\f": "$P"}


class ConversionError(Exception):
    pass


def tc6(name):
    return "{%s}%s" % (TC6_NS, name)


def localname(element):
    return etree.QName(element).localname


def iec_string(text):
    """ IEC single byte string literal """
    return "'%s'" % "".join(
        _IEC_ESCAPES.get(c) or ("$%02X" % ord(c) if ord(c) < 0x20 else c) for c in text)


def name_or_text(text):
    return text if _NAME_RE.match(text) else iec_string(text)


def is_true(value):
    return value in ("true", "1")


def formatted_text(element):
    """ Text of TC6 formattedText element (xhtml:p) """
    paragraph = element.find("{%s}p" % XHTML_NS)
    if paragraph is None or len(paragraph):
        raise ConversionError("%s: only plain text is supported" % localname(element))
    return paragraph.text or ""


def simple_operand(text, syntax):
    """ True if text can be written bare as an expression or a variable """
    # TODO: check with parser Expression and Variable_Access rules
    if not text or text != text.strip() or re.search(r"[\n;{}]|\(\*", text):
        return False
    if syntax == "variable":
        return re.match(r"%?[A-Za-z_][A-Za-z0-9_.%\[\], ]*$", text) is not None
    return True


def where(element):
    return "%s #%s" % (localname(element), element.get("localId", "?"))


class GraphWriter:

    def __init__(self, indent=INDENT):
        self.indent = indent

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
                raise ConversionError("connection to #%s: addData and globalId are not supported"
                                      % connection.get("refLocalId"))
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
        """ AT (x, y) := sources; """
        text = ""
        position = point_in.find(tc6("relPosition"))
        if position is not None:
            text += " AT " + self.point(position)
        sources = self.sources(point_in)
        if sources:
            text += " := " + sources
        return text

    def output_tail(self, point_out):
        """ => AT (x, y); """
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
            raise ConversionError("%s: addData is not supported" % localname(point))
        attributes = self.attributes(point, spec["attrs"])
        head = spec["pin"] + (" " + attributes if attributes else "")
        if spec["direction"] == "in":
            return head + self.input_tail(point) + ";"
        return head + self.output_tail(point) + ";"

    # bodies

    def body(self, body, depth, tag_st=True):
        """ Lines of a nested body, tagged with its language unless ST and not tag_st """
        language = body[0]
        name = localname(language)
        prefix = self.indent * depth
        if name in ("ST", "IL"):
            text = formatted_text(language)
            if name == "IL" or tag_st:
                return self.text_body(prefix + name, text, prefix + "END_" + name)
            return text
        lines = [prefix + name]
        for element in language:
            lines.extend(self.element(element, depth + 1))
        lines.append(prefix + "END_" + name)
        return lines

    def text_body(self, head, text, end):
        """ Lines of raw text body between head and end lines """
        if "\n" not in text:
            return [head + " " + text + " " + end.lstrip()]
        return [head] + text.split("\n") + [end]

    def graphical(self, language, depth):
        """ Lines of FBD, LD or SFC body content """
        lines = []
        for element in language:
            lines.extend(self.element(element, depth))
        return lines

    # elements

    def element(self, element, depth):
        if not isinstance(element.tag, str):
            return []
        tag = localname(element)
        if tag in EXCLUDED:
            raise ConversionError("%s: %s is not supported" % (tag, EXCLUDED[tag]))
        spec = ELEMENTS.get(tag)
        if spec is None:
            raise ConversionError("unknown element " + tag)
        if element.find(tc6("addData")) is not None:
            raise ConversionError("%s: addData is not supported" % where(element))
        prefix = self.indent * depth
        head = self.head(element, spec)
        items = []
        for child_name, pin_spec in spec["pins"].items():
            items.extend(prefix + self.indent + self.pin(point, pin_spec)
                         for point in element.iterfind(tc6(child_name)))
        special = getattr(self, "special_" + tag, None)
        if special is not None:
            return special(element, head, items, depth)
        if not items:
            return [prefix + head + ";"]
        return [prefix + head] + items + [prefix + "END_" + spec["keyword"]]

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
        child = element.find(tc6(operand["name"]))
        text = child.text or "" if child is not None else None
        if text is not None and simple_operand(text, operand["syntax"]):
            return text, {}
        return None, {operand["name"]: text}

    def special_block(self, element, head, items, depth):
        prefix = self.indent * (depth + 1)
        spec = ELEMENTS["block/variable"]
        for group, direction in spec["groups"].items():
            for variable in element.find(tc6(group)).iterfind(tc6("variable")):
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
                    raise ConversionError("%s: pin %s must have connection points of its direction"
                                          % (where(element), variable.get(spec["name"])))
                line = pin
                if direction == "inout":
                    line = "IN_OUT " + line
                if point_in is not None:
                    line += self.input_tail(point_in)
                if point_out is not None:
                    line += self.output_tail(point_out)
                items.append(prefix + line + ";")
        return [self.indent * depth + head] + items + [self.indent * depth + "END_BLOCK"]

    def special_actionBlock(self, element, head, items, depth):
        prefix = self.indent * (depth + 1)
        spec = ELEMENTS["actionBlock/action"]
        for action in element.iterfind(tc6("action")):
            if action.find(tc6("connectionPointOut")) is not None:
                raise ConversionError("%s: action output is not supported" % where(element))
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
                items.append(prefix + " ".join(parts))
            else:
                text = self.body(action.find(tc6("inline")), depth + 1, tag_st=False)
                head_line = prefix + " ".join(["ACTION"] + parts + [qualifier.strip()]) + tail
                if isinstance(text, str):
                    items.extend(self.text_body(head_line, text, prefix + "END_ACTION"))
                else:
                    items.extend([head_line] + text + [prefix + "END_ACTION"])
        return [self.indent * depth + head] + items + [self.indent * depth + "END_ACTION_BLOCK"]

    def qualifier(self, action, spec, element):
        qualifier = action.get("qualifier", "N")
        duration, indicator = action.get("duration"), action.get("indicator")
        text = qualifier
        if qualifier in spec["timed"]:
            if duration is None:
                raise ConversionError("%s: %s action has no duration" % (where(element), qualifier))
            text += ", " + (duration if _DURATION_RE.match(duration) or _NAME_RE.match(duration)
                            else iec_string(duration))
        elif duration is not None:
            raise ConversionError("%s: %s action has a duration" % (where(element), qualifier))
        if indicator is not None:
            text += ", " + name_or_text(indicator)
        return "(%s)" % text

    def special_transition(self, element, head, items, depth):
        prefix = self.indent * (depth + 1)
        condition = element.find(tc6("condition"))
        if condition is not None:
            spec = ELEMENTS["transition/condition"]
            line = prefix + "CONDITION"
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
                language = inline[0]
                text = formatted_text(language) if localname(language) == "ST" else None
                if text is not None and ";" not in text and "(*" not in text:
                    items.append(line + " := " + text + ";")
                else:
                    body = self.body(inline, depth + 1)
                    items.extend([line + " " + body[0].lstrip()] + body[1:])
        return [self.indent * depth + head] + items + [self.indent * depth + "END_TRANSITION"]

    def special_comment(self, element, head, items, depth, keyword="COMMENT"):
        prefix = self.indent * depth
        text = formatted_text(element.find(tc6("content")))
        if "*)" in text:
            return [prefix + head + " " + iec_string(text) + ";"]
        return [prefix + head, prefix + self.indent + "(*" + text + "*)", prefix + "END_" + keyword]

    def special_error(self, element, head, items, depth):
        return self.special_comment(element, head, items, depth, "ERROR")

    def special_macroStep(self, element, head, items, depth):
        body = element.find(tc6("body"))
        if body is not None:
            items.extend(self.body(body, depth + 1))
        return [self.indent * depth + head] + items + [self.indent * depth + "END_MACRO_STEP"]


def preview(path, names):
    """ Print graphical bodies of named POUs, for review """
    tree = etree.parse(path)
    writer = GraphWriter()
    for pou in tree.iter(tc6("pou")):
        if names and pou.get("name") not in names:
            continue
        kind = {"function": "FUNCTION", "functionBlock": "FUNCTION_BLOCK",
                "program": "PROGRAM"}[pou.get("pouType")]
        print("%s %s\n(* interface : step 5 *)" % (kind, pou.get("name")))
        for action in pou.iterfind(tc6("actions") + "/" + tc6("action")):
            body = writer.body(action.find(tc6("body")), 0, tag_st=False)
            print("\n".join(writer.text_body("ACTION %s :" % action.get("name"), body,
                                             "END_ACTION") if isinstance(body, str)
                            else ["ACTION %s :" % action.get("name")] + body + ["END_ACTION"]))
        for transition in pou.iterfind(tc6("transitions") + "/" + tc6("transition")):
            body = writer.body(transition.find(tc6("body")), 0, tag_st=False)
            print("\n".join(writer.text_body("TRANSITION %s :" % transition.get("name"), body,
                                             "END_TRANSITION") if isinstance(body, str)
                            else ["TRANSITION %s :" % transition.get("name")] + body +
                            ["END_TRANSITION"]))
        language = pou.find(tc6("body"))[0]
        if localname(language) in ("FBD", "LD", "SFC"):
            print("\n".join(writer.graphical(language, 0)))
        else:
            print(formatted_text(language))
        print("END_" + kind + "\n")


if __name__ == "__main__":
    import sys
    preview(sys.argv[1], sys.argv[2:])
