#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os, sys
import re
import datetime
from types import *
from xml.dom import minidom
from xml.sax.saxutils import escape, unescape, quoteattr
from new import classobj

def CreateNode(name):
    node = minidom.Node()
    node.nodeName = name
    node._attrs = {}
    node.childNodes = []
    return node

def NodeRenameAttr(node, old_name, new_name):
    node._attrs[new_name] = node._attrs.pop(old_name)

def NodeSetAttr(node, name, value):
    attr = minidom.Attr(name)
    text = minidom.Text()
    text.data = value
    attr.childNodes[0] = text
    node._attrs[name] = attr

"""
Regular expression models for checking all kind of string values defined in XML
standard
"""
Name_model = re.compile('([a-zA-Z_\:][\w\.\-\:]*)$')
Names_model = re.compile('([a-zA-Z_\:][\w\.\-\:]*(?: [a-zA-Z_\:][\w\.\-\:]*)*)$')
NMToken_model = re.compile('([\w\.\-\:]*)$')
NMTokens_model = re.compile('([\w\.\-\:]*(?: [\w\.\-\:]*)*)$')
QName_model = re.compile('((?:[a-zA-Z_][\w]*:)?[a-zA-Z_][\w]*)$')
QNames_model = re.compile('((?:[a-zA-Z_][\w]*:)?[a-zA-Z_][\w]*(?: (?:[a-zA-Z_][\w]*:)?[a-zA-Z_][\w]*)*)$')
NCName_model = re.compile('([a-zA-Z_][\w]*)$')
URI_model = re.compile('((?:http://|/)?(?:[\w.-]*/?)*)$')
LANGUAGE_model = re.compile('([a-zA-Z]{1,8}(?:-[a-zA-Z0-9]{1,8})*)$')

ONLY_ANNOTATION = re.compile("((?:annotation )?)")

"""
Regular expression models for extracting dates and times from a string
"""
time_model = re.compile('([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]*)?)(?:Z)?$')
date_model = re.compile('([0-9]{4})-([0-9]{2})-([0-9]{2})((?:[\-\+][0-9]{2}:[0-9]{2})|Z)?$')
datetime_model = re.compile('([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]*)?)((?:[\-\+][0-9]{2}:[0-9]{2})|Z)?$')

class xml_timezone(datetime.tzinfo):

    def SetOffset(self, offset):
        if offset == "Z":
            self.__offset = timedelta(minutes = 0)
            self.__name = "UTC"
        else:
            sign = {"-" : -1, "+" : 1}[offset[0]]
            hours, minutes = [int(val) for val in offset[1:].split(":")]
            self.__offset = timedelta(minutes=sign * (hours * 60 + minutes))
            self.__name = ""

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return ZERO

[SYNTAXELEMENT, SYNTAXATTRIBUTE, SIMPLETYPE, COMPLEXTYPE, COMPILEDCOMPLEXTYPE, 
 ATTRIBUTESGROUP, ELEMENTSGROUP, ATTRIBUTE, ELEMENT, CHOICE, ANY, TAG, CONSTRAINT,
] = range(13)

def NotSupportedYet(type):
    """
    Function that generates a function that point out to user that datatype
    used is not supported by xmlclass yet
    @param type: data type
    @return: function generated
    """
    def GetUnknownValue(attr):
        raise ValueError("\"%s\" type isn't supported by \"xmlclass\" yet!" % \
                         type)
    return GetUnknownValue

"""
This function calculates the number of whitespace for indentation
"""
def getIndent(indent, balise):
    first = indent * 2
    second = first + len(balise) + 1
    return u'\t'.expandtabs(first), u'\t'.expandtabs(second)


def GetAttributeValue(attr, extract=True):
    """
    Function that extracts data from a tree node
    @param attr: tree node containing data to extract
    @param extract: attr is a tree node or not
    @return: data extracted as string
    """
    if not extract:
        return attr
    if len(attr.childNodes) == 1:
        return unicode(unescape(attr.childNodes[0].data))
    else:
        # content is a CDATA
        text = u''
        for node in attr.childNodes:
            if not (node.nodeName == "#text" and node.data.strip() == u''):
                text += unicode(unescape(node.data))
        return text


def GetNormalizedString(attr, extract=True):
    """
    Function that normalizes a string according to XML 1.0. Replace  
    tabulations, line feed and carriage return by white space
    @param attr: tree node containing data to extract or data to normalize
    @param extract: attr is a tree node or not
    @return: data normalized as string
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    return value.replace("\t", " ").replace("\r", " ").replace("\n", " ")


def GetToken(attr, extract=True):
    """
    Function that tokenizes a string according to XML 1.0. Remove any leading  
    and trailing white space and replace internal sequence of two or more 
    spaces by only one white space
    @param attr: tree node containing data to extract or data to tokenize
    @param extract: attr is a tree node or not
    @return: data tokenized as string
    """
    return " ".join([part for part in 
                     GetNormalizedString(attr, extract).split(" ")
                     if part])


def GetHexInteger(attr, extract=True):
    """
    Function that extracts an hexadecimal integer from a tree node or a string
    @param attr: tree node containing data to extract or data as a string
    @param extract: attr is a tree node or not
    @return: data as an integer
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    if len(value) % 2 != 0:
        raise ValueError("\"%s\" isn't a valid hexadecimal integer!" % value)
    try:
        return int(value, 16)
    except:
        raise ValueError("\"%s\" isn't a valid hexadecimal integer!" % value)


def GenerateIntegerExtraction(minInclusive=None, maxInclusive=None, 
                              minExclusive=None, maxExclusive=None):
    """
    Function that generates an extraction function for integer defining min and
    max of integer value
    @param minInclusive: inclusive minimum
    @param maxInclusive: inclusive maximum
    @param minExclusive: exclusive minimum
    @param maxExclusive: exclusive maximum
    @return: function generated
    """
    def GetInteger(attr, extract=True):
        """
        Function that extracts an integer from a tree node or a string
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: data as an integer
        """

        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        try:
            # TODO: permit to write value like 1E2
            value = int(value)
        except:
            raise ValueError("\"%s\" isn't a valid integer!" % value)
        if minInclusive is not None and value < minInclusive:
            raise ValueError("\"%d\" isn't greater or equal to %d!" % \
                             (value, minInclusive))
        if maxInclusive is not None and value > maxInclusive:
            raise ValueError("\"%d\" isn't lesser or equal to %d!" % \
                             (value, maxInclusive))
        if minExclusive is not None and value <= minExclusive:
            raise ValueError("\"%d\" isn't greater than %d!" % \
                             (value, minExclusive))
        if maxExclusive is not None and value >= maxExclusive:
            raise ValueError("\"%d\" isn't lesser than %d!" % \
                             (value, maxExclusive))
        return value
    return GetInteger


def GenerateFloatExtraction(type, extra_values=[]):
    """
    Function that generates an extraction function for float
    @param type: name of the type of float
    @return: function generated
    """
    def GetFloat(attr, extract = True):
        """
        Function that extracts a float from a tree node or a string
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: data as a float
        """
        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        if value in extra_values:
            return value
        try:
            return float(value)
        except:
            raise ValueError("\"%s\" isn't a valid %s!" % (value, type))
    return GetFloat


def GetBoolean(attr, extract=True):
    """
    Function that extracts a boolean from a tree node or a string
    @param attr: tree node containing data to extract or data as a string
    @param extract: attr is a tree node or not
    @return: data as a boolean
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    if value == "true" or value == "1":
        return True
    elif value == "false" or value == "0":
        return False
    else:
        raise ValueError("\"%s\" isn't a valid boolean!" % value)


def GetTime(attr, extract=True):
    """
    Function that extracts a time from a tree node or a string
    @param attr: tree node containing data to extract or data as a string
    @param extract: attr is a tree node or not
    @return: data as a time
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    result = time_model.match(value)
    if result:
        values = result.groups()
        time_values = [int(v) for v in values[:2]]
        seconds = float(values[2])
        time_values.extend([int(seconds), int((seconds % 1) * 1000000)])
        return datetime.time(*time_values)
    else:
        raise ValueError("\"%s\" isn't a valid time!" % value)


