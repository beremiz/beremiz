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

from xmlclass import *
from structures import *
from types import *
import os, re

"""
Dictionary that makes the relation between var names in plcopen and displayed values
"""
VarTypes = {"Local" : "localVars", "Temp" : "tempVars", "Input" : "inputVars",
            "Output" : "outputVars", "InOut" : "inOutVars", "External" : "externalVars",
            "Global" : "globalVars", "Access" : "accessVars"}

searchResultVarTypes = {
    "inputVars": "var_input",
    "outputVars": "var_output",
    "inOutVars": "var_inout"
}

"""
Define in which order var types must be displayed
"""
VarOrder = ["Local","Temp","Input","Output","InOut","External","Global","Access"]

"""
Define which action qualifier must be associated with a duration 
"""
QualifierList = {"N" : False, "R" : False, "S" : False, "L" : True, "D" : True, 
    "P" : False, "P0" : False, "P1" : False, "SD" : True, "DS" : True, "SL" : True}


FILTER_ADDRESS_MODEL = "(%%[IQM](?:[XBWDL])?)(%s)((?:\.[0-9]+)*)" 

def update_address(address, address_model, new_leading):
    result = address_model.match(address)
    if result is None:
        return address
    groups = result.groups()
    return groups[0] + new_leading + groups[2]

def _init_and_compare(function, v1, v2):
    if v1 is None:
        return v2
    if v2 is not None:
        return function(v1, v2)
    return v1

"""
Helper class for bounding_box calculation 
"""
class rect:
    
    def __init__(self, x=None, y=None, width=None, height=None):
        self.x_min = x
        self.x_max = None
        self.y_min = y
        self.y_max = None
        if width is not None and x is not None:
            self.x_max = x + width
        if height is not None and y is not None:
            self.y_max = y + height
    
    def update(self, x, y):
        self.x_min = _init_and_compare(min, self.x_min, x)
        self.x_max = _init_and_compare(max, self.x_max, x)
        self.y_min = _init_and_compare(min, self.y_min, y)
        self.y_max = _init_and_compare(max, self.y_max, y)
        
    def union(self, rect):
        self.x_min = _init_and_compare(min, self.x_min, rect.x_min)
        self.x_max = _init_and_compare(max, self.x_max, rect.x_max)
        self.y_min = _init_and_compare(min, self.y_min, rect.y_min)
        self.y_max = _init_and_compare(max, self.y_max, rect.y_max)
    
    def bounding_box(self):
        width = height = None
        if self.x_min is not None and self.x_max is not None:
            width = self.x_max - self.x_min
        if self.y_min is not None and self.y_max is not None:
            height = self.y_max - self.y_min
        return self.x_min, self.y_min, width, height

def TextLenInRowColumn(text):
    if text == "":
        return (0, 0)
    lines = text.split("\n")
    return len(lines) - 1, len(lines[-1])

def TestTextElement(text, criteria):
    lines = text.splitlines()
    if not criteria["case_sensitive"]:
        text = text.upper()
    test_result = []
    result = criteria["pattern"].search(text)
    while result is not None:
        start = TextLenInRowColumn(text[:result.start()])
        end = TextLenInRowColumn(text[:result.end() - 1])
        test_result.append((start, end, "\n".join(lines[start[0]:end[0] + 1])))
        result = criteria["pattern"].search(text, result.end())
    return test_result

PLCOpenClasses = GenerateClassesFromXSD(os.path.join(os.path.split(__file__)[0], "tc6_xml_v201.xsd"))

ElementNameToClass = {}

cls = PLCOpenClasses.get("formattedText", None)
if cls:
    def updateElementName(self, old_name, new_name):
        text = self.text
        index = text.find(old_name)
        while index != -1:
            if index > 0 and (text[index - 1].isalnum() or text[index - 1] == "_"):
                index = text.find(old_name, index + len(old_name))
            elif index < len(text) - len(old_name) and (text[index + len(old_name)].isalnum() or text[index + len(old_name)] == "_"):
                index = text.find(old_name, index + len(old_name))
            else:
                text = text[:index] + new_name + text[index + len(old_name):]
                index = text.find(old_name, index + len(new_name))
        self.text = text
    setattr(cls, "updateElementName", updateElementName)
    
    def updateElementAddress(self, address_model, new_leading):
        text = self.text
        startpos = 0
        result = address_model.search(text, startpos)
        while result is not None:
            groups = result.groups()
            new_address = groups[0] + new_leading + groups[2]
            text = text[:result.start()] + new_address + text[result.end():]
            startpos = result.start() + len(new_address)
            result = address_model.search(self.text, startpos)
        self.text = text
    setattr(cls, "updateElementAddress", updateElementAddress)
    
    def Search(self, criteria, parent_infos):
        return [(tuple(parent_infos),) + result for result in TestTextElement(self.gettext(), criteria)]
    setattr(cls, "Search", Search)
    
