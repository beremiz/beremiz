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

from plcopen import plcopen
from plcopen.structures import *
from types import *
import re

# Dictionary associating PLCOpen variable categories to the corresponding 
# IEC 61131-3 variable categories
varTypeNames = {"localVars" : "VAR", "tempVars" : "VAR_TEMP", "inputVars" : "VAR_INPUT", 
                "outputVars" : "VAR_OUTPUT", "inOutVars" : "VAR_IN_OUT", "externalVars" : "VAR_EXTERNAL",
                "globalVars" : "VAR_GLOBAL", "accessVars" : "VAR_ACCESS"}


# Dictionary associating PLCOpen POU categories to the corresponding 
# IEC 61131-3 POU categories
pouTypeNames = {"function" : "FUNCTION", "functionBlock" : "FUNCTION_BLOCK", "program" : "PROGRAM"}


errorVarTypes = {
    "VAR_INPUT": "var_input",
    "VAR_OUTPUT": "var_output",
    "VAR_INOUT": "var_inout",
}

# Helper function for reindenting text
def ReIndentText(text, nb_spaces):
    compute = ""
    lines = text.splitlines()
    if len(lines) > 0:
        line_num = 0
        while line_num < len(lines) and len(lines[line_num].strip()) == 0:
            line_num += 1
        if line_num < len(lines):
            spaces = 0
            while lines[line_num][spaces] == " ":
                spaces += 1
            indent = ""
            for i in xrange(spaces, nb_spaces):
                indent += " "
            for line in lines:
                if line != "":
                    compute += "%s%s\n"%(indent, line)
                else:
                    compute += "\n"
    return compute

def SortInstances(a, b):
    ax, ay = int(a.getx()), int(a.gety())
    bx, by = int(b.getx()), int(b.gety())
    if abs(ay - by) < 10:
        return cmp(ax, bx)
    else:
        return cmp(ay, by)

#-------------------------------------------------------------------------------
#                  Specific exception for PLC generating errors
#-------------------------------------------------------------------------------


class PLCGenException(Exception):
    pass


#-------------------------------------------------------------------------------
#                           Generator of PLC program
#-------------------------------------------------------------------------------


