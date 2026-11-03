#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Textual form of TC6 declarations : project header, data types, POUs, configuration

Writer turns TC6 XML into text, and Builder text parse tree into TC6 XML. Each
declaration is a unit, with its documentation and the gap before it. Writer
takes unchanged units from a cache of the text they were built from, if any.
"""

import re

from . import iec_parser
from .common import ConversionError, INDENT, tc6, localname, sub, elements
from .common import formatted_text, add_formatted_text, iec_string, iec_unquote, is_name, is_true
from .common import child, children, kids, source, body_text, body_region
from .comments import Trivia, doc_comment, check_add_data, set_gap, gap
from .graph import GraphWriter, GraphBuilder, check_body

POU_KEYWORDS = {"function": "FUNCTION", "functionBlock": "FUNCTION_BLOCK", "program": "PROGRAM"}
VAR_KINDS = {"localVars": "VAR", "tempVars": "VAR_TEMP", "inputVars": "VAR_INPUT",
             "outputVars": "VAR_OUTPUT", "inOutVars": "VAR_IN_OUT",
             "externalVars": "VAR_EXTERNAL", "globalVars": "VAR_GLOBAL"}
QUALIFIERS = [("constant", "CONSTANT"), ("retain", "RETAIN"), ("nonretain", "NON_RETAIN")]
ELEMENTARY = ["BOOL", "BYTE", "WORD", "DWORD", "LWORD", "SINT", "INT", "DINT", "LINT", "USINT",
              "UINT", "UDINT", "ULINT", "REAL", "LREAL", "TIME", "DATE", "DT", "TOD", "ANY",
              "ANY_DERIVED", "ANY_ELEMENTARY", "ANY_MAGNITUDE", "ANY_NUM", "ANY_REAL", "ANY_INT",
              "ANY_BIT", "ANY_STRING", "ANY_DATE"]
TYPE_ALIASES = {"TIME_OF_DAY": "TOD", "DATE_AND_TIME": "DT"}
UNSIGNED = ["USINT", "UINT", "UDINT", "ULINT", "BYTE", "WORD", "DWORD", "LWORD"]
FILE_HEADER = ["companyName", "companyURL", "productName", "productVersion", "productRelease",
               "creationDateTime", "contentDescription"]
CONTENT_HEADER = ["name", "version", "organization", "author", "language"]
SCALINGS = [("fbd", "fbdScaling"), ("ld", "ldScaling"), ("sfc", "sfcScaling")]
DEFAULT_HEADER = {"companyName": "Unknown", "productName": "Unnamed", "productVersion": "1",
                  "name": "Unnamed"}

_ARRAY_VALUE_RE = re.compile(r"([0-9]+)\((.*)\)$", re.S)
_STRUCT_VALUE_RE = re.compile(r"(.*?):=(.*)", re.S)


def pragma_string(text):
    """ IEC string for pragma content, that can not hold } """
    return iec_string(text).replace("}", "$7D")


def extract_values(values):
    """ Split on commas outside brackets, as Beremiz plcopen.extractValues does """
    items = values.split(",")
    i = 1
    while i < len(items):
        opened = items[i - 1].count("(") + items[i - 1].count("[")
        closed = items[i - 1].count(")") + items[i - 1].count("]")
        if opened > closed:
            items[i - 1] = ",".join([items[i - 1], items.pop(i)])
        elif opened == closed:
            i += 1
        else:
            raise ConversionError("%r is an invalid value" % values)
    return items


class Writer:
    """ TC6 XML to text """

    def __init__(self, cache=None):
        self.cache = cache
        self.graph = GraphWriter(self)

    def error(self, message, element=None):
        if element is not None:
            message = "%s %s: %s" % (localname(element), element.get("name", ""), message)
        return ConversionError(message)

    def unit(self, element, depth, generate, default_gap):
        """ Gap and text of element, with its documentation """
        check_add_data(element)
        if self.cache is not None:
            cached = self.cache.take(element)
            if cached is not None:
                return cached[0] + cached[1]
        stored = gap(element, "before")
        text = generate(element, depth)
        documentation = element.find(tc6("documentation"))
        if documentation is not None:
            text = doc_comment(formatted_text(documentation)) + "\n" + INDENT * depth + text
        return (default_gap if stored is None else stored) + text

    def units(self, items, depth, generate, suffix=""):
        return "".join(self.unit(i, depth, generate, "\n" + INDENT * depth) + suffix
                       for i in items)

    def end(self, element, depth):
        """ Gap before END keyword of element """
        stored = gap(element, "end") if element is not None else None
        return "\n" + INDENT * depth if stored is None else stored

    def name(self, element, attribute="name"):
        value = element.get(attribute)
        if value is None or not is_name(value):
            raise self.error("%r is not an IEC 61131-3 name" % value, element)
        return value

    # project

    def header(self, project):
        """ {TC6 PROJECT(...)} pragma of project header """
        file_header = project.find(tc6("fileHeader"))
        content_header = project.find(tc6("contentHeader"))
        items = ["%s := %s" % (a, pragma_string(header.get(a)))
                 for header, names in ((file_header, FILE_HEADER), (content_header, CONTENT_HEADER))
                 for a in names if header.get(a) is not None]
        comment = content_header.find(tc6("Comment"))
        if comment is not None:
            items.append("Comment := %s" % pragma_string(comment.text or ""))
        info = content_header.find(tc6("coordinateInfo"))
        page = info.find(tc6("pageSize"))
        if page is not None:
            items.append("pageSize := (%s, %s)" % (page.get("x"), page.get("y")))
        for language, name in SCALINGS:
            scaling = info.find(tc6(language) + "/" + tc6("scaling"))
            items.append("%s := (%s, %s)" % (name, scaling.get("x"), scaling.get("y")))
        for element in (project, content_header, file_header):
            check_add_data(element)
            if element.find(tc6("addDataInfo")) is not None:
                raise self.error("project additional data is not supported")
        if project.find(tc6("documentation")) is not None:
            raise self.error("project documentation is not supported")
        return "{TC6 PROJECT(" + ",\n    ".join(items) + ")}"

    # data types

    def type_spec(self, container, depth):
        """ Text of data type held by container (type, baseType or returnType) """
        content = elements(container)[0]
        name = localname(content)
        if name in ELEMENTARY:
            return name
        if name in ("string", "wstring"):
            length = content.get("length")
            return name.upper() + ("[%s]" % length if length is not None else "")
        if name == "derived":
            if content.find(tc6("addData")) is not None:
                raise self.error("derived type additional data is not supported")
            return self.name(content)
        if name == "array":
            return "ARRAY [%s] OF %s" % (", ".join(
                "%s..%s" % (d.get("lower"), d.get("upper")) for d in content.iterfind(tc6("dimension"))),
                self.type_spec(content.find(tc6("baseType")), depth))
        if name == "enum":
            base = content.find(tc6("baseType"))
            values = ", ".join(v.get("name") + (" := " + v.get("value") if v.get("value") is not None
                                                else "")
                               for v in content.iterfind(tc6("values") + "/" + tc6("value")))
            return (self.type_spec(base, depth) + " " if base is not None else "") + "(%s)" % values
        if name == "struct":
            check_add_data(content)
            return "STRUCT" + self.units(elements(content, "variable"), depth + 1, self.variable, ";") + \
                self.end(content, depth) + "END_STRUCT"
        if name in ("subrangeSigned", "subrangeUnsigned"):
            bounds = content.find(tc6("range"))
            return "%s (%s..%s)" % (self.type_spec(content.find(tc6("baseType")), depth),
                                    bounds.get("lower"), bounds.get("upper"))
        if name == "pointer":
            return "REF_TO " + self.type_spec(content.find(tc6("baseType")), depth)
        raise self.error("unsupported data type " + name)

    def value(self, value):
        """ Text of TC6 value, as Beremiz value.getvalue gives it """
        content = elements(value)[0]
        name = localname(content)
        if name == "simpleValue":
            return content.get("value", "")
        if name == "arrayValue":
            texts = []
            for item in content.iterfind(tc6("value")):
                try:
                    repetition = int(item.get("repetitionValue", "1"))
                except ValueError:
                    repetition = 1
                text = self.value(item)
                texts.append("%d(%s)" % (repetition, text) if repetition > 1 else text)
            return "[%s]" % ", ".join(texts)
        return "(%s)" % ", ".join("%s := %s" % (item.get("member"), self.value(item))
                                  for item in content.iterfind(tc6("value")))

    def initial_value(self, element):
        initial = element.find(tc6("initialValue"))
        if initial is None:
            return ""
        text = self.value(initial)
        if not iec_parser.matches(text, "TC6_Initial_Value"):
            raise self.error("initial value %r is not IEC 61131-3" % text, element)
        return " := " + text

    def data_type(self, data_type, depth):
        return self.name(data_type) + " : " + \
            self.type_spec(data_type.find(tc6("baseType")), depth) + self.initial_value(data_type)

    # variables

    def variable(self, variable, depth):
        text = self.name(variable)
        address = variable.get("address")
        if address is not None:
            text += " AT " + address
        return text + " : " + self.type_spec(variable.find(tc6("type")), depth) + \
            self.initial_value(variable)

    def var_block(self, var_list, depth):
        kind = VAR_KINDS.get(localname(var_list))
        if kind is None or var_list.get("name") is not None or \
           is_true(var_list.get("persistent")) or is_true(var_list.get("nonpersistent")):
            raise self.error("access variables, named and persistent variable blocks"
                             " are not supported", var_list)
        text = kind + "".join(" " + keyword for attribute, keyword in QUALIFIERS
                              if is_true(var_list.get(attribute)))
        return text + self.units(elements(var_list, "variable"), depth + 1, self.variable, ";") + \
            self.end(var_list, depth) + "END_VAR"

    # POUs

    def member(self, member, depth):
        """ POU action or transition """
        keyword = localname(member).upper()
        return self.graph.nested_body(member.find(tc6("body")), depth,
                                      "%s %s :" % (keyword, self.name(member)), "END_" + keyword)

    def pou(self, pou, depth):
        kind = POU_KEYWORDS[pou.get("pouType")]
        text = kind + " " + self.name(pou)
        interface = pou.find(tc6("interface"))
        blocks = []
        if interface is not None:
            if interface.find(tc6("addData")) is not None or \
               interface.find(tc6("documentation")) is not None:
                raise self.error("interface additional data and documentation are not supported",
                                 pou)
            return_type = interface.find(tc6("returnType"))
            if return_type is not None:
                text += " : " + self.type_spec(return_type, depth)
            blocks = [b for b in elements(interface) if localname(b) != "returnType"]
        text += self.units(blocks, depth + 1, self.var_block)
        members = pou.findall(tc6("actions") + "/" + tc6("action")) + \
            pou.findall(tc6("transitions") + "/" + tc6("transition"))
        text += self.units(members, depth + 1, self.member)
        bodies = pou.findall(tc6("body"))
        if len(bodies) != 1:
            raise self.error("POU must have one body", pou)
        language = check_body(bodies[0])
        if localname(language) in ("ST", "IL"):
            text += body_region(formatted_text(language), single_line=False)
        else:
            text += self.graphical(language, depth + 1) + self.end(pou, depth)
        return text + "END_" + kind

    def graphical(self, language, depth):
        return self.units(elements(language), depth, self.graph.element)

    @staticmethod
    def language(pou):
        """ Body language of POU """
        body = pou.find(tc6("body"))
        return localname(elements(body)[0]) if body is not None else "ST"

    # configuration

    def configuration(self, configuration, depth):
        for name in ("accessVars", "configVars"):
            if configuration.find(tc6(name)) is not None:
                raise self.error("access and configuration variables are not supported",
                                 configuration)
        return "CONFIGURATION " + self.name(configuration) + \
            self.units(elements(configuration, "globalVars"), depth + 1, self.var_block) + \
            self.units(elements(configuration, "resource"), depth + 1, self.resource) + \
            self.end(configuration, depth) + "END_CONFIGURATION"

    def resource(self, resource, depth):
        tasks = elements(resource, "task")
        text = "RESOURCE " + self.name(resource) + " ON PLC" + \
            self.units(elements(resource, "globalVars"), depth + 1, self.var_block) + \
            self.units(tasks, depth + 1, self.task, ";")
        for task in tasks:
            text += self.units(elements(task, "pouInstance"), depth + 1,
                               lambda i, d, t=task: self.instance(i, d, t), ";")
        return text + self.units(elements(resource, "pouInstance"), depth + 1, self.instance, ";") + \
            self.end(resource, depth) + "END_RESOURCE"

    def task(self, task, depth):
        settings = []
        for attribute in ("single", "interval"):
            value = task.get(attribute)
            if value is not None:
                if not iec_parser.matches(value, "Data_Source"):
                    raise self.error("%s %r is not IEC 61131-3" % (attribute, value), task)
                settings.append("%s := %s" % (attribute.upper(), value))
        settings.append("PRIORITY := %s" % task.get("priority"))
        return "TASK %s(%s)" % (self.name(task), ", ".join(settings))

    def instance(self, instance, depth, task=None):
        return "PROGRAM %s%s : %s" % (self.name(instance),
                                      " WITH " + self.name(task) if task is not None else "",
                                      self.name(instance, "typeName"))


class Builder:
    """ Parse tree of a file to TC6 XML """

    def __init__(self, text, path, trivia):
        self.text = text
        self.path = path
        self.trivia = Trivia(text, trivia)
        self.graph = GraphBuilder(self)
        self.built_units = []   # (element, gap, text start, text end)

    def error(self, message, node):
        return ConversionError(message, self.path, self.text, node[1])

    def exclude(self, start, end):
        self.trivia.exclude(start, end)

    def unit(self, element, node, previous, cached=True):
        """ Documentation and gap of element built from node, after token ending at previous """
        unit_gap, doc_start, doc = self.trivia.leading(previous, node[1])
        if doc is not None:
            add_formatted_text(element, "documentation", doc)
        set_gap(element, "before", unit_gap)
        if cached:
            self.built_units.append((element, unit_gap, doc_start, node[2]))

    def end(self, element, previous, end):
        """ Gap before END keyword of element """
        set_gap(element, "end", self.trivia.gap(previous, end))

    def pragma(self, start, end):
        """ Exclude pragma of project header from comments """
        self.exclude(start, end)

    # data types

    def type_spec(self, parent, name, node):
        """ Data type element, child of parent, from TC6_Type_Spec node """
        container = sub(parent, name)
        nodes = kids(node)
        first = nodes[0]
        if first[0] == "Elem_Type_Name" and len(nodes) == 1:
            self.elementary(container, first)
        elif first[0] == "TC6_Generic_Type":
            sub(container, source(self.text, first).upper())
        elif first[0] == "'ARRAY'":
            array = sub(container, "array")
            for bounds in children(node, "Subrange"):
                lower, upper = children(bounds, "Constant_Expr")
                sub(array, "dimension", {"lower": source(self.text, lower),
                                         "upper": source(self.text, upper)})
            self.type_spec(array, "baseType", child(node, "TC6_Type_Spec"))
        elif first[0] == "'REF_TO'":
            self.type_spec(sub(container, "pointer"), "baseType", child(node, "TC6_Type_Spec"))
        elif child(node, "Subrange") is not None:
            base = source(self.text, first).upper()
            subrange = sub(container, "subrangeUnsigned" if base in UNSIGNED else "subrangeSigned")
            lower, upper = children(child(node, "Subrange"), "Constant_Expr")
            sub(subrange, "range", {"lower": source(self.text, lower),
                                    "upper": source(self.text, upper)})
            sub(sub(subrange, "baseType"), base)
        elif child(node, "Enum_Value_Spec") is not None:
            enum = sub(container, "enum")
            values = sub(enum, "values")
            for spec in children(node, "Enum_Value_Spec"):
                value = sub(values, "value", {"name": source(self.text, kids(spec)[0])})
                if len(kids(spec)) > 1:
                    value.set("value", source(self.text, kids(spec)[2]))
            if first[0] == "Elem_Type_Name":
                self.elementary(sub(enum, "baseType"), first)
        elif first[0] == "Struct_Decl":
            struct = sub(container, "struct")
            previous = kids(first)[0][2]
            for member in kids(first)[1:-1]:
                if member[0] == "Struct_Elem_Decl":
                    variable = sub(struct, "variable", {
                        "name": source(self.text, child(member, "Struct_Elem_Name"))})
                    self.variable_content(variable, member)
                    self.unit(variable, member, previous)
                previous = member[2]
            self.end(struct, previous, kids(first)[-1][1])
        elif first[0] == "Identifier":
            sub(container, "derived", {"name": source(self.text, first)})
        else:
            raise self.error("unsupported data type", node)
        return container

    def elementary(self, container, node):
        text = source(self.text, node)
        match = re.match(r"(W?STRING)\s*(\[\s*([0-9_]+)\s*\])?$", text, re.I)
        if match is not None:
            sub(container, match.group(1).lower(), {"length": match.group(3)})
            return
        name = TYPE_ALIASES.get(text.upper(), text.upper())
        if name not in ELEMENTARY:
            raise self.error("%s is not a TC6 data type" % text, node)
        sub(container, name)

    def value(self, parent, name, text):
        """ TC6 value element from text, as Beremiz value.setvalue makes it """
        value = sub(parent, name)
        text = text.strip()
        if text.startswith("[") and text.endswith("]"):
            content = sub(value, "arrayValue")
            for item in extract_values(text[1:-1]):
                item = item.strip()
                match = _ARRAY_VALUE_RE.match(item)
                if match is not None:
                    self.value(content, "value", match.group(2).strip()).set(
                        "repetitionValue", match.group(1))
                else:
                    self.value(content, "value", item)
        elif text.startswith("(") and text.endswith(")"):
            content = sub(value, "structValue")
            for item in extract_values(text[1:-1]):
                match = _STRUCT_VALUE_RE.match(item)
                if match is None:
                    raise ConversionError("structure value %r has no member name" % item)
                self.value(content, "value", match.group(2).strip()).set(
                    "member", match.group(1).strip())
        else:
            sub(value, "simpleValue", {"value": text})
        return value

    def variable_content(self, variable, node):
        """ Address, type and initial value of variable from node with Located_At,
        TC6_Type_Spec and TC6_Initial_Value """
        located = child(node, "Located_At")
        if located is not None:
            variable.set("address", source(self.text, child(located, "Direct_Variable")))
        self.type_spec(variable, "type", child(node, "TC6_Type_Spec"))
        initial = child(node, "TC6_Initial_Value")
        if initial is not None:
            self.value(variable, "initialValue", source(self.text, initial))

    def data_types(self, parent, node, previous):
        """ dataType elements of a TYPE block, return them """
        types = []
        previous_token = kids(node)[0][2]
        for item in kids(node)[1:-1]:
            if item[0] == "Type_Decl":
                data_type = sub(parent, "dataType", {"name": source(self.text, kids(item)[0])})
                self.type_spec(data_type, "baseType", child(item, "TC6_Type_Spec"))
                initial = child(item, "TC6_Initial_Value")
                if initial is not None:
                    self.value(data_type, "initialValue", source(self.text, initial))
                self.unit(data_type, item, previous_token)
                types.append(data_type)
            previous_token = item[2]
        set_gap(types[-1], "end", self.trivia.gap(previous_token, kids(node)[-1][1]))
        return types

    # variables

    def var_block(self, parent, node, previous):
        kind = source(self.text, child(node, "TC6_Var_Kind")).upper()
        name = next(n for n, k in VAR_KINDS.items() if k == kind)
        var_list = sub(parent, name)
        previous_token = None
        for item in kids(node)[:-1]:
            if item[0] == "TC6_Var_Qualifier":
                keyword = source(self.text, item).upper()
                attribute = next(a for a, k in QUALIFIERS if k == keyword)
                if var_list.get(attribute) is not None:
                    raise self.error("%s given twice" % keyword, item)
                var_list.set(attribute, "true")
            elif item[0] == "TC6_Var_Decl":
                names = [source(self.text, n)
                         for n in children(child(item, "Variable_List"), "Variable_Name")]
                variables = []
                for name in names:
                    variable = sub(var_list, "variable", {"name": name})
                    self.variable_content(variable, item)
                    variables.append(variable)
                self.unit(variables[0], item, previous_token, cached=len(names) == 1)
            previous_token = item[2]
        self.end(var_list, previous_token, kids(node)[-1][1])
        self.unit(var_list, node, previous)
        return var_list

    # POUs

    def pou(self, parent, node, language, previous):
        head = child(node, "TC6_POU_Head")
        keyword = source(self.text, kids(head)[0]).upper()
        pou_type = next(t for t, k in POU_KEYWORDS.items() if k == keyword)
        end = child(node, "TC6_POU_End")
        if source(self.text, end).upper() != "END_" + keyword:
            raise self.error("%s ends with %s" % (keyword, source(self.text, end)), end)
        pou = sub(parent, "pou", {"name": source(self.text, kids(head)[1]),
                                  "pouType": pou_type})
        interface = sub(pou, "interface")
        return_type = child(head, "TC6_Type_Spec")
        if return_type is not None:
            self.type_spec(interface, "returnType", return_type)
        previous_token = head[2]
        for block in children(node, "TC6_Var_Decls"):
            self.var_block(interface, block, previous_token)
            previous_token = block[2]
        actions, transitions = None, None
        for member in children(node, "TC6_POU_Member"):
            keyword = source(self.text, kids(member)[0]).lower()
            if keyword == "action":
                actions = actions if actions is not None else sub(pou, "actions")
                container = actions
            else:
                transitions = transitions if transitions is not None else sub(pou, "transitions")
                container = transitions
            element = sub(container, keyword, {"name": source(self.text, kids(member)[1])})
            body = kids(member)[3]
            self.graph.nested_body(element, "body", body, kids(member)[2][2], kids(member)[-1][1])
            self.unit(element, member, previous_token)
            previous_token = member[2]
        if transitions is not None and actions is not None:
            actions.addnext(transitions)
        body = sub(pou, "body")
        if language in ("ST", "IL"):
            self.exclude(previous_token, end[1])
            add_formatted_text(body, language,
                               body_text(self.text[previous_token:end[1]], single_line=False))
        else:
            graphical = sub(body, language)
            self.graph.elements(graphical, children(node, "TC6_%s_Element" % language),
                                previous_token, end[1], pou)
        self.unit(pou, node, previous)
        return pou

    # configuration

    def configuration(self, parent, node, previous):
        configuration = sub(parent, "configuration", {"name": source(self.text, kids(node)[1])})
        previous_token = kids(node)[1][2]
        for item in kids(node)[2:-1]:
            if item[0] == "TC6_Var_Decls":
                self.global_vars(configuration, item, previous_token)
            else:
                self.resource(configuration, item, previous_token)
            previous_token = item[2]
        self.end(configuration, previous_token, kids(node)[-1][1])
        self.order(configuration, ["resource", "globalVars"])
        self.unit(configuration, node, previous)
        return configuration

    def global_vars(self, parent, node, previous):
        if source(self.text, child(node, "TC6_Var_Kind")).upper() != "VAR_GLOBAL":
            raise self.error("configurations and resources only have VAR_GLOBAL", node)
        self.var_block(parent, node, previous)

    def resource(self, parent, node, previous):
        resource = sub(parent, "resource", {"name": source(self.text, kids(node)[1])})
        tasks = {}
        previous_token = kids(node)[3][2]
        for item in kids(node)[4:-1]:
            if item[0] == "TC6_Var_Decls":
                self.global_vars(resource, item, previous_token)
            elif item[0] == "Task_Config":
                task = self.task(resource, item)
                tasks[task.get("name").upper()] = task
                self.unit(task, item, previous_token)
            elif item[0] == "TC6_Program_Config":
                task_name = child(item, "Task_Name")
                container = resource
                if task_name is not None:
                    container = tasks.get(source(self.text, task_name).upper())
                    if container is None:
                        raise self.error("unknown task " + source(self.text, task_name), task_name)
                instance = sub(container, "pouInstance", {
                    "name": source(self.text, child(item, "Prog_Name")),
                    "typeName": source(self.text, child(item, "Prog_Type_Name"))})
                self.unit(instance, item, previous_token)
            previous_token = item[2]
        self.end(resource, previous_token, kids(node)[-1][1])
        self.order(resource, ["task", "globalVars", "pouInstance"])
        self.unit(resource, node, previous)
        return resource

    def task(self, parent, node):
        task = sub(parent, "task", {"name": source(self.text, child(node, "Task_Name"))})
        settings = kids(child(node, "Task_Init"))
        for n, item in enumerate(settings):
            if item[0] in ("'SINGLE'", "'INTERVAL'", "'PRIORITY'"):
                task.set(item[0][1:-1].lower(), source(self.text, settings[n + 2]))
        return task

    @staticmethod
    def order(element, names):
        """ Reorder children of element as names are ordered in schema """
        for item in sorted(elements(element),
                           key=lambda e: names.index(localname(e)) if localname(e) in names
                           else len(names)):
            element.append(item)

    # project header

    def header(self, project, text, node):
        """ Fill project header from {TC6 PROJECT(...)} pragma content parse tree """
        file_header, content_header = project.find(tc6("fileHeader")), \
            project.find(tc6("contentHeader"))
        info = content_header.find(tc6("coordinateInfo"))
        for attribute in children(node, "TC6_Project_Attribute"):
            name = source(text, kids(attribute)[0])
            value = kids(attribute)[2]
            point = [source(text, d) for d in children(value, "TC6_Decimal")] \
                if value[0] == "TC6_Point" else None
            matching = [n for n in FILE_HEADER + CONTENT_HEADER + ["Comment", "pageSize"] +
                        [s for _l, s in SCALINGS] if n.upper() == name.upper()]
            name = matching[0]
            if (point is not None) != (name == "pageSize" or name.endswith("Scaling")):
                raise ConversionError("project %s has a wrong value" % name)
            if name in FILE_HEADER:
                file_header.set(name, iec_unquote(source(text, value)))
            elif name in CONTENT_HEADER:
                content_header.set(name, iec_unquote(source(text, value)))
            elif name == "Comment":
                comment = sub(content_header, "Comment")
                comment.text = iec_unquote(source(text, value))
                content_header.insert(0, comment)
            elif name == "pageSize":
                page = sub(info, "pageSize", {"x": point[0], "y": point[1]})
                info.insert(0, page)
            else:
                language = next(l for l, s in SCALINGS if s == name)
                scaling = info.find(tc6(language) + "/" + tc6("scaling"))
                scaling.set("x", point[0])
                scaling.set("y", point[1])