cls = PLCOpenClasses.get("project", None)
if cls:
    cls.singleLineAttributes = False
    cls.EnumeratedDataTypeValues = {}
    cls.CustomDataTypeRange = {}
    cls.CustomTypeHierarchy = {}
    cls.ElementUsingTree = {}
    cls.CustomBlockTypes = []
    
    def setname(self, name):
        self.contentHeader.setname(name)
    setattr(cls, "setname", setname)
        
    def getname(self):
        return self.contentHeader.getname()
    setattr(cls, "getname", getname)
    
    def getfileHeader(self):
        fileheader = {}
        for name, value in [("companyName", self.fileHeader.getcompanyName()),
                            ("companyURL", self.fileHeader.getcompanyURL()),
                            ("productName", self.fileHeader.getproductName()),
                            ("productVersion", self.fileHeader.getproductVersion()),
                            ("productRelease", self.fileHeader.getproductRelease()),
                            ("creationDateTime", self.fileHeader.getcreationDateTime()),
                            ("contentDescription", self.fileHeader.getcontentDescription())]:
            if value is not None:
                fileheader[name] = value
            else:
                fileheader[name] = ""
        return fileheader
    setattr(cls, "getfileHeader", getfileHeader)
    
    def setfileHeader(self, fileheader):
        if fileheader.has_key("companyName"):
            self.fileHeader.setcompanyName(fileheader["companyName"])
        if fileheader.has_key("companyURL"):
            self.fileHeader.setcompanyURL(fileheader["companyURL"])
        if fileheader.has_key("productName"):
            self.fileHeader.setproductName(fileheader["productName"])
        if fileheader.has_key("productVersion"):
            self.fileHeader.setproductVersion(fileheader["productVersion"])
        if fileheader.has_key("productRelease"):
            self.fileHeader.setproductRelease(fileheader["productRelease"])
        if fileheader.has_key("creationDateTime"):
            self.fileHeader.setcreationDateTime(fileheader["creationDateTime"])
        if fileheader.has_key("contentDescription"):
            self.fileHeader.setcontentDescription(fileheader["contentDescription"])
    setattr(cls, "setfileHeader", setfileHeader)
    
    def getcontentHeader(self):
        contentheader = {}
        for name, value in [("projectName", self.contentHeader.getname()),
                            ("projectVersion", self.contentHeader.getversion()),
                            ("modificationDateTime", self.contentHeader.getmodificationDateTime()),
                            ("organization", self.contentHeader.getorganization()),
                            ("authorName", self.contentHeader.getauthor()),
                            ("language", self.contentHeader.getlanguage())]:
            if value is not None:
                contentheader[name] = value
            else:
                contentheader[name] = ""
        contentheader["pageSize"] = self.contentHeader.getpageSize()
        contentheader["scaling"] = self.contentHeader.getscaling()
        return contentheader
    setattr(cls, "getcontentHeader", getcontentHeader)
    
    def setcontentHeader(self, contentheader):
        if contentheader.has_key("projectName"):
            self.contentHeader.setname(contentheader["projectName"])
        if contentheader.has_key("projectVersion"):
            self.contentHeader.setversion(contentheader["projectVersion"])
        if contentheader.has_key("modificationDateTime"):
            self.contentHeader.setmodificationDateTime(contentheader["modificationDateTime"])
        if contentheader.has_key("organization"):
            self.contentHeader.setorganization(contentheader["organization"])
        if contentheader.has_key("authorName"):
            self.contentHeader.setauthor(contentheader["authorName"])
        if contentheader.has_key("language"):
            self.contentHeader.setlanguage(contentheader["language"])
        if contentheader.has_key("pageSize"):
            self.contentHeader.setpageSize(*contentheader["pageSize"])
        if contentheader.has_key("scaling"):
            self.contentHeader.setscaling(contentheader["scaling"])
    setattr(cls, "setcontentHeader", setcontentHeader)
    
    def getdataTypes(self):
        return self.types.getdataTypeElements()
    setattr(cls, "getdataTypes", getdataTypes)
    
    def getdataType(self, name):
        return self.types.getdataTypeElement(name)
    setattr(cls, "getdataType", getdataType)
    
    def appenddataType(self, name):
        if self.CustomTypeHierarchy.has_key(name):
            raise ValueError, "\"%s\" Data Type already exists !!!"%name
        self.types.appenddataTypeElement(name)
        self.AddCustomDataType(self.getdataType(name))
    setattr(cls, "appenddataType", appenddataType)
        
    def insertdataType(self, index, datatype):
        self.types.insertdataTypeElement(index, datatype)
        self.AddCustomDataType(datatype)
    setattr(cls, "insertdataType", insertdataType)
    
    def removedataType(self, name):
        self.types.removedataTypeElement(name)
        self.RefreshDataTypeHierarchy()
        self.RefreshElementUsingTree()
    setattr(cls, "removedataType", removedataType)
    
    def getpous(self):
        return self.types.getpouElements()
    setattr(cls, "getpous", getpous)
    
    def getpou(self, name):
        return self.types.getpouElement(name)
    setattr(cls, "getpou", getpou)
    
    def appendpou(self, name, pou_type, body_type):
        self.types.appendpouElement(name, pou_type, body_type)
        self.AddCustomBlockType(self.getpou(name))
    setattr(cls, "appendpou", appendpou)
        
    def insertpou(self, index, pou):
        self.types.insertpouElement(index, pou)
        self.AddCustomBlockType(pou)
    setattr(cls, "insertpou", insertpou)
    
    def removepou(self, name):
        self.types.removepouElement(name)
        self.RefreshCustomBlockTypes()
        self.RefreshElementUsingTree()
    setattr(cls, "removepou", removepou)

    def getconfigurations(self):
        configurations = self.instances.configurations.getconfiguration()
        if configurations:
            return configurations
        return []
    setattr(cls, "getconfigurations", getconfigurations)

    def getconfiguration(self, name):
        for configuration in self.instances.configurations.getconfiguration():
            if configuration.getname() == name:
                return configuration
        return None
    setattr(cls, "getconfiguration", getconfiguration)

    def addconfiguration(self, name):
        for configuration in self.instances.configurations.getconfiguration():
            if configuration.getname() == name:
                raise ValueError, _("\"%s\" configuration already exists !!!")%name
        new_configuration = PLCOpenClasses["configurations_configuration"]()
        new_configuration.setname(name)
        self.instances.configurations.appendconfiguration(new_configuration)
    setattr(cls, "addconfiguration", addconfiguration)    

    def removeconfiguration(self, name):
        found = False
        for idx, configuration in enumerate(self.instances.configurations.getconfiguration()):
            if configuration.getname() == name:
                self.instances.configurations.removeconfiguration(idx)
                found = True
                break
        if not found:
            raise ValueError, ("\"%s\" configuration doesn't exist !!!")%name
    setattr(cls, "removeconfiguration", removeconfiguration)

    def getconfigurationResource(self, config_name, name):
        configuration = self.getconfiguration(config_name)
        if configuration:
            for resource in configuration.getresource():
                if resource.getname() == name:
                    return resource
        return None
    setattr(cls, "getconfigurationResource", getconfigurationResource)

    def addconfigurationResource(self, config_name, name):
        configuration = self.getconfiguration(config_name)
        if configuration:
            for resource in configuration.getresource():
                if resource.getname() == name:
                    raise ValueError, _("\"%s\" resource already exists in \"%s\" configuration !!!")%(name, config_name)
            new_resource = PLCOpenClasses["configuration_resource"]()
            new_resource.setname(name)
            configuration.appendresource(new_resource)
    setattr(cls, "addconfigurationResource", addconfigurationResource)

    def removeconfigurationResource(self, config_name, name):
        configuration = self.getconfiguration(config_name)
        if configuration:
            found = False
            for idx, resource in enumerate(configuration.getresource()):
                if resource.getname() == name:
                    configuration.removeresource(idx)
                    found = True
                    break
            if not found:
                raise ValueError, _("\"%s\" resource doesn't exist in \"%s\" configuration !!!")%(name, config_name)
    setattr(cls, "removeconfigurationResource", removeconfigurationResource)

    def updateElementName(self, old_name, new_name):
        for datatype in self.types.getdataTypeElements():
            datatype.updateElementName(old_name, new_name)
        for pou in self.types.getpouElements():
            pou.updateElementName(old_name, new_name)
        for configuration in self.instances.configurations.getconfiguration():
            configuration.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, old_leading, new_leading):
        address_model = re.compile(FILTER_ADDRESS_MODEL % old_leading)
        for pou in self.types.getpouElements():
            pou.updateElementAddress(address_model, new_leading)
        for configuration in self.instances.configurations.getconfiguration():
            configuration.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def removeVariableByAddress(self, address):
        for pou in self.types.getpouElements():
            pou.removeVariableByAddress(address)
        for configuration in self.instances.configurations.getconfiguration():
            configuration.removeVariableByAddress(address)
    setattr(cls, "removeVariableByAddress", removeVariableByAddress)

    def removeVariableByFilter(self, leading):
        address_model = re.compile(FILTER_ADDRESS_MODEL % leading)
        for pou in self.types.getpouElements():
            pou.removeVariableByFilter(address_model)
        for configuration in self.instances.configurations.getconfiguration():
            configuration.removeVariableByFilter(address_model)
    setattr(cls, "removeVariableByFilter", removeVariableByFilter)

    def RefreshDataTypeHierarchy(self):
        self.EnumeratedDataTypeValues = {}
        self.CustomDataTypeRange = {}
        self.CustomTypeHierarchy = {}
        for datatype in self.getdataTypes():
            self.AddCustomDataType(datatype)
    setattr(cls, "RefreshDataTypeHierarchy", RefreshDataTypeHierarchy)

    def AddCustomDataType(self, datatype):
        name = datatype.getname()
        basetype_content = datatype.getbaseType().getcontent()
        if basetype_content["value"] is None:
            self.CustomTypeHierarchy[name] = basetype_content["name"]
        elif basetype_content["name"] in ["string", "wstring"]:
            self.CustomTypeHierarchy[name] = basetype_content["name"].upper()
        elif basetype_content["name"] == "derived":
            self.CustomTypeHierarchy[name] = basetype_content["value"].getname()
        elif basetype_content["name"] in ["subrangeSigned", "subrangeUnsigned"]:
            range = (basetype_content["value"].range.getlower(), 
                     basetype_content["value"].range.getupper())
            self.CustomDataTypeRange[name] = range
            base_type = basetype_content["value"].baseType.getcontent()
            if base_type["value"] is None:
                self.CustomTypeHierarchy[name] = base_type["name"]
            else:
                self.CustomTypeHierarchy[name] = base_type["value"].getname()
        else:
            if basetype_content["name"] == "enum":
                values = []
                for value in basetype_content["value"].values.getvalue():
                    values.append(value.getname())
                self.EnumeratedDataTypeValues[name] = values
            self.CustomTypeHierarchy[name] = "ANY_DERIVED"
    setattr(cls, "AddCustomDataType", AddCustomDataType)

    # Update Block types with user-defined pou added
    def RefreshCustomBlockTypes(self):
        # Reset the tree of user-defined pou cross-use
        self.CustomBlockTypes = []
        for pou in self.getpous():
            self.AddCustomBlockType(pou)
    setattr(cls, "RefreshCustomBlockTypes", RefreshCustomBlockTypes)

    def AddCustomBlockType(self, pou): 
        pou_name = pou.getname()
        pou_type = pou.getpouType()
        block_infos = {"name" : pou_name, "type" : pou_type, "extensible" : False,
                       "inputs" : [], "outputs" : [], "comment" : pou.getdescription(),
                       "generate" : generate_block, "initialise" : initialise_block}
        if pou.getinterface():
            return_type = pou.interface.getreturnType()
            if return_type:
                var_type = return_type.getcontent()
                if var_type["name"] == "derived":
                    block_infos["outputs"].append(("OUT", var_type["value"].getname(), "none"))
                elif var_type["name"] in ["string", "wstring"]:
                    block_infos["outputs"].append(("OUT", var_type["name"].upper(), "none"))
                else:
                    block_infos["outputs"].append(("OUT", var_type["name"], "none"))
            for type, varlist in pou.getvars():
                if type == "InOut":
                    for var in varlist.getvariable():
                        var_type = var.type.getcontent()
                        if var_type["name"] == "derived":
                            block_infos["inputs"].append((var.getname(), var_type["value"].getname(), "none"))
                            block_infos["outputs"].append((var.getname(), var_type["value"].getname(), "none"))
                        elif var_type["name"] in ["string", "wstring"]:
                            block_infos["inputs"].append((var.getname(), var_type["name"].upper(), "none"))
                            block_infos["outputs"].append((var.getname(), var_type["name"].upper(), "none"))
                        else:
                            block_infos["inputs"].append((var.getname(), var_type["name"], "none"))
                            block_infos["outputs"].append((var.getname(), var_type["name"], "none"))
                elif type == "Input":
                    for var in varlist.getvariable():
                        var_type = var.type.getcontent()
                        if var_type["name"] == "derived":
                            block_infos["inputs"].append((var.getname(), var_type["value"].getname(), "none"))
                        elif var_type["name"] in ["string", "wstring"]:
                            block_infos["inputs"].append((var.getname(), var_type["name"].upper(), "none"))
                        else:
                            block_infos["inputs"].append((var.getname(), var_type["name"], "none"))
                elif type == "Output":
                    for var in varlist.getvariable():
                        var_type = var.type.getcontent()
                        if var_type["name"] == "derived":
                            block_infos["outputs"].append((var.getname(), var_type["value"].getname(), "none"))
                        elif var_type["name"] in ["string", "wstring"]:
                            block_infos["outputs"].append((var.getname(), var_type["name"].upper(), "none"))
                        else:
                            block_infos["outputs"].append((var.getname(), var_type["name"], "none"))    
        block_infos["usage"] = "\n (%s) => (%s)" % (", ".join(["%s:%s" % (input[1], input[0]) for input in block_infos["inputs"]]),
                                                    ", ".join(["%s:%s" % (output[1], output[0]) for output in block_infos["outputs"]]))
        self.CustomBlockTypes.append(block_infos)
    setattr(cls, "AddCustomBlockType", AddCustomBlockType)

    def RefreshElementUsingTree(self):
        # Reset the tree of user-defined element cross-use
        self.ElementUsingTree = {}
        pous = self.getpous()
        datatypes = self.getdataTypes()
        # Reference all the user-defined elementu names and initialize the tree of 
        # user-defined elemnt cross-use
        elementnames = [datatype.getname() for datatype in datatypes] + \
                       [pou.getname() for pou in pous]
        for name in elementnames:
            self.ElementUsingTree[name] = []
        # Analyze each datatype
        for datatype in datatypes:
            name = datatype.getname()
            basetype_content = datatype.baseType.getcontent()
            if basetype_content["name"] == "derived":
                typename = basetype_content["value"].getname()
                if name in self.ElementUsingTree[typename]:
                    self.ElementUsingTree[typename].append(name)
            elif basetype_content["name"] in ["subrangeSigned", "subrangeUnsigned", "array"]:
                base_type = basetype_content["value"].baseType.getcontent()
                if base_type["name"] == "derived":
                    typename = base_type["value"].getname()
                    if self.ElementUsingTree.has_key(typename) and name not in self.ElementUsingTree[typename]:
                        self.ElementUsingTree[typename].append(name)
            elif basetype_content["name"] == "struct":
                for element in basetype_content["value"].getvariable():
                    type_content = element.type.getcontent()
                    if type_content["name"] == "derived":
                        typename = type_content["value"].getname()
                        if self.ElementUsingTree.has_key(typename) and name not in self.ElementUsingTree[typename]:
                            self.ElementUsingTree[typename].append(name)
        # Analyze each pou
        for pou in pous:
            name = pou.getname()
            if pou.interface:
                # Extract variables from every varLists
                for type, varlist in pou.getvars():
                    for var in varlist.getvariable():
                        vartype_content = var.gettype().getcontent()
                        if vartype_content["name"] == "derived":
                            typename = vartype_content["value"].getname()
                            if self.ElementUsingTree.has_key(typename) and name not in self.ElementUsingTree[typename]:
                                self.ElementUsingTree[typename].append(name)
    setattr(cls, "RefreshElementUsingTree", RefreshElementUsingTree)

    def GetParentType(self, type):
        if self.CustomTypeHierarchy.has_key(type):
            return self.CustomTypeHierarchy[type]
        elif TypeHierarchy.has_key(type):
            return TypeHierarchy[type]
        return None
    setattr(cls, "GetParentType", GetParentType)

    def GetBaseType(self, type):
        parent_type = self.GetParentType(type)
        if parent_type is not None:
            if parent_type.startswith("ANY"):
                return type
            else:
                return self.GetBaseType(parent_type)
        return None
    setattr(cls, "GetBaseType", GetBaseType)

    def GetSubrangeBaseTypes(self, exclude):
        derived = []
        for type in self.CustomTypeHierarchy.keys():
            for base_type in DataTypeRange.keys():
                if self.IsOfType(type, base_type) and not self.IsOfType(type, exclude):
                    derived.append(type)
                    break
        return derived
    setattr(cls, "GetSubrangeBaseTypes", GetSubrangeBaseTypes)

    """
    returns true if the given data type is the same that "reference" meta-type or one of its types.
    """
    def IsOfType(self, type, reference):
        if reference is None:
            return True
        elif type == reference:
            return True
        else:
            parent_type = self.GetParentType(type)
            if parent_type is not None:
                return self.IsOfType(parent_type, reference)
        return False
    setattr(cls, "IsOfType", IsOfType)

    # Return if pou given by name is used by another pou
    def ElementIsUsed(self, name):
        if self.ElementUsingTree.has_key(name):
            return len(self.ElementUsingTree[name]) > 0
        return False
    setattr(cls, "ElementIsUsed", ElementIsUsed)

    def DataTypeIsDerived(self, name):
        return name in self.CustomTypeHierarchy.values()
    setattr(cls, "DataTypeIsDerived", DataTypeIsDerived)

    # Return if pou given by name is directly or undirectly used by the reference pou
    def ElementIsUsedBy(self, name, reference):
        if self.ElementUsingTree.has_key(name):
            list = self.ElementUsingTree[name]
            # Test if pou is directly used by reference
            if reference in list:
                return True
            else:
                # Test if pou is undirectly used by reference, by testing if pous 
                # that directly use pou is directly or undirectly used by reference
                used = False
                for element in list:
                    used |= self.ElementIsUsedBy(element, reference)
                return used
        return False
    setattr(cls, "ElementIsUsedBy", ElementIsUsedBy)

    def GetDataTypeRange(self, type):
        if self.CustomDataTypeRange.has_key(type):
            return self.CustomDataTypeRange[type]
        elif DataTypeRange.has_key(type):
            return DataTypeRange[type]
        else:
            parent_type = self.GetParentType(type)
            if parent_type is not None:
                return self.GetDataTypeRange(parent_type)
        return None
    setattr(cls, "GetDataTypeRange", GetDataTypeRange)

    def GetEnumeratedDataTypeValues(self, type = None):
        if type is None:
            all_values = []
            for values in self.EnumeratedDataTypeValues.values():
                all_values.extend(values)
            return all_values
        elif self.EnumeratedDataTypeValues.has_key(type):
            return self.EnumeratedDataTypeValues[type]
        return []
    setattr(cls, "GetEnumeratedDataTypeValues", GetEnumeratedDataTypeValues)

    # Function that returns the block definition associated to the block type given
    def GetCustomBlockType(self, type, inputs = None):
        for customblocktype in self.CustomBlockTypes:
            if inputs is not None and inputs != "undefined":
                customblock_inputs = tuple([var_type for name, var_type, modifier in customblocktype["inputs"]])
                same_inputs = inputs == customblock_inputs
            else:
                same_inputs = True
            if customblocktype["name"] == type and same_inputs:
                return customblocktype
        return None
    setattr(cls, "GetCustomBlockType", GetCustomBlockType)

    # Return Block types checking for recursion
    def GetCustomBlockTypes(self, exclude = "", onlyfunctions = False):
        type = None
        if exclude != "":
            pou = self.getpou(exclude)
            if pou is not None:
                type = pou.getpouType()
        customblocktypes = []
        for customblocktype in self.CustomBlockTypes:
            if customblocktype["type"] != "program" and customblocktype["name"] != exclude and not self.ElementIsUsedBy(exclude, customblocktype["name"]) and not (onlyfunctions and customblocktype["type"] != "function"):
                customblocktypes.append(customblocktype)
        return customblocktypes
    setattr(cls, "GetCustomBlockTypes", GetCustomBlockTypes)

    # Return Function Block types checking for recursion
    def GetCustomFunctionBlockTypes(self, exclude = ""):
        customblocktypes = []
        for customblocktype in self.CustomBlockTypes:
            if customblocktype["type"] == "functionBlock" and customblocktype["name"] != exclude and not self.ElementIsUsedBy(exclude, customblocktype["name"]):
                customblocktypes.append(customblocktype["name"])
        return customblocktypes
    setattr(cls, "GetCustomFunctionBlockTypes", GetCustomFunctionBlockTypes)

    # Return Block types checking for recursion
    def GetCustomBlockResource(self):
        customblocktypes = []
        for customblocktype in self.CustomBlockTypes:
            if customblocktype["type"] == "program":
                customblocktypes.append(customblocktype["name"])
        return customblocktypes
    setattr(cls, "GetCustomBlockResource", GetCustomBlockResource)

    # Return Data Types checking for recursion
    def GetCustomDataTypes(self, exclude = "", only_locatable = False):
        customdatatypes = []
        for customdatatype in self.getdataTypes():
            if not only_locatable or self.IsLocatableType(customdatatype):
                customdatatype_name = customdatatype.getname()
                if customdatatype_name != exclude and not self.ElementIsUsedBy(exclude, customdatatype_name):
                    customdatatypes.append({"name": customdatatype_name, "infos": customdatatype})
        return customdatatypes
    setattr(cls, "GetCustomDataTypes", GetCustomDataTypes)

    # Return if Data Type can be used for located variables
    def IsLocatableType(self, datatype):
        basetype_content = datatype.baseType.getcontent()
        if basetype_content["name"] in ["enum", "struct"]:
            return False
        elif basetype_content["name"] == "derived":
            base_type = self.getdataType(basetype_content["value"].getname())
            if base_type is not None:
                return self.IsLocatableType(base_type)
        elif basetype_content["name"] == "array":
            array_base_type = basetype_content["value"].baseType.getcontent()
            if array_base_type["value"] is not None and array_base_type["name"] not in ["string", "wstring"]:
                base_type = self.getdataType(array_base_type["value"].getname())
                if base_type is not None:
                    return self.IsLocatableType(base_type)
        return True
    setattr(cls, "IsLocatableType", IsLocatableType)

    def Search(self, criteria, parent_infos=[]):
        result = self.types.Search(criteria, parent_infos)
        for configuration in self.instances.configurations.getconfiguration():
            result.extend(configuration.Search(criteria, parent_infos))
        return result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("project_fileHeader", None)