def GetDate(attr, extract=True):
    """
    Function that extracts a date from a tree node or a string
    @param attr: tree node containing data to extract or data as a string
    @param extract: attr is a tree node or not
    @return: data as a date
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    result = date_model.match(value)
    if result:
        values = result.groups()
        date_values = [int(v) for v in values[:3]]
        if values[3] is not None:
            tz = xml_timezone()
            tz.SetOffset(values[3])
            date_values.append(tz)
        return datetime.date(*date_values)
    else:
        raise ValueError("\"%s\" isn't a valid date!" % value)


def GetDateTime(attr, extract=True):
    """
    Function that extracts date and time from a tree node or a string
    @param attr: tree node containing data to extract or data as a string
    @param extract: attr is a tree node or not
    @return: data as date and time
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    result = datetime_model.match(value)
    if result:
        values = result.groups()
        datetime_values = [int(v) for v in values[:5]]
        seconds = float(values[5])
        datetime_values.extend([int(seconds), int((seconds % 1) * 1000000)])
        if values[6] is not None:
            tz = xml_timezone()
            tz.SetOffset(values[6])
            datetime_values.append(tz)
        return datetime.datetime(*datetime_values)
    else:
        raise ValueError("\"%s\" isn't a valid datetime!" % value)


def GenerateModelNameExtraction(type, model):
    """
    Function that generates an extraction function for string matching a model
    @param type: name of the data type
    @param model: model that data must match
    @return: function generated
    """
    def GetModelName(attr, extract=True):
        """
        Function that extracts a string from a tree node or not and check that
        string extracted or given match the model
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: data as a string if matching
        """
        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        result = model.match(value)
        if not result:
            raise ValueError("\"%s\" isn't a valid %s!" % (value, type))
        return value
    return GetModelName


def GenerateLimitExtraction(min=None, max=None, unbounded=True):
    """
    Function that generates an extraction function for integer defining min and
    max of integer value
    @param min: minimum limit value
    @param max: maximum limit value
    @param unbounded: value can be "unbounded" or not
    @return: function generated
    """
    def GetLimit(attr, extract=True):
        """
        Function that extracts a string from a tree node or not and check that
        string extracted or given is in a list of values
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: data as a string
        """
        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        if value == "unbounded":
            if unbounded:
                return value
            else:
                raise ValueError("Member limit can't be defined to \"unbounded\"!")
        try:
            limit = int(value)
        except:
            raise ValueError("\"%s\" isn't a valid value for this member limit!" % value)
        if limit < 0:
            raise ValueError("Member limit can't be negative!")
        elif min is not None and limit < min:
            raise ValueError("Member limit can't be lower than \"%d\"!" % min)
        elif max is not None and limit > max:
            raise ValueError("Member limit can't be upper than \"%d\"!" % max)
        return limit
    return GetLimit


def GenerateEnumeratedExtraction(type, list):
    """
    Function that generates an extraction function for enumerated values
    @param type: name of the data type
    @param list: list of possible values
    @return: function generated
    """
    def GetEnumerated(attr, extract=True):
        """
        Function that extracts a string from a tree node or not and check that
        string extracted or given is in a list of values
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: data as a string
        """
        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        if value in list:
            return value
        else:
            raise ValueError("\"%s\" isn't a valid value for %s!" % \
                             (value, type))
    return GetEnumerated


def GetNamespaces(attr, extract=True):
    """
    Function that extracts a list of namespaces from a tree node or a string
    @param attr: tree node containing data to extract or data as a string
    @param extract: attr is a tree node or not
    @return: list of namespaces
    """
    if extract:
        value = GetAttributeValue(attr)
    else:
        value = attr
    if value == "":
        return []
    elif value == "##any" or value == "##other":
        namespaces = [value]
    else:
        namespaces = []
        for item in value.split(" "):
            if item == "##targetNamespace" or item == "##local":
                namespaces.append(item)
            else:
                result = URI_model.match(item)
                if result is not None:
                    namespaces.append(item)
                else:
                    raise ValueError("\"%s\" isn't a valid value for namespace!" % value)
    return namespaces


def GenerateGetList(type, list):
    """
    Function that generates an extraction function for a list of values
    @param type: name of the data type
    @param list: list of possible values
    @return: function generated
    """
    def GetLists(attr, extract=True):
        """
        Function that extracts a list of values from a tree node or a string
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: list of values
        """
        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        if value == "":
            return []
        elif value == "#all":
            return [value]
        else:
            values = []
            for item in value.split(" "):
                if item in list:
                    values.append(item)
                else:
                    raise ValueError("\"%s\" isn't a valid value for %s!" % \
                                     (value, type))
            return values
    return GetLists


def GenerateModelNameListExtraction(type, model):
    """
    Function that generates an extraction function for list of string matching
    a model
    @param type: name of the data type
    @param model: model that list elements must match
    @return: function generated
    """
    def GetModelNameList(attr, extract=True):
        """
        Function that extracts a list of string from a tree node or not and
        check that all extracted items match the model
        @param attr: tree node containing data to extract or data as a string
        @param extract: attr is a tree node or not
        @return: data as a list of string if matching 
        """
        if extract:
            value = GetAttributeValue(attr)
        else:
            value = attr
        values = []
        for item in value.split(" "):
            result = model.match(item)
            if result is not None:
                values.append(item)
            else:
                raise ValueError("\"%s\" isn't a valid value for %s!" % \
                                 (value, type))
        return values
    return GetModelNameList

def GenerateAnyInfos(infos):
    def ExtractAny(tree):
        if tree.nodeName in ["#text", "#cdata-section"]:
            return unicode(unescape(tree.data))
        else:
            return tree
    
    def GenerateAny(value, name=None, indent=0):
        if isinstance(value, (StringType, UnicodeType)):
            try:
                value = value.decode("utf-8")
            except:
                pass
            return u'<![CDATA[%s]]>\n' % value
        else:
            return value.toprettyxml(indent=" "*indent, encoding="utf-8")
        
    return {
        "type": COMPLEXTYPE, 
        "extract": ExtractAny,
        "generate": GenerateAny,
        "initial": lambda: "",
        "check": lambda x: isinstance(x, (StringType, UnicodeType, minidom.Node))
    }

def GenerateTagInfos(infos):
    def ExtractTag(tree):
        if len(tree._attrs) > 0:
            raise ValueError("\"%s\" musn't have attributes!" % infos["name"])
        if len(tree.childNodes) > 0:
            raise ValueError("\"%s\" musn't have children!" % infos["name"])
        if infos["minOccurs"] == 0:
            return True
        else:
            return None
    
    def GenerateTag(value, name=None, indent=0):
        if name is not None and not (infos["minOccurs"] == 0 and value is None):
            ind1, ind2 = getIndent(indent, name)
            return ind1 + "<%s/>\n" % name
        else:
            return ""
    
    return {
        "type": TAG, 
        "extract": ExtractTag,
        "generate": GenerateTag,
        "initial": lambda: None,
        "check": lambda x: x == None or infos["minOccurs"] == 0 and value == True
    }

def FindTypeInfos(factory, infos):
    if isinstance(infos, (UnicodeType, StringType)):
        namespace, name = DecomposeQualifiedName(infos)
        return factory.GetQualifiedNameInfos(name, namespace)
    return infos
    
def GetElementInitialValue(factory, infos):
    infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
    if infos["minOccurs"] == 0 and infos["maxOccurs"] == 1:
        if infos.has_key("default"):
            return infos["elmt_type"]["extract"](infos["default"], False)
        else:
            return None
    elif infos["minOccurs"] == 1 and infos["maxOccurs"] == 1:
        return infos["elmt_type"]["initial"]()
    else:
        return [infos["elmt_type"]["initial"]() for i in xrange(infos["minOccurs"])]

def HandleError(message, raise_exception):
    if raise_exception:
        raise ValueError(message)
    return False

def CheckElementValue(factory, name, infos, value, raise_exception=True):
    infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
    if value is None and raise_exception:
        if not (infos["minOccurs"] == 0 and infos["maxOccurs"] == 1):
            return HandleError("Attribute '%s' isn't optional." % name, raise_exception)
    elif infos["maxOccurs"] == "unbounded" or infos["maxOccurs"] > 1:
        if not isinstance(value, ListType):
            return HandleError("Attribute '%s' must be a list." % name, raise_exception)
        if len(value) < infos["minOccurs"] or infos["maxOccurs"] != "unbounded" and len(value) > infos["maxOccurs"]:
            return HandleError("List out of bounds for attribute '%s'." % name, raise_exception)
        if not reduce(lambda x, y: x and y, map(infos["elmt_type"]["check"], value), True):
            return HandleError("Attribute '%s' must be a list of valid elements." % name, raise_exception)
    elif infos.has_key("fixed") and value != infos["fixed"]:
        return HandleError("Value of attribute '%s' can only be '%s'." % (name, str(infos["fixed"])), raise_exception)
    else:
        return infos["elmt_type"]["check"](value)
    return True