class ProgramGenerator:

    # Create a new PCL program generator
    def __init__(self, controler, project, errors, warnings):
        # Keep reference of the controler and project
        self.Controler = controler
        self.Project = project
        # Reset the internal variables used to generate PLC programs
        self.Program = []
        self.DatatypeComputed = {}
        self.PouComputed = {}
        self.Errors = errors
        self.Warnings = warnings

    # Compute value according to type given
    def ComputeValue(self, value, var_type):
        base_type = self.Controler.GetBaseType(var_type)
        if base_type == "STRING" and not value.startswith("'") and not value.endswith("'"):
            return "'%s'"%value
        elif base_type == "WSTRING" and not value.startswith('"') and not value.endswith('"'):
            return "\"%s\""%value
        return value

    # Generate a data type from its name
    def GenerateDataType(self, datatype_name):
        # Verify that data type hasn't been generated yet
        if not self.DatatypeComputed.get(datatype_name, True):
            # If not mark data type as computed
            self.DatatypeComputed[datatype_name] = True
            
            # Getting datatype model from project
            datatype = self.Project.getdataType(datatype_name)
            tagname = self.Controler.ComputeDataTypeName(datatype.getname())
            datatype_def = [("  ", ()), 
                            (datatype.getname(), (tagname, "name")),
                            (" : ", ())]
            basetype_content = datatype.baseType.getcontent()
            # Data type derived directly from a string type 
            if basetype_content["name"] in ["string", "wstring"]:
                datatype_def += [(basetype_content["name"].upper(), (tagname, "base"))]
            # Data type derived directly from a user defined type 
            elif basetype_content["name"] == "derived":
                basetype_name = basetype_content["value"].getname()
                self.GenerateDataType(basetype_name)
                datatype_def += [(basetype_name, (tagname, "base"))]
            # Data type is a subrange
            elif basetype_content["name"] in ["subrangeSigned", "subrangeUnsigned"]:
                base_type = basetype_content["value"].baseType.getcontent()
                # Subrange derived directly from a user defined type 
                if base_type["name"] == "derived":
                    basetype_name = base_type["value"].getname()
                    self.GenerateDataType(basetype_name)
                # Subrange derived directly from an elementary type 
                else:
                    basetype_name = base_type["name"]
                min_value = basetype_content["value"].range.getlower()
                max_value = basetype_content["value"].range.getupper()
                datatype_def += [(basetype_name, (tagname, "base")),
                                 (" (", ()),
                                 ("%s"%min_value, (tagname, "lower")),
                                 ("..", ()),
                                 ("%s"%max_value, (tagname, "upper")),
                                 (")",())]
            # Data type is an enumerated type
            elif basetype_content["name"] == "enum":
                values = [[(value.getname(), (tagname, "value", i))]
                          for i, value in enumerate(basetype_content["value"].values.getvalue())]
                datatype_def += [("(", ())]
                datatype_def += JoinList([(", ", ())], values)
                datatype_def += [(")", ())]
            # Data type is an array
            elif basetype_content["name"] == "array":
                base_type = basetype_content["value"].baseType.getcontent()
                # Array derived directly from a user defined type 
                if base_type["name"] == "derived":
                    basetype_name = base_type["value"].getname()
                    self.GenerateDataType(basetype_name)
                # Array derived directly from a string type 
                elif base_type["name"] in ["string", "wstring"]:
                    basetype_name = base_type["name"].upper()
                # Array derived directly from an elementary type 
                else:
                    basetype_name = base_type["name"]
                dimensions = [[("%s"%dimension.getlower(), (tagname, "range", i, "lower")),
                               ("..", ()),
                               ("%s"%dimension.getupper(), (tagname, "range", i, "upper"))] 
                              for i, dimension in enumerate(basetype_content["value"].getdimension())]
                datatype_def += [("ARRAY [", ())]
                datatype_def += JoinList([(",", ())], dimensions)
                datatype_def += [("] OF " , ()),
                                 (basetype_name, (tagname, "base"))]
            # Data type is a structure
            elif basetype_content["name"] == "struct":
                elements = []
                for i, element in enumerate(basetype_content["value"].getvariable()):
                    element_type = element.type.getcontent()
                    # Structure element derived directly from a user defined type 
                    if element_type["name"] == "derived":
                        elementtype_name = element_type["value"].getname()
                        self.GenerateDataType(elementtype_name)
                    elif element_type["name"] == "array":
                        base_type = element_type["value"].baseType.getcontent()
                        # Array derived directly from a user defined type 
                        if base_type["name"] == "derived":
                            basetype_name = base_type["value"].getname()
                            self.GenerateDataType(basetype_name)
                        # Array derived directly from a string type 
                        elif base_type["name"] in ["string", "wstring"]:
                            basetype_name = base_type["name"].upper()
                        # Array derived directly from an elementary type 
                        else:
                            basetype_name = base_type["name"]
                        dimensions = ["%s..%s" % (dimension.getlower(), dimension.getupper())
                                      for dimension in element_type["value"].getdimension()]
                        elementtype_name = "ARRAY [%s] OF %s" % (",".join(dimensions), basetype_name)
                    # Structure element derived directly from a string type 
                    elif element_type["name"] in ["string", "wstring"]:
                        elementtype_name = element_type["name"].upper()
                    # Structure element derived directly from an elementary type 
                    else:
                        elementtype_name = element_type["name"]
                    element_text = [("\n    ", ()),
                                    (element.getname(), (tagname, "struct", i, "name")),
                                    (" : ", ()),
                                    (elementtype_name, (tagname, "struct", i, "type"))]
                    if element.initialValue is not None:
                        element_text.extend([(" := ", ()),
                                             (self.ComputeValue(element.initialValue.getvalue(), elementtype_name), (tagname, "struct", i, "initial value"))])
                    element_text.append((";", ()))
                    elements.append(element_text)
                datatype_def += [("STRUCT", ())]
                datatype_def += JoinList([("", ())], elements)
                datatype_def += [("\n  END_STRUCT", ())]
            # Data type derived directly from a elementary type 
            else:
                datatype_def += [(basetype_content["name"], (tagname, "base"))]
            # Data type has an initial value
            if datatype.initialValue is not None:
                datatype_def += [(" := ", ()),
                                 (self.ComputeValue(datatype.initialValue.getvalue(), datatype_name), (tagname, "initial value"))]
            datatype_def += [(";\n", ())]
            self.Program += datatype_def

    # Generate a POU from its name
    def GeneratePouProgram(self, pou_name):
        # Verify that POU hasn't been generated yet
        if not self.PouComputed.get(pou_name, True):
            # If not mark POU as computed
            self.PouComputed[pou_name] = True
            
            # Getting POU model from project
            pou = self.Project.getpou(pou_name)
            pou_type = pou.getpouType()
            # Verify that POU type exists
            if pouTypeNames.has_key(pou_type):
                # Create a POU program generator
                pou_program = PouProgramGenerator(self, pou.getname(), pouTypeNames[pou_type], self.Errors, self.Warnings)
                program = pou_program.GenerateProgram(pou)
                self.Program += program
            else:
                raise PLCGenException, _("Undefined pou type \"%s\"")%pou_type
    
    # Generate a POU defined and used in text
    def GeneratePouProgramInText(self, text):
        for pou_name in self.PouComputed.keys():
            model = re.compile("(?:^|[^0-9^A-Z])%s(?:$|[^0-9^A-Z])"%pou_name.upper())
            if model.search(text) is not None:
                self.GeneratePouProgram(pou_name)
    
    # Generate a configuration from its model
    def GenerateConfiguration(self, configuration):
        tagname = self.Controler.ComputeConfigurationName(configuration.getname())
        config = [("\nCONFIGURATION ", ()),
                  (configuration.getname(), (tagname, "name")),
                  ("\n", ())]
        var_number = 0
        
        varlists = [(varlist, varlist.getvariable()[:]) for varlist in configuration.getglobalVars()]
        
        extra_variables = self.Controler.GetConfigurationExtraVariables()
        if len(extra_variables) > 0:
            if len(varlists) == 0:
                varlists = [(plcopen.interface_globalVars(), [])]
            varlists[-1][1].extend(extra_variables)
            
        # Generate any global variable in configuration
        for varlist, varlist_variables in varlists:
            variable_type = errorVarTypes.get("VAR_GLOBAL", "var_local")
            # Generate variable block with modifier
            config += [("  VAR_GLOBAL", ())]
            if varlist.getconstant():
                config += [(" CONSTANT", (tagname, variable_type, (var_number, var_number + len(varlist.getvariable())), "constant"))]
            elif varlist.getretain():
                config += [(" RETAIN", (tagname, variable_type, (var_number, var_number + len(varlist.getvariable())), "retain"))]
            elif varlist.getnonretain():
                config += [(" NON_RETAIN", (tagname, variable_type, (var_number, var_number + len(varlist.getvariable())), "non_retain"))]
            config += [("\n", ())]
            # Generate any variable of this block
            for var in varlist_variables:
                vartype_content = var.gettype().getcontent()
                if vartype_content["name"] == "derived":
                    var_type = vartype_content["value"].getname()
                    self.GenerateDataType(var_type)
                else:
                    var_type = var.gettypeAsText()
                
                config += [("    ", ()),
                           (var.getname(), (tagname, variable_type, var_number, "name")),
                           (" ", ())]
                # Generate variable address if exists
                address = var.getaddress()
                if address:
                    config += [("AT ", ()),
                               (address, (tagname, variable_type, var_number, "location")),
                               (" ", ())]
                config += [(": ", ()),
                           (var.gettypeAsText(), (tagname, variable_type, var_number, "type"))]
                # Generate variable initial value if exists
                initial = var.getinitialValue()
                if initial:
                    config += [(" := ", ()),
                               (self.ComputeValue(initial.getvalue(), var_type), (tagname, variable_type, var_number, "initial value"))]
                config += [(";\n", ())]
                var_number += 1
            config += [("  END_VAR\n", ())]
        # Generate any resource in the configuration
        for resource in configuration.getresource():
            config += self.GenerateResource(resource, configuration.getname())
        config += [("END_CONFIGURATION\n", ())]
        return config
    
    # Generate a resource from its model
    def GenerateResource(self, resource, config_name):
        tagname = self.Controler.ComputeConfigurationResourceName(config_name, resource.getname())
        resrce = [("\n  RESOURCE ", ()),
                  (resource.getname(), (tagname, "name")),
                  (" ON PLC\n", ())]
        var_number = 0
        # Generate any global variable in configuration
        for varlist in resource.getglobalVars():
            variable_type = errorVarTypes.get("VAR_GLOBAL", "var_local")
            # Generate variable block with modifier
            resrce += [("    VAR_GLOBAL", ())]
            if varlist.getconstant():
                resrce += [(" CONSTANT", (tagname, variable_type, (var_number, var_number + len(varlist.getvariable())), "constant"))]
            elif varlist.getretain():
                resrce += [(" RETAIN", (tagname, variable_type, (var_number, var_number + len(varlist.getvariable())), "retain"))]
            elif varlist.getnonretain():
                resrce += [(" NON_RETAIN", (tagname, variable_type, (var_number, var_number + len(varlist.getvariable())), "non_retain"))]
            resrce += [("\n", ())]
            # Generate any variable of this block
            for var in varlist.getvariable():
                vartype_content = var.gettype().getcontent()
                if vartype_content["name"] == "derived":
                    var_type = vartype_content["value"].getname()
                    self.GenerateDataType(var_type)
                else:
                    var_type = var.gettypeAsText()
                
                resrce += [("      ", ()),
                           (var.getname(), (tagname, variable_type, var_number, "name")),
                           (" ", ())]
                address = var.getaddress()
                # Generate variable address if exists
                if address:
                    resrce += [("AT ", ()),
                               (address, (tagname, variable_type, var_number, "location")),
                               (" ", ())]
                resrce += [(": ", ()),
                           (var.gettypeAsText(), (tagname, variable_type, var_number, "type"))]
                # Generate variable initial value if exists
                initial = var.getinitialValue()
                if initial:
                    resrce += [(" := ", ()),
                               (self.ComputeValue(initial.getvalue(), var_type), (tagname, variable_type, var_number, "initial value"))]
                resrce += [(";\n", ())]
                var_number += 1
            resrce += [("    END_VAR\n", ())]
        # Generate any task in the resource
        tasks = resource.gettask()
        task_number = 0
        for task in tasks:
            # Task declaration
            resrce += [("    TASK ", ()),
                       (task.getname(), (tagname, "task", task_number, "name")),
                       ("(", ())]
            args = []
            single = task.getsingle()
            # Single argument if exists
            if single:
                resrce += [("SINGLE := ", ()),
                           (single, (tagname, "task", task_number, "single")),
                           (",", ())]
            # Interval argument if exists
            interval = task.getinterval()
            if interval:
                resrce += [("INTERVAL := ", ()),
                           (interval, (tagname, "task", task_number, "interval")),
                           (",", ())]