if cls:
    cls.singleLineAttributes = False

cls = PLCOpenClasses.get("project_contentHeader", None)
if cls:
    cls.singleLineAttributes = False
    
    def setpageSize(self, width, height):
        self.coordinateInfo.setpageSize(width, height)
    setattr(cls, "setpageSize", setpageSize)
    
    def getpageSize(self):
        return self.coordinateInfo.getpageSize()
    setattr(cls, "getpageSize", getpageSize)

    def setscaling(self, scaling):
        for language, (x, y) in scaling.items():
            self.coordinateInfo.setscaling(language, x, y)
    setattr(cls, "setscaling", setscaling)
    
    def getscaling(self):
        scaling = {}
        scaling["FBD"] = self.coordinateInfo.getscaling("FBD")
        scaling["LD"] = self.coordinateInfo.getscaling("LD")
        scaling["SFC"] = self.coordinateInfo.getscaling("SFC")
        return scaling
    setattr(cls, "getscaling", getscaling)

cls = PLCOpenClasses.get("contentHeader_coordinateInfo", None)
if cls:
    def setpageSize(self, width, height):
        if width == 0 and height == 0:
            self.deletepageSize()
        else:
            if self.pageSize is None:
                self.addpageSize()
            self.pageSize.setx(width)
            self.pageSize.sety(height)
    setattr(cls, "setpageSize", setpageSize)
    
    def getpageSize(self):
        if self.pageSize is not None:
            return self.pageSize.getx(), self.pageSize.gety()
        return 0, 0
    setattr(cls, "getpageSize", getpageSize)

    def setscaling(self, language, x, y):
        if language == "FBD":
            self.fbd.scaling.setx(x)
            self.fbd.scaling.sety(y)
        elif language == "LD":
            self.ld.scaling.setx(x)
            self.ld.scaling.sety(y)
        elif language == "SFC":
            self.sfc.scaling.setx(x)
            self.sfc.scaling.sety(y)
    setattr(cls, "setscaling", setscaling)
    
    def getscaling(self, language):
        if language == "FBD":
            return self.fbd.scaling.getx(), self.fbd.scaling.gety()
        elif language == "LD":
            return self.ld.scaling.getx(), self.ld.scaling.gety()
        elif language == "SFC":
            return self.sfc.scaling.getx(), self.sfc.scaling.gety()
        return 0, 0
    setattr(cls, "getscaling", getscaling)

def _Search(attributes, criteria, parent_infos):
    search_result = []
    for attr, value in attributes:
        if value is not None:
            search_result.extend([(tuple(parent_infos + [attr]),) + result for result in TestTextElement(value, criteria)])
    return search_result

def _updateConfigurationResourceElementName(self, old_name, new_name):
    for varlist in self.getglobalVars():
        for var in varlist.getvariable():
            var_address = var.getaddress()
            if var_address is not None:
                if var_address == old_name:
                    var.setaddress(new_name)
                if var.getname() == old_name:
                    var.setname(new_name)

def _updateConfigurationResourceElementAddress(self, address_model, new_leading):
    for varlist in self.getglobalVars():
        for var in varlist.getvariable():
            var_address = var.getaddress()
            if var_address is not None:
                var.setaddress(update_address(var_address, address_model, new_leading))

def _removeConfigurationResourceVariableByAddress(self, address):
    for varlist in self.getglobalVars():
        variables = varlist.getvariable()
        for i in xrange(len(variables)-1, -1, -1):
            if variables[i].getaddress() == address:
                variables.pop(i)

def _removeConfigurationResourceVariableByFilter(self, address_model):
    for varlist in self.getglobalVars():
        variables = varlist.getvariable()
        for i in xrange(len(variables)-1, -1, -1):
            var_address = variables[i].getaddress()
            if var_address is not None:
                result = address_model.match(var_address)
                if result is not None:
                    variables.pop(i)

def _SearchInConfigurationResource(self, criteria, parent_infos=[]):
    search_result = _Search([("name", self.getname())], criteria, parent_infos)
    var_number = 0
    for varlist in self.getglobalVars():
        variable_type = searchResultVarTypes.get("globalVars", "var_local")
        variables = varlist.getvariable()
        for modifier, has_modifier in [("constant", varlist.getconstant()),
                                       ("retain", varlist.getretain()),
                                       ("non_retain", varlist.getnonretain())]:
            if has_modifier:
                for result in TestTextElement(modifier, criteria):
                    search_result.append((tuple(parent_infos + [variable_type, (var_number, var_number + len(variables)), modifier]),) + result)
                break
        for variable in variables:
            search_result.extend(variable.Search(criteria, parent_infos + [variable_type, var_number]))
            var_number += 1
    return search_result