def GetContentInfos(name, choices):
    for choice_infos in choices:
        if choices_infos["type"] == "sequence":
            for element_infos in choices_infos["elements"]:
                if element_infos["type"] == CHOICE:
                    if GetContentInfos(name, element_infos["choices"]):
                        return choices_infos
                elif element_infos["name"] == name:
                    return choices_infos
        elif choice_infos["name"] == name:
            return choices_infos
    return None

def ComputeContentChoices(factory, name, infos):
    choices = []
    for choice in infos["choices"]:
        if choice["type"] == "sequence":
            choice["name"] = "sequence"
            for sequence_element in choice["elements"]:
                if sequence_element["type"] != CHOICE:
                    element_infos = factory.ExtractTypeInfos(sequence_element["name"], name, sequence_element["elmt_type"])
                    if element_infos is not None:
                        sequence_element["elmt_type"] = element_infos
        elif choice["elmt_type"] == "tag":
            choice["elmt_type"] = GenerateTagInfos(choice)
        else:
            choice_infos = factory.ExtractTypeInfos(choice["name"], name, choice["elmt_type"])
            if choice_infos is not None:
                choice["elmt_type"] = choice_infos
        choices.append((choice["name"], choice))
    return choices

def ExtractContentElement(factory, tree, infos, content):
    infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
    if infos["maxOccurs"] == "unbounded" or infos["maxOccurs"] > 1:
        if isinstance(content, ListType) and len(content) > 0 and \
           content[-1]["name"] == tree.nodeName:
            content_item = content.pop(-1)
            content_item["value"].append(infos["elmt_type"]["extract"](tree))
            return content_item
        elif not isinstance(content, ListType) and \
             content is not None and \
             content["name"] == tree.nodeName:
            return {"name": tree.nodeName, 
                    "value": content["value"] + [infos["elmt_type"]["extract"](tree)]}
        else:
            return {"name": tree.nodeName, 
                    "value": [infos["elmt_type"]["extract"](tree)]}
    else:
        return {"name": tree.nodeName, 
                "value": infos["elmt_type"]["extract"](tree)}

def GenerateContentInfos(factory, name, choices):
    choices_dict = {}
    for choice_name, infos in choices:
        if choice_name == "sequence":
            for element in infos["elements"]:
                if element["type"] == CHOICE:
                    element["elmt_type"] = GenerateContentInfos(factory, name, ComputeContentChoices(factory, name, element))
                elif choices_dict.has_key(element["name"]):
                    raise ValueError("'%s' element defined two times in choice" % choice_name)
                else:
                    choices_dict[element["name"]] = infos
        else:
            if choices_dict.has_key(choice_name):
                raise ValueError("'%s' element defined two times in choice" % choice_name)
            choices_dict[choice_name] = infos
    
    def GetContentInitial():
        content_name, infos = choices[0]
        if content_name == "sequence":
            content_value = []
            for i in xrange(infos["minOccurs"]):
                for element_infos in infos["elements"]:
                    value = GetElementInitialValue(factory, element_infos)
                    if value is not None:
                        if element_infos["type"] == CHOICE:
                            content_value.append(value)
                        else:
                            content_value.append({"name": element_infos["name"], "value": value})
        else:
            content_value = GetElementInitialValue(factory, infos)
        return {"name": content_name, "value": content_value}
        
    def CheckContent(value):
        if value["name"] != "sequence":
            infos = choices_dict.get(value["name"], None)
            if infos is not None:
                return CheckElementValue(factory, value["name"], infos, value["value"], False)
        elif len(value["value"]) > 0:
            infos = choices_dict.get(value["value"][0]["name"], None)
            if infos is None:
                for choice_name, infos in choices:
                    if infos["type"] == "sequence":
                        for element_infos in infos["elements"]:
                            if element_infos["type"] == CHOICE:
                                infos = GetContentInfos(value["value"][0]["name"], element_infos["choices"])
            if infos is not None:
                sequence_number = 0
                element_idx = 0
                while element_idx < len(value["value"]):
                    for element_infos in infos["elements"]:
                        element_value = None
                        if element_infos["type"] == CHOICE:
                            choice_infos = None
                            if element_idx < len(value["value"]):
                                for choice in element_infos["choices"]:
                                    if choice["name"] == value["value"][element_idx]["name"]:
                                        choice_infos = choice
                                        element_value = value["value"][element_idx]["value"]
                                        element_idx += 1
                                        break
                            if ((choice_infos is not None and 
                                 not CheckElementValue(factory, choice_infos["name"], choice_infos, element_value, False)) or
                                (choice_infos is None and element_infos["minOccurs"] > 0)):
                                raise ValueError("Invalid sequence value in attribute 'content'")
                        else:
                            if element_idx < len(value["value"]) and element_infos["name"] == value["value"][element_idx]["name"]:
                                element_value = value["value"][element_idx]["value"]
                                element_idx += 1
                            if not CheckElementValue(factory, element_infos["name"], element_infos, element_value, False):
                                raise ValueError("Invalid sequence value in attribute 'content'")
                    sequence_number += 1
                if sequence_number < infos["minOccurs"] or infos["maxOccurs"] != "unbounded" and sequence_number > infos["maxOccurs"]:
                    raise ValueError("Invalid sequence value in attribute 'content'")
                return True
        else:
            for element_name, infos in choices:
                if element_name == "sequence":
                    required = 0
                    for element in infos["elements"]:
                        if element["minOccurs"] > 0:
                            required += 1
                    if required == 0:
                        return True
        return False
    
    def ExtractContent(tree, content):
        infos = choices_dict.get(tree.nodeName, None)
        if infos is not None:
            if infos["name"] == "sequence":
                sequence_dict = dict([(element_infos["name"], element_infos) for element_infos in infos["elements"] if element_infos["type"] != CHOICE])
                element_infos = sequence_dict.get(tree.nodeName)
                if content is not None and \
                   content["name"] == "sequence" and \
                   len(content["value"]) > 0 and \
                   choices_dict.get(content["value"][-1]["name"]) == infos:
                    return {"name": "sequence",
                            "value": content["value"] + [ExtractContentElement(factory, tree, element_infos, content["value"][-1])]}
                else:
                    return {"name": "sequence",
                            "value": [ExtractContentElement(factory, tree, element_infos, None)]}
            else:
                return ExtractContentElement(factory, tree, infos, content)
        else:
            for choice_name, infos in choices:
                if infos["type"] == "sequence":
                    for element_infos in infos["elements"]:
                        if element_infos["type"] == CHOICE:
                            try:
                                if content is not None and \
                                    content["name"] == "sequence" and \
                                    len(content["value"]) > 0:
                                    return {"name": "sequence",
                                            "value": content["value"] + [element_infos["elmt_type"]["extract"](tree, content["value"][-1])]}
                                else:
                                    return {"name": "sequence",
                                            "value": [element_infos["elmt_type"]["extract"](tree, None)]}
                            except:
                                pass
        raise ValueError("Invalid element \"%s\" for content!" % tree.nodeName)
    
    def GenerateContent(value, name=None, indent=0):
        text = ""
        if value["name"] != "sequence":
            infos = choices_dict.get(value["name"], None)
            if infos is not None:
                infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
                if infos["maxOccurs"] == "unbounded" or infos["maxOccurs"] > 1:
                    for item in value["value"]:
                        text += infos["elmt_type"]["generate"](item, value["name"], indent)
                else:
                    text += infos["elmt_type"]["generate"](value["value"], value["name"], indent)
        elif len(value["value"]) > 0:
            infos = choices_dict.get(value["value"][0]["name"], None)
            if infos is None:
                for choice_name, infos in choices:
                    if infos["type"] == "sequence":
                        for element_infos in infos["elements"]:
                            if element_infos["type"] == CHOICE:
                                infos = GetContentInfos(value["value"][0]["name"], element_infos["choices"])
            if infos is not None:
                sequence_dict = dict([(element_infos["name"], element_infos) for element_infos in infos["elements"]]) 
                for element_value in value["value"]:
                    element_infos = sequence_dict.get(element_value["name"])
                    if element_infos["maxOccurs"] == "unbounded" or element_infos["maxOccurs"] > 1:
                        for item in element_value["value"]:
                            text += element_infos["elmt_type"]["generate"](item, element_value["name"], indent)
                    else:
                        text += element_infos["elmt_type"]["generate"](element_value["value"], element_infos["name"], indent)
        return text
        
    return {
        "type": COMPLEXTYPE,
        "initial": GetContentInitial,
        "check": CheckContent,
        "extract": ExtractContent,
        "generate": GenerateContent
    }

#-------------------------------------------------------------------------------
#                           Structure extraction functions
#-------------------------------------------------------------------------------