##                resrce += [("INTERVAL := t#", ())]
##                if interval.hour != 0:
##                    resrce += [("%dh"%interval.hour, (tagname, "task", task_number, "interval", "hour"))]
##                if interval.minute != 0:
##                    resrce += [("%dm"%interval.minute, (tagname, "task", task_number, "interval", "minute"))]
##                if interval.second != 0:
##                    resrce += [("%ds"%interval.second, (tagname, "task", task_number, "interval", "second"))]
##                if interval.microsecond != 0:
##                    resrce += [("%dms"%(interval.microsecond / 1000), (tagname, "task", task_number, "interval", "millisecond"))]
##                resrce += [(",", ())]
            # Priority argument
            resrce += [("PRIORITY := ", ()), 
                       ("%d"%task.getpriority(), (tagname, "task", task_number, "priority")),
                       (");\n", ())]
            task_number += 1
        instance_number = 0
        # Generate any program assign to each task
        for task in tasks:
            for instance in task.getpouInstance():
                resrce += [("    PROGRAM ", ()),
                           (instance.getname(), (tagname, "instance", instance_number, "name")),
                           (" WITH ", ()),
                           (task.getname(), (tagname, "instance", instance_number, "task")),
                           (" : ", ()),
                           (instance.gettypeName(), (tagname, "instance", instance_number, "type")),
                           (";\n", ())]
                instance_number += 1
        # Generate any program assign to no task
        for instance in resource.getpouInstance():
            resrce += [("    PROGRAM ", ()),
                           (instance.getname(), (tagname, "instance", instance_number, "name")),
                           (" : ", ()),
                           (instance.gettypeName(), (tagname, "instance", instance_number, "type")),
                           (";\n", ())]
            instance_number += 1
        resrce += [("  END_RESOURCE\n", ())]
        return resrce
    
    # Generate the entire program for current project
    def GenerateProgram(self):        
        # Find all data types defined
        for datatype in self.Project.getdataTypes():
            self.DatatypeComputed[datatype.getname()] = False
        # Find all data types defined
        for pou in self.Project.getpous():
            self.PouComputed[pou.getname()] = False
        # Generate data type declaration structure if there is at least one data 
        # type defined
        if len(self.DatatypeComputed) > 0:
            self.Program += [("TYPE\n", ())]
            # Generate every data types defined
            for datatype_name in self.DatatypeComputed.keys():
                self.GenerateDataType(datatype_name)
            self.Program += [("END_TYPE\n\n", ())]
        # Generate every POUs defined
        for pou_name in self.PouComputed.keys():
            self.GeneratePouProgram(pou_name)
        # Generate every configurations defined
        for config in self.Project.getconfigurations():
            self.Program += self.GenerateConfiguration(config)
    
    # Return generated program
    def GetGeneratedProgram(self):
        return self.Program


#-------------------------------------------------------------------------------
#                           Generator of POU programs
#-------------------------------------------------------------------------------