cls = PLCOpenClasses.get("configurations_configuration", None)
if cls:
    def updateElementName(self, old_name, new_name):
        _updateConfigurationResourceElementName(self, old_name, new_name)
        for resource in self.getresource():
            resource.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        _updateConfigurationResourceElementAddress(self, address_model, new_leading)
        for resource in self.getresource():
            resource.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    setattr(cls, "removeVariableByAddress", _removeConfigurationResourceVariableByAddress)
    setattr(cls, "removeVariableByFilter", _removeConfigurationResourceVariableByFilter)

    def Search(self, criteria, parent_infos=[]):
        search_result = []
        parent_infos = parent_infos + ["C::%s" % self.getname()]
        filter = criteria["filter"]
        if filter == "all" or "configuration" in filter:
            search_result = _SearchInConfigurationResource(self, criteria, parent_infos)
            for resource in self.getresource():
                search_result.extend(resource.Search(criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)
    
cls = PLCOpenClasses.get("configuration_resource", None)
if cls:
    def updateElementName(self, old_name, new_name):
        _updateConfigurationResourceElementName(self, old_name, new_name)
        for instance in self.getpouInstance():
            instance.updateElementName(old_name, new_name)
        for task in self.gettask():
            task.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        _updateConfigurationResourceElementAddress(self, address_model, new_leading)
        for task in self.gettask():
            task.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    setattr(cls, "removeVariableByAddress", _removeConfigurationResourceVariableByAddress)
    setattr(cls, "removeVariableByFilter", _removeConfigurationResourceVariableByFilter)

    def Search(self, criteria, parent_infos=[]):
        parent_infos = parent_infos[:-1] + ["R::%s::%s" % (parent_infos[-1].split("::")[1], self.getname())]
        search_result = _SearchInConfigurationResource(self, criteria, parent_infos)
        task_number = 0
        instance_number = 0
        for task in self.gettask():
            results = TestTextElement(task.getname(), criteria)
            for result in results:
                search_result.append((tuple(parent_infos + ["task", task_number, "name"]),) + result)
            search_result.extend(task.Search(criteria, parent_infos + ["task", task_number]))
            task_number += 1
            for instance in task.getpouInstance():
                search_result.extend(task.Search(criteria, parent_infos + ["instance", instance_number]))
                for result in results:
                    search_result.append((tuple(parent_infos + ["instance", instance_number, "task"]),) + result)
                instance_number += 1
        for instance in self.getpouInstance():
            search_result.extend(instance.Search(criteria, parent_infos + ["instance", instance_number]))
            instance_number += 1
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("resource_task", None)
if cls:
    def compatibility(self, tree):
        if tree.hasAttribute("interval"):
            interval = GetAttributeValue(tree._attrs["interval"])
            result = time_model.match(interval)
            if result is not None:
                values = result.groups()
                time_values = [int(v) for v in values[:2]]
                seconds = float(values[2])
                time_values.extend([int(seconds), int((seconds % 1) * 1000000)])
                text = "t#"
                if time_values[0] != 0:
                    text += "%dh"%time_values[0]
                if time_values[1] != 0:
                    text += "%dm"%time_values[1]
                if time_values[2] != 0:
                    text += "%ds"%time_values[2]
                if time_values[3] != 0:
                    if time_values[3] % 1000 != 0:
                        text += "%.3fms"%(float(time_values[3]) / 1000)
                    else:
                        text += "%dms"%(time_values[3] / 1000)
                NodeSetAttr(tree, "interval", text)
    setattr(cls, "compatibility", compatibility)
    
    def updateElementName(self, old_name, new_name):
        if self.single == old_name:
            self.single = new_name
        if self.interval == old_name:
            self.interval = new_name
        for instance in self.getpouInstance():
            instance.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        if self.single is not None:
            self.single = update_address(self.single, address_model, new_leading)
        if self.interval is not None:
            self.interval = update_address(self.interval, address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def Search(self, criteria, parent_infos=[]):
        return _Search([("single", self.getsingle()), 
                        ("interval", self.getinterval()),
                        ("priority", str(self.getpriority()))],
                       criteria, parent_infos)
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("pouInstance", None)
if cls:
    def compatibility(self, tree):
        if tree.hasAttribute("type"):
            NodeRenameAttr(tree, "type", "typeName")
    setattr(cls, "compatibility", compatibility)
    
    def updateElementName(self, old_name, new_name):
        if self.typeName == old_name:
            self.typeName = new_name
    setattr(cls, "updateElementName", updateElementName)

    def Search(self, criteria, parent_infos=[]):
        return _Search([("name", self.getname()), 
                        ("type", self.gettypeName())],
                       criteria, parent_infos)
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("varListPlain_variable", None)
if cls:
    def gettypeAsText(self):
        vartype_content = self.gettype().getcontent()
        # Variable type is a user data type
        if vartype_content["name"] == "derived":
            return vartype_content["value"].getname()
        # Variable type is a string type
        elif vartype_content["name"] in ["string", "wstring"]:
            return vartype_content["name"].upper()
        # Variable type is an array
        elif vartype_content["name"] == "array":
            base_type = vartype_content["value"].baseType.getcontent()
            # Array derived directly from a user defined type 
            if base_type["name"] == "derived":
                basetype_name = base_type["value"].getname()
            # Array derived directly from a string type 
            elif base_type["name"] in ["string", "wstring"]:
                basetype_name = base_type["name"].upper()
            # Array derived directly from an elementary type 
            else:
                basetype_name = base_type["name"]
            return "ARRAY [%s] OF %s" % (",".join(map(lambda x : "%s..%s" % (x.getlower(), x.getupper()), vartype_content["value"].getdimension())), basetype_name)
        # Variable type is an elementary type
        return vartype_content["name"]
    setattr(cls, "gettypeAsText", gettypeAsText)
    
    def Search(self, criteria, parent_infos=[]):
        search_result = _Search([("name", self.getname()), 
                                 ("type", self.gettypeAsText()),
                                 ("location", self.getaddress())],
                                criteria, parent_infos)
        initial = self.getinitialValue()
        if initial is not None:
            search_result.extend(_Search([("initial value", initial.getvalue())], criteria, parent_infos))
        doc = self.getdocumentation()
        if doc is not None:
            search_result.extend(doc.Search(criteria, parent_infos + ["documentation"]))
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("project_types", None)
if cls:
    def getdataTypeElements(self):
        return self.dataTypes.getdataType()
    setattr(cls, "getdataTypeElements", getdataTypeElements)
    
    def getdataTypeElement(self, name):
        elements = self.dataTypes.getdataType()
        for element in elements:
            if element.getname() == name:
                return element
        return None
    setattr(cls, "getdataTypeElement", getdataTypeElement)

    def appenddataTypeElement(self, name):
        new_datatype = PLCOpenClasses["dataTypes_dataType"]()
        new_datatype.setname(name)
        new_datatype.baseType.setcontent({"name" : "BOOL", "value" : None})
        self.dataTypes.appenddataType(new_datatype)
    setattr(cls, "appenddataTypeElement", appenddataTypeElement)
    
    def insertdataTypeElement(self, index, dataType):
        self.dataTypes.insertdataType(index, dataType)
    setattr(cls, "insertdataTypeElement", insertdataTypeElement)
    
    def removedataTypeElement(self, name):
        found = False
        for idx, element in enumerate(self.dataTypes.getdataType()):
            if element.getname() == name:
                self.dataTypes.removedataType(idx)
                found = True
                break
        if not found:
            raise ValueError, _("\"%s\" Data Type doesn't exist !!!")%name
    setattr(cls, "removedataTypeElement", removedataTypeElement)
    
    def getpouElements(self):
        return self.pous.getpou()
    setattr(cls, "getpouElements", getpouElements)
    
    def getpouElement(self, name):
        elements = self.pous.getpou()
        for element in elements:
            if element.getname() == name:
                return element
        return None
    setattr(cls, "getpouElement", getpouElement)

    def appendpouElement(self, name, pou_type, body_type):
        for element in self.pous.getpou():
            if element.getname() == name:
                raise ValueError, _("\"%s\" POU already exists !!!")%name
        new_pou = PLCOpenClasses["pous_pou"]()
        new_pou.setname(name)
        new_pou.setpouType(pou_type)
        new_pou.appendbody(PLCOpenClasses["body"]())
        new_pou.setbodyType(body_type)
        self.pous.appendpou(new_pou)
    setattr(cls, "appendpouElement", appendpouElement)
        
    def insertpouElement(self, index, pou):
        self.pous.insertpou(index, pou)
    setattr(cls, "insertpouElement", insertpouElement)
    
    def removepouElement(self, name):
        found = False
        for idx, element in enumerate(self.pous.getpou()):
            if element.getname() == name:
                self.pous.removepou(idx)
                found = True
                break
        if not found:
            raise ValueError, _("\"%s\" POU doesn't exist !!!")%name
    setattr(cls, "removepouElement", removepouElement)

    def Search(self, criteria, parent_infos=[]):
        search_result = []
        filter = criteria["filter"]
        for datatype in self.dataTypes.getdataType():
            search_result.extend(datatype.Search(criteria, parent_infos))
        for pou in self.pous.getpou():
            search_result.extend(pou.Search(criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

def _updateBaseTypeElementName(self, old_name, new_name):
    self.baseType.updateElementName(old_name, new_name)

cls = PLCOpenClasses.get("dataTypes_dataType", None)
if cls:
    setattr(cls, "updateElementName", _updateBaseTypeElementName)
    
    def Search(self, criteria, parent_infos=[]):
        search_result = []
        filter = criteria["filter"]
        if filter == "all" or "datatype" in filter:
            parent_infos = parent_infos + ["D::%s" % self.getname()]
            search_result.extend(_Search([("name", self.getname())], criteria, parent_infos))
            search_result.extend(self.baseType.Search(criteria, parent_infos))
            if self.initialValue is not None:
                search_result.extend(_Search([("initial", self.initialValue.getvalue())], criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("dataType", None)
if cls:
    
    def updateElementName(self, old_name, new_name):
        if self.content["name"] in ["derived", "array", "subrangeSigned", "subrangeUnsigned"]:
            self.content["value"].updateElementName(old_name, new_name)
        elif self.content["name"] == "struct":
            for element in self.content["value"].getvariable():
                element_type = element.type.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def Search(self, criteria, parent_infos=[]):
        search_result = []
        if self.content["name"] in ["derived", "array", "enum", "subrangeSigned", "subrangeUnsigned"]:
            search_result.extend(self.content["value"].Search(criteria, parent_infos))
        elif self.content["name"] == "struct":
            for i, element in enumerate(self.content["value"].getvariable()):
                search_result.extend(element.Search(criteria, parent_infos + ["struct", i]))
        else:
            basetype = self.content["name"]
            if basetype in ["string", "wstring"]:
                basetype = basetype.upper()
            search_result.extend(_Search([("base", basetype)], criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("derivedTypes_array", None)
if cls:
    setattr(cls, "updateElementName", _updateBaseTypeElementName)
    
    def Search(self, criteria, parent_infos=[]):
        search_result = self.baseType.Search(criteria, parent_infos)
        for i, dimension in enumerate(self.getdimension()):
            search_result.extend(_Search([("lower", dimension.getlower()),
                                          ("upper", dimension.getupper())],
                                         criteria, parent_infos + ["range", i]))
        return search_result
    setattr(cls, "Search", Search)

def _SearchInSubrange(self, criteria, parent_infos=[]):
    search_result = self.baseType.Search(criteria, parent_infos)
    search_result.extend(_Search([("lower", self.range.getlower()),
                                  ("upper", self.range.getupper())],
                                 criteria, parent_infos))
    return search_result

cls = PLCOpenClasses.get("derivedTypes_subrangeSigned", None)
if cls:
    setattr(cls, "updateElementName", _updateBaseTypeElementName)
    setattr(cls, "Search", _SearchInSubrange)

cls = PLCOpenClasses.get("derivedTypes_subrangeUnsigned", None)
if cls:
    setattr(cls, "updateElementName", _updateBaseTypeElementName)
    setattr(cls, "Search", _SearchInSubrange)

cls = PLCOpenClasses.get("derivedTypes_enum", None)
if cls:
    
    def updateElementName(self, old_name, new_name):
        pass
    setattr(cls, "updateElementName", updateElementName)
    
    def Search(self, criteria, parent_infos=[]):
        search_result = []
        for i, value in enumerate(self.values.getvalue()):
            for result in TestTextElement(value.getname(), criteria):
                search_result.append((tuple(parent_infos + ["value", i]),) + result)
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("pous_pou", None)
if cls:
    
    def setdescription(self, description):
        doc = self.getdocumentation()
        if doc is None:
            doc = PLCOpenClasses["formattedText"]()
            self.setdocumentation(doc)
        doc.settext(description)
    setattr(cls, "setdescription", setdescription)
    
    def getdescription(self):
        doc = self.getdocumentation()
        if doc is not None:
            return doc.gettext()
        return ""
    setattr(cls, "getdescription", getdescription)
    
    def setbodyType(self, type):
        if len(self.body) > 0:
            if type == "IL":
                self.body[0].setcontent({"name" : "IL", "value" : PLCOpenClasses["formattedText"]()})
            elif type == "ST":
                self.body[0].setcontent({"name" : "ST", "value" : PLCOpenClasses["formattedText"]()})
            elif type == "LD":
                self.body[0].setcontent({"name" : "LD", "value" : PLCOpenClasses["body_LD"]()})
            elif type == "FBD":
                self.body[0].setcontent({"name" : "FBD", "value" : PLCOpenClasses["body_FBD"]()})
            elif type == "SFC":
                self.body[0].setcontent({"name" : "SFC", "value" : PLCOpenClasses["body_SFC"]()})
            else:
                raise ValueError, "%s isn't a valid body type!"%type
    setattr(cls, "setbodyType", setbodyType)
    
    def getbodyType(self):
        if len(self.body) > 0:
            return self.body[0].getcontent()["name"]
    setattr(cls, "getbodyType", getbodyType)
    
    def resetexecutionOrder(self):
        if len(self.body) > 0:
            self.body[0].resetexecutionOrder()
    setattr(cls, "resetexecutionOrder", resetexecutionOrder)
    
    def compileexecutionOrder(self):
        if len(self.body) > 0:
            self.body[0].compileexecutionOrder()
    setattr(cls, "compileexecutionOrder", compileexecutionOrder)
    
    def setelementExecutionOrder(self, instance, new_executionOrder):
        if len(self.body) > 0:
            self.body[0].setelementExecutionOrder(instance, new_executionOrder)
    setattr(cls, "setelementExecutionOrder", setelementExecutionOrder)
    
    def addinstance(self, name, instance):
        if len(self.body) > 0:
            self.body[0].appendcontentInstance(name, instance)
    setattr(cls, "addinstance", addinstance)
    
    def getinstances(self):
        if len(self.body) > 0:
            return self.body[0].getcontentInstances()
        return []
    setattr(cls, "getinstances", getinstances)
    
    def getinstance(self, id):
        if len(self.body) > 0:
            return self.body[0].getcontentInstance(id)
        return None
    setattr(cls, "getinstance", getinstance)
    
    def getrandomInstance(self, exclude):
        if len(self.body) > 0:
            return self.body[0].getcontentRandomInstance(exclude)
        return None
    setattr(cls, "getrandomInstance", getrandomInstance)
    
    def getinstanceByName(self, name):
        if len(self.body) > 0:
            return self.body[0].getcontentInstanceByName(name)
        return None
    setattr(cls, "getinstanceByName", getinstanceByName)
    
    def removeinstance(self, id):
        if len(self.body) > 0:
            self.body[0].removecontentInstance(id)
    setattr(cls, "removeinstance", removeinstance)
    
    def settext(self, text):
        if len(self.body) > 0:
            self.body[0].settext(text)
    setattr(cls, "settext", settext)
    
    def gettext(self):
        if len(self.body) > 0:
            return self.body[0].gettext()
        return ""
    setattr(cls, "gettext", gettext)

    def getvars(self):
        vars = []
        if self.interface is not None:
            reverse_types = {}
            for name, value in VarTypes.items():
                reverse_types[value] = name
            for varlist in self.interface.getcontent():
                vars.append((reverse_types[varlist["name"]], varlist["value"]))
        return vars
    setattr(cls, "getvars", getvars)
    
    def setvars(self, vars):
        if self.interface is None:
            self.interface = PLCOpenClasses["pou_interface"]()
        self.interface.setcontent([])
        for vartype, varlist in vars:
            self.interface.appendcontent({"name" : VarTypes[vartype], "value" : varlist})
    setattr(cls, "setvars", setvars)
    
    def addpouLocalVar(self, type, name, location="", description=""):
        self.addpouVar(type, name, location=location, description=description)
    setattr(cls, "addpouLocalVar", addpouLocalVar)
        
    def addpouExternalVar(self, type, name):
        self.addpouVar(type, name, "externalVars")
    setattr(cls, "addpouExternalVar", addpouExternalVar)
    
    def addpouVar(self, type, name, var_class="localVars", location="", description=""):
        if self.interface is None:
            self.interface = PLCOpenClasses["pou_interface"]()
        content = self.interface.getcontent()
        if len(content) == 0 or content[-1]["name"] != var_class:
            content.append({"name" : var_class, "value" : PLCOpenClasses["interface_%s" % var_class]()})
        else:
            varlist = content[-1]["value"]
            variables = varlist.getvariable()
            if varlist.getconstant() or varlist.getretain() or len(variables) > 0 and variables[0].getaddress():
                content.append({"name" : var_class, "value" : PLCOpenClasses["interface_%s" % var_class]()})
        var = PLCOpenClasses["varListPlain_variable"]()
        var.setname(name)
        var_type = PLCOpenClasses["dataType"]()
        if type in [x for x,y in TypeHierarchy_list if not x.startswith("ANY")]:
            if type == "STRING":
                var_type.setcontent({"name" : "string", "value" : PLCOpenClasses["elementaryTypes_string"]()})
            elif type == "WSTRING":
                var_type.setcontent({"name" : "wstring", "value" : PLCOpenClasses["elementaryTypes_wstring"]()})
            else:
                var_type.setcontent({"name" : type, "value" : None})
        else:
            derived_type = PLCOpenClasses["derivedTypes_derived"]()
            derived_type.setname(type)
            var_type.setcontent({"name" : "derived", "value" : derived_type})
        var.settype(var_type)
        if location != "":
            var.setaddress(location)
        if description != "":
            ft = PLCOpenClasses["formattedText"]()
            ft.settext(description)
            var.setdocumentation(ft)
        
        content[-1]["value"].appendvariable(var)
    setattr(cls, "addpouVar", addpouVar)
    
    def changepouVar(self, old_type, old_name, new_type, new_name):
        if self.interface is not None:
            content = self.interface.getcontent()
            for varlist in content:
                variables = varlist["value"].getvariable()
                for var in variables:
                    if var.getname() == old_name:
                        vartype_content = var.gettype().getcontent()
                        if vartype_content["name"] == "derived" and vartype_content["value"].getname() == old_type:
                            var.setname(new_name)
                            vartype_content["value"].setname(new_type)
                            return
    setattr(cls, "changepouVar", changepouVar)
    
    def removepouVar(self, type, name):
        if self.interface is not None:
            content = self.interface.getcontent()
            for varlist in content:
                variables = varlist["value"].getvariable()
                for var in variables:
                    if var.getname() == name:
                        vartype_content = var.gettype().getcontent()
                        if vartype_content["name"] == "derived" and vartype_content["value"].getname() == type:
                            variables.remove(var)
                            break
                if len(varlist["value"].getvariable()) == 0:
                    content.remove(varlist)
                    break
    setattr(cls, "removepouVar", removepouVar)
    
    def hasblock(self, name):
        if name != "" and self.getbodyType() in ["FBD", "LD", "SFC"]:
            for instance in self.getinstances():
                if isinstance(instance, PLCOpenClasses["fbdObjects_block"]) and instance.getinstanceName() == name:
                    return True
            if self.transitions:
                for transition in self.transitions.gettransition():
                    result = transition.hasblock(name)
                    if result:
                        return result
            if self.actions:
                for action in self.actions.getaction():
                    result = action.hasblock(name)
                    if result:
                        return result
        return False
    setattr(cls, "hasblock", hasblock)
    
    def addtransition(self, name, type):
        if not self.transitions:
            self.addtransitions()
            self.transitions.settransition([])
        transition = PLCOpenClasses["transitions_transition"]()
        transition.setname(name)
        transition.setbodyType(type)
        if type == "ST":
            transition.settext(":= ;")
        elif type == "IL":
            transition.settext("\tST\t%s"%name)
        self.transitions.appendtransition(transition)
    setattr(cls, "addtransition", addtransition)
    
    def gettransition(self, name):
        if self.transitions:
            for transition in self.transitions.gettransition():
                if transition.getname() == name:
                    return transition
        return None
    setattr(cls, "gettransition", gettransition)
        
    def gettransitionList(self):
        if self.transitions:
            return self.transitions.gettransition()
        return []
    setattr(cls, "gettransitionList", gettransitionList)
    
    def removetransition(self, name):
        if self.transitions:
            transitions = self.transitions.gettransition()
            i = 0
            removed = False
            while i < len(transitions) and not removed:
                if transitions[i].getname() == name:
                    if transitions[i].getbodyType() in ["FBD", "LD", "SFC"]:
                        for instance in transitions[i].getinstances():
                            if isinstance(instance, PLCOpenClasses["fbdObjects_block"]):
                                self.removepouVar(instance.gettypeName(), 
                                                  instance.getinstanceName())
                    transitions.pop(i)
                    removed = True
                i += 1
            if not removed:
                raise ValueError, _("Transition with name %s doesn't exist!")%name
    setattr(cls, "removetransition", removetransition)

    def addaction(self, name, type):
        if not self.actions:
            self.addactions()
            self.actions.setaction([])
        action = PLCOpenClasses["actions_action"]()
        action.setname(name)
        action.setbodyType(type)
        self.actions.appendaction(action)
    setattr(cls, "addaction", addaction)
    
    def getaction(self, name):
        if self.actions:
            for action in self.actions.getaction():
                if action.getname() == name:
                    return action
        return None
    setattr(cls, "getaction", getaction)
    
    def getactionList(self):
        if self.actions:
            return self.actions.getaction()
        return []
    setattr(cls, "getactionList", getactionList)
    
    def removeaction(self, name):
        if self.actions:
            actions = self.actions.getaction()
            i = 0
            removed = False
            while i < len(actions) and not removed:
                if actions[i].getname() == name:
                    if actions[i].getbodyType() in ["FBD", "LD", "SFC"]:
                        for instance in actions[i].getinstances():
                            if isinstance(instance, PLCOpenClasses["fbdObjects_block"]):
                                self.removepouVar(instance.gettypeName(), 
                                                  instance.getinstanceName())
                    actions.pop(i)
                    removed = True
                i += 1
            if not removed:
                raise ValueError, _("Action with name %s doesn't exist!")%name
    setattr(cls, "removeaction", removeaction)

    def updateElementName(self, old_name, new_name):
        if self.interface:
            for content in self.interface.getcontent():
                for var in content["value"].getvariable():
                    var_address = var.getaddress()
                    if var_address is not None:
                        if var_address == old_name:
                            var.setaddress(new_name)
                        if var.getname() == old_name:
                            var.setname(new_name)
                    var_type_content = var.gettype().getcontent()
                    if var_type_content["name"] == "derived":
                        if var_type_content["value"].getname() == old_name:
                            var_type_content["value"].setname(new_name)
        self.body[0].updateElementName(old_name, new_name)
        for action in self.getactionList():
            action.updateElementName(old_name, new_name)
        for transition in self.gettransitionList():
            transition.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        if self.interface:
            for content in self.interface.getcontent():
                for var in content["value"].getvariable():
                    var_address = var.getaddress()
                    if var_address is not None:
                        var.setaddress(update_address(var_address, address_model, new_leading))
        self.body[0].updateElementAddress(address_model, new_leading)
        for action in self.getactionList():
            action.updateElementAddress(address_model, new_leading)
        for transition in self.gettransitionList():
            transition.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def removeVariableByAddress(self, address):
        if self.interface:
            for content in self.interface.getcontent():
                variables = content["value"].getvariable()
                for i in xrange(len(variables)-1, -1, -1):
                    if variables[i].getaddress() == address:
                        variables.pop(i)
    setattr(cls, "removeVariableByAddress", removeVariableByAddress)

    def removeVariableByFilter(self, address_model):
        if self.interface:
            for content in self.interface.getcontent():
                variables = content["value"].getvariable()
                for i in xrange(len(variables)-1, -1, -1):
                    var_address = variables[i].getaddress()
                    if var_address is not None:
                        result = address_model.match(var_address)
                        if result is not None:
                            variables.pop(i)
    setattr(cls, "removeVariableByFilter", removeVariableByFilter)
    
    def Search(self, criteria, parent_infos=[]):
        search_result = []
        filter = criteria["filter"]
        if filter == "all" or self.getpouType() in filter:
            parent_infos = parent_infos + ["P::%s" % self.getname()]
            search_result.extend(_Search([("name", self.getname())], criteria, parent_infos))
            if self.interface is not None:
                var_number = 0
                for content in self.interface.getcontent():
                    variable_type = searchResultVarTypes.get(content["value"], "var_local")
                    variables = content["value"].getvariable()
                    for modifier, has_modifier in [("constant", content["value"].getconstant()),
                                                   ("retain", content["value"].getretain()),
                                                   ("non_retain", content["value"].getnonretain())]:
                        if has_modifier:
                            for result in TestTextElement(modifier, criteria):
                                search_result.append((tuple(parent_infos + [variable_type, (var_number, var_number + len(variables)), modifier]),) + result)
                            break
                    for variable in variables:
                        search_result.extend(variable.Search(criteria, parent_infos + [variable_type, var_number]))
                        var_number += 1
            if len(self.body) > 0:
                search_result.extend(self.body[0].Search(criteria, parent_infos))
            for action in self.getactionList():
                search_result.extend(action.Search(criteria, parent_infos))
            for transition in self.gettransitionList():
                search_result.extend(transition.Search(criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

def setbodyType(self, type):
    if type == "IL":
        self.body.setcontent({"name" : "IL", "value" : PLCOpenClasses["formattedText"]()})
    elif type == "ST":
        self.body.setcontent({"name" : "ST", "value" : PLCOpenClasses["formattedText"]()})
    elif type == "LD":
        self.body.setcontent({"name" : "LD", "value" : PLCOpenClasses["body_LD"]()})
    elif type == "FBD":
        self.body.setcontent({"name" : "FBD", "value" : PLCOpenClasses["body_FBD"]()})
    elif type == "SFC":
        self.body.setcontent({"name" : "SFC", "value" : PLCOpenClasses["body_SFC"]()})
    else:
        raise ValueError, "%s isn't a valid body type!"%type

def getbodyType(self):
    return self.body.getcontent()["name"]

def resetexecutionOrder(self):
    self.body.resetexecutionOrder()

def compileexecutionOrder(self):
    self.body.compileexecutionOrder()

def setelementExecutionOrder(self, instance, new_executionOrder):
    self.body.setelementExecutionOrder(instance, new_executionOrder)

def addinstance(self, name, instance):
    self.body.appendcontentInstance(name, instance)

def getinstances(self):
    return self.body.getcontentInstances()

def getinstance(self, id):
    return self.body.getcontentInstance(id)

def getrandomInstance(self, exclude):
    return self.body.getcontentRandomInstance(exclude)

def getinstanceByName(self, name):
    return self.body.getcontentInstanceByName(name)

def removeinstance(self, id):
    self.body.removecontentInstance(id)

def settext(self, text):
    self.body.settext(text)

def gettext(self):
    return self.body.gettext()

cls = PLCOpenClasses.get("transitions_transition", None)
if cls:
    setattr(cls, "setbodyType", setbodyType)
    setattr(cls, "getbodyType", getbodyType)
    setattr(cls, "resetexecutionOrder", resetexecutionOrder)
    setattr(cls, "compileexecutionOrder", compileexecutionOrder)
    setattr(cls, "setelementExecutionOrder", setelementExecutionOrder)
    setattr(cls, "addinstance", addinstance)
    setattr(cls, "getinstances", getinstances)
    setattr(cls, "getinstance", getinstance)
    setattr(cls, "getrandomInstance", getrandomInstance)
    setattr(cls, "getinstanceByName", getinstanceByName)
    setattr(cls, "removeinstance", removeinstance)
    setattr(cls, "settext", settext)
    setattr(cls, "gettext", gettext)

    def updateElementName(self, old_name, new_name):
        self.body.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.body.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def hasblock(self, name):
        if self.getbodyType() in ["FBD", "LD", "SFC"]:
            for instance in self.getinstances():
                if isinstance(instance, PLCOpenClasses["fbdObjects_block"]) and instance.getinstanceName() == name:
                    return True
        return False
    setattr(cls, "hasblock", hasblock)

    def Search(self, criteria, parent_infos):
        search_result = []
        parent_infos = parent_infos[:-1] + ["T::%s::%s" % (parent_infos[-1].split("::")[1], self.getname())]
        for result in TestTextElement(self.getname(), criteria):
            search_result.append((tuple(parent_infos + ["name"]),) + result)
        search_result.extend(self.body.Search(criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("actions_action", None)
if cls:
    setattr(cls, "setbodyType", setbodyType)
    setattr(cls, "getbodyType", getbodyType)
    setattr(cls, "resetexecutionOrder", resetexecutionOrder)
    setattr(cls, "compileexecutionOrder", compileexecutionOrder)
    setattr(cls, "setelementExecutionOrder", setelementExecutionOrder)
    setattr(cls, "addinstance", addinstance)
    setattr(cls, "getinstances", getinstances)
    setattr(cls, "getinstance", getinstance)
    setattr(cls, "getrandomInstance", getrandomInstance)
    setattr(cls, "getinstanceByName", getinstanceByName)
    setattr(cls, "removeinstance", removeinstance)
    setattr(cls, "settext", settext)
    setattr(cls, "gettext", gettext)

    def updateElementName(self, old_name, new_name):
        self.body.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.body.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def hasblock(self, name):
        if self.getbodyType() in ["FBD", "LD", "SFC"]:
            for instance in self.getinstances():
                if isinstance(instance, PLCOpenClasses["fbdObjects_block"]) and instance.getinstanceName() == name:
                    return True
        return False
    setattr(cls, "hasblock", hasblock)

    def Search(self, criteria, parent_infos):
        search_result = []
        parent_infos = parent_infos[:-1] + ["A::%s::%s" % (parent_infos[-1].split("::")[1], self.getname())]
        for result in TestTextElement(self.getname(), criteria):
            search_result.append((tuple(parent_infos + ["name"]),) + result)
        search_result.extend(self.body.Search(criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("body", None)
if cls:
    cls.currentExecutionOrderId = 0
    
    def resetcurrentExecutionOrderId(self):
        object.__setattr__(self, "currentExecutionOrderId", 0)
    setattr(cls, "resetcurrentExecutionOrderId", resetcurrentExecutionOrderId)
    
    def getnewExecutionOrderId(self):
        object.__setattr__(self, "currentExecutionOrderId", self.currentExecutionOrderId + 1)
        return self.currentExecutionOrderId
    setattr(cls, "getnewExecutionOrderId", getnewExecutionOrderId)
    
    def resetexecutionOrder(self):
        if self.content["name"] == "FBD":
            for element in self.content["value"].getcontent():
                if not isinstance(element["value"], (PLCOpenClasses.get("commonObjects_comment", None), 
                                                     PLCOpenClasses.get("commonObjects_connector", None), 
                                                     PLCOpenClasses.get("commonObjects_continuation", None))):
                    element["value"].setexecutionOrderId(0)
        else:
            raise TypeError, _("Can only generate execution order on FBD networks!")
    setattr(cls, "resetexecutionOrder", resetexecutionOrder)
    
    def compileexecutionOrder(self):
        if self.content["name"] == "FBD":
            self.resetexecutionOrder()
            self.resetcurrentExecutionOrderId()
            for element in self.content["value"].getcontent():
                if isinstance(element["value"], PLCOpenClasses.get("fbdObjects_outVariable", None)) and element["value"].getexecutionOrderId() == 0:
                    connections = element["value"].connectionPointIn.getconnections()
                    if connections and len(connections) == 1:
                        self.compileelementExecutionOrder(connections[0])
                    element["value"].setexecutionOrderId(self.getnewExecutionOrderId())
        else:
            raise TypeError, _("Can only generate execution order on FBD networks!")
    setattr(cls, "compileexecutionOrder", compileexecutionOrder)
    
    def compileelementExecutionOrder(self, link):
        if self.content["name"] == "FBD":
            localid = link.getrefLocalId()
            instance = self.getcontentInstance(localid)
            if isinstance(instance, PLCOpenClasses.get("fbdObjects_block", None)) and instance.getexecutionOrderId() == 0:
                for variable in instance.inputVariables.getvariable():
                    connections = variable.connectionPointIn.getconnections()
                    if connections and len(connections) == 1:
                        self.compileelementExecutionOrder(connections[0])
                instance.setexecutionOrderId(self.getnewExecutionOrderId())
            elif isinstance(instance, PLCOpenClasses.get("commonObjects_continuation", None)) and instance.getexecutionOrderId() == 0:
                name = instance.getname()
                for tmp_instance in self.getcontentInstances():
                    if isinstance(tmp_instance, PLCOpenClasses.get("commonObjects_connector", None)) and tmp_instance.getname() == name and tmp_instance.getexecutionOrderId() == 0:
                        connections = tmp_instance.connectionPointIn.getconnections()
                        if connections and len(connections) == 1:
                            self.compileelementExecutionOrder(connections[0])
        else:
            raise TypeError, _("Can only generate execution order on FBD networks!")
    setattr(cls, "compileelementExecutionOrder", compileelementExecutionOrder)
    
    def setelementExecutionOrder(self, instance, new_executionOrder):
        if self.content["name"] == "FBD":
            old_executionOrder = instance.getexecutionOrderId()
            if old_executionOrder is not None and old_executionOrder != 0 and new_executionOrder != 0:
                for element in self.content["value"].getcontent():
                    if element["value"] != instance and not isinstance(element["value"], PLCOpenClasses.get("commonObjects_comment", None)):
                        element_executionOrder = element["value"].getexecutionOrderId()
                        if old_executionOrder <= element_executionOrder <= new_executionOrder:
                            element["value"].setexecutionOrderId(element_executionOrder - 1)
                        if new_executionOrder <= element_executionOrder <= old_executionOrder:
                            element["value"].setexecutionOrderId(element_executionOrder + 1)
            instance.setexecutionOrderId(new_executionOrder)
        else:
            raise TypeError, _("Can only generate execution order on FBD networks!")
    setattr(cls, "setelementExecutionOrder", setelementExecutionOrder)
    
    def appendcontentInstance(self, name, instance):
        if self.content["name"] in ["LD","FBD","SFC"]:
            self.content["value"].appendcontent({"name" : name, "value" : instance})
        else:
            raise TypeError, _("%s body don't have instances!")%self.content["name"]
    setattr(cls, "appendcontentInstance", appendcontentInstance)
    
    def getcontentInstances(self):
        if self.content["name"] in ["LD","FBD","SFC"]:
            instances = []
            for element in self.content["value"].getcontent():
                instances.append(element["value"])
            return instances
        else:
            raise TypeError, _("%s body don't have instances!")%self.content["name"]
    setattr(cls, "getcontentInstances", getcontentInstances)

    def getcontentInstance(self, id):
        if self.content["name"] in ["LD","FBD","SFC"]:
            for element in self.content["value"].getcontent():
                if element["value"].getlocalId() == id:
                    return element["value"]
            return None
        else:
            raise TypeError, _("%s body don't have instances!")%self.content["name"]
    setattr(cls, "getcontentInstance", getcontentInstance)
    
    def getcontentRandomInstance(self, exclude):
        if self.content["name"] in ["LD","FBD","SFC"]:
            for element in self.content["value"].getcontent():
                if element["value"].getlocalId() not in exclude:
                    return element["value"]
            return None
        else:
            raise TypeError, _("%s body don't have instances!")%self.content["name"]
    setattr(cls, "getcontentRandomInstance", getcontentRandomInstance)
    
    def getcontentInstanceByName(self, name):
        if self.content["name"] in ["LD","FBD","SFC"]:
            for element in self.content["value"].getcontent():
                if isinstance(element["value"], PLCOpenClasses.get("fbdObjects_block", None)) and element["value"].getinstanceName() == name:
                    return element["value"]
        else:
            raise TypeError, _("%s body don't have instances!")%self.content["name"]
    setattr(cls, "getcontentInstanceByName", getcontentInstanceByName)
    
    def removecontentInstance(self, id):
        if self.content["name"] in ["LD","FBD","SFC"]:
            i = 0
            removed = False
            elements = self.content["value"].getcontent()
            while i < len(elements) and not removed:
                if elements[i]["value"].getlocalId() == id:
                    self.content["value"].removecontent(i)
                    removed = True
                i += 1
            if not removed:
                raise ValueError, _("Instance with id %d doesn't exist!")%id
        else:
            raise TypeError, "%s body don't have instances!"%self.content["name"]
    setattr(cls, "removecontentInstance", removecontentInstance)
    
    def settext(self, text):
        if self.content["name"] in ["IL","ST"]:
            self.content["value"].settext(text)
        else:
            raise TypeError, _("%s body don't have text!")%self.content["name"]
    setattr(cls, "settext", settext)

    def gettext(self):
        if self.content["name"] in ["IL","ST"]:
            return self.content["value"].gettext()
        else:
            raise TypeError, _("%s body don't have text!")%self.content["name"]
    setattr(cls, "gettext", gettext)
    
    def updateElementName(self, old_name, new_name):
        if self.content["name"] in ["IL", "ST"]:
            self.content["value"].updateElementName(old_name, new_name)
        else:
            for element in self.content["value"].getcontent():
                element["value"].updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        if self.content["name"] in ["IL", "ST"]:
            self.content["value"].updateElementAddress(address_model, new_leading)
        else:
            for element in self.content["value"].getcontent():
                element["value"].updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def Search(self, criteria, parent_infos=[]):
        if self.content["name"] in ["IL", "ST"]:
            search_result = self.content["value"].Search(criteria, parent_infos + ["body", 0])
        else:
            search_result = []
            for element in self.content["value"].getcontent():
                search_result.extend(element["value"].Search(criteria, parent_infos))
        return search_result
    setattr(cls, "Search", Search)

def getx(self):
    return self.position.getx()

def gety(self):
    return self.position.gety()

def setx(self, x):
    self.position.setx(x)
    
def sety(self, y):
    self.position.sety(y)

def _getBoundingBox(self):
    return rect(self.getx(), self.gety(), self.getwidth(), self.getheight())

def _getConnectionsBoundingBox(connectionPointIn):
    bbox = rect()
    connections = connectionPointIn.getconnections()
    if connections is not None:
        for connection in connections:
            for x, y in connection.getpoints():
                bbox.update(x, y)
    return bbox

def _getBoundingBoxSingle(self):
    bbox = _getBoundingBox(self)
    if self.connectionPointIn is not None:
        bbox.union(_getConnectionsBoundingBox(self.connectionPointIn))
    return bbox

def _getBoundingBoxMultiple(self):
    bbox = _getBoundingBox(self)
    for connectionPointIn in self.getconnectionPointIn():
        bbox.union(_getConnectionsBoundingBox(connectionPointIn))
    return bbox

def _filterConnections(connectionPointIn, localId, connections):
    in_connections = connectionPointIn.getconnections()
    if in_connections is not None:
        to_delete = []
        for i, connection in enumerate(in_connections):
            connected = connection.getrefLocalId()
            if not connections.has_key((localId, connected)) and \
               not connections.has_key((connected, localId)):
                to_delete.append(i)
        to_delete.reverse()
        for i in to_delete:
            connectionPointIn.removeconnection(i)

def _filterConnectionsSingle(self, connections):
    if self.connectionPointIn is not None:
        _filterConnections(self.connectionPointIn, self.localId, connections)

def _filterConnectionsMultiple(self, connections):
    for connectionPointIn in self.getconnectionPointIn():
        _filterConnections(connectionPointIn, self.localId, connections)

def _getconnectionsdefinition(instance, connections_end):
    id = instance.getlocalId()
    return dict([((id, end), True) for end in connections_end])

def _updateConnectionsId(connectionPointIn, translation):
    connections_end = []
    connections = connectionPointIn.getconnections()
    if connections is not None:
        for connection in connections:
            refLocalId = connection.getrefLocalId()
            new_reflocalId = translation.get(refLocalId, refLocalId)
            connection.setrefLocalId(new_reflocalId)
            connections_end.append(new_reflocalId)
    return connections_end

def _updateConnectionsIdSingle(self, translation):
    connections_end = []
    if self.connectionPointIn is not None:
        connections_end = _updateConnectionsId(self.connectionPointIn, translation)
    return _getconnectionsdefinition(self, connections_end)

def _updateConnectionsIdMultiple(self, translation):
    connections_end = []
    for connectionPointIn in self.getconnectionPointIn():
        connections_end.extend(_updateConnectionsId(connectionPointIn, translation))
    return _getconnectionsdefinition(self, connections_end)

def _translate(self, dx, dy):
    self.setx(self.getx() + dx)
    self.sety(self.gety() + dy)
    
def _translateConnections(connectionPointIn, dx, dy):
    connections = connectionPointIn.getconnections()
    if connections is not None:
        for connection in connections:
            for position in connection.getposition():
                position.setx(position.getx() + dx)
                position.sety(position.gety() + dy)

def _translateSingle(self, dx, dy):
    _translate(self, dx, dy)
    if self.connectionPointIn is not None:
        _translateConnections(self.connectionPointIn, dx, dy)

def _translateMultiple(self, dx, dy):
    _translate(self, dx, dy)
    for connectionPointIn in self.getconnectionPointIn():
        _translateConnections(connectionPointIn, dx, dy)

def _updateElementName(self, old_name, new_name):
    pass

def _updateElementAddress(self, address_model, new_leading):
    pass

def _SearchInElement(self, criteria, parent_infos=[]):
    return []

_connectionsFunctions = {
    "bbox": {"none": _getBoundingBox,
             "single": _getBoundingBoxSingle,
             "multiple": _getBoundingBoxMultiple},
    "translate": {"none": _translate,
               "single": _translateSingle,
               "multiple": _translateMultiple},
    "filter": {"none": lambda self, connections: None,
               "single": _filterConnectionsSingle,
               "multiple": _filterConnectionsMultiple},
    "update": {"none": lambda self, translation: {},
               "single": _updateConnectionsIdSingle,
               "multiple": _updateConnectionsIdMultiple},
}

def _initElementClass(name, classname, connectionPointInType="none"):
    ElementNameToClass[name] = classname
    cls = PLCOpenClasses.get(classname, None)
    if cls:
        setattr(cls, "getx", getx)
        setattr(cls, "gety", gety)
        setattr(cls, "setx", setx)
        setattr(cls, "sety", sety)
        setattr(cls, "updateElementName", _updateElementName)
        setattr(cls, "updateElementAddress", _updateElementAddress)
        setattr(cls, "getBoundingBox", _connectionsFunctions["bbox"][connectionPointInType])
        setattr(cls, "translate", _connectionsFunctions["translate"][connectionPointInType])
        setattr(cls, "filterConnections", _connectionsFunctions["filter"][connectionPointInType])
        setattr(cls, "updateConnectionsId", _connectionsFunctions["update"][connectionPointInType])
        setattr(cls, "Search", _SearchInElement)
    return cls

def _getexecutionOrder(instance, specific_values):
    executionOrder = instance.getexecutionOrderId()
    if executionOrder is None:
        executionOrder = 0
    specific_values["executionOrder"] = executionOrder
    
def _getdefaultmodifiers(instance, infos):
    infos["negated"] = instance.getnegated()
    infos["edge"] = instance.getedge()

def _getinputmodifiers(instance, infos):
    infos["negated"] = instance.getnegatedIn()
    infos["edge"] = instance.getedgeIn()

def _getoutputmodifiers(instance, infos):
    infos["negated"] = instance.getnegatedOut()
    infos["edge"] = instance.getedgeOut()

MODIFIERS_FUNCTIONS = {"default": _getdefaultmodifiers,
                       "input": _getinputmodifiers,
                       "output": _getoutputmodifiers}

def _getconnectioninfos(instance, connection, links=False, modifiers=None, parameter=False):
    infos = {"position": connection.getrelPositionXY()}
    if parameter:
        infos["name"] = instance.getformalParameter()
    MODIFIERS_FUNCTIONS.get(modifiers, lambda x, y: None)(instance, infos)
    if links:
        infos["links"] = []
        connections = connection.getconnections()
        if connections is not None:
            for link in connections:
                dic = {"refLocalId": link.getrefLocalId(),
                       "points": link.getpoints(),
                       "formalParameter": link.getformalParameter()}
                infos["links"].append(dic)
    return infos

def _getelementinfos(instance):
    return {"id": instance.getlocalId(),
            "x": instance.getx(),
            "y": instance.gety(),
            "height": instance.getheight(),
            "width": instance.getwidth(),
            "specific_values": {},
            "inputs": [],
            "outputs": []}

def _getvariableinfosFunction(type, input, output):
    def getvariableinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = type
        specific_values = infos["specific_values"]
        specific_values["name"] = self.getexpression()
        _getexecutionOrder(self, specific_values)
        if input and output:
            infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True, "input"))
            infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut, False, "output"))
        elif input:
            infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True, "default"))
        elif output:
            infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut, False, "default"))
        return infos
    return getvariableinfos

def _getconnectorinfosFunction(type):
    def getvariableinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = type
        infos["specific_values"]["name"] = self.getname()
        if type == "connector":
            infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
        elif type == "continuation":
            infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut))
        return infos
    return getvariableinfos

def _getpowerrailinfosFunction(type):
    def getpowerrailinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = type
        if type == "rightPowerRail":
            for connectionPointIn in self.getconnectionPointIn():
                infos["inputs"].append(_getconnectioninfos(self, connectionPointIn, True))
            infos["specific_values"]["connectors"] = len(infos["inputs"])
        elif type == "leftPowerRail":
            for connectionPointOut in self.getconnectionPointOut():
                infos["outputs"].append(_getconnectioninfos(self, connectionPointOut))
            infos["specific_values"]["connectors"] = len(infos["outputs"])
        return infos
    return getpowerrailinfos

def _getldelementinfosFunction(type):
    def getldelementinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = type
        specific_values = infos["specific_values"]
        specific_values["name"] = self.getvariable()
        _getexecutionOrder(self, specific_values)
        specific_values["negated"] = self.getnegated()
        specific_values["edge"] = self.getedge()
        if type == "coil":
            specific_values["storage"] = self.getstorage()
        infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
        infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut))
        return infos
    return getldelementinfos

DIVERGENCE_TYPES = {(True, True): "simultaneousDivergence",
                    (True, False): "selectionDivergence",
                    (False, True): "simultaneousConvergence",
                    (False, False): "selectionConvergence"}

def _getdivergenceinfosFunction(divergence, simultaneous):
    def getdivergenceinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = DIVERGENCE_TYPES[(divergence, simultaneous)]
        if divergence:
            infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
            for connectionPointOut in self.getconnectionPointOut():
                infos["outputs"].append(_getconnectioninfos(self, connectionPointOut))
            infos["specific_values"]["connectors"] = len(infos["outputs"])
        else:
            for connectionPointIn in self.getconnectionPointIn():
                infos["inputs"].append(_getconnectioninfos(self, connectionPointIn, True))
            infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut))
            infos["specific_values"]["connectors"] = len(infos["inputs"])
        return infos
    return getdivergenceinfos