def DecomposeQualifiedName(name):
    result = QName_model.match(name)
    if not result:
        raise ValueError("\"%s\" isn't a valid QName value!" % name) 
    parts = result.groups()[0].split(':')
    if len(parts) == 1:
        return None, parts[0]
    return parts
    
def GenerateElement(element_name, attributes, elements_model, 
                    accept_text=False):
    def ExtractElement(factory, node):
        attrs = factory.ExtractNodeAttrs(element_name, node, attributes)
        children_structure = ""
        children_infos = []
        children = []
        for child in node.childNodes:
            if child.nodeName not in ["#comment", "#text"]:
                namespace, childname = DecomposeQualifiedName(child.nodeName)
                children_structure += "%s "%childname
        result = elements_model.match(children_structure)
        if not result:
            raise ValueError("Invalid structure for \"%s\" children!. First element invalid." % node.nodeName)
        valid = result.groups()[0]
        if len(valid) < len(children_structure):
            raise ValueError("Invalid structure for \"%s\" children!. Element number %d invalid." % (node.nodeName, len(valid.split(" ")) - 1))
        for child in node.childNodes:
            if child.nodeName != "#comment" and \
               (accept_text or child.nodeName != "#text"):
                if child.nodeName == "#text":
                    children.append(GetAttributeValue(node))
                else:
                    namespace, childname = DecomposeQualifiedName(child.nodeName)
                    infos = factory.GetQualifiedNameInfos(childname, namespace)
                    if infos["type"] != SYNTAXELEMENT:
                        raise ValueError("\"%s\" can't be a member child!" % name)
                    if infos["extract"].has_key(element_name):
                        children.append(infos["extract"][element_name](factory, child))
                    else:
                        children.append(infos["extract"]["default"](factory, child))
        return node.nodeName, attrs, children
    return ExtractElement