class PouProgramGenerator:
    
    # Create a new POU program generator
    def __init__(self, parent, name, type, errors, warnings):
        # Keep Reference to the parent generator
        self.ParentGenerator = parent
        self.Name = name
        self.Type = type
        self.TagName = self.ParentGenerator.Controler.ComputePouName(name)
        self.CurrentIndent = "  "
        self.ReturnType = None
        self.Interface = []
        self.InitialSteps = []
        self.ComputedBlocks = {}
        self.ComputedConnectors = {}
        self.ConnectionTypes = {}
        self.RelatedConnections = []
        self.SFCNetworks = {"Steps":{}, "Transitions":{}, "Actions":{}}
        self.SFCComputedBlocks = []
        self.ActionNumber = 0
        self.Program = []
        self.Errors = errors
        self.Warnings = warnings
    
    def GetBlockType(self, type, inputs=None):
        return self.ParentGenerator.Controler.GetBlockType(type, inputs)
    
    def IndentLeft(self):
        if len(self.CurrentIndent) >= 2:
            self.CurrentIndent = self.CurrentIndent[:-2]
    
    def IndentRight(self):
        self.CurrentIndent += "  "
    
    # Generator of unique ID for inline actions
    def GetActionNumber(self):
        self.ActionNumber += 1
        return self.ActionNumber
    
    # Test if a variable has already been defined
    def IsAlreadyDefined(self, name):
        for list_type, option, located, vars in self.Interface:
            for var_type, var_name, var_address, var_initial in vars:
                if name == var_name:
                    return True
        return False
    
    # Return the type of a variable defined in interface
    def GetVariableType(self, name):
        parts = name.split('.')
        current_type = None
        if len(parts) > 0:
            name = parts.pop(0)
            for list_type, option, located, vars in self.Interface:
                for var_type, var_name, var_address, var_initial in vars:
                    if name == var_name:
                        current_type = var_type
                        break
            while current_type is not None and len(parts) > 0:
                blocktype = self.ParentGenerator.Controler.GetBlockType(current_type)
                if blocktype is not None:
                    name = parts.pop(0)
                    current_type = None
                    for var_name, var_type, var_modifier in blocktype["inputs"] + blocktype["outputs"]:
                        if var_name == name:
                            current_type = var_type
                            break
                else:
                    tagname = self.ParentGenerator.Controler.ComputeDataTypeName(current_type)
                    infos = self.ParentGenerator.Controler.GetDataTypeInfos(tagname)
                    if infos is not None and infos["type"] == "Structure":
                        name = parts.pop(0)
                        current_type = None
                        for element in infos["elements"]:
                            if element["Name"] == name:
                                current_type = element["Type"]
                                break
        return current_type
    
    # Return connectors linked by a connection to the given connector
    def GetConnectedConnector(self, connector, body):
        links = connector.getconnections()
        if links and len(links) == 1:
            return self.GetLinkedConnector(links[0], body)
        return None        

    def GetLinkedConnector(self, link, body):
        parameter = link.getformalParameter()
        instance = body.getcontentInstance(link.getrefLocalId())
        if isinstance(instance, (plcopen.fbdObjects_inVariable, plcopen.fbdObjects_inOutVariable, plcopen.commonObjects_continuation, plcopen.ldObjects_contact, plcopen.ldObjects_coil)):
            return instance.connectionPointOut
        elif isinstance(instance, plcopen.fbdObjects_block):
            outputvariables = instance.outputVariables.getvariable()
            if len(outputvariables) == 1:
                return outputvariables[0].connectionPointOut
            elif parameter:
                for variable in outputvariables:
                    if variable.getformalParameter() == parameter:
                        return variable.connectionPointOut
            else:
                point = link.getposition()[-1]
                for variable in outputvariables:
                    relposition = variable.connectionPointOut.getrelPositionXY()
                    blockposition = instance.getposition()
                    if point.x == blockposition.x + relposition[0] and point.y == blockposition.y + relposition[1]:
                        return variable.connectionPointOut
        elif isinstance(instance, plcopen.ldObjects_leftPowerRail):
            outputconnections = instance.getconnectionPointOut()
            if len(outputconnections) == 1:
                return outputconnections[0]
            else:
                point = link.getposition()[-1]
                for outputconnection in outputconnections:
                    relposition = outputconnection.getrelPositionXY()
                    powerrailposition = instance.getposition()
                    if point.x == powerrailposition.x + relposition[0] and point.y == powerrailposition.y + relposition[1]:
                        return outputconnection
        return None
        
    def ExtractRelatedConnections(self, connection):
        for i, related in enumerate(self.RelatedConnections):
            if connection in related:
                return self.RelatedConnections.pop(i)
        return [connection]
    
    def ComputeInterface(self, pou):
        interface = pou.getinterface()
        if interface is not None:
            body = pou.getbody()
            if isinstance(body, ListType):
                body = body[0]
            body_content = body.getcontent()
            if self.Type == "FUNCTION":
                returntype_content = interface.getreturnType().getcontent()
                if returntype_content["name"] == "derived":
                    self.ReturnType = returntype_content["value"].getname()
                elif returntype_content["name"] in ["string", "wstring"]:
                    self.ReturnType = returntype_content["name"].upper()
                else:
                    self.ReturnType = returntype_content["name"]
            for varlist in interface.getcontent():
                variables = []
                located = []
                for var in varlist["value"].getvariable():
                    vartype_content = var.gettype().getcontent()
                    if vartype_content["name"] == "derived":
                        var_type = vartype_content["value"].getname()
                        blocktype = self.GetBlockType(var_type)
                        if blocktype is not None:
                            self.ParentGenerator.GeneratePouProgram(var_type)
                            if body_content["name"] in ["FBD", "LD", "SFC"]:
                                block = pou.getinstanceByName(var.getname())
                            else:
                                block = None
                            for variable in blocktype["initialise"](var_type, var.getname(), block):
                                if variable[2] is not None:
                                    located.append(variable)
                                else:
                                    variables.append(variable)
                        else:
                            self.ParentGenerator.GenerateDataType(var_type)
                            initial = var.getinitialValue()
                            if initial:
                                initial_value = initial.getvalue()
                            else:
                                initial_value = None
                            address = var.getaddress()
                            if address is not None:
                                located.append((vartype_content["value"].getname(), var.getname(), address, initial_value))
                            else:
                                variables.append((vartype_content["value"].getname(), var.getname(), None, initial_value))
                    else:
                        var_type = var.gettypeAsText()
                        initial = var.getinitialValue()
                        if initial:
                            initial_value = initial.getvalue()
                        else:
                            initial_value = None
                        address = var.getaddress()
                        if address is not None:
                            located.append((var_type, var.getname(), address, initial_value))
                        else:
                            variables.append((var_type, var.getname(), None, initial_value))
                if varlist["value"].getconstant():
                    option = "CONSTANT"
                elif varlist["value"].getretain():
                    option = "RETAIN"
                elif varlist["value"].getnonretain():
                    option = "NON_RETAIN"
                else:
                    option = None
                if len(variables) > 0:
                    self.Interface.append((varTypeNames[varlist["name"]], option, False, variables))
                if len(located) > 0:
                    self.Interface.append((varTypeNames[varlist["name"]], option, True, located))
        
    def ComputeConnectionTypes(self, pou):
        body = pou.getbody()
        if isinstance(body, ListType):
            body = body[0]
        body_content = body.getcontent()
        body_type = body_content["name"]
        if body_type in ["FBD", "LD", "SFC"]:
            undefined_blocks = []
            for instance in body.getcontentInstances():
                if isinstance(instance, (plcopen.fbdObjects_inVariable, plcopen.fbdObjects_outVariable, plcopen.fbdObjects_inOutVariable)):
                    expression = instance.getexpression()
                    var_type = self.GetVariableType(expression)
                    if isinstance(pou, plcopen.transitions_transition) and expression == pou.getname():
                        var_type = "BOOL"
                    elif (not isinstance(pou, (plcopen.transitions_transition, plcopen.actions_action)) and
                          pou.getpouType() == "function" and expression == pou.getname()):
                        returntype_content = pou.interface.getreturnType().getcontent()
                        if returntype_content["name"] == "derived":
                            var_type = returntype_content["value"].getname()
                        elif returntype_content["name"] in ["string", "wstring"]:
                            var_type = returntype_content["name"].upper()
                        else:
                            var_type = returntype_content["name"]
                    elif var_type is None:
                        parts = expression.split("#")
                        if len(parts) > 1:
                            var_type = parts[0]
                        elif expression.startswith("'"):
                            var_type = "STRING"
                        elif expression.startswith('"'):
                            var_type = "WSTRING"
                    if var_type is not None:
                        if isinstance(instance, (plcopen.fbdObjects_inVariable, plcopen.fbdObjects_inOutVariable)):
                            for connection in self.ExtractRelatedConnections(instance.connectionPointOut):
                                self.ConnectionTypes[connection] = var_type
                        if isinstance(instance, (plcopen.fbdObjects_outVariable, plcopen.fbdObjects_inOutVariable)):
                            self.ConnectionTypes[instance.connectionPointIn] = var_type
                            connected = self.GetConnectedConnector(instance.connectionPointIn, body)
                            if connected and not self.ConnectionTypes.has_key(connected):
                                for connection in self.ExtractRelatedConnections(connected):
                                    self.ConnectionTypes[connection] = var_type
                elif isinstance(instance, (plcopen.ldObjects_contact, plcopen.ldObjects_coil)):
                    for connection in self.ExtractRelatedConnections(instance.connectionPointOut):
                        self.ConnectionTypes[connection] = "BOOL"
                    self.ConnectionTypes[instance.connectionPointIn] = "BOOL"
                    connected = self.GetConnectedConnector(instance.connectionPointIn, body)
                    if connected and not self.ConnectionTypes.has_key(connected):
                        for connection in self.ExtractRelatedConnections(connected):
                            self.ConnectionTypes[connection] = "BOOL"
                elif isinstance(instance, plcopen.ldObjects_leftPowerRail):
                    for connection in instance.getconnectionPointOut():
                        for related in self.ExtractRelatedConnections(connection):
                            self.ConnectionTypes[related] = "BOOL"
                elif isinstance(instance, plcopen.ldObjects_rightPowerRail):
                    for connection in instance.getconnectionPointIn():
                        self.ConnectionTypes[connection] = "BOOL"
                        connected = self.GetConnectedConnector(connection, body)
                        if connected and not self.ConnectionTypes.has_key(connected):
                            for connection in self.ExtractRelatedConnections(connected):
                                self.ConnectionTypes[connection] = "BOOL"
                elif isinstance(instance, plcopen.sfcObjects_transition):
                    content = instance.condition.getcontent()
                    if content["name"] == "connection" and len(content["value"]) == 1:
                        connected = self.GetLinkedConnector(content["value"][0], body)
                        if connected and not self.ConnectionTypes.has_key(connected):
                            for connection in self.ExtractRelatedConnections(connected):
                                self.ConnectionTypes[connection] = "BOOL"
                elif isinstance(instance, plcopen.commonObjects_continuation):
                    name = instance.getname()
                    connector = None
                    var_type = "ANY"
                    for element in body.getcontentInstances():
                        if isinstance(element, plcopen.commonObjects_connector) and element.getname() == name:
                            if connector is not None:
                                raise PLCGenException, _("More than one connector found corresponding to \"%s\" continuation in \"%s\" POU")%(name, self.Name)
                            connector = element
                    if connector is not None:
                        undefined = [instance.connectionPointOut, connector.connectionPointIn]
                        connected = self.GetConnectedConnector(connector.connectionPointIn, body)
                        if connected:
                            undefined.append(connected)
                        related = []
                        for connection in undefined:
                            if self.ConnectionTypes.has_key(connection):
                                var_type = self.ConnectionTypes[connection]
                            else:
                                related.extend(self.ExtractRelatedConnections(connection))
                        if var_type.startswith("ANY") and len(related) > 0:
                            self.RelatedConnections.append(related)
                        else:
                            for connection in related:
                                self.ConnectionTypes[connection] = var_type
                    else:
                        raise PLCGenException, _("No connector found corresponding to \"%s\" continuation in \"%s\" POU")%(name, self.Name)
                elif isinstance(instance, plcopen.fbdObjects_block):
                    block_infos = self.GetBlockType(instance.gettypeName(), "undefined")
                    if block_infos is not None:
                        self.ComputeBlockInputTypes(instance, block_infos, body)
                    else:
                        for variable in instance.inputVariables.getvariable():
                            connected = self.GetConnectedConnector(variable.connectionPointIn, body)
                            if connected is not None:
                                var_type = self.ConnectionTypes.get(connected, None)
                                if var_type is not None:
                                    self.ConnectionTypes[variable.connectionPointIn] = var_type
                                else:
                                    related = self.ExtractRelatedConnections(connected)
                                    related.append(variable.connectionPointIn)
                                    self.RelatedConnections.append(related)
                        undefined_blocks.append(instance)
            for instance in undefined_blocks:
                block_infos = self.GetBlockType(instance.gettypeName(), tuple([self.ConnectionTypes.get(variable.connectionPointIn, "ANY") for variable in instance.inputVariables.getvariable() if variable.getformalParameter() != "EN"]))
                if block_infos is not None:
                    self.ComputeBlockInputTypes(instance, block_infos, body)
                else:
                    raise PLCGenException, _("No informations found for \"%s\" block")%(instance.gettypeName())
            if body_type == "SFC":
                previous_tagname = self.TagName
                for action in pou.getactionList():
                    self.TagName = self.ParentGenerator.Controler.ComputePouActionName(self.Name, action.getname())
                    self.ComputeConnectionTypes(action)
                for transition in pou.gettransitionList():
                    self.TagName = self.ParentGenerator.Controler.ComputePouTransitionName(self.Name, transition.getname())
                    self.ComputeConnectionTypes(transition)
                self.TagName = previous_tagname
                
    def ComputeBlockInputTypes(self, instance, block_infos, body):
        undefined = {}
        for variable in instance.outputVariables.getvariable():
            output_name = variable.getformalParameter()
            if output_name == "ENO":
                for connection in self.ExtractRelatedConnections(variable.connectionPointOut):
                    self.ConnectionTypes[connection] = "BOOL"
            else:
                for oname, otype, oqualifier in block_infos["outputs"]:
                    if output_name == oname:
                        if otype.startswith("ANY"):
                            if not undefined.has_key(otype):
                                undefined[otype] = []
                            undefined[otype].append(variable.connectionPointOut)
                        elif not self.ConnectionTypes.has_key(variable.connectionPointOut):
                            for connection in self.ExtractRelatedConnections(variable.connectionPointOut):
                                self.ConnectionTypes[connection] = otype
        for variable in instance.inputVariables.getvariable():
            input_name = variable.getformalParameter()
            if input_name == "EN":
                for connection in self.ExtractRelatedConnections(variable.connectionPointIn):
                    self.ConnectionTypes[connection] = "BOOL"
            else:
                for iname, itype, iqualifier in block_infos["inputs"]:
                    if input_name == iname:
                        connected = self.GetConnectedConnector(variable.connectionPointIn, body)
                        if itype.startswith("ANY"):
                            if not undefined.has_key(itype):
                                undefined[itype] = []
                            undefined[itype].append(variable.connectionPointIn)
                            if connected:
                                undefined[itype].append(connected)
                        else:
                            self.ConnectionTypes[variable.connectionPointIn] = itype
                            if connected and not self.ConnectionTypes.has_key(connected):
                                for connection in self.ExtractRelatedConnections(connected):
                                    self.ConnectionTypes[connection] = itype
        for var_type, connections in undefined.items():
            related = []
            for connection in connections:
                connection_type = self.ConnectionTypes.get(connection)
                if connection_type and not connection_type.startswith("ANY"):
                    var_type = connection_type
                else:
                    related.extend(self.ExtractRelatedConnections(connection))
            if var_type.startswith("ANY") and len(related) > 0:
                self.RelatedConnections.append(related)
            else:
                for connection in related:
                    self.ConnectionTypes[connection] = var_type

    def ComputeProgram(self, pou):
        body = pou.getbody()
        if isinstance(body, ListType):
            body = body[0]
        body_content = body.getcontent()
        body_type = body_content["name"]
        if body_type in ["IL","ST"]:
            text = body_content["value"].gettext()
            self.ParentGenerator.GeneratePouProgramInText(text.upper())
            self.Program = [(ReIndentText(text, len(self.CurrentIndent)), 
                            (self.TagName, "body", len(self.CurrentIndent)))]
        elif body_type == "SFC":
            self.IndentRight()
            for instance in body.getcontentInstances():
                if isinstance(instance, plcopen.sfcObjects_step):
                    self.GenerateSFCStep(instance, pou)
                elif isinstance(instance, plcopen.commonObjects_actionBlock):
                    self.GenerateSFCStepActions(instance, pou)
                elif isinstance(instance, plcopen.sfcObjects_transition):
                    self.GenerateSFCTransition(instance, pou)
                elif isinstance(instance, plcopen.sfcObjects_jumpStep):
                    self.GenerateSFCJump(instance, pou)
            if len(self.InitialSteps) > 0 and len(self.SFCComputedBlocks) > 0:
                action_name = "COMPUTE_FUNCTION_BLOCKS"
                action_infos = {"qualifier" : "S", "content" : action_name}
                self.SFCNetworks["Steps"][self.InitialSteps[0]]["actions"].append(action_infos)
                self.SFCNetworks["Actions"][action_name] = (self.SFCComputedBlocks, ())
                self.Program = []
            self.IndentLeft()
            for initialstep in self.InitialSteps:
                self.ComputeSFCStep(initialstep)
        else:
            otherInstances = {"outVariables&coils" : [], "blocks" : [], "connectors" : []}
            orderedInstances = []
            for instance in body.getcontentInstances():
                if isinstance(instance, (plcopen.fbdObjects_outVariable, plcopen.fbdObjects_inOutVariable, plcopen.fbdObjects_block)):
                    executionOrderId = instance.getexecutionOrderId()
                    if executionOrderId > 0:
                        orderedInstances.append((executionOrderId, instance))
                    elif isinstance(instance, (plcopen.fbdObjects_outVariable, plcopen.fbdObjects_inOutVariable)):
                        otherInstances["outVariables&coils"].append(instance)
                    elif isinstance(instance, plcopen.fbdObjects_block):
                        otherInstances["blocks"].append(instance)
                elif isinstance(instance, plcopen.commonObjects_connector):
                    otherInstances["connectors"].append(instance)
                elif isinstance(instance, plcopen.ldObjects_coil):
                    otherInstances["outVariables&coils"].append(instance)
            orderedInstances.sort()
            otherInstances["outVariables&coils"].sort(SortInstances)
            otherInstances["blocks"].sort(SortInstances)
            instances = [instance for (executionOrderId, instance) in orderedInstances]
            instances.extend(otherInstances["outVariables&coils"] + otherInstances["blocks"] + otherInstances["connectors"])
            for instance in instances:
                if isinstance(instance, (plcopen.fbdObjects_outVariable, plcopen.fbdObjects_inOutVariable)):
                    connections = instance.connectionPointIn.getconnections()
                    if connections is not None:
                        expression = self.ComputeExpression(body, connections)
                        self.Program += [(self.CurrentIndent, ()),
                                         (instance.getexpression(), (self.TagName, "io_variable", instance.getlocalId(), "expression")),
                                         (" := ", ())]
                        self.Program += expression
                        self.Program += [(";\n", ())]
                elif isinstance(instance, plcopen.fbdObjects_block):
                    block_type = instance.gettypeName()
                    self.ParentGenerator.GeneratePouProgram(block_type)
                    block_infos = self.GetBlockType(block_type, tuple([self.ConnectionTypes.get(variable.connectionPointIn, "ANY") for variable in instance.inputVariables.getvariable() if variable.getformalParameter() != "EN"]))
                    if block_infos is None:
                        block_infos = self.GetBlockType(block_type)
                    if block_infos is None:
                        raise PLCGenException, _("Undefined block type \"%s\" in \"%s\" POU")%(block_type, self.Name)
                    block_infos["generate"](self, instance, block_infos, body, None)
                elif isinstance(instance, plcopen.commonObjects_connector):
                    connector = instance.getname()
                    if self.ComputedConnectors.get(connector, None):
                        continue 
                    self.ComputedConnectors[connector] = self.ComputeExpression(body, instance.connectionPointIn.getconnections())
                elif isinstance(instance, plcopen.ldObjects_coil):
                    connections = instance.connectionPointIn.getconnections()
                    if connections is not None:
                        coil_info = (self.TagName, "coil", instance.getlocalId())
                        expression = self.ExtractModifier(instance, self.ComputeExpression(body, connections), coil_info)
                        self.Program += [(self.CurrentIndent, ())]
                        self.Program += [(instance.getvariable(), coil_info + ("reference",))]
                        self.Program += [(" := ", ())] + expression + [(";\n", ())]
                        
    def FactorizePaths(self, paths):
        same_paths = {}
        uncomputed_index = range(len(paths))
        factorized_paths = []
        for num, path in enumerate(paths):
            if type(path) == ListType:
                if len(path) > 1:
                    str_path = str(path[-1:])
                    same_paths.setdefault(str_path, [])
                    same_paths[str_path].append((path[:-1], num))
            else:
                factorized_paths.append(path)
                uncomputed_index.remove(num)
        for same_path, elements in same_paths.items():
            if len(elements) > 1:
                elements_paths = self.FactorizePaths([path for path, num in elements])
                if len(elements_paths) > 1:
                    factorized_paths.append([tuple(elements_paths)] + eval(same_path))        
                else:
                    factorized_paths.append(elements_paths + eval(same_path))
                for path, num in elements:
                    uncomputed_index.remove(num)
        for num in uncomputed_index:
            factorized_paths.append(paths[num])
        factorized_paths.sort()
        return factorized_paths

    def GeneratePaths(self, connections, body, order = False, to_inout = False):
        paths = []
        for connection in connections:
            localId = connection.getrefLocalId()
            next = body.getcontentInstance(localId)
            if isinstance(next, plcopen.ldObjects_leftPowerRail):
                paths.append(None)
            elif isinstance(next, (plcopen.fbdObjects_inVariable, plcopen.fbdObjects_inOutVariable)):
                paths.append(str([(next.getexpression(), (self.TagName, "io_variable", localId, "expression"))]))
            elif isinstance(next, plcopen.fbdObjects_block):
                block_type = next.gettypeName()
                self.ParentGenerator.GeneratePouProgram(block_type)
                block_infos = self.GetBlockType(block_type, tuple([self.ConnectionTypes.get(variable.connectionPointIn, "ANY") for variable in next.inputVariables.getvariable() if variable.getformalParameter() != "EN"]))
                if block_infos is None:
                    block_infos = self.GetBlockType(block_type)
                if block_infos is None:
                    raise PLCGenException, _("Undefined block type \"%s\" in \"%s\" POU")%(block_type, self.Name)
                paths.append(str(block_infos["generate"](self, next, block_infos, body, connection, order, to_inout)))
            elif isinstance(next, plcopen.commonObjects_continuation):
                name = next.getname()
                computed_value = self.ComputedConnectors.get(name, None)
                if computed_value != None:
                    paths.append(str(computed_value))
                else:
                    connector = None
                    for instance in body.getcontentInstances():
                        if isinstance(instance, plcopen.commonObjects_connector) and instance.getname() == name:
                            if connector is not None:
                                raise PLCGenException, _("More than one connector found corresponding to \"%s\" continuation in \"%s\" POU")%(name, self.Name)
                            connector = instance
                    if connector is not None:
                        connections = connector.connectionPointIn.getconnections()
                        if connections is not None:
                            expression = self.ComputeExpression(body, connections, order)
                            self.ComputedConnectors[name] = expression
                            paths.append(str(expression))
                    else:
                        raise PLCGenException, _("No connector found corresponding to \"%s\" continuation in \"%s\" POU")%(name, self.Name)
            elif isinstance(next, plcopen.ldObjects_contact):
                contact_info = (self.TagName, "contact", next.getlocalId())
                variable = str(self.ExtractModifier(next, [(next.getvariable(), contact_info + ("reference",))], contact_info))
                result = self.GeneratePaths(next.connectionPointIn.getconnections(), body, order)
                if len(result) > 1:
                    factorized_paths = self.FactorizePaths(result)
                    if len(factorized_paths) > 1:
                        paths.append([variable, tuple(factorized_paths)])
                    else:
                        paths.append([variable] + factorized_paths)
                elif type(result[0]) == ListType:
                    paths.append([variable] + result[0])
                elif result[0] is not None:
                    paths.append([variable, result[0]])
                else:
                    paths.append(variable)
            elif isinstance(next, plcopen.ldObjects_coil):
                paths.append(str(self.GeneratePaths(next.connectionPointIn.getconnections(), body, order)))
        return paths

    def ComputePaths(self, paths, first = False):
        if type(paths) == TupleType:
            if None in paths:
                return [("TRUE", ())]
            else:
                vars = [self.ComputePaths(path) for path in paths]
                if first:
                    return JoinList([(" OR ", ())], vars)
                else:
                    return [("(", ())] + JoinList([(" OR ", ())], vars) + [(")", ())]
        elif type(paths) == ListType:
            vars = [self.ComputePaths(path) for path in paths]
            return JoinList([(" AND ", ())], vars)
        elif paths is None:
            return [("TRUE", ())]
        else:
            return eval(paths)

    def ComputeExpression(self, body, connections, order = False, to_inout = False):
        paths = self.GeneratePaths(connections, body, order, to_inout)
        if len(paths) > 1:
            factorized_paths = self.FactorizePaths(paths)
            if len(factorized_paths) > 1:
                paths = tuple(factorized_paths)
            else:
                paths = factorized_paths[0]
        else:
            paths = paths[0]
        return self.ComputePaths(paths, True)

    def ExtractModifier(self, variable, expression, var_info):
        if variable.getnegated():
            return [("NOT(", var_info + ("negated",))] + expression + [(")", ())]
        else:
            storage = variable.getstorage()
            if storage in ["set", "reset"]:
                self.Program += [(self.CurrentIndent + "IF ", var_info + (storage,))] + expression
                self.Program += [(" THEN\n  ", ())]
                if storage == "set":
                    return [("TRUE; (*set*)\n" + self.CurrentIndent + "END_IF", ())]
                else:
                    return [("FALSE; (*reset*)\n" + self.CurrentIndent + "END_IF", ())]
            edge = variable.getedge()
            if edge == "rising":
                return self.AddTrigger("R_TRIG", expression, var_info + ("rising",))
            elif edge == "falling":
                return self.AddTrigger("F_TRIG", expression, var_info + ("falling",))
        return expression
    
    def AddTrigger(self, edge, expression, var_info):
        if self.Interface[-1][0] != "VAR" or self.Interface[-1][1] is not None or self.Interface[-1][2]:
            self.Interface.append(("VAR", None, False, []))
        i = 1
        name = "%s%d"%(edge, i)
        while self.IsAlreadyDefined(name):
            i += 1
            name = "%s%d"%(edge, i)
        self.Interface[-1][3].append((edge, name, None, None))
        self.Program += [(self.CurrentIndent, ()), (name, var_info), ("(CLK := ", ())] 
        self.Program += expression
        self.Program += [(");\n", ())]
        return [("%s.Q"%name, var_info)]
    
    def ExtractDivergenceInput(self, divergence, pou):
        connectionPointIn = divergence.getconnectionPointIn()
        if connectionPointIn:
            connections = connectionPointIn.getconnections()
            if connections is not None and len(connections) == 1:
                instanceLocalId = connections[0].getrefLocalId()
                body = pou.getbody()
                if isinstance(body, ListType):
                    body = body[0]
                return body.getcontentInstance(instanceLocalId)
        return None

    def ExtractConvergenceInputs(self, convergence, pou):
        instances = []
        for connectionPointIn in convergence.getconnectionPointIn():
            connections = connectionPointIn.getconnections()
            if connections is not None and len(connections) == 1:
                instanceLocalId = connections[0].getrefLocalId()
                body = pou.getbody()
                if isinstance(body, ListType):
                    body = body[0]
                instances.append(body.getcontentInstance(instanceLocalId))
        return instances

    def GenerateSFCStep(self, step, pou):
        step_name = step.getname()
        if step_name not in self.SFCNetworks["Steps"].keys():
            if step.getinitialStep():
                self.InitialSteps.append(step_name)
            step_infos = {"id" : step.getlocalId(), 
                          "initial" : step.getinitialStep(), 
                          "transitions" : [], 
                          "actions" : []}
            self.SFCNetworks["Steps"][step_name] = step_infos
            if step.connectionPointIn:
                instances = []
                connections = step.connectionPointIn.getconnections()
                if connections is not None and len(connections) == 1:
                    instanceLocalId = connections[0].getrefLocalId()
                    body = pou.getbody()
                    if isinstance(body, ListType):
                        body = body[0]
                    instance = body.getcontentInstance(instanceLocalId)
                    if isinstance(instance, plcopen.sfcObjects_transition):
                        instances.append(instance)
                    elif isinstance(instance, plcopen.sfcObjects_selectionConvergence):
                        instances.extend(self.ExtractConvergenceInputs(instance, pou))
                    elif isinstance(instance, plcopen.sfcObjects_simultaneousDivergence):
                        transition = self.ExtractDivergenceInput(instance, pou)
                        if transition:
                            if isinstance(transition, plcopen.sfcObjects_transition):
                                instances.append(transition)
                            elif isinstance(transition, plcopen.sfcObjects_selectionConvergence):
                                instances.extend(self.ExtractConvergenceInputs(transition, pou))
                for instance in instances:
                    self.GenerateSFCTransition(instance, pou)
                    if instance in self.SFCNetworks["Transitions"].keys():
                        target_info = (self.TagName, "transition", instance.getlocalId(), "to", step_infos["id"])
                        self.SFCNetworks["Transitions"][instance]["to"].append([(step_name, target_info)])
    
    def GenerateSFCJump(self, jump, pou):
        jump_target = jump.gettargetName()
        if jump.connectionPointIn:
            instances = []
            connections = jump.connectionPointIn.getconnections()
            if connections is not None and len(connections) == 1:
                instanceLocalId = connections[0].getrefLocalId()
                body = pou.getbody()
                if isinstance(body, ListType):
                    body = body[0]
                instance = body.getcontentInstance(instanceLocalId)
                if isinstance(instance, plcopen.sfcObjects_transition):
                    instances.append(instance)
                elif isinstance(instance, plcopen.sfcObjects_selectionConvergence):
                    instances.extend(self.ExtractConvergenceInputs(instance, pou))
                elif isinstance(instance, plcopen.sfcObjects_simultaneousDivergence):
                    transition = self.ExtractDivergenceInput(instance, pou)
                    if transition:
                        if isinstance(transition, plcopen.sfcObjects_transition):
                            instances.append(transition)
                        elif isinstance(transition, plcopen.sfcObjects_selectionConvergence):
                            instances.extend(self.ExtractConvergenceInputs(transition, pou))
            for instance in instances:
                self.GenerateSFCTransition(instance, pou)
                if instance in self.SFCNetworks["Transitions"].keys():
                    target_info = (self.TagName, "jump", jump.getlocalId(), "target")
                    self.SFCNetworks["Transitions"][instance]["to"].append([(jump_target, target_info)])
    
    def GenerateSFCStepActions(self, actionBlock, pou):
        connections = actionBlock.connectionPointIn.getconnections()
        if connections is not None and len(connections) == 1:
            stepLocalId = connections[0].getrefLocalId()
            body = pou.getbody()
            if isinstance(body, ListType):
                body = body[0]
            step = body.getcontentInstance(stepLocalId)
            self.GenerateSFCStep(step, pou)
            step_name = step.getname()
            if step_name in self.SFCNetworks["Steps"].keys():
                actions = actionBlock.getactions()
                for i, action in enumerate(actions):
                    action_infos = {"id" : actionBlock.getlocalId(), 
                                    "qualifier" : action["qualifier"], 
                                    "content" : action["value"],
                                    "num" : i}
                    if "duration" in action:
                        action_infos["duration"] = action["duration"]
                    if "indicator" in action:
                        action_infos["indicator"] = action["indicator"]
                    if action["type"] == "reference":
                        self.GenerateSFCAction(action["value"], pou)
                    else:
                        action_name = "%s_INLINE%d"%(step_name.upper(), self.GetActionNumber())
                        self.SFCNetworks["Actions"][action_name] = ([(self.CurrentIndent, ()), 
                            (action["value"], (self.TagName, "action_block", action_infos["id"], "action", i, "inline")),
                            ("\n", ())], ())
                        action_infos["content"] = action_name
                    self.SFCNetworks["Steps"][step_name]["actions"].append(action_infos)
    
    def GenerateSFCAction(self, action_name, pou):
        if action_name not in self.SFCNetworks["Actions"].keys():
            actionContent = pou.getaction(action_name)
            if actionContent:
                previous_tagname = self.TagName
                self.TagName = self.ParentGenerator.Controler.ComputePouActionName(self.Name, action_name)
                self.ComputeProgram(actionContent)
                self.SFCNetworks["Actions"][action_name] = (self.Program, (self.TagName, "name"))
                self.Program = []
                self.TagName = previous_tagname
    
    def GenerateSFCTransition(self, transition, pou):
        if transition not in self.SFCNetworks["Transitions"].keys():
            steps = []
            connections = transition.connectionPointIn.getconnections()
            if connections is not None and len(connections) == 1:
                instanceLocalId = connections[0].getrefLocalId()
                body = pou.getbody()
                if isinstance(body, ListType):
                    body = body[0]
                instance = body.getcontentInstance(instanceLocalId)
                if isinstance(instance, plcopen.sfcObjects_step):
                    steps.append(instance)
                elif isinstance(instance, plcopen.sfcObjects_selectionDivergence):
                    step = self.ExtractDivergenceInput(instance, pou)
                    if step:
                        if isinstance(step, plcopen.sfcObjects_step):
                            steps.append(step)
                        elif isinstance(step, plcopen.sfcObjects_simultaneousConvergence):
                            steps.extend(self.ExtractConvergenceInputs(step, pou))
                elif isinstance(instance, plcopen.sfcObjects_simultaneousConvergence):
                    steps.extend(self.ExtractConvergenceInputs(instance, pou))
            transition_infos = {"id" : transition.getlocalId(), 
                                "priority": transition.getpriority(), 
                                "from": [], 
                                "to" : []}
            self.SFCNetworks["Transitions"][transition] = transition_infos
            transitionValues = transition.getconditionContent()
            if transitionValues["type"] == "inline":
                transition_infos["content"] = [("\n%s:= "%self.CurrentIndent, ()),
                                               (transitionValues["value"], (self.TagName, "transition", transition.getlocalId(), "inline")),
                                               (";\n", ())]
            elif transitionValues["type"] == "reference":
                transitionContent = pou.gettransition(transitionValues["value"])
                transitionType = transitionContent.getbodyType()
                transitionBody = transitionContent.getbody()
                previous_tagname = self.TagName
                self.TagName = self.ParentGenerator.Controler.ComputePouTransitionName(self.Name, transitionValues["value"])
                if transitionType == "IL":
                    transition_infos["content"] = [(":\n", ()),
                                                   (ReIndentText(transitionBody.gettext(), len(self.CurrentIndent)), (self.TagName, "body", len(self.CurrentIndent)))]
                elif transitionType == "ST":
                    transition_infos["content"] = [("\n", ()),
                                                   (ReIndentText(transitionBody.gettext(), len(self.CurrentIndent)), (self.TagName, "body", len(self.CurrentIndent)))]
                else:
                    for instance in transitionBody.getcontentInstances():
                        if isinstance(instance, plcopen.fbdObjects_outVariable) and instance.getexpression() == transitionValues["value"]\
                            or isinstance(instance, plcopen.ldObjects_coil) and instance.getvariable() == transitionValues["value"]:
                            connections = instance.connectionPointIn.getconnections()
                            if connections is not None:
                                expression = self.ComputeExpression(transitionBody, connections)
                                transition_infos["content"] = [("\n%s:= "%self.CurrentIndent, ())] + expression + [(";\n", ())]
                                self.SFCComputedBlocks += self.Program
                                self.Program = []
                    if not transition_infos.has_key("content"):
                        raise PLCGenException, _("Transition \"%s\" body must contain an output variable or coil referring to its name") % transitionValues["value"]
                self.TagName = previous_tagname
            elif transitionValues["type"] == "connection":
                body = pou.getbody()
                if isinstance(body, ListType):
                    body = body[0]
                connections = transition.getconnections()
                if connections is not None:
                    expression = self.ComputeExpression(body, connections)
                    transition_infos["content"] = [("\n%s:= "%self.CurrentIndent, ())] + expression + [(";\n", ())]
                    self.SFCComputedBlocks += self.Program
                    self.Program = []
            for step in steps:
                self.GenerateSFCStep(step, pou)
                step_name = step.getname()
                if step_name in self.SFCNetworks["Steps"].keys():
                    transition_infos["from"].append([(step_name, (self.TagName, "transition", transition.getlocalId(), "from", step.getlocalId()))])
                    self.SFCNetworks["Steps"][step_name]["transitions"].append(transition)

    def ComputeSFCStep(self, step_name):
        if step_name in self.SFCNetworks["Steps"].keys():
            step_infos = self.SFCNetworks["Steps"].pop(step_name)
            self.Program += [(self.CurrentIndent, ())]
            if step_infos["initial"]:
                self.Program += [("INITIAL_", ())]
            self.Program += [("STEP ", ()),
                             (step_name, (self.TagName, "step", step_infos["id"], "name")),
                             (":\n", ())]
            actions = []
            self.IndentRight()
            for action_infos in step_infos["actions"]:
                if action_infos.get("id", None) is not None:
                    action_info = (self.TagName, "action_block", action_infos["id"], "action", action_infos["num"])
                else:
                    action_info = ()
                actions.append(action_infos["content"])
                self.Program += [(self.CurrentIndent, ()),
                                 (action_infos["content"], action_info + ("reference",)),
                                 ("(", ()),
                                 (action_infos["qualifier"], action_info + ("qualifier",))]
                if "duration" in action_infos:
                    self.Program += [(", ", ()),
                                     (action_infos["duration"], action_info + ("duration",))]
                if "indicator" in action_infos:
                    self.Program += [(", ", ()),
                                     (action_infos["indicator"], action_info + ("indicator",))]
                self.Program += [(");\n", ())]
            self.IndentLeft()
            self.Program += [("%sEND_STEP\n\n"%self.CurrentIndent, ())]
            for action in actions:
                self.ComputeSFCAction(action)
            for transition in step_infos["transitions"]:
                self.ComputeSFCTransition(transition)
                
    def ComputeSFCAction(self, action_name):
        if action_name in self.SFCNetworks["Actions"].keys():
            action_content, action_info = self.SFCNetworks["Actions"].pop(action_name)
            self.Program += [("%sACTION "%self.CurrentIndent, ()),
                             (action_name, action_info),
                             (" :\n", ())]
            self.Program += action_content
            self.Program += [("%sEND_ACTION\n\n"%self.CurrentIndent, ())]
    
    def ComputeSFCTransition(self, transition):
        if transition in self.SFCNetworks["Transitions"].keys():
            transition_infos = self.SFCNetworks["Transitions"].pop(transition)
            self.Program += [("%sTRANSITION"%self.CurrentIndent, ())]
            if transition_infos["priority"] != None:
                self.Program += [(" (PRIORITY := ", ()),
                                 ("%d"%transition_infos["priority"], (self.TagName, "transition", transition_infos["id"], "priority")),
                                 (")", ())]
            self.Program += [(" FROM ", ())]
            if len(transition_infos["from"]) > 1:
                self.Program += [("(", ())]
                self.Program += JoinList([(", ", ())], transition_infos["from"])
                self.Program += [(")", ())]
            elif len(transition_infos["from"]) == 1:
                self.Program += transition_infos["from"][0]
            else:
                raise PLCGenException, _("Transition with content \"%s\" not connected to a previous step in \"%s\" POU")%(transition_infos["content"], self.Name)
            self.Program += [(" TO ", ())]
            if len(transition_infos["to"]) > 1:
                self.Program += [("(", ())]
                self.Program += JoinList([(", ", ())], transition_infos["to"])
                self.Program += [(")", ())]
            elif len(transition_infos["to"]) == 1:
                self.Program += transition_infos["to"][0]
            else:
                raise PLCGenException, _("Transition with content \"%s\" not connected to a next step in \"%s\" POU")%(transition_infos["content"], self.Name)
            self.Program += transition_infos["content"]
            self.Program += [("%sEND_TRANSITION\n\n"%self.CurrentIndent, ())]
            for [(step_name, step_infos)] in transition_infos["to"]:
                self.ComputeSFCStep(step_name)
    
    def GenerateProgram(self, pou):
        self.ComputeInterface(pou)
        self.ComputeConnectionTypes(pou)
        self.ComputeProgram(pou)
        
        program = [("%s "%self.Type, ()),
                   (self.Name, (self.TagName, "name"))]
        if self.ReturnType:
            program += [(" : ", ()),
                        (self.ReturnType, (self.TagName, "return"))]
        program += [("\n", ())]
        if len(self.Interface) == 0:
            raise PLCGenException, _("No variable defined in \"%s\" POU")%self.Name
        if len(self.Program) == 0 :
            raise PLCGenException, _("No body defined in \"%s\" POU")%self.Name
        var_number = 0
        for list_type, option, located, variables in self.Interface:
            variable_type = errorVarTypes.get(list_type, "var_local")
            program += [("  %s"%list_type, ())]
            if option is not None:
                program += [(" %s"%option, (self.TagName, variable_type, (var_number, var_number + len(variables)), option.lower()))]
            program += [("\n", ())]
            for var_type, var_name, var_address, var_initial in variables:
                program += [("    ", ())]
                if var_name:
                    program += [(var_name, (self.TagName, variable_type, var_number, "name")),
                                (" ", ())]
                if var_address != None:
                    program += [("AT ", ()),
                                (var_address, (self.TagName, variable_type, var_number, "location")),
                                (" ", ())]
                program += [(": ", ()),
                            (var_type, (self.TagName, variable_type, var_number, "type"))]
                if var_initial != None:
                    program += [(" := ", ()),
                                (self.ParentGenerator.ComputeValue(var_initial, var_type), (self.TagName, variable_type, var_number, "initial value"))]
                program += [(";\n", ())]
                var_number += 1
            program += [("  END_VAR\n", ())]
        program += [("\n", ())]
        program += self.Program
        program += [("END_%s\n\n"%self.Type, ())]
        return program

def GenerateCurrentProgram(controler, project, errors, warnings):
    generator = ProgramGenerator(controler, project, errors, warnings)
    generator.GenerateProgram()
    return generator.GetGeneratedProgram()