cls = _initElementClass("comment", "commonObjects_comment")
if cls:
    def getinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = "comment"
        infos["specific_values"]["content"] = self.getcontentText()
        return infos
    setattr(cls, "getinfos", getinfos)
    
    def setcontentText(self, text):
        self.content.settext(text)
    setattr(cls, "setcontentText", setcontentText)
        
    def getcontentText(self):
        return self.content.gettext()
    setattr(cls, "getcontentText", getcontentText)
    
    def updateElementName(self, old_name, new_name):
        self.content.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.content.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def Search(self, criteria, parent_infos=[]):
        return self.content.Search(criteria, parent_infos + ["comment", self.getlocalId(), "content"])
    setattr(cls, "Search", Search)

cls = _initElementClass("block", "fbdObjects_block")
if cls:
    def getBoundingBox(self):
        bbox = _getBoundingBox(self)
        for input in self.inputVariables.getvariable():
            bbox.union(_getConnectionsBoundingBox(input.connectionPointIn))
        return bbox
    setattr(cls, "getBoundingBox", getBoundingBox)

    def getinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = self.gettypeName()
        specific_values = infos["specific_values"]
        specific_values["name"] = self.getinstanceName()
        _getexecutionOrder(self, specific_values)
        for variable in self.inputVariables.getvariable():
            infos["inputs"].append(_getconnectioninfos(variable, variable.connectionPointIn, True, "default", True))
        for variable in self.outputVariables.getvariable():
            infos["outputs"].append(_getconnectioninfos(variable, variable.connectionPointOut, False, "default", True))
        return infos
    setattr(cls, "getinfos", getinfos)

    def updateElementName(self, old_name, new_name):
        if self.typeName == old_name:
            self.typeName = new_name
    setattr(cls, "updateElementName", updateElementName)

    def filterConnections(self, connections):
        for input in self.inputVariables.getvariable():
            _filterConnections(input.connectionPointIn, self.localId, connections)
    setattr(cls, "filterConnections", filterConnections)

    def updateConnectionsId(self, translation):
        connections_end = []
        for input in self.inputVariables.getvariable():
            connections_end.extend(_updateConnectionsId(input.connectionPointIn, translation))
        return _getconnectionsdefinition(self, connections_end)
    setattr(cls, "updateConnectionsId", updateConnectionsId)

    def translate(self, dx, dy):
        _translate(self, dx, dy)
        for input in self.inputVariables.getvariable():
            _translateConnections(input.connectionPointIn, dx, dy)
    setattr(cls, "translate", translate)

    def Search(self, criteria, parent_infos=[]):
        parent_infos = parent_infos + ["block", self.getlocalId()]
        search_result = _Search([("name", self.getinstanceName()),
                                 ("type", self.gettypeName())],
                                criteria, parent_infos)
        for i, variable in enumerate(self.inputVariables.getvariable()):
            for result in TestTextElement(variable.getformalParameter(), criteria):
                search_result.append((tuple(parent_infos + ["input", i]),) + result)
        for i, variable in enumerate(self.outputVariables.getvariable()):
            for result in TestTextElement(variable.getformalParameter(), criteria):
                search_result.append((tuple(parent_infos + ["output", i]),) + result)
        return search_result
    setattr(cls, "Search", Search)