"""
Class that generate class from an XML Tree
"""
class ClassFactory:

    def __init__(self, document, filepath=None, debug=False):
        self.Document = document
        if filepath is not None:
            self.BaseFolder, self.FileName = os.path.split(filepath)
        else:
            self.BaseFolder = self.FileName = None
        self.Debug = debug
        
        # Dictionary for stocking Classes and Types definitions created from
        # the XML tree
        self.XMLClassDefinitions = {}
        
        self.DefinedNamespaces = {}
        self.Namespaces = {}
        self.SchemaNamespace = None
        self.TargetNamespace = None
        
        self.CurrentCompilations = []
        
        # Dictionaries for stocking Classes and Types generated
        self.ComputeAfter = []
        if self.FileName is not None:
            self.ComputedClasses = {self.FileName: {}}
        else:
            self.ComputedClasses = {}
        self.ComputedClassesInfos = {}
        self.AlreadyComputed = {}

    def GetQualifiedNameInfos(self, name, namespace=None, canbenone=False):
        if namespace is None:
            if self.Namespaces[self.SchemaNamespace].has_key(name):
                return self.Namespaces[self.SchemaNamespace][name]
            for space, elements in self.Namespaces.iteritems():
                if space != self.SchemaNamespace and elements.has_key(name):
                    return elements[name]
            parts = name.split("_", 1)
            if len(parts) > 1:
                group = self.GetQualifiedNameInfos(parts[0], namespace)
                if group is not None and group["type"] == ELEMENTSGROUP:
                    elements = []
                    if group.has_key("elements"):
                        elements = group["elements"]
                    elif group.has_key("choices"):
                        elements = group["choices"]
                    for element in elements:
                        if element["name"] == parts[1]:
                            return element
            if not canbenone:
                raise ValueError("Unknown element \"%s\" for any defined namespaces!" % name)
        elif self.Namespaces.has_key(namespace):
            if self.Namespaces[namespace].has_key(name):
                return self.Namespaces[namespace][name]
            parts = name.split("_", 1)
            if len(parts) > 1:
                group = self.GetQualifiedNameInfos(parts[0], namespace)
                if group is not None and group["type"] == ELEMENTSGROUP:
                    elements = []
                    if group.has_key("elements"):
                        elements = group["elements"]
                    elif group.has_key("choices"):
                        elements = group["choices"]
                    for element in elements:
                        if element["name"] == parts[1]:
                            return element
            if not canbenone:
                raise ValueError("Unknown element \"%s\" for namespace \"%s\"!" % (name, namespace))
        elif not canbenone:
            raise ValueError("Unknown namespace \"%s\"!" % namespace)
        return None

    def SplitQualifiedName(self, name, namespace=None, canbenone=False):
        if namespace is None:
            if self.Namespaces[self.SchemaNamespace].has_key(name):
                return name, None
            for space, elements in self.Namespaces.items():
                if space != self.SchemaNamespace and elements.has_key(name):
                    return name, None
            parts = name.split("_", 1)
            if len(parts) > 1:
                group = self.GetQualifiedNameInfos(parts[0], namespace)
                if group is not None and group["type"] == ELEMENTSGROUP:
                    elements = []
                    if group.has_key("elements"):
                        elements = group["elements"]
                    elif group.has_key("choices"):
                        elements = group["choices"]
                    for element in elements:
                        if element["name"] == parts[1]:
                            return part[1], part[0]
            if not canbenone:
                raise ValueError("Unknown element \"%s\" for any defined namespaces!" % name)
        elif self.Namespaces.has_key(namespace):
            if self.Namespaces[namespace].has_key(name):
                return name, None
            parts = name.split("_", 1)
            if len(parts) > 1:
                group = self.GetQualifiedNameInfos(parts[0], namespace)
                if group is not None and group["type"] == ELEMENTSGROUP:
                    elements = []
                    if group.has_key("elements"):
                        elements = group["elements"]
                    elif group.has_key("choices"):
                        elements = group["choices"]
                    for element in elements:
                        if element["name"] == parts[1]:
                            return parts[1], parts[0]
            if not canbenone:
                raise ValueError("Unknown element \"%s\" for namespace \"%s\"!" % (name, namespace))
        elif not canbenone:
            raise ValueError("Unknown namespace \"%s\"!" % namespace)
        return None, None

    def ExtractNodeAttrs(self, element_name, node, valid_attrs):
        attrs = {}
        for qualified_name, attr in node._attrs.items():
            namespace, name =  DecomposeQualifiedName(qualified_name)
            if name in valid_attrs:
                infos = self.GetQualifiedNameInfos(name, namespace)
                if infos["type"] != SYNTAXATTRIBUTE:
                    raise ValueError("\"%s\" can't be a member attribute!" % name)
                elif name in attrs:
                    raise ValueError("\"%s\" attribute has been twice!" % name)
                elif element_name in infos["extract"]:
                    attrs[name] = infos["extract"][element_name](attr)
                else:
                    attrs[name] = infos["extract"]["default"](attr)
            elif namespace == "xmlns":
                infos = self.GetQualifiedNameInfos("anyURI", self.SchemaNamespace)
                self.DefinedNamespaces[infos["extract"](attr)] = name
            else:
                raise ValueError("Invalid attribute \"%s\" for member \"%s\"!" % (qualified_name, node.nodeName))
        for attr in valid_attrs:
            if attr not in attrs and \
               self.Namespaces[self.SchemaNamespace].has_key(attr) and \
               self.Namespaces[self.SchemaNamespace][attr].has_key("default"):
                if self.Namespaces[self.SchemaNamespace][attr]["default"].has_key(element_name):
                    default = self.Namespaces[self.SchemaNamespace][attr]["default"][element_name]
                else:
                    default = self.Namespaces[self.SchemaNamespace][attr]["default"]["default"]
                if default is not None:
                    attrs[attr] = default
        return attrs

    def ReduceElements(self, elements, schema=False):
        result = []
        for child_infos in elements:
            if child_infos is not None:
                if child_infos[1].has_key("name") and schema:
                    self.CurrentCompilations.append(child_infos[1]["name"])
                namespace, name = DecomposeQualifiedName(child_infos[0])
                infos = self.GetQualifiedNameInfos(name, namespace)
                if infos["type"] != SYNTAXELEMENT:
                    raise ValueError("\"%s\" can't be a member child!" % name)
                element = infos["reduce"](self, child_infos[1], child_infos[2])
                if element is not None:
                    result.append(element)
                if child_infos[1].has_key("name") and schema:
                    self.CurrentCompilations.pop(-1)
        annotations = []
        children = []
        for element in result:
            if element["type"] == "annotation":
                annotations.append(element)
            else:
                children.append(element)
        return annotations, children

    def AddComplexType(self, typename, infos):
        if not self.XMLClassDefinitions.has_key(typename):
            self.XMLClassDefinitions[typename] = infos
        else:
            raise ValueError("\"%s\" class already defined. Choose another name!" % typename)

    def ParseSchema(self):
        pass

    def ExtractTypeInfos(self, name, parent, typeinfos):
        if isinstance(typeinfos, (StringType, UnicodeType)):
            namespace, name = DecomposeQualifiedName(typeinfos)
            infos = self.GetQualifiedNameInfos(name, namespace)
            if infos["type"] == COMPLEXTYPE:
                name, parent = self.SplitQualifiedName(name, namespace)
                result = self.CreateClass(name, parent, infos)
                if result is not None and not isinstance(result, (UnicodeType, StringType)):
                    self.Namespaces[self.TargetNamespace][result["name"]] = result
                return result
            elif infos["type"] == ELEMENT and infos["elmt_type"]["type"] == COMPLEXTYPE:
                name, parent = self.SplitQualifiedName(name, namespace)
                result = self.CreateClass(name, parent, infos["elmt_type"])
                if result is not None and not isinstance(result, (UnicodeType, StringType)):
                    self.Namespaces[self.TargetNamespace][result["name"]] = result
                return result
            else:
                return infos
        elif typeinfos["type"] == COMPLEXTYPE:
            return self.CreateClass(name, parent, typeinfos)
        elif typeinfos["type"] == SIMPLETYPE:
            return typeinfos
            
    """
    Methods that generates the classes
    """
    def CreateClasses(self):
        self.ParseSchema()
        for name, infos in self.Namespaces[self.TargetNamespace].items():
            if infos["type"] == ELEMENT:
                if not isinstance(infos["elmt_type"], (UnicodeType, StringType)) and \
                   infos["elmt_type"]["type"] == COMPLEXTYPE:
                    self.ComputeAfter.append((name, None, infos["elmt_type"], True))
                    while len(self.ComputeAfter) > 0:
                        result = self.CreateClass(*self.ComputeAfter.pop(0))
                        if result is not None and not isinstance(result, (UnicodeType, StringType)):
                            self.Namespaces[self.TargetNamespace][result["name"]] = result
            elif infos["type"] == COMPLEXTYPE:
                self.ComputeAfter.append((name, None, infos))
                while len(self.ComputeAfter) > 0:
                    result = self.CreateClass(*self.ComputeAfter.pop(0))
                    if result is not None and \
                       not isinstance(result, (UnicodeType, StringType)):
                        self.Namespaces[self.TargetNamespace][result["name"]] = result
            elif infos["type"] == ELEMENTSGROUP:
                elements = []
                if infos.has_key("elements"):
                    elements = infos["elements"]
                elif infos.has_key("choices"):
                    elements = infos["choices"]
                for element in elements:
                    if not isinstance(element["elmt_type"], (UnicodeType, StringType)) and \
                       element["elmt_type"]["type"] == COMPLEXTYPE:
                        self.ComputeAfter.append((element["name"], infos["name"], element["elmt_type"]))
                        while len(self.ComputeAfter) > 0:
                            result = self.CreateClass(*self.ComputeAfter.pop(0))
                            if result is not None and \
                               not isinstance(result, (UnicodeType, StringType)):
                                self.Namespaces[self.TargetNamespace][result["name"]] = result
        return self.ComputedClasses

    def CreateClass(self, name, parent, classinfos, baseclass = False):
        if parent is not None:
            classname = "%s_%s" % (parent, name)
        else:
            classname = name
        
        # Checks that classe haven't been generated yet
        if self.AlreadyComputed.get(classname, False):
            if baseclass:
                self.AlreadyComputed[classname].IsBaseClass = baseclass
            return self.ComputedClassesInfos.get(classname, None)
        
        # If base classes haven't been generated
        bases = []
        base_infos = classinfos.get("base", None)
        if base_infos is not None:
            result = self.ExtractTypeInfos("base", name, base_infos)
            if result is None:
                namespace, base_name = DecomposeQualifiedName(base_infos)                
                if self.AlreadyComputed.get(base_name, False):
                    self.ComputeAfter.append((name, parent, classinfos))
                    if self.TargetNamespace is not None:
                        return "%s:%s" % (self.TargetNamespace, classname)
                    else:
                        return classname
            elif result is not None:
                if self.FileName is not None:
                    classinfos["base"] = self.ComputedClasses[self.FileName].get(result["name"], None)
                    if classinfos["base"] is None:
                        for filename, classes in self.ComputedClasses.iteritems():
                            if filename != self.FileName:
                                classinfos["base"] = classes.get(result["name"], None)
                                if classinfos["base"] is not None:
                                    break
                else:
                    classinfos["base"] = self.ComputedClasses.get(result["name"], None)
                if classinfos["base"] is None:
                    raise ValueError("No class found for base type")
                bases.append(classinfos["base"])
        bases.append(object)
        bases = tuple(bases)
        classmembers = {"__doc__": classinfos.get("doc", ""), "IsBaseClass": baseclass}
        
        self.AlreadyComputed[classname] = True
        
        for attribute in classinfos["attributes"]:
            infos = self.ExtractTypeInfos(attribute["name"], name, attribute["attr_type"])
            if infos is not None:                    
                if infos["type"] != SIMPLETYPE:
                    raise ValueError("\"%s\" type is not a simple type!" % attribute["attr_type"])
                attrname = attribute["name"]
                if attribute["use"] == "optional":
                    classmembers[attrname] = None
                    classmembers["add%s"%attrname] = generateAddMethod(attrname, self, attribute)
                    classmembers["delete%s"%attrname] = generateDeleteMethod(attrname)
                else:
                    classmembers[attrname] = infos["initial"]()
                classmembers["set%s"%attrname] = generateSetMethod(attrname)
                classmembers["get%s"%attrname] = generateGetMethod(attrname)
            else:
                raise ValueError("\"%s\" type unrecognized!" % attribute["attr_type"])
            attribute["attr_type"] = infos
        
        for element in classinfos["elements"]:
            if element["type"] == CHOICE:
                elmtname = element["name"]
                choices = ComputeContentChoices(self, name, element)
                classmembers["get%schoices"%elmtname] = generateGetChoicesMethod(element["choices"])
                if element["maxOccurs"] == "unbounded" or element["maxOccurs"] > 1:
                    classmembers["append%sbytype" % elmtname] = generateAppendChoiceByTypeMethod(element["maxOccurs"], self, element["choices"])
                    classmembers["insert%sbytype" % elmtname] = generateInsertChoiceByTypeMethod(element["maxOccurs"], self, element["choices"])
                else:
                    classmembers["set%sbytype" % elmtname] = generateSetChoiceByTypeMethod(self, element["choices"])
                infos = GenerateContentInfos(self, name, choices)
            elif element["type"] == ANY:
                elmtname = element["name"] = "text"
                element["minOccurs"] = element["maxOccurs"] = 1
                infos = GenerateAnyInfos(element)
            else:
                elmtname = element["name"]
                if element["elmt_type"] == "tag":
                    infos = GenerateTagInfos(element)
                else:
                    infos = self.ExtractTypeInfos(element["name"], name, element["elmt_type"])
            if infos is not None:
                element["elmt_type"] = infos
            if element["maxOccurs"] == "unbounded" or element["maxOccurs"] > 1:
                classmembers[elmtname] = []
                classmembers["append%s" % elmtname] = generateAppendMethod(elmtname, element["maxOccurs"], self, element)
                classmembers["insert%s" % elmtname] = generateInsertMethod(elmtname, element["maxOccurs"], self, element)
                classmembers["remove%s" % elmtname] = generateRemoveMethod(elmtname, element["minOccurs"])
                classmembers["count%s" % elmtname] = generateCountMethod(elmtname)
            else:
                if element["minOccurs"] == 0:
                    classmembers[elmtname] = None
                    classmembers["add%s" % elmtname] = generateAddMethod(elmtname, self, element)
                    classmembers["delete%s" % elmtname] = generateDeleteMethod(elmtname)
                elif not isinstance(element["elmt_type"], (UnicodeType, StringType)):
                    classmembers[elmtname] = element["elmt_type"]["initial"]()
                else:
                    classmembers[elmtname] = None
            classmembers["set%s" % elmtname] = generateSetMethod(elmtname)
            classmembers["get%s" % elmtname] = generateGetMethod(elmtname)
            
        classmembers["__init__"] = generateInitMethod(self, classinfos)
        classmembers["getStructure"] = generateStructureMethod(classinfos)
        classmembers["loadXMLTree"] = generateLoadXMLTree(self, classinfos)
        classmembers["generateXMLText"] = generateGenerateXMLText(self, classinfos)
        classmembers["getElementAttributes"] = generateGetElementAttributes(self, classinfos)
        classmembers["getElementInfos"] = generateGetElementInfos(self, classinfos)
        classmembers["setElementValue"] = generateSetElementValue(self, classinfos)
        classmembers["singleLineAttributes"] = True
        classmembers["compatibility"] = lambda x, y: None
        classmembers["extraAttrs"] = {}
        
        class_definition = classobj(str(classname), bases, classmembers)
        setattr(class_definition, "__setattr__", generateSetattrMethod(self, class_definition, classinfos))
        class_infos = {"type": COMPILEDCOMPLEXTYPE,
                       "name": classname,
                       "check": generateClassCheckFunction(class_definition),
                       "initial": generateClassCreateFunction(class_definition),
                       "extract": generateClassExtractFunction(class_definition),
                       "generate": class_definition.generateXMLText}
        
        if self.FileName is not None:
            self.ComputedClasses[self.FileName][classname] = class_definition
        else:
            self.ComputedClasses[classname] = class_definition
        self.ComputedClassesInfos[classname] = class_infos
        
        return class_infos

    """
    Methods that print the classes generated
    """
    def PrintClasses(self):
        items = self.ComputedClasses.items()
        items.sort()
        if self.FileName is not None:
            for filename, classes in items:
                print "File '%s':" % filename
                class_items = classes.items()
                class_items.sort()
                for classname, xmlclass in class_items:
                    print "%s: %s" % (classname, str(xmlclass))
        else:
            for classname, xmlclass in items:
                print "%s: %s" % (classname, str(xmlclass))
        
    def PrintClassNames(self):
        classnames = self.XMLClassDefinitions.keys()
        classnames.sort()
        for classname in classnames:
            print classname

"""
Method that generate the method for checking a class instance
"""
def generateClassCheckFunction(class_definition):
    def classCheckfunction(instance):
        return isinstance(instance, class_definition)
    return classCheckfunction

"""
Method that generate the method for creating a class instance
"""
def generateClassCreateFunction(class_definition):
    def classCreatefunction():
        return class_definition()
    return classCreatefunction

"""
Method that generate the method for extracting a class instance
"""
def generateClassExtractFunction(class_definition):
    def classExtractfunction(node):
        instance = class_definition()
        instance.loadXMLTree(node)
        return instance
    return classExtractfunction

"""
Method that generate the method for loading an xml tree by following the
attributes list defined
"""
def generateSetattrMethod(factory, class_definition, classinfos):
    attributes = dict([(attr["name"], attr) for attr in classinfos["attributes"] if attr["use"] != "prohibited"])
    optional_attributes = dict([(attr["name"], True) for attr in classinfos["attributes"] if attr["use"] == "optional"])
    elements = dict([(element["name"], element) for element in classinfos["elements"]])
    
    def setattrMethod(self, name, value):
        if attributes.has_key(name):
            attributes[name]["attr_type"] = FindTypeInfos(factory, attributes[name]["attr_type"])
            if value is None:
                if optional_attributes.get(name, False):
                    return object.__setattr__(self, name, None)
                else:
                    raise ValueError("Attribute '%s' isn't optional." % name)
            elif attributes[name].has_key("fixed") and value != attributes[name]["fixed"]:
                raise ValueError, "Value of attribute '%s' can only be '%s'."%(name, str(attributes[name]["fixed"]))
            elif attributes[name]["attr_type"]["check"](value):
                return object.__setattr__(self, name, value)
            else:
                raise ValueError("Invalid value for attribute '%s'." % (name))
        elif elements.has_key(name):
            if CheckElementValue(factory, name, elements[name], value):
                return object.__setattr__(self, name, value)
            else:
                raise ValueError("Invalid value for attribute '%s'." % (name))
        elif classinfos.has_key("base"):
            return classinfos["base"].__setattr__(self, name, value)
        elif class_definition.__dict__.has_key(name):
            return object.__setattr__(self, name, value)
        else:
            raise AttributeError("'%s' can't have an attribute '%s'." % (self.__class__.__name__, name))
        
    return setattrMethod

"""
Method that generate the method for generating the xml tree structure model by 
following the attributes list defined
"""
def ComputeMultiplicity(name, infos):
    if infos["minOccurs"] == 0:
        if infos["maxOccurs"] == "unbounded":
            return "(?:%s)*" % name
        elif infos["maxOccurs"] == 1:
            return "(?:%s)?" % name
        else:
            return "(?:%s){,%d}" % (name, infos["maxOccurs"])
    elif infos["minOccurs"] == 1:
        if infos["maxOccurs"] == "unbounded":
            return "(?:%s)+" % name
        elif infos["maxOccurs"] == 1:
            return "(?:%s)" % name
        else:
            return "(?:%s){1,%d}" % (name, infos["maxOccurs"])
    else:
        if infos["maxOccurs"] == "unbounded":
            return "(?:%s){%d,}" % (name, infos["minOccurs"], name)
        else:
            return "(?:%s){%d,%d}" % (name, infos["minOccurs"], 
                                       infos["maxOccurs"])

def GetStructure(classinfos):
    elements = []
    for element in classinfos["elements"]:
        if element["type"] == ANY:
            infos = element.copy()
            infos["minOccurs"] = 0
            elements.append(ComputeMultiplicity("#text |#cdata-section |\w* ", infos))
        elif element["type"] == CHOICE:
            choices = []
            for infos in element["choices"]:
                if infos["type"] == "sequence":
                    structure = "(?:%s)" % GetStructure(infos)
                else:
                    structure = "%s " % infos["name"]
                choices.append(ComputeMultiplicity(structure, infos))
            elements.append(ComputeMultiplicity("|".join(choices), element))
        elif element["name"] == "content" and element["elmt_type"]["type"] == SIMPLETYPE:
            elements.append("(?:#text |#cdata-section )?")
        else:
            elements.append(ComputeMultiplicity("%s " % element["name"], element))
    if classinfos.get("order", True) or len(elements) == 0:
        return "".join(elements)
    else:
        raise ValueError("XSD structure not yet supported!")

def generateStructureMethod(classinfos):
    def getStructureMethod(self):
        structure = GetStructure(classinfos)
        if classinfos.has_key("base"):
            return classinfos["base"].getStructure(self) + structure
        return structure
    return getStructureMethod

"""
Method that generate the method for loading an xml tree by following the
attributes list defined
"""
def generateLoadXMLTree(factory, classinfos):
    attributes = dict([(attr["name"], attr) for attr in classinfos["attributes"] if attr["use"] != "prohibited"])
    elements = dict([(element["name"], element) for element in classinfos["elements"]])
    
    def loadXMLTreeMethod(self, tree, extras=[], derived=False):
        self.extraAttrs = {}
        self.compatibility(tree)
        if not derived:
            children_structure = ""
            for node in tree.childNodes:
                if not (node.nodeName == "#text" and node.data.strip() == "") and node.nodeName != "#comment":
                    children_structure += "%s " % node.nodeName
            structure_pattern = self.getStructure()
            if structure_pattern != "":
                structure_model = re.compile("(%s)$" % structure_pattern)
                result = structure_model.match(children_structure)
                if not result:
                    raise ValueError("Invalid structure for \"%s\" children!." % tree.nodeName)
        required_attributes = dict([(attr["name"], True) for attr in classinfos["attributes"] if attr["use"] == "required"])
        if classinfos.has_key("base"):
            extras.extend([attr["name"] for attr in classinfos["attributes"] if attr["use"] != "prohibited"])
            classinfos["base"].loadXMLTree(self, tree, extras, True)
        for attrname, attr in tree._attrs.iteritems():
            if attributes.has_key(attrname):
                attributes[attrname]["attr_type"] = FindTypeInfos(factory, attributes[attrname]["attr_type"])
                object.__setattr__(self, attrname, attributes[attrname]["attr_type"]["extract"](attr))
            elif not classinfos.has_key("base") and not attrname in extras and not self.extraAttrs.has_key(attrname):
                self.extraAttrs[attrname] = GetAttributeValue(attr)
            required_attributes.pop(attrname, None)
        if len(required_attributes) > 0:
            raise ValueError("Required attributes %s missing for \"%s\" element!" % (", ".join(["\"%s\""%name for name in required_attributes]), tree.nodeName))
        first = {}
        for node in tree.childNodes:
            name = node.nodeName
            if name == "#text" and node.data.strip() == "" or name == "#comment":
                continue
            elif elements.has_key(name):
                elements[name]["elmt_type"] = FindTypeInfos(factory, elements[name]["elmt_type"])
                if elements[name]["maxOccurs"] == "unbounded" or elements[name]["maxOccurs"] > 1:
                    if first.get(name, True):
                        object.__setattr__(self, name, [elements[name]["elmt_type"]["extract"](node)])
                        first[name] = False
                    else:
                        getattr(self, name).append(elements[name]["elmt_type"]["extract"](node))
                else:
                    object.__setattr__(self, name, elements[name]["elmt_type"]["extract"](node))
            elif elements.has_key("text"):
                if elements["text"]["maxOccurs"] == "unbounded" or elements["text"]["maxOccurs"] > 1:
                    if first.get("text", True):
                        object.__setattr__(self, "text", [elements["text"]["elmt_type"]["extract"](node)])
                        first["text"] = False
                    else:
                        getattr(self, "text").append(elements["text"]["elmt_type"]["extract"](node))
                else:
                    object.__setattr__(self, "text", elements["text"]["elmt_type"]["extract"](node))
            elif elements.has_key("content"):
                if name in ["#cdata-section", "#text"]:
                    if elements["content"]["elmt_type"]["type"] == SIMPLETYPE:
                        object.__setattr__(self, "content", elements["content"]["elmt_type"]["extract"](node.data, False))
                else:
                    content = getattr(self, "content")
                    if elements["content"]["maxOccurs"] == "unbounded" or elements["content"]["maxOccurs"] > 1:
                        if first.get("content", True):
                            object.__setattr__(self, "content", [elements["content"]["elmt_type"]["extract"](node, None)])
                            first["content"] = False
                        else:
                            content.append(elements["content"]["elmt_type"]["extract"](node, content))
                    else:
                        object.__setattr__(self, "content", elements["content"]["elmt_type"]["extract"](node, content))
    return loadXMLTreeMethod
        