cls = _initElementClass("leftPowerRail", "ldObjects_leftPowerRail")
if cls:
    setattr(cls, "getinfos", _getpowerrailinfosFunction("leftPowerRail"))

cls = _initElementClass("rightPowerRail", "ldObjects_rightPowerRail", "multiple")
if cls:
    setattr(cls, "getinfos", _getpowerrailinfosFunction("rightPowerRail"))

cls = _initElementClass("contact", "ldObjects_contact", "single")
if cls:
    setattr(cls, "getinfos", _getldelementinfosFunction("contact"))
    
    def updateElementName(self, old_name, new_name):
        if self.variable == old_name:
            self.variable = new_name
    setattr(cls, "updateElementName", updateElementName)
    
    def updateElementAddress(self, address_model, new_leading):
        self.variable = update_address(self.variable, address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)
    
    def Search(self, criteria, parent_infos=[]):
        return _Search([("reference", self.getvariable())], criteria, parent_infos + ["contact", self.getlocalId()])
    setattr(cls, "Search", Search)

cls = _initElementClass("coil", "ldObjects_coil", "single")
if cls:
    setattr(cls, "getinfos", _getldelementinfosFunction("coil"))
    
    def updateElementName(self, old_name, new_name):
        if self.variable == old_name:
            self.variable = new_name
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.variable = update_address(self.variable, address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def Search(self, criteria, parent_infos=[]):
        return _Search([("reference", self.getvariable())], criteria, parent_infos + ["coil", self.getlocalId()])
    setattr(cls, "Search", Search)

cls = _initElementClass("step", "sfcObjects_step", "single")
if cls:
    def getinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = "step"
        specific_values = infos["specific_values"]
        specific_values["name"] = self.getname()
        specific_values["initial"] = self.getinitialStep()
        if self.connectionPointIn:
            infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
        if self.connectionPointOut:
            infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut))
        if self.connectionPointOutAction:
            specific_values["action"] = _getconnectioninfos(self, self.connectionPointOutAction)
        return infos
    setattr(cls, "getinfos", getinfos)

    def Search(self, criteria, parent_infos=[]):
        return _Search([("name", self.getname())], criteria, parent_infos + ["step", self.getlocalId()])
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("transition_condition", None)
if cls:
    def compatibility(self, tree):
        connections = []
        for child in tree.childNodes:
            if child.nodeName == "connection":
                connections.append(child)
        if len(connections) > 0:
            node = CreateNode("connectionPointIn")
            relPosition = CreateNode("relPosition")
            NodeSetAttr(relPosition, "x", "0")
            NodeSetAttr(relPosition, "y", "0")
            node.childNodes.append(relPosition)
            node.childNodes.extend(connections)
            tree.childNodes = [node]
    setattr(cls, "compatibility", compatibility)

cls = _initElementClass("transition", "sfcObjects_transition")
if cls:
    def getinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = "transition"
        specific_values = infos["specific_values"]
        priority = self.getpriority()
        if priority is None:
            priority = 0
        specific_values["priority"] = priority
        condition = self.getconditionContent()
        specific_values["condition_type"] = condition["type"]
        if specific_values["condition_type"] == "connection":
            specific_values["connection"] = _getconnectioninfos(self, condition["value"], True)
        else:
            specific_values["condition"] = condition["value"]
        infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
        infos["outputs"].append(_getconnectioninfos(self, self.connectionPointOut))
        return infos
    setattr(cls, "getinfos", getinfos)

    def setconditionContent(self, type, value):
        if not self.condition:
            self.addcondition()
        if type == "reference":
            condition = PLCOpenClasses["condition_reference"]()
            condition.setname(value)
        elif type == "inline":
            condition = PLCOpenClasses["condition_inline"]()
            condition.setcontent({"name" : "ST", "value" : PLCOpenClasses["formattedText"]()})
            condition.settext(value)
        elif type == "connection":
            type = "connectionPointIn"
            condition = PLCOpenClasses["connectionPointIn"]()
        self.condition.setcontent({"name" : type, "value" : condition})
    setattr(cls, "setconditionContent", setconditionContent)
        
    def getconditionContent(self):
        if self.condition:
            content = self.condition.getcontent()
            values = {"type" : content["name"]}
            if values["type"] == "reference":
                values["value"] = content["value"].getname()
            elif values["type"] == "inline":
                values["value"] = content["value"].gettext()
            elif values["type"] == "connectionPointIn":
                values["type"] = "connection"
                values["value"] = content["value"]
            return values
        return ""
    setattr(cls, "getconditionContent", getconditionContent)

    def getconditionConnection(self):
        if self.condition:
            content = self.condition.getcontent()
            if content["name"] == "connectionPointIn":
                return content["value"]
        return None
    setattr(cls, "getconditionConnection", getconditionConnection)

    def getBoundingBox(self):
        bbox = _getBoundingBoxSingle(self)
        condition_connection = self.getconditionConnection()
        if condition_connection:
            bbox.union(_getConnectionsBoundingBox(condition_connection))
        return bbox
    setattr(cls, "getBoundingBox", getBoundingBox)
    
    def translate(self, dx, dy):
        _translateSingle(self, dx, dy)
        condition_connection = self.getconditionConnection()
        if condition_connection:
            _translateConnections(condition_connection, dx, dy)
    setattr(cls, "translate", translate)
    
    def filterConnections(self, connections):
        _filterConnectionsSingle(self, connections)
        condition_connection = self.getconditionConnection()
        if condition_connection:
            _filterConnections(condition_connection, self.localId, connections)
    setattr(cls, "filterConnections", filterConnections)
    
    def updateConnectionsId(self, translation):
        connections_end = []
        if self.connectionPointIn is not None:
            connections_end = _updateConnectionsId(self.connectionPointIn, translation)
        condition_connection = self.getconditionConnection()
        if condition_connection:
            connections_end.extend(_updateConnectionsId(condition_connection, translation))
        return _getconnectionsdefinition(self, connections_end)
    setattr(cls, "updateConnectionsId", updateConnectionsId)

    def updateElementName(self, old_name, new_name):
        if self.condition:
            content = self.condition.getcontent()
            if content["name"] == "reference":
                if content["value"].getname() == old_name:
                    content["value"].setname(new_name)
            elif content["name"] == "inline":
                content["value"].updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        if self.condition:
            content = self.condition.getcontent()
            if content["name"] == "reference":
                content["value"].setname(update_address(content["value"].getname(), address_model, new_leading))
            elif content["name"] == "inline":
                content["value"].updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def getconnections(self):
        condition_connection = self.getconditionConnection()
        if condition_connection:
            return condition_connection.getconnections()
        return None
    setattr(cls, "getconnections", getconnections)
    
    def Search(self, criteria, parent_infos=[]):
        parent_infos = parent_infos + ["transition", self.getlocalId()]
        search_result = []
        content = self.condition.getcontent()
        if content["name"] == "reference":
            search_result.extend(_Search([("reference", content["value"].getname())], criteria, parent_infos))
        elif content["name"] == "inline":
            search_result.extend(content["value"].Search(criteria, parent_infos + ["inline"]))
        return search_result
    setattr(cls, "Search", Search)
    
cls = _initElementClass("selectionDivergence", "sfcObjects_selectionDivergence", "single")
if cls:
    setattr(cls, "getinfos", _getdivergenceinfosFunction(True, False))

cls = _initElementClass("selectionConvergence", "sfcObjects_selectionConvergence", "multiple")
if cls:
    setattr(cls, "getinfos", _getdivergenceinfosFunction(False, False))

cls = _initElementClass("simultaneousDivergence", "sfcObjects_simultaneousDivergence", "single")
if cls:
    setattr(cls, "getinfos", _getdivergenceinfosFunction(True, True))

cls = _initElementClass("simultaneousConvergence", "sfcObjects_simultaneousConvergence", "multiple")
if cls:
    setattr(cls, "getinfos", _getdivergenceinfosFunction(False, True))