"""
Method that generates the method for generating an xml text by following the
attributes list defined
"""
def generateGenerateXMLText(factory, classinfos):
    def generateXMLTextMethod(self, name, indent=0, extras={}, derived=False):
        ind1, ind2 = getIndent(indent, name)
        if not derived:
            text = ind1 + u'<%s' % name
        else:
            text = u''
        
        first = True
        
        if not classinfos.has_key("base"):
            extras.update(self.extraAttrs)
            for attr, value in extras.iteritems():
                if not first and not self.singleLineAttributes:
                    text += u'\n%s' % (ind2)
                text += u' %s=%s' % (attr, quoteattr(value))
                first = False
            extras.clear()
        for attr in classinfos["attributes"]:
            if attr["use"] != "prohibited":
                attr["attr_type"] = FindTypeInfos(factory, attr["attr_type"])
                value = getattr(self, attr["name"], None)
                if value != None:
                    computed_value = attr["attr_type"]["generate"](value)
                else:
                    computed_value = None
                if attr["use"] != "optional" or (value != None and \
                   computed_value != attr.get("default", attr["attr_type"]["generate"](attr["attr_type"]["initial"]()))):
                    if classinfos.has_key("base"):
                        extras[attr["name"]] = computed_value
                    else:
                        if not first and not self.singleLineAttributes:
                            text += u'\n%s' % (ind2)
                        text += ' %s=%s' % (attr["name"], quoteattr(computed_value))
                    first = False
        if classinfos.has_key("base"):
            first, new_text = classinfos["base"].generateXMLText(self, name, indent, extras, True)
            text += new_text
        else:
            first = True
        for element in classinfos["elements"]:
            element["elmt_type"] = FindTypeInfos(factory, element["elmt_type"])
            value = getattr(self, element["name"], None)
            if element["minOccurs"] == 0 and element["maxOccurs"] == 1:
                if value is not None:
                    if first:
                        text += u'>\n'
                        first = False
                    text += element["elmt_type"]["generate"](value, element["name"], indent + 1)
            elif element["minOccurs"] == 1 and element["maxOccurs"] == 1:
                if first:
                    text += u'>\n'
                    first = False
                if element["name"] == "content" and element["elmt_type"]["type"] == SIMPLETYPE:
                    text += element["elmt_type"]["generate"](value)
                else:
                    text += element["elmt_type"]["generate"](value, element["name"], indent + 1)
            else:
                if first and len(value) > 0:
                    text += u'>\n'
                    first = False
                for item in value:
                    text += element["elmt_type"]["generate"](item, element["name"], indent + 1)
        if not derived:
            if first:
                text += u'/>\n'
            else:
                text += ind1 + u'</%s>\n' % (name)
            return text
        else:
            return first, text
    return generateXMLTextMethod

def gettypeinfos(name, facets):
    if facets.has_key("enumeration") and facets["enumeration"][0] is not None:
        return facets["enumeration"][0]
    elif facets.has_key("maxInclusive"):
        limits = {"max" : None, "min" : None}
        if facets["maxInclusive"][0] is not None:
            limits["max"] = facets["maxInclusive"][0]
        elif facets["maxExclusive"][0] is not None:
            limits["max"] = facets["maxExclusive"][0] - 1
        if facets["minInclusive"][0] is not None:
            limits["min"] = facets["minInclusive"][0]
        elif facets["minExclusive"][0] is not None:
            limits["min"] = facets["minExclusive"][0] + 1
        if limits["max"] is not None or limits["min"] is not None:
            return limits
    return name

def generateGetElementAttributes(factory, classinfos):
    def getElementAttributes(self):
        attr_list = []
        if classinfos.has_key("base"):
            attr_list.extend(classinfos["base"].getElementAttributes(self))
        for attr in classinfos["attributes"]:
            if attr["use"] != "prohibited":
                attr_params = {"name" : attr["name"], "use" : attr["use"], 
                    "type" : gettypeinfos(attr["attr_type"]["basename"], attr["attr_type"]["facets"]),
                    "value" : getattr(self, attr["name"], "")}
                attr_list.append(attr_params)
        return attr_list
    return getElementAttributes

def generateGetElementInfos(factory, classinfos):
    attributes = dict([(attr["name"], attr) for attr in classinfos["attributes"] if attr["use"] != "prohibited"])
    elements = dict([(element["name"], element) for element in classinfos["elements"]])
    
    def getElementInfos(self, name, path=None, derived=False):
        attr_type = "element"
        value = None
        use = "required"
        children = []
        if path is not None:
            parts = path.split(".", 1)
            if attributes.has_key(parts[0]):
                if len(parts) != 0:
                    raise ValueError("Wrong path!")
                attr_type = gettypeinfos(attributes[parts[0]]["attr_type"]["basename"], 
                                         attributes[parts[0]]["attr_type"]["facets"])
                value = getattr(self, parts[0], "")
            elif elements.has_key(parts[0]):
                if elements[parts[0]]["elmt_type"]["type"] == SIMPLETYPE:
                    if len(parts) != 0:
                        raise ValueError("Wrong path!")
                    attr_type = gettypeinfos(elements[parts[0]]["elmt_type"]["basename"], 
                                             elements[parts[0]]["elmt_type"]["facets"])
                    value = getattr(self, parts[0], "")
                elif parts[0] == "content":
                    return self.content["value"].getElementInfos(self.content["name"], path)
                else:
                    attr = getattr(self, parts[0], None)
                    if attr is None:
                        raise ValueError("Wrong path!")
                    if len(parts) == 1:
                        return attr.getElementInfos(parts[0])
                    else:
                        return attr.getElementInfos(parts[0], parts[1])
            else:
                raise ValueError("Wrong path!")
        else:
            if not derived:
                children.extend(self.getElementAttributes())
            if classinfos.has_key("base"):
                children.extend(classinfos["base"].getElementInfos(self, name, derived=True)["children"])
            for element_name, element in elements.items():
                if element["minOccurs"] == 0:
                    use = "optional"
                if element_name == "content" and element["type"] == CHOICE:
                    attr_type = [(choice["name"], None) for choice in element["choices"]]
                    if self.content is None:
                        value = ""
                    else:
                        value = self.content["name"]
                        if self.content["value"] is not None:
                            if self.content["name"] == "sequence":
                                choices_dict = dict([(choice["name"], choice) for choice in element["choices"]])
                                sequence_infos = choices_dict.get("sequence", None)
                                if sequence_infos is not None:
                                    children.extend([item.getElementInfos(infos["name"]) for item, infos in zip(self.content["value"], sequence_infos["elements"])])
                            else:
                                children.extend(self.content["value"].getElementInfos(self.content["name"])["children"])
                elif element["elmt_type"]["type"] == SIMPLETYPE:
                    children.append({"name": element_name, "require": element["minOccurs"] != 0, 
                        "type": gettypeinfos(element["elmt_type"]["basename"], 
                                             element["elmt_type"]["facets"]),
                        "value": getattr(self, element_name, None)})
                else:
                    instance = getattr(self, element_name, None)
                    if instance is None:
                        instance = element["elmt_type"]["initial"]()
                    children.append(instance.getElementInfos(element_name))
        return {"name": name, "type": attr_type, "value": value, "use": use, "children": children}
    return getElementInfos

def generateSetElementValue(factory, classinfos):
    attributes = dict([(attr["name"], attr) for attr in classinfos["attributes"] if attr["use"] != "prohibited"])
    elements = dict([(element["name"], element) for element in classinfos["elements"]])
    
    def setElementValue(self, path, value):
        if path is not None:
            parts = path.split(".", 1)
            if attributes.has_key(parts[0]):
                if len(parts) != 1:
                    raise ValueError("Wrong path!")
                if attributes[parts[0]]["attr_type"]["basename"] == "boolean":
                    setattr(self, parts[0], value)
                elif attributes[parts[0]]["use"] == "optional" and value == "":
                    if attributes[parts[0]].has_key("default"):
                        setattr(self, parts[0], 
                            attributes[parts[0]]["attr_type"]["extract"](
                                attributes[parts[0]]["default"], False))
                    else:
                        setattr(self, parts[0], None)
                else:
                    setattr(self, parts[0], attributes[parts[0]]["attr_type"]["extract"](value, False))
            elif elements.has_key(parts[0]):
                if elements[parts[0]]["elmt_type"]["type"] == SIMPLETYPE:
                    if len(parts) != 1:
                        raise ValueError("Wrong path!")
                    if elements[parts[0]]["elmt_type"]["basename"] == "boolean":
                        setattr(self, parts[0], value)
                    elif attributes[parts[0]]["minOccurs"] == 0 and value == "":
                        setattr(self, parts[0], None)
                    else:
                        setattr(self, parts[0], elements[parts[0]]["elmt_type"]["extract"](value, False))
                else:
                    instance = getattr(self, parts[0], None)
                    if instance is None and elements[parts[0]]["minOccurs"] == 0:
                        instance = elements[parts[0]]["elmt_type"]["initial"]()
                        setattr(self, parts[0], instance)
                    if instance != None:
                        if len(parts) > 1:
                            instance.setElementValue(parts[1], value)
                        else:
                            instance.setElementValue(None, value)
            elif elements.has_key("content"):
                if len(parts) > 0:
                    self.content["value"].setElementValue(path, value)
            elif classinfos.has_key("base"):
                classinfos["base"].setElementValue(self, path, value)
        elif elements.has_key("content"):
            if value == "":
                if elements["content"]["minOccurs"] == 0:
                    self.setcontent(None)
                else:
                    raise ValueError("\"content\" element is required!")
            else:
                self.setcontentbytype(value)
    return setElementValue

"""
Methods that generates the different methods for setting and getting the attributes
"""
def generateInitMethod(factory, classinfos):
    def initMethod(self):
        self.extraAttrs = {}
        if classinfos.has_key("base"):
            classinfos["base"].__init__(self)
        for attribute in classinfos["attributes"]:
            attribute["attr_type"] = FindTypeInfos(factory, attribute["attr_type"])
            if attribute["use"] == "required":
                setattr(self, attribute["name"], attribute["attr_type"]["initial"]())
            elif attribute["use"] == "optional":
                if attribute.has_key("default"):
                    setattr(self, attribute["name"], attribute["attr_type"]["extract"](attribute["default"], False))
                else:
                    setattr(self, attribute["name"], None)
        for element in classinfos["elements"]:
            setattr(self, element["name"], GetElementInitialValue(factory, element))
    return initMethod

def generateSetMethod(attr):
    def setMethod(self, value):
        setattr(self, attr, value)
    return setMethod

def generateGetMethod(attr):
    def getMethod(self):
        return getattr(self, attr, None)
    return getMethod

def generateAddMethod(attr, factory, infos):
    def addMethod(self):
        if infos["type"] == ATTRIBUTE:
            infos["attr_type"] = FindTypeInfos(factory, infos["attr_type"])
            initial = infos["attr_type"]["initial"]
            extract = infos["attr_type"]["extract"]
        elif infos["type"] == ELEMENT:
            infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
            initial = infos["elmt_type"]["initial"]
            extract = infos["elmt_type"]["extract"]
        else:
            raise ValueError("Invalid class attribute!")
        if infos.has_key("default"):
            setattr(self, attr, extract(infos["default"], False))
        else:
            setattr(self, attr, initial())
    return addMethod

def generateDeleteMethod(attr):
    def deleteMethod(self):
        setattr(self, attr, None)
    return deleteMethod

def generateAppendMethod(attr, maxOccurs, factory, infos):
    def appendMethod(self, value):
        infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
        attr_list = getattr(self, attr)
        if maxOccurs == "unbounded" or len(attr_list) < maxOccurs:
            if infos["elmt_type"]["check"](value):
                attr_list.append(value)
            else:
                raise ValueError("\"%s\" value isn't valid!" % attr)
        else:
            raise ValueError("There can't be more than %d values in \"%s\"!" % (maxOccurs, attr))
    return appendMethod

def generateInsertMethod(attr, maxOccurs, factory, infos):
    def insertMethod(self, index, value):
        infos["elmt_type"] = FindTypeInfos(factory, infos["elmt_type"])
        attr_list = getattr(self, attr)
        if maxOccurs == "unbounded" or len(attr_list) < maxOccurs:
            if infos["elmt_type"]["check"](value):
                attr_list.insert(index, value)
            else:
                raise ValueError("\"%s\" value isn't valid!" % attr)
        else:
            raise ValueError("There can't be more than %d values in \"%s\"!" % (maxOccurs, attr))
    return insertMethod

def generateGetChoicesMethod(choice_types):
    def getChoicesMethod(self):
        return [choice["name"] for choice in choice_types]
    return getChoicesMethod

def generateSetChoiceByTypeMethod(factory, choice_types):
    choices = dict([(choice["name"], choice) for choice in choice_types])
    def setChoiceMethod(self, type):
        if not choices.has_key(type):
            raise ValueError("Unknown \"%s\" choice type for \"content\"!" % type)
        choices[type]["elmt_type"] = FindTypeInfos(factory, choices[type]["elmt_type"])
        new_element = choices[type]["elmt_type"]["initial"]()
        self.content = {"name": type, "value": new_element}
        return new_element
    return setChoiceMethod

def generateAppendChoiceByTypeMethod(maxOccurs, factory, choice_types):
    choices = dict([(choice["name"], choice) for choice in choice_types])
    def appendChoiceMethod(self, type):
        if not choices.has_key(type):
            raise ValueError("Unknown \"%s\" choice type for \"content\"!" % type)
        choices[type]["elmt_type"] = FindTypeInfos(factory, choices[type]["elmt_type"])
        if maxOccurs == "unbounded" or len(self.content) < maxOccurs:
            new_element = choices[type]["elmt_type"]["initial"]()
            self.content.append({"name": type, "value": new_element})
            return new_element
        else:
            raise ValueError("There can't be more than %d values in \"content\"!" % maxOccurs)
    return appendChoiceMethod

def generateInsertChoiceByTypeMethod(maxOccurs, factory, choice_types):
    choices = dict([(choice["name"], choice) for choice in choice_types])
    def insertChoiceMethod(self, index, type):
        if not choices.has_key(type):
            raise ValueError("Unknown \"%s\" choice type for \"content\"!" % type)
        choices[type]["elmt_type"] = FindTypeInfos(factory, choices[type]["elmt_type"])
        if maxOccurs == "unbounded" or len(self.content) < maxOccurs:
            new_element = choices[type]["elmt_type"]["initial"]()
            self.content.insert(index, {"name" : type, "value" : new_element})
            return new_element
        else:
            raise ValueError("There can't be more than %d values in \"content\"!" % maxOccurs)
    return insertChoiceMethod

def generateRemoveMethod(attr, minOccurs):
    def removeMethod(self, index):
        attr_list = getattr(self, attr)
        if len(attr_list) > minOccurs:
            getattr(self, attr).pop(index)
        else:
            raise ValueError("There can't be less than %d values in \"%s\"!" % (minOccurs, attr))
    return removeMethod

def generateCountMethod(attr):
    def countMethod(self):
        return len(getattr(self, attr))
    return countMethod

"""
This function generate the classes from a class factory
"""
def GenerateClasses(factory):
    ComputedClasses = factory.CreateClasses()
    if factory.FileName is not None and len(ComputedClasses) == 1:
        globals().update(ComputedClasses[factory.FileName])
        return ComputedClasses[factory.FileName]
    else:
        globals().update(ComputedClasses)
        return ComputedClasses