cls = _initElementClass("jumpStep", "sfcObjects_jumpStep", "single")
if cls:
    def getinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = "jump"
        infos["specific_values"]["target"] = self.gettargetName()
        infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
        return infos
    setattr(cls, "getinfos", getinfos)

    def Search(self, criteria, parent_infos):
        return _Search([("target", self.gettargetName())], criteria, parent_infos + ["jump", self.getlocalId()])
    setattr(cls, "Search", Search)

cls = PLCOpenClasses.get("actionBlock_action", None)
if cls:
    def compatibility(self, tree):
        relPosition = reduce(lambda x, y: x | (y.nodeName == "relPosition"), tree.childNodes, False)
        if not tree.hasAttribute("localId"):
            NodeSetAttr(tree, "localId", "0")
        if not relPosition:
            node = CreateNode("relPosition")
            NodeSetAttr(node, "x", "0")
            NodeSetAttr(node, "y", "0")
            tree.childNodes.insert(0, node)
    setattr(cls, "compatibility", compatibility)
    
    def setreferenceName(self, name):
        if self.reference:
            self.reference.setname(name)
    setattr(cls, "setreferenceName", setreferenceName)
    
    def getreferenceName(self):
        if self.reference:
            return self.reference.getname()
        return None
    setattr(cls, "getreferenceName", getreferenceName)

    def setinlineContent(self, content):
        if self.inline:
            self.inline.setcontent({"name" : "ST", "value" : PLCOpenClasses["formattedText"]()})
            self.inline.settext(content)
    setattr(cls, "setinlineContent", setinlineContent)
    
    def getinlineContent(self):
        if self.inline:
            return self.inline.gettext()
        return None
    setattr(cls, "getinlineContent", getinlineContent)

    def updateElementName(self, old_name, new_name):
        if self.reference and self.reference.getname() == old_name:
            self.reference.setname(new_name)
        if self.inline:
            self.inline.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        if self.reference:
            self.reference.setname(update_address(self.reference.getname(), address_model, new_leading))
        if self.inline:
            self.inline.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def Search(self, criteria, parent_infos=[]):
        qualifier = self.getqualifier()
        if qualifier is None:
            qualifier = "N"
        return _Search([("inline", self.getinlineContent()),
                        ("reference", self.getreferenceName()), 
                        ("qualifier", qualifier),
                        ("duration", self.getduration()),
                        ("indicator", self.getindicator())],
                       criteria, parent_infos)
    setattr(cls, "Search", Search)

cls = _initElementClass("actionBlock", "commonObjects_actionBlock", "single")
if cls:
    def compatibility(self, tree):
        for child in tree.childNodes[:]:
            if child.nodeName == "connectionPointOut":
                tree.childNodes.remove(child)
    setattr(cls, "compatibility", compatibility)
    
    def getinfos(self):
        infos = _getelementinfos(self)
        infos["type"] = "actionBlock"
        infos["specific_values"]["actions"] = self.getactions()
        infos["inputs"].append(_getconnectioninfos(self, self.connectionPointIn, True))
        return infos
    setattr(cls, "getinfos", getinfos)
    
    def setactions(self, actions):
        self.action = []
        for params in actions:
            action = PLCOpenClasses["actionBlock_action"]()
            action.setqualifier(params["qualifier"])
            if params["type"] == "reference":
                action.addreference()
                action.setreferenceName(params["value"])
            else:
                action.addinline()
                action.setinlineContent(params["value"])
            if params.has_key("duration"):
                action.setduration(params["duration"])
            if params.has_key("indicator"):
                action.setindicator(params["indicator"])
            self.action.append(action)
    setattr(cls, "setactions", setactions)

    def getactions(self):
        actions = []
        for action in self.action:
            params = {}
            params["qualifier"] = action.getqualifier()
            if params["qualifier"] is None:
                params["qualifier"] = "N"
            if action.getreference():
                params["type"] = "reference"
                params["value"] = action.getreferenceName()
            elif action.getinline():
                params["type"] = "inline"
                params["value"] = action.getinlineContent()
            duration = action.getduration()
            if duration:
                params["duration"] = duration
            indicator = action.getindicator()
            if indicator:
                params["indicator"] = indicator
            actions.append(params)
        return actions
    setattr(cls, "getactions", getactions)

    def updateElementName(self, old_name, new_name):
        for action in self.action:
            action.updateElementName(old_name, new_name)
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        for action in self.action:
            action.updateElementAddress(address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    def Search(self, criteria, parent_infos=[]):
        parent_infos = parent_infos + ["action_block", self.getlocalId()]
        search_result = []
        for idx, action in enumerate(self.action):
            search_result.extend(action.Search(criteria, parent_infos + ["action", idx]))
        return search_result
    setattr(cls, "Search", Search)

def _SearchInIOVariable(self, criteria, parent_infos=[]):
    return _Search([("expression", self.getexpression())], criteria, parent_infos + ["io_variable", self.getlocalId()])

cls = _initElementClass("inVariable", "fbdObjects_inVariable")
if cls:
    setattr(cls, "getinfos", _getvariableinfosFunction("input", False, True))
    
    def updateElementName(self, old_name, new_name):
        if self.expression == old_name:
            self.expression = new_name
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.expression = update_address(self.expression, address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    setattr(cls, "Search", _SearchInIOVariable)

cls = _initElementClass("outVariable", "fbdObjects_outVariable", "single")
if cls:
    setattr(cls, "getinfos", _getvariableinfosFunction("output", True, False))
    
    def updateElementName(self, old_name, new_name):
        if self.expression == old_name:
            self.expression = new_name
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.expression = update_address(self.expression, address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    setattr(cls, "Search", _SearchInIOVariable)

cls = _initElementClass("inOutVariable", "fbdObjects_inOutVariable", "single")
if cls:
    setattr(cls, "getinfos", _getvariableinfosFunction("inout", True, True))
    
    def updateElementName(self, old_name, new_name):
        if self.expression == old_name:
            self.expression = new_name
    setattr(cls, "updateElementName", updateElementName)

    def updateElementAddress(self, address_model, new_leading):
        self.expression = update_address(self.expression, address_model, new_leading)
    setattr(cls, "updateElementAddress", updateElementAddress)

    setattr(cls, "Search", _SearchInIOVariable)


def _SearchInConnector(self, criteria, parent_infos=[]):
    return _Search([("name", self.getname())], criteria, parent_infos + ["connector", self.getlocalId()])

cls = _initElementClass("continuation", "commonObjects_continuation")
if cls:
    setattr(cls, "getinfos", _getconnectorinfosFunction("continuation"))
    setattr(cls, "Search", _SearchInConnector)

    def updateElementName(self, old_name, new_name):
        if self.name == old_name:
            self.name = new_name
    setattr(cls, "updateElementName", updateElementName)

cls = _initElementClass("connector", "commonObjects_connector", "single")
if cls:
    setattr(cls, "getinfos", _getconnectorinfosFunction("connector"))
    setattr(cls, "Search", _SearchInConnector)

    def updateElementName(self, old_name, new_name):
        if self.name == old_name:
            self.name = new_name
    setattr(cls, "updateElementName", updateElementName)

cls = PLCOpenClasses.get("connection", None)
if cls:
    def setpoints(self, points):
        self.position = []
        for point in points:
            position = PLCOpenClasses["position"]()
            position.setx(point.x)
            position.sety(point.y)
            self.position.append(position)
    setattr(cls, "setpoints", setpoints)

    def getpoints(self):
        points = []
        for position in self.position:
            points.append((position.getx(),position.gety()))
        return points
    setattr(cls, "getpoints", getpoints)

cls = PLCOpenClasses.get("connectionPointIn", None)
if cls:
    def setrelPositionXY(self, x, y):
        self.relPosition = PLCOpenClasses["position"]()
        self.relPosition.setx(x)
        self.relPosition.sety(y)
    setattr(cls, "setrelPositionXY", setrelPositionXY)

    def getrelPositionXY(self):
        if self.relPosition:
            return self.relPosition.getx(), self.relPosition.gety()
        else:
            return self.relPosition
    setattr(cls, "getrelPositionXY", getrelPositionXY)

    def addconnection(self):
        if not self.content:
            self.content = {"name" : "connection", "value" : [PLCOpenClasses["connection"]()]}
        else:
            self.content["value"].append(PLCOpenClasses["connection"]())
    setattr(cls, "addconnection", addconnection)

    def removeconnection(self, idx):
        if self.content:
            self.content["value"].pop(idx)
        if len(self.content["value"]) == 0:
            self.content = None
    setattr(cls, "removeconnection", removeconnection)

    def removeconnections(self):
        if self.content:
            self.content = None
    setattr(cls, "removeconnections", removeconnections)
    
    def getconnections(self):
        if self.content:
            return self.content["value"]
    setattr(cls, "getconnections", getconnections)
    
    def setconnectionId(self, idx, id):
        if self.content:
            self.content["value"][idx].setrefLocalId(id)
    setattr(cls, "setconnectionId", setconnectionId)
    
    def getconnectionId(self, idx):
        if self.content:
            return self.content["value"][idx].getrefLocalId()
        return None
    setattr(cls, "getconnectionId", getconnectionId)
    
    def setconnectionPoints(self, idx, points):
        if self.content:
            self.content["value"][idx].setpoints(points)
    setattr(cls, "setconnectionPoints", setconnectionPoints)

    def getconnectionPoints(self, idx):
        if self.content:
            return self.content["value"][idx].getpoints()
        return None
    setattr(cls, "getconnectionPoints", getconnectionPoints)

    def setconnectionParameter(self, idx, parameter):
        if self.content:
            self.content["value"][idx].setformalParameter(parameter)
    setattr(cls, "setconnectionParameter", setconnectionParameter)
    
    def getconnectionParameter(self, idx):
        if self.content:
            return self.content["value"][idx].getformalParameter()
        return None
    setattr(cls, "getconnectionParameter", getconnectionParameter)

cls = PLCOpenClasses.get("connectionPointOut", None)
if cls:
    def setrelPositionXY(self, x, y):
        self.relPosition = PLCOpenClasses["position"]()
        self.relPosition.setx(x)
        self.relPosition.sety(y)
    setattr(cls, "setrelPositionXY", setrelPositionXY)

    def getrelPositionXY(self):
        if self.relPosition:
            return self.relPosition.getx(), self.relPosition.gety()
        return self.relPosition
    setattr(cls, "getrelPositionXY", getrelPositionXY)

cls = PLCOpenClasses.get("value", None)
if cls:
    def setvalue(self, value):
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            arrayValue = PLCOpenClasses["value_arrayValue"]()
            self.content = {"name" : "arrayValue", "value" : arrayValue}
        elif value.startswith("(") and value.endswith(")"):
            structValue = PLCOpenClasses["value_structValue"]()
            self.content = {"name" : "structValue", "value" : structValue}
        else:
            simpleValue = PLCOpenClasses["value_simpleValue"]()
            self.content = {"name" : "simpleValue", "value": simpleValue}
        self.content["value"].setvalue(value)
    setattr(cls, "setvalue", setvalue)
    
    def getvalue(self):
        return self.content["value"].getvalue()
    setattr(cls, "getvalue", getvalue)

def extractValues(values):
    items = values.split(",")
    i = 1
    while i < len(items):
        opened = items[i - 1].count("(") + items[i - 1].count("[")
        closed = items[i - 1].count(")") + items[i - 1].count("]")
        if opened > closed:
            items[i - 1] = ','.join([items[i - 1], items.pop(i)])
        elif opened == closed:
            i += 1
        else:
            raise ValueError, _("\"%s\" is an invalid value!")%value
    return items

cls = PLCOpenClasses.get("value_arrayValue", None)
if cls:
    arrayValue_model = re.compile("([0-9]*)\((.*)\)$")
    
    def setvalue(self, value):
        self.value = []
        for item in extractValues(value[1:-1]):
            item = item.strip()
            element = PLCOpenClasses["arrayValue_value"]()
            result = arrayValue_model.match(item)
            if result is not None:
                groups = result.groups()
                element.setrepetitionValue(groups[0])
                element.setvalue(groups[1].strip())
            else:
                element.setvalue(item)
            self.value.append(element)
    setattr(cls, "setvalue", setvalue)
    
    def getvalue(self):
        values = []
        for element in self.value:
            repetition = element.getrepetitionValue()
            if repetition is not None and int(repetition) > 1:
                value = element.getvalue()
                if value is None:
                    value = ""
                values.append("%s(%s)"%(repetition, value))
            else:
                values.append(element.getvalue())
        return "[%s]"%", ".join(values)
    setattr(cls, "getvalue", getvalue)

cls = PLCOpenClasses.get("value_structValue", None)
if cls:
    structValue_model = re.compile("(.*):=(.*)")
    
    def setvalue(self, value):
        self.value = []
        for item in extractValues(value[1:-1]):
            result = structValue_model.match(item)
            if result is not None:
                groups = result.groups()
                element = PLCOpenClasses["structValue_value"]()
                element.setmember(groups[0].strip())
                element.setvalue(groups[1].strip())
                self.value.append(element)
    setattr(cls, "setvalue", setvalue)
    
    def getvalue(self):
        values = []
        for element in self.value:
            values.append("%s := %s"%(element.getmember(), element.getvalue()))
        return "(%s)"%", ".join(values)
    setattr(cls, "getvalue", getvalue)
