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

from xml.dom import minidom
from types import StringType, UnicodeType, TupleType
import cPickle
import os,sys,re
import datetime
from time import localtime

from plcopen import plcopen
from plcopen.structures import *
from graphics.GraphicCommons import *
from PLCGenerator import *

duration_model = re.compile("(?:([0-9]{1,2})h)?(?:([0-9]{1,2})m(?!s))?(?:([0-9]{1,2})s)?(?:([0-9]{1,3}(?:\.[0-9]*)?)ms)?")

ITEMS_EDITABLE = [ITEM_PROJECT,
                  ITEM_POU,
                  ITEM_VARIABLE,
                  ITEM_TRANSITION,
                  ITEM_ACTION,
                  ITEM_CONFIGURATION,
                  ITEM_RESOURCE,
                  ITEM_DATATYPE
                 ] = range(8)

ITEMS_UNEDITABLE = [ITEM_DATATYPES,
                    ITEM_FUNCTION,
                    ITEM_FUNCTIONBLOCK,
                    ITEM_PROGRAM,
                    ITEM_TRANSITIONS,
                    ITEM_ACTIONS,
                    ITEM_CONFIGURATIONS,
                    ITEM_RESOURCES,
                    ITEM_PROPERTIES
                   ] = range(8, 17)
 
ITEMS_VARIABLE = [ITEM_VAR_LOCAL,
                  ITEM_VAR_GLOBAL,
                  ITEM_VAR_EXTERNAL,
                  ITEM_VAR_TEMP,
                  ITEM_VAR_INPUT,
                  ITEM_VAR_OUTPUT,
                  ITEM_VAR_INOUT
                 ] = range(17, 24)

VAR_CLASS_INFOS = {"Local" :    (plcopen.interface_localVars,    ITEM_VAR_LOCAL),
                   "Global" :   (plcopen.interface_globalVars,   ITEM_VAR_GLOBAL),
                   "External" : (plcopen.interface_externalVars, ITEM_VAR_EXTERNAL),
                   "Temp" :     (plcopen.interface_tempVars,     ITEM_VAR_TEMP),
                   "Input" :    (plcopen.interface_inputVars,    ITEM_VAR_INPUT),
                   "Output" :   (plcopen.interface_outputVars,   ITEM_VAR_OUTPUT),
                   "InOut" :    (plcopen.interface_inOutVars,    ITEM_VAR_INOUT)
                  }

POU_TYPES = {"program": ITEM_PROGRAM,
             "functionBlock": ITEM_FUNCTIONBLOCK,
             "function": ITEM_FUNCTION,
            }

LOCATIONS_ITEMS = [LOCATION_CONFNODE,
                   LOCATION_MODULE,
                   LOCATION_GROUP,
                   LOCATION_VAR_INPUT,
                   LOCATION_VAR_OUTPUT,
                   LOCATION_VAR_MEMORY] = range(6)

ScriptDirectory = os.path.split(os.path.realpath(__file__))[0]

def GetUneditableNames():
    _ = lambda x:x
    return [_("User-defined POUs"), _("Functions"), _("Function Blocks"), 
            _("Programs"), _("Data Types"), _("Transitions"), _("Actions"), 
            _("Configurations"), _("Resources"), _("Properties")]
UNEDITABLE_NAMES = GetUneditableNames()
[USER_DEFINED_POUS, FUNCTIONS, FUNCTION_BLOCKS, PROGRAMS, 
 DATA_TYPES, TRANSITIONS, ACTIONS, CONFIGURATIONS, 
 RESOURCES, PROPERTIES] = UNEDITABLE_NAMES

#-------------------------------------------------------------------------------
#                         Undo Buffer for PLCOpenEditor
#-------------------------------------------------------------------------------

# Length of the buffer
UNDO_BUFFER_LENGTH = 20

"""
Class implementing a buffer of changes made on the current editing model
"""
class UndoBuffer:

    # Constructor initialising buffer
    def __init__(self, currentstate, issaved = False):
        self.Buffer = []
        self.CurrentIndex = -1
        self.MinIndex = -1
        self.MaxIndex = -1
        # if current state is defined
        if currentstate:
            self.CurrentIndex = 0
            self.MinIndex = 0
            self.MaxIndex = 0
        # Initialising buffer with currentstate at the first place
        for i in xrange(UNDO_BUFFER_LENGTH):
            if i == 0:
                self.Buffer.append(currentstate)
            else:
                self.Buffer.append(None)
        # Initialising index of state saved
        if issaved:
            self.LastSave = 0
        else:
            self.LastSave = -1
    
    # Add a new state in buffer
    def Buffering(self, currentstate):
        self.CurrentIndex = (self.CurrentIndex + 1) % UNDO_BUFFER_LENGTH
        self.Buffer[self.CurrentIndex] = currentstate
        # Actualising buffer limits
        self.MaxIndex = self.CurrentIndex
        if self.MinIndex == self.CurrentIndex:
            # If the removed state was the state saved, there is no state saved in the buffer
            if self.LastSave == self.MinIndex:
                self.LastSave = -1
            self.MinIndex = (self.MinIndex + 1) % UNDO_BUFFER_LENGTH
        self.MinIndex = max(self.MinIndex, 0)
    
    # Return current state of buffer
    def Current(self):
        return self.Buffer[self.CurrentIndex]
    
    # Change current state to previous in buffer and return new current state
    def Previous(self):
        if self.CurrentIndex != self.MinIndex:
            self.CurrentIndex = (self.CurrentIndex - 1) % UNDO_BUFFER_LENGTH
            return self.Buffer[self.CurrentIndex]
        return None
    
    # Change current state to next in buffer and return new current state
    def Next(self):
        if self.CurrentIndex != self.MaxIndex:
            self.CurrentIndex = (self.CurrentIndex + 1) % UNDO_BUFFER_LENGTH
            return self.Buffer[self.CurrentIndex]
        return None
    
    # Return True if current state is the first in buffer
    def IsFirst(self):
        return self.CurrentIndex == self.MinIndex
    
    # Return True if current state is the last in buffer
    def IsLast(self):
        return self.CurrentIndex == self.MaxIndex

    # Note that current state is saved
    def CurrentSaved(self):
        self.LastSave = self.CurrentIndex
        
    # Return True if current state is saved
    def IsCurrentSaved(self):
        return self.LastSave == self.CurrentIndex


#-------------------------------------------------------------------------------
#                           Controler for PLCOpenEditor
#-------------------------------------------------------------------------------

"""
Class which controls the operations made on the plcopen model and answers to view requests
"""
class PLCControler:
    
    # Create a new PLCControler
    def __init__(self):
        self.LastNewIndex = 0
        self.Reset()
    
    # Reset PLCControler internal variables
    def Reset(self):
        self.Project = None
        self.ProjectBufferEnabled = True
        self.ProjectBuffer = None
        self.ProjectSaved = True
        self.Buffering = False
        self.FilePath = ""
        self.FileName = ""
        self.ProgramChunks = []
        self.ProgramOffset = 0
        self.NextCompiledProject = None
        self.CurrentCompiledProject = None
        self.ConfNodeTypes = []
        self.ProgramFilePath = ""
        
    def GetQualifierTypes(self):
        return plcopen.QualifierList

    def GetProject(self, debug = False):
        if debug and self.CurrentCompiledProject is not None:
            return self.CurrentCompiledProject
        else:
            return self.Project

#-------------------------------------------------------------------------------
#                         Project management functions
#-------------------------------------------------------------------------------

    # Return if a project is opened
    def HasOpenedProject(self):
        return self.Project is not None

    # Create a new project by replacing the current one
    def CreateNewProject(self, properties):
        # Create the project
        self.Project = plcopen.project()
        properties["creationDateTime"] = datetime.datetime(*localtime()[:6])
        self.Project.setfileHeader(properties)
        self.Project.setcontentHeader(properties)
        self.SetFilePath("")
        # Initialize the project buffer
        self.CreateProjectBuffer(False)
        self.ProgramChunks = []
        self.ProgramOffset = 0
        self.NextCompiledProject = self.Copy(self.Project)
        self.CurrentCompiledProject = None
        self.Buffering = False
    
    # Return project data type names
    def GetProjectDataTypeNames(self, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            return [datatype.getname() for datatype in project.getdataTypes()]
        return []
    
    # Return project pou names
    def GetProjectPouNames(self, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            return [pou.getname() for pou in project.getpous()]
        return []
    
    # Return project pou names
    def GetProjectConfigNames(self, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            return [config.getname() for config in project.getconfigurations()]
        return []
    
    # Return project pou variables
    def GetProjectPouVariables(self, pou_name = None, debug = False):
        variables = []
        project = self.GetProject(debug)
        if project is not None:
            for pou in project.getpous():
                if pou_name is None or pou_name == pou.getname():
                    variables.extend([var["Name"] for var in self.GetPouInterfaceVars(pou, debug)])
                    for transition in pou.gettransitionList():
                        variables.append(transition.getname())
                    for action in pou.getactionList():
                        variables.append(action.getname())
        return variables
    
    # Return file path if project is an open file
    def GetFilePath(self):
        return self.FilePath
    
    # Return file path if project is an open file
    def GetProgramFilePath(self):
        return self.ProgramFilePath
    
    # Return file name and point out if file is up to date
    def GetFilename(self):
        if self.Project is not None:
            if self.ProjectIsSaved():
                return self.FileName
            else:
                return "~%s~"%self.FileName
        return ""
    
    # Change file path and save file name or create a default one if file path not defined
    def SetFilePath(self, filepath):
        self.FilePath = filepath
        if filepath == "":
            self.LastNewIndex += 1
            self.FileName = _("Unnamed%d")%self.LastNewIndex
        else:
            self.FileName = os.path.splitext(os.path.basename(filepath))[0]
    
    # Change project properties
    def SetProjectProperties(self, name = None, properties = None, buffer = True):
        if self.Project is not None:
            if name is not None:
                self.Project.setname(name)
            if properties is not None:
                self.Project.setfileHeader(properties)
                self.Project.setcontentHeader(properties)
            if buffer and (name is not None or properties is not None):
                self.BufferProject()
    
    # Return project name
    def GetProjectName(self, debug=False):
        project = self.GetProject(debug)
        if project is not None:
            return project.getname()
        return None
    
    # Return project properties
    def GetProjectProperties(self, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            properties = project.getfileHeader()
            properties.update(project.getcontentHeader())
            return properties
        return None
    
    # Return project informations
    def GetProjectInfos(self, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            infos = {"name": project.getname(), "type": ITEM_PROJECT}
            datatypes = {"name": DATA_TYPES, "type": ITEM_DATATYPES, "values":[]}
            for datatype in project.getdataTypes():
                datatypes["values"].append({"name": datatype.getname(), "type": ITEM_DATATYPE, 
                    "tagname": self.ComputeDataTypeName(datatype.getname()), "values": []})
            pou_types = {"function": {"name": FUNCTIONS, "type": ITEM_FUNCTION, "values":[]},
                         "functionBlock": {"name": FUNCTION_BLOCKS, "type": ITEM_FUNCTIONBLOCK, "values":[]},
                         "program": {"name": PROGRAMS, "type": ITEM_PROGRAM, "values":[]}}
            for pou in project.getpous():
                pou_type = pou.getpouType()
                pou_infos = {"name": pou.getname(), "type": ITEM_POU,
                             "tagname": self.ComputePouName(pou.getname())}
                pou_values = []
                if pou.getbodyType() == "SFC":
                    transitions = []
                    for transition in pou.gettransitionList():
                        transitions.append({"name": transition.getname(), "type": ITEM_TRANSITION, 
                            "tagname": self.ComputePouTransitionName(pou.getname(), transition.getname()), 
                            "values": []})
                    pou_values.append({"name": TRANSITIONS, "type": ITEM_TRANSITIONS, "values": transitions})
                    actions = []
                    for action in pou.getactionList():
                        actions.append({"name": action.getname(), "type": ITEM_ACTION, 
                            "tagname": self.ComputePouActionName(pou.getname(), action.getname()), 
                            "values": []})
                    pou_values.append({"name": ACTIONS, "type": ITEM_ACTIONS, "values": actions})
                if pou_type in pou_types:
                    pou_infos["values"] = pou_values
                    pou_types[pou_type]["values"].append(pou_infos)
            configurations = {"name": CONFIGURATIONS, "type": ITEM_CONFIGURATIONS, "values": []}
            for config in project.getconfigurations():
                config_name = config.getname()
                config_infos = {"name": config_name, "type": ITEM_CONFIGURATION, 
                    "tagname": self.ComputeConfigurationName(config.getname()), 
                    "values": []}
                resources = {"name": RESOURCES, "type": ITEM_RESOURCES, "values": []}
                for resource in config.getresource():
                    resource_name = resource.getname()
                    resource_infos = {"name": resource_name, "type": ITEM_RESOURCE, 
                        "tagname": self.ComputeConfigurationResourceName(config.getname(), resource.getname()), 
                        "values": []}
                    resources["values"].append(resource_infos)
                config_infos["values"] = [resources]
                configurations["values"].append(config_infos)
            infos["values"] = [datatypes, pou_types["function"], pou_types["functionBlock"], 
                               pou_types["program"], configurations]
            return infos
        return None

    def GetPouVariableInfos(self, project, variable, var_class, debug=False):
        vartype_content = variable.gettype().getcontent()
        if vartype_content["name"] == "derived":
            var_type = vartype_content["value"].getname()
            pou_type = None
            pou = project.getpou(var_type)
            if pou is not None:
                pou_type = pou.getpouType()
            edit = debug = pou_type is not None
            if pou_type is None:
                block_infos = self.GetBlockType(var_type, debug = debug)
                if block_infos is not None:
                    pou_type = block_infos["type"]
            if pou_type is not None:
                var_class = None
                if pou_type == "program":
                    var_class = ITEM_PROGRAM
                elif pou_type != "function":
                    var_class = ITEM_FUNCTIONBLOCK
                if var_class is not None:
                    return {"name": variable.getname(), 
                            "type": var_type, 
                            "class": var_class,
                            "edit": edit,
                            "debug": debug}
            elif var_type in self.GetDataTypes(debug = debug):
                return {"name": variable.getname(), 
                        "type": var_type, 
                        "class": var_class,
                        "edit": False,
                        "debug": False}
        elif vartype_content["name"] in ["string", "wstring"]:
            return {"name": variable.getname(), 
                    "type": vartype_content["name"].upper(), 
                    "class": var_class,
                    "edit": False,
                    "debug": True}
        else:
            return {"name": variable.getname(),
                    "type": vartype_content["name"], 
                    "class": var_class,
                    "edit": False,
                    "debug": True}
        return None

    def GetPouVariables(self, tagname, debug = False):
        vars = []
        pou_type = None
        project = self.GetProject(debug)
        if project is not None:
            words = tagname.split("::")
            if words[0] == "P":
                pou = project.getpou(words[1])
                if pou is not None:
                    pou_type = pou.getpouType()
                    if (pou_type in ["program", "functionBlock"] and 
                        pou.interface is not None):
                        # Extract variables from every varLists
                        for varlist_type, varlist in pou.getvars():
                            var_infos = VAR_CLASS_INFOS.get(varlist_type, None)
                            if var_infos is not None:
                                var_class = var_infos[1]
                            else:
                                var_class = ITEM_VAR_LOCAL
                            for variable in varlist.getvariable():
                                var_infos = self.GetPouVariableInfos(project, variable, var_class, debug)
                                if var_infos is not None:
                                    vars.append(var_infos)
                        if pou.getbodyType() == "SFC":
                            for transition in pou.gettransitionList():
                                vars.append({
                                    "name": transition.getname(),
                                    "type": None, 
                                    "class": ITEM_TRANSITION,
                                    "edit": True,
                                    "debug": True})
                            for action in pou.getactionList():
                                vars.append({
                                    "name": action.getname(),
                                    "type": None, 
                                    "class": ITEM_ACTION,
                                    "edit": True,
                                    "debug": True})
                        return {"class": POU_TYPES[pou_type],
                                "type": words[1],
                                "variables": vars,
                                "edit": True,
                                "debug": True}
                else:
                    block_infos = self.GetBlockType(words[1], debug = debug)
                    if (block_infos is not None and 
                        block_infos["type"] in ["program", "functionBlock"]):
                        for varname, vartype, varmodifier in block_infos["inputs"]:
                            vars.append({"name" : varname, 
                                         "type" : vartype, 
                                         "class" : ITEM_VAR_INPUT,
                                         "edit": False,
                                         "debug": True})
                        for varname, vartype, varmodifier in block_infos["outputs"]:
                            vars.append({"name" : varname, 
                                         "type" : vartype, 
                                         "class" : ITEM_VAR_OUTPUT,
                                         "edit": False,
                                         "debug": True})
                        return {"class": POU_TYPES[block_infos["type"]],
                                "type": None,
                                "variables": vars,
                                "edit": False,
                                "debug": False}
            elif words[0] in ['A', 'T']:
                pou_vars = self.GetPouVariables(self.ComputePouName(words[1]), debug)
                if pou_vars is not None:
                    if words[0] == 'A':
                        element_type = ITEM_ACTION
                    elif words[0] == 'T':
                        element_type = ITEM_TRANSITION
                    return {"class": element_type,
                            "type": None,
                            "variables": [var for var in pou_vars["variables"] 
                                          if var["class"] not in [ITEM_ACTION, ITEM_TRANSITION]],
                            "edit": True,
                            "debug": True}
            elif words[0] in ['C', 'R']:
                if words[0] == 'C':
                    element_type = ITEM_CONFIGURATION
                    element = project.getconfiguration(words[1])
                    if element is not None:
                        for resource in element.getresource():
                            vars.append({"name": resource.getname(),
                                         "type": None,
                                         "class": ITEM_RESOURCE,
                                         "edit": True,
                                         "debug": False})
                elif words[0] == 'R':
                    element_type = ITEM_RESOURCE
                    element = project.getconfigurationResource(words[1], words[2])
                    if element is not None:
                        for task in element.gettask():
                            for pou in task.getpouInstance():
                                vars.append({"name": pou.getname(),
                                             "type": pou.gettypeName(),
                                             "class": ITEM_PROGRAM,
                                             "edit": True,
                                             "debug": True})
                        for pou in element.getpouInstance():
                            vars.append({"name": pou.getname(),
                                         "type": pou.gettypeName(),
                                         "class": ITEM_PROGRAM,
                                         "edit": True,
                                         "debug": True})
                if element is not None:
                    for varlist in element.getglobalVars():
                        for variable in varlist.getvariable():
                            var_infos = self.GetPouVariableInfos(project, variable, ITEM_VAR_GLOBAL, debug)
                            if var_infos is not None:
                                vars.append(var_infos)
                    return {"class": element_type,
                            "type": None,
                            "variables": vars,
                            "edit": True,
                            "debug": False}
        return None

    def RecursiveSearchPouInstances(self, project, pou_type, parent_path, varlists, debug = False):
        instances = []
        for varlist in varlists:
            for variable in varlist.getvariable():
                vartype_content = variable.gettype().getcontent()
                if vartype_content["name"] == "derived":
                    var_path = "%s.%s" % (parent_path, variable.getname())
                    var_type = vartype_content["value"].getname()
                    if var_type == pou_type:
                        instances.append(var_path)
                    else:
                        pou = project.getpou(var_type)
                        if pou is not None:
                            instances.extend(
                                self.RecursiveSearchPouInstances(
                                    project, pou_type, var_path, 
                                    [varlist for type, varlist in pou.getvars()], 
                                    debug))
        return instances
                        
    def SearchPouInstances(self, tagname, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            words = tagname.split("::")
            if words[0] == "P":
                instances = []
                for config in project.getconfigurations():
                    config_name = config.getname()
                    instances.extend(
                        self.RecursiveSearchPouInstances(
                            project, words[1], config_name, 
                            config.getglobalVars(), debug))
                    for resource in config.getresource():
                        res_path = "%s.%s" % (config_name, resource.getname())
                        instances.extend(
                            self.RecursiveSearchPouInstances(
                                project, words[1], res_path, 
                                resource.getglobalVars(), debug))
                        pou_instances = resource.getpouInstance()[:]
                        for task in resource.gettask():
                            pou_instances.extend(task.getpouInstance())
                        for pou_instance in pou_instances:
                            pou_path = "%s.%s" % (res_path, pou_instance.getname())
                            pou_type = pou_instance.gettypeName()
                            if pou_type == words[1]:
                                instances.append(pou_path)
                            pou = project.getpou(pou_type)
                            if pou is not None:
                                instances.extend(
                                    self.RecursiveSearchPouInstances(
                                        project, words[1], pou_path, 
                                        [varlist for type, varlist in pou.getvars()], 
                                        debug))
                return instances
            elif words[0] == 'C':
                return [words[1]]
            elif words[0] == 'R':
                return ["%s.%s" % (words[1], words[2])]
            elif words[0] in ['T', 'A']:
                return ["%s.%s" % (instance, words[2])
                        for instance in self.SearchPouInstances(
                            self.ComputePouName(words[1]), debug)]
        return []
    
    def RecursiveGetPouInstanceTagName(self, project, pou_type, parts, debug = False):
        pou = project.getpou(pou_type)
        if pou is not None:
            if len(parts) == 0:
                return self.ComputePouName(pou_type)
            
            for varlist_type, varlist in pou.getvars():
                for variable in varlist.getvariable():
                    if variable.getname() == parts[0]:
                        vartype_content = variable.gettype().getcontent()
                        if vartype_content["name"] == "derived":
                            return self.RecursiveGetPouInstanceTagName(
                                            project, 
                                            vartype_content["value"].getname(),
                                            parts[1:], debug)
            
            if pou.getbodyType() == "SFC" and len(parts) == 1:
                for action in pou.getactionList():
                    if action.getname() == parts[0]:
                        return self.ComputePouActionName(pou_type, parts[0])
                for transition in pou.gettransitionList():
                    if transition.getname() == parts[0]:
                        return self.ComputePouTransitionName(pou_type, parts[0])
        else:
            block_infos = self.GetBlockType(pou_type, debug=debug)
            if (block_infos is not None and 
                block_infos["type"] in ["program", "functionBlock"]):
                
                if len(parts) == 0:
                    return self.ComputePouName(pou_type)
                
                for varname, vartype, varmodifier in block_infos["inputs"] + block_infos["outputs"]:
                    if varname == parts[0]:
                        return self.RecursiveGetPouInstanceTagName(project, vartype, parts[1:], debug)
        return None
    
    def GetPouInstanceTagName(self, instance_path, debug = False):
        parts = instance_path.split(".")
        if len(parts) == 1:
            return self.ComputeConfigurationName(parts[0])
        elif len(parts) == 2:
            return self.ComputeConfigurationResourceName(parts[0], parts[1])
        else:
            project = self.GetProject(debug)
            for config in project.getconfigurations():
                if config.getname() == parts[0]:
                    for resource in config.getresource():
                        if resource.getname() == parts[1]:
                            pou_instances = resource.getpouInstance()[:]
                            for task in resource.gettask():
                                pou_instances.extend(task.getpouInstance())
                            for pou_instance in pou_instances:
                                if pou_instance.getname() == parts[2]:
                                    if len(parts) == 3:
                                        return self.ComputePouName(
                                                    pou_instance.gettypeName())
                                    else:
                                        return self.RecursiveGetPouInstanceTagName(
                                                    project,
                                                    pou_instance.gettypeName(),
                                                    parts[3:], debug)
        return None
    
    def GetInstanceInfos(self, instance_path, debug = False):
        tagname = self.GetPouInstanceTagName(instance_path)
        if tagname is not None:
            infos = self.GetPouVariables(tagname, debug)
            infos["type"] = tagname
            return infos
        else:
            pou_path, var_name = instance_path.rsplit(".", 1)
            tagname = self.GetPouInstanceTagName(pou_path)
            if tagname is not None:
                pou_infos = self.GetPouVariables(tagname, debug)
                for var_infos in pou_infos["variables"]:
                    if var_infos["name"] == var_name:
                        return var_infos
        return None
    
    # Return if data type given by name is used by another data type or pou
    def DataTypeIsUsed(self, name, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            return project.ElementIsUsed(name) or project.DataTypeIsDerived(name)
        return False

    # Return if pou given by name is used by another pou
    def PouIsUsed(self, name, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            return project.ElementIsUsed(name)
        return False

    # Return if pou given by name is directly or undirectly used by the reference pou
    def PouIsUsedBy(self, name, reference, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            return project.ElementIsUsedBy(name, reference)
        return False

    def GenerateProgram(self, filepath=None):
        errors = []
        warnings = []
        if self.Project is not None:
            try:
                self.ProgramChunks = GenerateCurrentProgram(self, self.Project, errors, warnings)
                self.NextCompiledProject = self.Copy(self.Project)
                program_text = "".join([item[0] for item in self.ProgramChunks])
                if filepath is not None:
                    programfile = open(filepath, "w")
                    programfile.write(program_text.encode("utf-8"))
                    programfile.close()
                    self.ProgramFilePath = filepath
                return program_text, errors, warnings
            except PLCGenException, e:
                errors.append(e.message)
        else:
            errors.append("No project opened")
        return "", errors, warnings

    def DebugAvailable(self):
        return self.CurrentCompiledProject is not None

    def ProgramTransferred(self):
        if self.NextCompiledProject is None:
            self.CurrentCompiledProject = self.NextCompiledProject
        else:
            self.CurrentCompiledProject = self.Copy(self.Project)

    def GetChunkInfos(self, from_location, to_location):
        row = self.ProgramOffset + 1
        col = 1
        infos = []
        for chunk, chunk_infos in self.ProgramChunks:
            lines = chunk.split("\n")
            if len(lines) > 1:
                next_row = row + len(lines) - 1
                next_col = len(lines[-1]) + 1
            else:
                next_row = row
                next_col = col + len(chunk)
            if (next_row > from_location[0] or next_row == from_location[0] and next_col >= from_location[1]) and len(chunk_infos) > 0:
                infos.append((chunk_infos, (row, col)))
            if next_row == to_location[0] and next_col > to_location[1] or next_row > to_location[0]:
                return infos
            row, col = next_row, next_col
        return infos
        
#-------------------------------------------------------------------------------
#                        Project Pous management functions
#-------------------------------------------------------------------------------
    
    # Add a Data Type to Project
    def ProjectAddDataType(self, datatype_name=None):
        if self.Project is not None:
            if datatype_name is None:
                datatype_name = self.GenerateNewName(None, None, "datatype%d")
            # Add the datatype to project
            self.Project.appenddataType(datatype_name)
            self.BufferProject()
            return self.ComputeDataTypeName(datatype_name)
        return None
        
    # Remove a Data Type from project
    def ProjectRemoveDataType(self, datatype_name):
        if self.Project is not None:
            self.Project.removedataType(datatype_name)
            self.BufferProject()
    
    # Add a Pou to Project
    def ProjectAddPou(self, pou_name, pou_type, body_type):
        if self.Project is not None:
            # Add the pou to project
            self.Project.appendpou(pou_name, pou_type, body_type)
            if pou_type == "function":
                self.SetPouInterfaceReturnType(pou_name, "BOOL")
            self.BufferProject()
            return self.ComputePouName(pou_name)
        return None
    
    def ProjectChangePouType(self, name, pou_type):
        if self.Project is not None:
            pou = self.Project.getpou(name)
            if pou is not None:
                pou.setpouType(pou_type)
                self.Project.RefreshCustomBlockTypes()
                self.BufferProject()
                
    def GetPouXml(self, pou_name):
        if self.Project is not None:
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                return pou.generateXMLText('pou', 0)
        return None
    
    def PastePou(self, pou_type, pou_xml):
        '''
        Adds the POU defined by 'pou_xml' to the current project with type 'pou_type'
        '''
        try:
            tree = minidom.parseString(pou_xml.encode("utf-8"))
            root = tree.childNodes[0]
        except:
            return _("Couldn't paste non-POU object.")

        if root.nodeName == "pou":
            new_pou = plcopen.pous_pou()
            new_pou.loadXMLTree(root)

            name = new_pou.getname()
            
            idx = 0
            new_name = name
            while self.Project.getpou(new_name):
                # a POU with that name already exists.
                # make a new name and test if a POU with that name exists.
                # append an incrementing numeric suffix to the POU name.
                idx += 1
                new_name = "%s%d" % (name, idx)
                
            # we've found a name that does not already exist, use it
            new_pou.setname(new_name)
            
            if pou_type is not None:
                orig_type = new_pou.getpouType()
    
                # prevent violations of POU content restrictions:
                # function blocks cannot be pasted as functions,
                # programs cannot be pasted as functions or function blocks
                if orig_type == 'functionBlock' and pou_type == 'function' or \
                   orig_type == 'program' and pou_type in ['function', 'functionBlock']:
                    return _('''%s "%s" can't be pasted as a %s.''') % (orig_type, name, pou_type)
                
                new_pou.setpouType(pou_type)

            self.Project.insertpou(-1, new_pou)
            self.BufferProject()
            
            return self.ComputePouName(new_name),
        else:
            return _("Couldn't paste non-POU object.")

    # Remove a Pou from project
    def ProjectRemovePou(self, pou_name):
        if self.Project is not None:
            self.Project.removepou(pou_name)
            self.BufferProject()
    
    # Return the name of the configuration if only one exist
    def GetProjectMainConfigurationName(self):
        if self.Project is not None:
            # Found the configuration corresponding to old name and change its name to new name
            configurations = self.Project.getconfigurations()
            if len(configurations) == 1:
                return configurations[0].getname()
        return None
                
    # Add a configuration to Project
    def ProjectAddConfiguration(self, config_name=None):
        if self.Project is not None:
            if config_name is None:
                config_name = self.GenerateNewName(None, None, "configuration%d")
            self.Project.addconfiguration(config_name)
            self.BufferProject()
            return self.ComputeConfigurationName(config_name)
        return None
    
    # Remove a configuration from project
    def ProjectRemoveConfiguration(self, config_name):
        if self.Project is not None:
            self.Project.removeconfiguration(config_name)
            self.BufferProject()
    
    # Add a resource to a configuration of the Project
    def ProjectAddConfigurationResource(self, config_name, resource_name=None):
        if self.Project is not None:
            if resource_name is None:
                resource_name = self.GenerateNewName(None, None, "resource%d")
            self.Project.addconfigurationResource(config_name, resource_name)
            self.BufferProject()
            return self.ComputeConfigurationResourceName(config_name, resource_name)
        return None
    
    # Remove a resource from a configuration of the project
    def ProjectRemoveConfigurationResource(self, config_name, resource_name):
        if self.Project is not None:
            self.Project.removeconfigurationResource(config_name, resource_name)
            self.BufferProject()
    
    # Add a Transition to a Project Pou
    def ProjectAddPouTransition(self, pou_name, transition_name, transition_type):
        if self.Project is not None:
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                pou.addtransition(transition_name, transition_type)
                self.BufferProject()
                return self.ComputePouTransitionName(pou_name, transition_name)
        return None
    
    # Remove a Transition from a Project Pou
    def ProjectRemovePouTransition(self, pou_name, transition_name):
        # Search if the pou removed is currently opened
        if self.Project is not None:
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                pou.removetransition(transition_name)
                self.BufferProject()
    
    # Add an Action to a Project Pou
    def ProjectAddPouAction(self, pou_name, action_name, action_type):
        if self.Project is not None:
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                pou.addaction(action_name, action_type)
                self.BufferProject()
                return self.ComputePouActionName(pou_name, action_name)
        return None
    
    # Remove an Action from a Project Pou
    def ProjectRemovePouAction(self, pou_name, action_name):
        # Search if the pou removed is currently opened
        if self.Project is not None:
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                pou.removeaction(action_name)
                self.BufferProject()
    
    # Change the name of a pou
    def ChangeDataTypeName(self, old_name, new_name):
        if self.Project is not None:
            # Found the pou corresponding to old name and change its name to new name
            datatype = self.Project.getdataType(old_name)
            if datatype is not None:
                datatype.setname(new_name)
                self.Project.updateElementName(old_name, new_name)
                self.Project.RefreshElementUsingTree()
                self.Project.RefreshDataTypeHierarchy()
                self.BufferProject()
    
    # Change the name of a pou
    def ChangePouName(self, old_name, new_name):
        if self.Project is not None:
            # Found the pou corresponding to old name and change its name to new name
            pou = self.Project.getpou(old_name)
            if pou is not None:
                pou.setname(new_name)
                self.Project.updateElementName(old_name, new_name)
                self.Project.RefreshElementUsingTree()
                self.Project.RefreshCustomBlockTypes()
                self.BufferProject()
    
    # Change the name of a pou transition
    def ChangePouTransitionName(self, pou_name, old_name, new_name):
        if self.Project is not None:
            # Found the pou transition corresponding to old name and change its name to new name
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                transition = pou.gettransition(old_name)
                if transition is not None:
                    transition.setname(new_name)
                    pou.updateElementName(old_name, new_name)
                    self.BufferProject()
    
    # Change the name of a pou action
    def ChangePouActionName(self, pou_name, old_name, new_name):
        if self.Project is not None:
            # Found the pou action corresponding to old name and change its name to new name
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                action = pou.getaction(old_name)
                if action is not None:
                    action.setname(new_name)
                    pou.updateElementName(old_name, new_name)
                    self.BufferProject()
    
    # Change the name of a pou variable
    def ChangePouVariableName(self, pou_name, old_name, new_name):
        if self.Project is not None:
            # Found the pou action corresponding to old name and change its name to new name
            pou = self.Project.getpou(pou_name)
            if pou is not None:
                for type, varlist in pou.getvars():
                    for var in varlist.getvariable():
                        if var.getname() == old_name:
                            var.setname(new_name)
                self.Project.RefreshCustomBlockTypes()
                self.BufferProject()
        
    # Change the name of a configuration
    def ChangeConfigurationName(self, old_name, new_name):
        if self.Project is not None:
            # Found the configuration corresponding to old name and change its name to new name
            configuration = self.Project.getconfiguration(old_name)
            if configuration is not None:
                configuration.setname(new_name)
                self.BufferProject()
    
    # Change the name of a configuration resource
    def ChangeConfigurationResourceName(self, config_name, old_name, new_name):
        if self.Project is not None:
            # Found the resource corresponding to old name and change its name to new name
            resource = self.Project.getconfigurationResource(config_name, old_name)
            if resource is not None:
                resource.setname(new_name)
                self.BufferProject()
    
    # Return the description of the pou given by its name
    def GetPouDescription(self, name, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its type
            pou = project.getpou(name)
            if pou is not None:
                return pou.getdescription()
        return ""
    
    # Return the description of the pou given by its name
    def SetPouDescription(self, name, description, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its type
            pou = project.getpou(name)
            if pou is not None:
                pou.setdescription(description)
                project.RefreshCustomBlockTypes()
                self.BufferProject()
    
    # Return the type of the pou given by its name
    def GetPouType(self, name, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its type
            pou = project.getpou(name)
            if pou is not None:
                return pou.getpouType()
        return None
    
    # Return pous with SFC language
    def GetSFCPous(self, debug = False):
        list = []
        project = self.GetProject(debug)
        if project is not None:
            for pou in project.getpous():
                if pou.getBodyType() == "SFC":
                    list.append(pou.getname())
        return list
    
    # Return the body language of the pou given by its name
    def GetPouBodyType(self, name, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its body language
            pou = project.getpou(name)
            if pou is not None:
                return pou.getbodyType()
        return None
    
    # Return the actions of a pou
    def GetPouTransitions(self, pou_name, debug = False):
        transitions = []
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its transitions if SFC
            pou = project.getpou(pou_name)
            if pou is not None and pou.getbodyType() == "SFC":
                for transition in pou.gettransitionList():
                    transitions.append(transition.getname())
        return transitions
    
    # Return the body language of the transition given by its name
    def GetTransitionBodyType(self, pou_name, pou_transition, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name
            pou = project.getpou(pou_name)
            if pou is not None:
                # Found the pou transition correponding to name and return its body language
                transition = pou.gettransition(pou_transition)
                if transition is not None:
                    return transition.getbodyType()
        return None
    
    # Return the actions of a pou
    def GetPouActions(self, pou_name, debug = False):
        actions = []
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its actions if SFC
            pou = project.getpou(pou_name)
            if pou.getbodyType() == "SFC":
                for action in pou.getactionList():
                    actions.append(action.getname())
        return actions
    
    # Return the body language of the pou given by its name
    def GetActionBodyType(self, pou_name, pou_action, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return its body language
            pou = project.getpou(pou_name)
            if pou is not None:
                action = pou.getaction(pou_action)
                if action is not None:
                    return action.getbodyType()
        return None
    
    # Extract varlists from a list of vars
    def ExtractVarLists(self, vars):
        varlist_list = []
        current_varlist = None
        current_type = None
        for var in vars:
            next_type = (var["Class"], 
                         var["Option"], 
                         var["Location"] in ["", None] or 
                         # When declaring globals, located 
                         # and not located variables are 
                         # in the same declaration block
                         var["Class"] == "Global")
            if current_type != next_type:
                current_type = next_type
                infos = VAR_CLASS_INFOS.get(var["Class"], None)
                if infos is not None:
                    current_varlist = infos[0]()
                else:
                    current_varlist = plcopen.varList()
                varlist_list.append((var["Class"], current_varlist))
                if var["Option"] == "Constant":
                    current_varlist.setconstant(True)
                elif var["Option"] == "Retain":
                    current_varlist.setretain(True)
                elif var["Option"] == "Non-Retain":
                    current_varlist.setnonretain(True)
            # Create variable and change its properties
            tempvar = plcopen.varListPlain_variable()
            tempvar.setname(var["Name"])
            
            var_type = plcopen.dataType()
            if isinstance(var["Type"], TupleType):
                if var["Type"][0] == "array":
                    array_type, base_type_name, dimensions = var["Type"]
                    array = plcopen.derivedTypes_array()
                    for i, dimension in enumerate(dimensions):
                        dimension_range = plcopen.rangeSigned()
                        dimension_range.setlower(dimension[0])
                        dimension_range.setupper(dimension[1])
                        if i == 0:
                            array.setdimension([dimension_range])
                        else:
                            array.appenddimension(dimension_range)
                    if base_type_name in self.GetBaseTypes():
                        if base_type_name == "STRING":
                            array.baseType.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                        elif base_type_name == "WSTRING":
                            array.baseType.setcontent({"name" : "wstring", "value" : plcopen.wstring()})
                        else:
                            array.baseType.setcontent({"name" : base_type_name, "value" : None})
                    else:
                        derived_datatype = plcopen.derivedTypes_derived()
                        derived_datatype.setname(base_type_name)
                        array.baseType.setcontent({"name" : "derived", "value" : derived_datatype})
                    var_type.setcontent({"name" : "array", "value" : array})
            elif var["Type"] in self.GetBaseTypes():
                if var["Type"] == "STRING":
                    var_type.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                elif var["Type"] == "WSTRING":
                    var_type.setcontent({"name" : "wstring", "value" : plcopen.elementaryTypes_wstring()})
                else:
                    var_type.setcontent({"name" : var["Type"], "value" : None})
            else:
                derived_type = plcopen.derivedTypes_derived()
                derived_type.setname(var["Type"])
                var_type.setcontent({"name" : "derived", "value" : derived_type})
            tempvar.settype(var_type)

            if var["Initial Value"] != "":
                value = plcopen.value()
                value.setvalue(var["Initial Value"])
                tempvar.setinitialValue(value)
            if var["Location"] != "":
                tempvar.setaddress(var["Location"])
            else:
                tempvar.setaddress(None)
            if var['Documentation'] != "":
                ft = plcopen.formattedText()
                ft.settext(var['Documentation'])
                tempvar.setdocumentation(ft)

            # Add variable to varList
            current_varlist.appendvariable(tempvar)
        return varlist_list
    
    def GetVariableDictionary(self, varlist, var):
        '''
        convert a PLC variable to the dictionary representation
        returned by Get*Vars)
        '''

        tempvar = {"Name": var.getname()}

        vartype_content = var.gettype().getcontent()
        if vartype_content["name"] == "derived":
            tempvar["Type"] = vartype_content["value"].getname()
        elif vartype_content["name"] == "array":
            dimensions = []
            for dimension in vartype_content["value"].getdimension():
                dimensions.append((dimension.getlower(), dimension.getupper()))
            base_type = vartype_content["value"].baseType.getcontent()
            if base_type["value"] is None or base_type["name"] in ["string", "wstring"]:
                base_type_name = base_type["name"].upper()
            else:
                base_type_name = base_type["value"].getname()
            tempvar["Type"] = ("array", base_type_name, dimensions)
        elif vartype_content["name"] in ["string", "wstring"]:
            tempvar["Type"] = vartype_content["name"].upper()
        else:
            tempvar["Type"] = vartype_content["name"]

        tempvar["Edit"] = True

        initial = var.getinitialValue()
        if initial:
            tempvar["Initial Value"] = initial.getvalue()
        else:
            tempvar["Initial Value"] = ""

        address = var.getaddress()
        if address:
            tempvar["Location"] = address
        else:
            tempvar["Location"] = ""

        if varlist.getconstant():
            tempvar["Option"] = "Constant"
        elif varlist.getretain():
            tempvar["Option"] = "Retain"
        elif varlist.getnonretain():
            tempvar["Option"] = "Non-Retain"
        else:
            tempvar["Option"] = ""

        doc = var.getdocumentation()
        if doc:
            tempvar["Documentation"] = doc.gettext()
        else:
            tempvar["Documentation"] = ""

        return tempvar

    # Replace the configuration globalvars by those given
    def SetConfigurationGlobalVars(self, name, vars):
        if self.Project is not None:
            # Found the configuration corresponding to name
            configuration = self.Project.getconfiguration(name)
            if configuration is not None:
                # Set configuration global vars
                configuration.setglobalVars([])
                for vartype, varlist in self.ExtractVarLists(vars):
                    configuration.globalVars.append(varlist)
    
    # Return the configuration globalvars
    def GetConfigurationGlobalVars(self, name, debug = False):
        vars = []
        project = self.GetProject(debug)
        if project is not None:
            # Found the configuration corresponding to name
            configuration = project.getconfiguration(name)
            if configuration is not None:
                # Extract variables from every varLists
                for varlist in configuration.getglobalVars():
                    for var in varlist.getvariable():
                        tempvar = self.GetVariableDictionary(varlist, var)
                        tempvar["Class"] = "Global"
                        vars.append(tempvar)
        return vars

    # Replace the resource globalvars by those given
    def SetConfigurationResourceGlobalVars(self, config_name, name, vars):
        if self.Project is not None:
            # Found the resource corresponding to name
            resource = self.Project.getconfigurationResource(config_name, name)
            # Set resource global vars
            if resource is not None:
                resource.setglobalVars([])
                for vartype, varlist in self.ExtractVarLists(vars):
                    resource.globalVars.append(varlist)
    
    # Return the resource globalvars
    def GetConfigurationResourceGlobalVars(self, config_name, name, debug = False):
        vars = []
        project = self.GetProject(debug)
        if project is not None:
            # Found the resource corresponding to name
            resource = project.getconfigurationResource(config_name, name)
            if resource:
                # Extract variables from every varLists
                for varlist in resource.getglobalVars():
                    for var in varlist.getvariable():
                        tempvar = self.GetVariableDictionary(varlist, var)
                        tempvar["Class"] = "Global"
                        vars.append(tempvar)
        return vars
    
    # Recursively generate element name tree for a structured variable
    def GenerateVarTree(self, typename, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            blocktype = self.GetBlockType(typename, debug = debug)
            if blocktype is not None:
                tree = []
                en = False
                eno = False
                for var_name, var_type, var_modifier in blocktype["inputs"] + blocktype["outputs"]:
                    en |= var_name.upper() == "EN"
                    eno |= var_name.upper() == "ENO"    
                    tree.append((var_name, var_type, self.GenerateVarTree(var_type, debug)))
                if not eno:
                    tree.insert(0, ("ENO", "BOOL", ([], [])))
                if not en:
                    tree.insert(0, ("EN", "BOOL", ([], [])))
                return tree, []
            datatype = project.getdataType(typename)
            if datatype is None:
                datatype = self.GetConfNodeDataType(typename)
            if datatype is not None:
                tree = []
                basetype_content = datatype.baseType.getcontent()
                if basetype_content["name"] == "derived":
                    return self.GenerateVarTree(basetype_content["value"].getname())
                elif basetype_content["name"] == "array":
                    dimensions = []
                    base_type = basetype_content["value"].baseType.getcontent()
                    if base_type["name"] == "derived":
                        tree = self.GenerateVarTree(base_type["value"].getname())
                        if len(tree[1]) == 0:
                            tree = tree[0]
                        for dimension in basetype_content["value"].getdimension():
                            dimensions.append((dimension.getlower(), dimension.getupper()))
                    return tree, dimensions
                elif basetype_content["name"] == "struct":
                    for element in basetype_content["value"].getvariable():
                        element_type = element.type.getcontent()
                        if element_type["name"] == "derived":
                            tree.append((element.getname(), element_type["value"].getname(), self.GenerateVarTree(element_type["value"].getname())))
                        else:
                            tree.append((element.getname(), element_type["name"], ([], [])))
                    return tree, []
        return [], []

    # Return the interface for the given pou
    def GetPouInterfaceVars(self, pou, debug = False):
        vars = []
        # Verify that the pou has an interface
        if pou.interface is not None:
            # Extract variables from every varLists
            for type, varlist in pou.getvars():
                for var in varlist.getvariable():
                    tempvar = self.GetVariableDictionary(varlist, var)

                    tempvar["Class"] = type
                    tempvar["Tree"] = ([], [])

                    vartype_content = var.gettype().getcontent()
                    if vartype_content["name"] == "derived":
                        tempvar["Edit"] = not pou.hasblock(tempvar["Name"])
                        tempvar["Tree"] = self.GenerateVarTree(tempvar["Type"], debug)

                    vars.append(tempvar)
        return vars

    # Replace the Pou interface by the one given
    def SetPouInterfaceVars(self, name, vars):
        if self.Project is not None:
            # Found the pou corresponding to name and add interface if there isn't one yet
            pou = self.Project.getpou(name)
            if pou is not None:
                if pou.interface is None:
                    pou.interface = plcopen.pou_interface()
                # Set Pou interface
                pou.setvars(self.ExtractVarLists(vars))
                self.Project.RefreshElementUsingTree()
                self.Project.RefreshCustomBlockTypes()
    
    # Replace the return type of the pou given by its name (only for functions)
    def SetPouInterfaceReturnType(self, name, type):
        if self.Project is not None:
            pou = self.Project.getpou(name)
            if pou is not None:
                if pou.interface is None:
                    pou.interface = plcopen.pou_interface()
                # If there isn't any return type yet, add it
                return_type = pou.interface.getreturnType()
                if not return_type:
                    return_type = plcopen.dataType()
                    pou.interface.setreturnType(return_type)
                # Change return type
                if type in self.GetBaseTypes():
                    if type == "STRING":
                        return_type.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                    elif type == "WSTRING":
                        return_type.setcontent({"name" : "wstring", "value" : plcopen.elementaryTypes_wstring()})
                    else:
                        return_type.setcontent({"name" : type, "value" : None})
                else:
                    derived_type = plcopen.derivedTypes_derived()
                    derived_type.setname(type)
                    return_type.setcontent({"name" : "derived", "value" : derived_type})
                self.Project.RefreshElementUsingTree()
                self.Project.RefreshCustomBlockTypes()
    
    def UpdateProjectUsedPous(self, old_name, new_name):
        if self.Project:
            self.Project.updateElementName(old_name, new_name)
    
    def UpdateEditedElementUsedVariable(self, tagname, old_name, new_name):
        pou = self.GetEditedElement(tagname)
        if pou:
            pou.updateElementName(old_name, new_name)
    
    # Return the return type of the pou given by its name
    def GetPouInterfaceReturnTypeByName(self, name):
        project = self.GetProject(debug)
        if project is not None:
            # Found the pou correponding to name and return the return type
            pou = project.getpou(name)
            if pou is not None:
                return self.GetPouInterfaceReturnType(pou)
        return False
    
    # Return the return type of the given pou
    def GetPouInterfaceReturnType(self, pou):
        # Verify that the pou has an interface
        if pou.interface is not None:
            # Return the return type if there is one
            return_type = pou.interface.getreturnType()
            if return_type:
                returntype_content = return_type.getcontent()
                if returntype_content["name"] == "derived":
                    return returntype_content["value"].getname()
                elif returntype_content["name"] in ["string", "wstring"]:
                    return returntype_content["name"].upper()
                else:
                    return returntype_content["name"]
        return None

    # Function that add a new confnode to the confnode list
    def AddConfNodeTypesList(self, typeslist):
        self.ConfNodeTypes.extend(typeslist)
        
    # Function that clear the confnode list
    def ClearConfNodeTypes(self):
        for i in xrange(len(self.ConfNodeTypes)):
            self.ConfNodeTypes.pop(0)

    def GetConfNodeBlockTypes(self):
        return [{"name": _("%s POUs") % confnodetypes["name"],
                 "list": confnodetypes["types"].GetCustomBlockTypes()}
                for confnodetypes in self.ConfNodeTypes]
        
    def GetConfNodeDataTypes(self, exclude = "", only_locatables = False):
        return [{"name": _("%s Data Types") % confnodetypes["name"],
                 "list": [datatype["name"] for datatype in confnodetypes["types"].GetCustomDataTypes(exclude, only_locatables)]}
                for confnodetypes in self.ConfNodeTypes]
    
    def GetConfNodeDataType(self, type):
        for confnodetype in self.ConfNodeTypes:
            datatype = confnodetype["types"].getdataType(type)
            if datatype is not None:
                return datatype
        return None
    
    def GetVariableLocationTree(self):
        return []

    def GetConfNodeGlobalInstances(self):
        return []

    def GetConfigurationExtraVariables(self):
        global_vars = []
        for var_name, var_type in self.GetConfNodeGlobalInstances():
            tempvar = plcopen.varListPlain_variable()
            tempvar.setname(var_name)
            
            tempvartype = plcopen.dataType()
            if var_type in self.GetBaseTypes():
                if var_type == "STRING":
                    var_type.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                elif var_type == "WSTRING":
                    var_type.setcontent({"name" : "wstring", "value" : plcopen.elementaryTypes_wstring()})
                else:
                    var_type.setcontent({"name" : var_type, "value" : None})
            else:
                tempderivedtype = plcopen.derivedTypes_derived()
                tempderivedtype.setname(var_type)
                tempvartype.setcontent({"name" : "derived", "value" : tempderivedtype})
            tempvar.settype(tempvartype)
            
            global_vars.append(tempvar)
        return global_vars

    # Function that returns the block definition associated to the block type given
    def GetBlockType(self, type, inputs = None, debug = False):
        result_blocktype = None
        for category in BlockTypes + self.GetConfNodeBlockTypes():
            for blocktype in category["list"]:
                if blocktype["name"] == type:
                    if inputs is not None and inputs != "undefined":
                        block_inputs = tuple([var_type for name, var_type, modifier in blocktype["inputs"]])
                        if reduce(lambda x, y: x and y, map(lambda x: x[0] == "ANY" or self.IsOfType(*x), zip(inputs, block_inputs)), True):
                            return blocktype
                    else:
                        if result_blocktype is not None:
                            if inputs == "undefined":
                                return None
                            else:
                                result_blocktype["inputs"] = [(i[0], "ANY", i[2]) for i in result_blocktype["inputs"]]
                                result_blocktype["outputs"] = [(o[0], "ANY", o[2]) for o in result_blocktype["outputs"]]
                                return result_blocktype
                        result_blocktype = blocktype
        if result_blocktype is not None:
            return result_blocktype
        project = self.GetProject(debug)
        if project is not None:
            return project.GetCustomBlockType(type, inputs)
        return None

    # Return Block types checking for recursion
    def GetBlockTypes(self, tagname = "", debug = False):
        type = None
        words = tagname.split("::")
        if self.Project:
            name = ""
            if words[0] in ["P","T","A"]:
                name = words[1]
                type = self.GetPouType(name, debug)
        if type == "function":
            blocktypes = []
            for category in BlockTypes + self.GetConfNodeBlockTypes():
                cat = {"name" : category["name"], "list" : []}
                for block in category["list"]:
                    if block["type"] == "function":
                        cat["list"].append(block)
                if len(cat["list"]) > 0:
                    blocktypes.append(cat)
        else:
            blocktypes = [category for category in BlockTypes + self.GetConfNodeBlockTypes()]
        project = self.GetProject(debug)
        if project is not None:
            blocktypes.append({"name" : USER_DEFINED_POUS, "list": project.GetCustomBlockTypes(name, type == "function" or words[0] == "T")})
        return blocktypes

    # Return Function Block types checking for recursion
    def GetFunctionBlockTypes(self, tagname = "", debug = False):
        blocktypes = []
        for category in BlockTypes + self.GetConfNodeBlockTypes():
            for block in category["list"]:
                if block["type"] == "functionBlock":
                    blocktypes.append(block["name"])
        project = self.GetProject(debug)
        if project is not None:
            name = ""
            words = tagname.split("::")
            if words[0] in ["P","T","A"]:
                name = words[1]
            blocktypes.extend(project.GetCustomFunctionBlockTypes(name))
        return blocktypes

    # Return Block types checking for recursion
    def GetBlockResource(self, debug = False):
        blocktypes = []
        for category in BlockTypes[:-1]:
            for blocktype in category["list"]:
                if blocktype["type"] == "program":
                    blocktypes.append(blocktype["name"])
        project = self.GetProject(debug)
        if project is not None:
            blocktypes.extend(project.GetCustomBlockResource())
        return blocktypes

    # Return Data Types checking for recursion
    def GetDataTypes(self, tagname = "", basetypes = True, confnodetypes = True, only_locatables = False, debug = False):
        if basetypes:
            datatypes = self.GetBaseTypes()
        else:
            datatypes = []
        project = self.GetProject(debug)
        if project is not None:
            name = ""
            words = tagname.split("::")
            if words[0] in ["D"]:
                name = words[1]
            datatypes.extend([datatype["name"] for datatype in project.GetCustomDataTypes(name, only_locatables)])
        if confnodetypes:
            for category in self.GetConfNodeDataTypes(name, only_locatables):
                datatypes.extend(category["list"])
        return datatypes

    # Return Base Type of given possible derived type
    def GetBaseType(self, type, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            result = project.GetBaseType(type)
            if result is not None:
                return result
        for confnodetype in self.ConfNodeTypes:
            result = confnodetype["types"].GetBaseType(type)
            if result is not None:
                return result
        return None

    def GetBaseTypes(self):
        '''
        return the list of datatypes defined in IEC 61131-3.
        TypeHierarchy_list has a rough order to it (e.g. SINT, INT, DINT, ...),
        which makes it easy for a user to find a type in a menu.
        '''
        return [x for x,y in TypeHierarchy_list if not x.startswith("ANY")]

    def IsOfType(self, type, reference, debug = False):
        if reference is None:
            return True
        elif type == reference:
            return True
        elif type in TypeHierarchy:
            return self.IsOfType(TypeHierarchy[type], reference)
        else:
            project = self.GetProject(debug)
            if project is not None and project.IsOfType(type, reference):
                return True
            for confnodetype in self.ConfNodeTypes:
                if confnodetype["types"].IsOfType(type, reference):
                    return True
        return False
    
    def IsEndType(self, type):
        if type is not None:
            return not type.startswith("ANY")
        return True

    def IsLocatableType(self, type, debug = False):
        if isinstance(type, TupleType):
            return False 
        if self.GetBlockType(type) is not None:
            return False
        project = self.GetProject(debug)
        if project is not None:
            datatype = project.getdataType(type)
            if datatype is None:
                datatype = self.GetConfNodeDataType(type)
            if datatype is not None:
                return project.IsLocatableType(datatype)
        return True
    
    def IsEnumeratedType(self, type, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            datatype = project.getdataType(type)
            if datatype is None:
                datatype = self.GetConfNodeDataType(type)
            if datatype is not None:
                basetype_content = datatype.baseType.getcontent()
                return basetype_content["name"] == "enum"
        return False

    def IsNumType(self, type, debug = False):
        return self.IsOfType(type, "ANY_NUM", debug) or\
               self.IsOfType(type, "ANY_BIT", debug)
            
    def GetDataTypeRange(self, type, debug = False):
        if type in DataTypeRange:
            return DataTypeRange[type]
        else:
            project = self.GetProject(debug)
            if project is not None:
                result = project.GetDataTypeRange(type)
                if result is not None:
                    return result
            for confnodetype in self.ConfNodeTypes:
                result = confnodetype["types"].GetDataTypeRange(type)
                if result is not None:
                    return result
        return None
    
    # Return Subrange types
    def GetSubrangeBaseTypes(self, exclude, debug = False):
        subrange_basetypes = []
        project = self.GetProject(debug)
        if project is not None:
            subrange_basetypes.extend(project.GetSubrangeBaseTypes(exclude))
        for confnodetype in self.ConfNodeTypes:
            subrange_basetypes.extend(confnodetype["types"].GetSubrangeBaseTypes(exclude))
        return DataTypeRange.keys() + subrange_basetypes
    
    # Return Enumerated Values
    def GetEnumeratedDataValues(self, type = None, debug = False):
        values = []
        project = self.GetProject(debug)
        if project is not None:
            values.extend(project.GetEnumeratedDataTypeValues(type))
            if type is None and len(values) > 0:
                return values
        for confnodetype in self.ConfNodeTypes:
            values.extend(confnodetype["types"].GetEnumeratedDataTypeValues(type))
            if type is None and len(values) > 0:
                return values
        return values

#-------------------------------------------------------------------------------
#                   Project Element tag name computation functions
#-------------------------------------------------------------------------------
    
    # Compute a data type name
    def ComputeDataTypeName(self, datatype):
        return "D::%s" % datatype
    
    # Compute a pou name
    def ComputePouName(self, pou):
        return "P::%s" % pou
    
    # Compute a pou transition name
    def ComputePouTransitionName(self, pou, transition):
        return "T::%s::%s" % (pou, transition)
    
    # Compute a pou action name
    def ComputePouActionName(self, pou, action):
        return "A::%s::%s" % (pou, action)

    # Compute a pou  name
    def ComputeConfigurationName(self, config):
        return "C::%s" % config

    # Compute a pou  name
    def ComputeConfigurationResourceName(self, config, resource):
        return "R::%s::%s" % (config, resource)

    def GetElementType(self, tagname):
        words = tagname.split("::")
        return {"D" : ITEM_DATATYPE, "P" : ITEM_POU, 
                "T" : ITEM_TRANSITION, "A" : ITEM_ACTION,
                "C" : ITEM_CONFIGURATION, "R" : ITEM_RESOURCE}[words[0]]

#-------------------------------------------------------------------------------
#                    Project opened Data types management functions
#-------------------------------------------------------------------------------

    # Return the data type informations
    def GetDataTypeInfos(self, tagname, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            words = tagname.split("::")
            if words[0] == "D":
                infos = {}
                datatype = project.getdataType(words[1])
                if datatype is None:
                    return None
                basetype_content = datatype.baseType.getcontent()
                if basetype_content["value"] is None or basetype_content["name"] in ["string", "wstring"]:
                    infos["type"] = "Directly"
                    infos["base_type"] = basetype_content["name"].upper()
                elif basetype_content["name"] == "derived":
                    infos["type"] = "Directly"
                    infos["base_type"] = basetype_content["value"].getname()
                elif basetype_content["name"] in ["subrangeSigned", "subrangeUnsigned"]:
                    infos["type"] = "Subrange"
                    infos["min"] = basetype_content["value"].range.getlower()
                    infos["max"] = basetype_content["value"].range.getupper()
                    base_type = basetype_content["value"].baseType.getcontent()
                    if base_type["value"] is None:
                        infos["base_type"] = base_type["name"]
                    else:
                        infos["base_type"] = base_type["value"].getname()
                elif basetype_content["name"] == "enum":
                    infos["type"] = "Enumerated"
                    infos["values"] = []
                    for value in basetype_content["value"].values.getvalue():
                        infos["values"].append(value.getname())
                elif basetype_content["name"] == "array":
                    infos["type"] = "Array"
                    infos["dimensions"] = []
                    for dimension in basetype_content["value"].getdimension():
                        infos["dimensions"].append((dimension.getlower(), dimension.getupper()))
                    base_type = basetype_content["value"].baseType.getcontent()
                    if base_type["value"] is None or base_type["name"] in ["string", "wstring"]:
                        infos["base_type"] = base_type["name"].upper()
                    else:
                        infos["base_type"] = base_type["value"].getname()
                elif basetype_content["name"] == "struct":
                    infos["type"] = "Structure"
                    infos["elements"] = []
                    for element in basetype_content["value"].getvariable():
                        element_infos = {}
                        element_infos["Name"] = element.getname()
                        element_type = element.type.getcontent()
                        if element_type["value"] is None or element_type["name"] in ["string", "wstring"]:
                            element_infos["Type"] = element_type["name"].upper()
                        elif element_type["name"] == "array":
                            dimensions = []
                            for dimension in element_type["value"].getdimension():
                                dimensions.append((dimension.getlower(), dimension.getupper()))
                            base_type = element_type["value"].baseType.getcontent()
                            if base_type["value"] is None or base_type["name"] in ["string", "wstring"]:
                                base_type_name = base_type["name"].upper()
                            else:
                                base_type_name = base_type["value"].getname()
                            element_infos["Type"] = ("array", base_type_name, dimensions)
                        else:
                            element_infos["Type"] = element_type["value"].getname()
                        if element.initialValue is not None:
                            element_infos["Initial Value"] = str(element.initialValue.getvalue())
                        else:
                            element_infos["Initial Value"] = ""
                        infos["elements"].append(element_infos)
                if datatype.initialValue is not None:
                    infos["initial"] = str(datatype.initialValue.getvalue())
                else:
                    infos["initial"] = ""
                return infos
        return None
    
    # Change the data type informations
    def SetDataTypeInfos(self, tagname, infos):
        words = tagname.split("::")
        if self.Project is not None and words[0] == "D":
            datatype = self.Project.getdataType(words[1])
            if infos["type"] == "Directly":
                if infos["base_type"] in self.GetBaseTypes():
                    if infos["base_type"] == "STRING":
                        datatype.baseType.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                    elif infos["base_type"] == "WSTRING":
                        datatype.baseType.setcontent({"name" : "wstring", "value" : plcopen.elementaryTypes_wstring()})
                    else:
                        datatype.baseType.setcontent({"name" : infos["base_type"], "value" : None})
                else:
                    derived_datatype = plcopen.derivedTypes_derived()
                    derived_datatype.setname(infos["base_type"])
                    datatype.baseType.setcontent({"name" : "derived", "value" : derived_datatype})
            elif infos["type"] == "Subrange":
                if infos["base_type"] in GetSubTypes("ANY_UINT"):
                    subrange = plcopen.derivedTypes_subrangeUnsigned()
                    datatype.baseType.setcontent({"name" : "subrangeUnsigned", "value" : subrange})
                else:
                    subrange = plcopen.derivedTypes_subrangeSigned()
                    datatype.baseType.setcontent({"name" : "subrangeSigned", "value" : subrange})
                subrange.range.setlower(infos["min"])
                subrange.range.setupper(infos["max"])
                if infos["base_type"] in self.GetBaseTypes():
                    subrange.baseType.setcontent({"name" : infos["base_type"], "value" : None})
                else:
                    derived_datatype = plcopen.derivedTypes_derived()
                    derived_datatype.setname(infos["base_type"])
                    subrange.baseType.setcontent({"name" : "derived", "value" : derived_datatype})
            elif infos["type"] == "Enumerated":
                enumerated = plcopen.derivedTypes_enum()
                for i, enum_value in enumerate(infos["values"]):
                    value = plcopen.values_value()
                    value.setname(enum_value)
                    if i == 0:
                        enumerated.values.setvalue([value])
                    else:
                        enumerated.values.appendvalue(value)
                datatype.baseType.setcontent({"name" : "enum", "value" : enumerated})
            elif infos["type"] == "Array":
                array = plcopen.derivedTypes_array()
                for i, dimension in enumerate(infos["dimensions"]):
                    dimension_range = plcopen.rangeSigned()
                    dimension_range.setlower(dimension[0])
                    dimension_range.setupper(dimension[1])
                    if i == 0:
                        array.setdimension([dimension_range])
                    else:
                        array.appenddimension(dimension_range)
                if infos["base_type"] in self.GetBaseTypes():
                    if infos["base_type"] == "STRING":
                        array.baseType.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                    elif infos["base_type"] == "WSTRING":
                        array.baseType.setcontent({"name" : "wstring", "value" : plcopen.wstring()})
                    else:
                        array.baseType.setcontent({"name" : infos["base_type"], "value" : None})
                else:
                    derived_datatype = plcopen.derivedTypes_derived()
                    derived_datatype.setname(infos["base_type"])
                    array.baseType.setcontent({"name" : "derived", "value" : derived_datatype})
                datatype.baseType.setcontent({"name" : "array", "value" : array})
            elif infos["type"] == "Structure":
                struct = plcopen.varListPlain()
                for i, element_infos in enumerate(infos["elements"]):
                    element = plcopen.varListPlain_variable()
                    element.setname(element_infos["Name"])
                    if isinstance(element_infos["Type"], TupleType):
                        if element_infos["Type"][0] == "array":
                            array_type, base_type_name, dimensions = element_infos["Type"]
                            array = plcopen.derivedTypes_array()
                            for j, dimension in enumerate(dimensions):
                                dimension_range = plcopen.rangeSigned()
                                dimension_range.setlower(dimension[0])
                                dimension_range.setupper(dimension[1])
                                if j == 0:
                                    array.setdimension([dimension_range])
                                else:
                                    array.appenddimension(dimension_range)
                            if base_type_name in self.GetBaseTypes():
                                if base_type_name == "STRING":
                                    array.baseType.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                                elif base_type_name == "WSTRING":
                                    array.baseType.setcontent({"name" : "wstring", "value" : plcopen.wstring()})
                                else:
                                    array.baseType.setcontent({"name" : base_type_name, "value" : None})
                            else:
                                derived_datatype = plcopen.derivedTypes_derived()
                                derived_datatype.setname(base_type_name)
                                array.baseType.setcontent({"name" : "derived", "value" : derived_datatype})
                            element.type.setcontent({"name" : "array", "value" : array})
                    elif element_infos["Type"] in self.GetBaseTypes():
                        if element_infos["Type"] == "STRING":
                            element.type.setcontent({"name" : "string", "value" : plcopen.elementaryTypes_string()})
                        elif element_infos["Type"] == "WSTRING":
                            element.type.setcontent({"name" : "wstring", "value" : plcopen.wstring()})
                        else:
                            element.type.setcontent({"name" : element_infos["Type"], "value" : None})
                    else:
                        derived_datatype = plcopen.derivedTypes_derived()
                        derived_datatype.setname(element_infos["Type"])
                        element.type.setcontent({"name" : "derived", "value" : derived_datatype})
                    if element_infos["Initial Value"] != "":
                        value = plcopen.value()
                        value.setvalue(element_infos["Initial Value"])
                        element.setinitialValue(value)
                    if i == 0:
                        struct.setvariable([element])
                    else:
                        struct.appendvariable(element)
                datatype.baseType.setcontent({"name" : "struct", "value" : struct})
            if infos["initial"] != "":
                if datatype.initialValue is None:
                    datatype.initialValue = plcopen.value()
                datatype.initialValue.setvalue(infos["initial"])
            else:
                datatype.initialValue = None
            self.Project.RefreshDataTypeHierarchy()
            self.Project.RefreshElementUsingTree()
            self.BufferProject()
    
#-------------------------------------------------------------------------------
#                       Project opened Pous management functions
#-------------------------------------------------------------------------------

    # Return edited element
    def GetEditedElement(self, tagname, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            words = tagname.split("::")
            if words[0] == "D":
                return project.getdataType(words[1])
            elif words[0] == "P":
                return project.getpou(words[1])
            elif words[0] in ['T', 'A']:
                pou = project.getpou(words[1])
                if pou is not None:
                    if words[0] == 'T':
                        return pou.gettransition(words[2])
                    elif words[0] == 'A':
                        return pou.getaction(words[2])
            elif words[0] == 'C':
                return project.getconfiguration(words[1])
            elif words[0] == 'R':
                return project.getconfigurationResource(words[1], words[2])
        return None
    
    # Return edited element name
    def GetEditedElementName(self, tagname):
        words = tagname.split("::")
        if words[0] in ["P","C","D"]:
            return words[1]
        else:
            return words[2]
        return None
    
    # Return edited element name and type
    def GetEditedElementType(self, tagname, debug = False):
        words = tagname.split("::")
        if words[0] in ["P","T","A"]:
            return words[1], self.GetPouType(words[1], debug)
        return None, None

    # Return language in which edited element is written
    def GetEditedElementBodyType(self, tagname, debug = False):
        words = tagname.split("::")
        if words[0] == "P":
            return self.GetPouBodyType(words[1], debug)
        elif words[0] == 'T':
            return self.GetTransitionBodyType(words[1], words[2], debug)
        elif words[0] == 'A':
            return self.GetActionBodyType(words[1], words[2], debug)
        return None

    # Return the edited element variables
    def GetEditedElementInterfaceVars(self, tagname, debug = False):
        words = tagname.split("::")
        if words[0] in ["P","T","A"]:
            project = self.GetProject(debug)
            if project is not None:
                pou = project.getpou(words[1])
                if pou is not None:
                    return self.GetPouInterfaceVars(pou, debug)
        return []

    # Return the edited element return type
    def GetEditedElementInterfaceReturnType(self, tagname, debug = False):
        words = tagname.split("::")
        if words[0] == "P":
            project = self.GetProject(debug)
            if project is not None:
                pou = self.Project.getpou(words[1])
                if pou is not None:
                    return self.GetPouInterfaceReturnType(pou)
        elif words[0] == 'T':
            return "BOOL"
        return None
    
    # Change the edited element text
    def SetEditedElementText(self, tagname, text):
        if self.Project is not None:
            element = self.GetEditedElement(tagname)
            if element is not None:
                element.settext(text)
                self.Project.RefreshElementUsingTree()
    
    # Return the edited element text
    def GetEditedElementText(self, tagname, debug = False):
        element = self.GetEditedElement(tagname, debug)
        if element is not None:
            return element.gettext()
        return ""

    # Return the edited element transitions
    def GetEditedElementTransitions(self, tagname, debug = False):
        pou = self.GetEditedElement(tagname, debug)
        if pou is not None and pou.getbodyType() == "SFC":
            transitions = []
            for transition in pou.gettransitionList():
                transitions.append(transition.getname())
            return transitions
        return []

    # Return edited element transitions
    def GetEditedElementActions(self, tagname, debug = False):
        pou = self.GetEditedElement(tagname, debug)
        if pou is not None and pou.getbodyType() == "SFC":
            actions = []
            for action in pou.getactionList():
                actions.append(action.getname())
            return actions
        return []

    # Return the names of the pou elements
    def GetEditedElementVariables(self, tagname, debug = False):
        words = tagname.split("::")
        if words[0] in ["P","T","A"]:
            return self.GetProjectPouVariables(words[1], debug)
        return []

    def GetEditedElementCopy(self, tagname, debug = False):
        element = self.GetEditedElement(tagname, debug)
        if element is not None:
            name = element.__class__.__name__
            return element.generateXMLText(name.split("_")[-1], 0)
        return ""
        
    def GetEditedElementInstancesCopy(self, tagname, blocks_id = None, wires = None, debug = False):
        element = self.GetEditedElement(tagname, debug)
        text = ""
        if element is not None:
            wires = dict([(wire, True) for wire in wires if wire[0] in blocks_id and wire[1] in blocks_id])
            for id in blocks_id:
                instance = element.getinstance(id)
                if instance is not None:
                    instance_copy = self.Copy(instance)
                    instance_copy.filterConnections(wires)
                    name = instance_copy.__class__.__name__
                    text += instance_copy.generateXMLText(name.split("_")[-1], 0)
        return text
    
    def GenerateNewName(self, tagname, name, format, exclude={}, debug=False):
        names = exclude.copy()
        if tagname is not None:
            names.update(dict([(varname.upper(), True) for varname in self.GetEditedElementVariables(tagname, debug)]))
            element = self.GetEditedElement(tagname, debug)
            if element is not None:
                for instance in element.getinstances():
                    if isinstance(instance, (plcopen.sfcObjects_step, plcopen.commonObjects_connector, plcopen.commonObjects_continuation)):
                        names[instance.getname().upper()] = True
        else:
            project = self.GetProject(debug)
            if project is not None:
                for datatype in project.getdataTypes():
                    names[datatype.getname().upper()] = True
                for pou in project.getpous():
                    names[pou.getname().upper()] = True
                    for var in self.GetPouInterfaceVars(pou, debug):
                        names[var["Name"].upper()] = True
                    for transition in pou.gettransitionList():
                        names[transition.getname().upper()] = True
                    for action in pou.getactionList():
                        names[action.getname().upper()] = True
                for config in project.getconfigurations():
                    names[config.getname().upper()] = True
                    for resource in config.getresource():
                        names[resource.getname().upper()] = True
            
        i = 0
        while name is None or names.get(name.upper(), False):
            name = (format%i)
            i += 1
        return name
    
    CheckPasteCompatibility = {"SFC": lambda name: True,
                               "LD": lambda name: not name.startswith("sfcObjects"),
                               "FBD": lambda name: name.startswith("fbdObjects") or name.startswith("commonObjects")}
    
    def PasteEditedElementInstances(self, tagname, text, new_pos, middle=False, debug=False):
        element = self.GetEditedElement(tagname, debug)
        element_name, element_type = self.GetEditedElementType(tagname, debug)
        if element is not None:
            bodytype = element.getbodyType()
            
            # Get edited element type scaling
            scaling = None
            project = self.GetProject(debug)
            if project is not None:
                properties = project.getcontentHeader()
                scaling = properties["scaling"][bodytype]
            
            # Get ids already by all the instances in edited element
            used_id = dict([(instance.getlocalId(), True) for instance in element.getinstances()])
            new_id = {}
            
            text = "<paste>%s</paste>"%text
            
            try:
                tree = minidom.parseString(text)
            except:
                return _("Invalid plcopen element(s)!!!")
            instances = []
            exclude = {}
            for root in tree.childNodes:
                if root.nodeType == tree.ELEMENT_NODE and root.nodeName == "paste":
                    for child in root.childNodes:
                        if child.nodeType == tree.ELEMENT_NODE:
                            if not child.nodeName in plcopen.ElementNameToClass:
                                return _("\"%s\" element can't be pasted here!!!")%child.nodeName

                            classname = plcopen.ElementNameToClass[child.nodeName]
                            if not self.CheckPasteCompatibility[bodytype](classname):
                                return _("\"%s\" element can't be pasted here!!!")%child.nodeName

                            classobj = getattr(plcopen, classname, None)
                            if classobj is not None:
                                instance = classobj()
                                instance.loadXMLTree(child)
                                if child.nodeName == "block":
                                    blockname = instance.getinstanceName()
                                    if blockname is not None:
                                        blocktype = instance.gettypeName()
                                        if element_type == "function":
                                            return _("FunctionBlock \"%s\" can't be pasted in a Function!!!")%blocktype
                                        blockname = self.GenerateNewName(tagname, blockname, "%s%%d"%blocktype, debug=debug)
                                        exclude[blockname] = True
                                        instance.setinstanceName(blockname)
                                        self.AddEditedElementPouVar(tagname, blocktype, blockname)
                                elif child.nodeName == "step":
                                    stepname = self.GenerateNewName(tagname, instance.getname(), "Step%d", exclude, debug)
                                    exclude[stepname] = True
                                    instance.setname(stepname)
                                localid = instance.getlocalId()
                                if not used_id.has_key(localid):
                                    new_id[localid] = True
                                instances.append((child.nodeName, instance))
            
            if len(instances) == 0:
                return _("Invalid plcopen element(s)!!!")
            
            idx = 1
            translate_id = {}
            bbox = plcopen.rect()
            for name, instance in instances:
                localId = instance.getlocalId()
                bbox.union(instance.getBoundingBox())
                if used_id.has_key(localId):
                    while used_id.has_key(idx) or new_id.has_key(idx):
                        idx += 1
                    new_id[idx] = True
                    instance.setlocalId(idx)
                    translate_id[localId] = idx
            
            x, y, width, height = bbox.bounding_box()
            if middle:
                new_pos[0] -= width / 2
                new_pos[1] -= height / 2
            else:
                new_pos = map(lambda x: x + 30, new_pos)
            if scaling[0] != 0 and scaling[1] != 0:
                min_pos = map(lambda x: 30 / x, scaling)
                minx = round(min_pos[0])
                if int(min_pos[0]) == round(min_pos[0]):
                    minx += 1
                miny = round(min_pos[1])
                if int(min_pos[1]) == round(min_pos[1]):
                    miny += 1
                minx *= scaling[0]
                miny *= scaling[1]
                new_pos = (max(minx, round(new_pos[0] / scaling[0]) * scaling[0]),
                           max(miny, round(new_pos[1] / scaling[1]) * scaling[1]))
            else:
                new_pos = (max(30, new_pos[0]), max(30, new_pos[1]))
            diff = (new_pos[0] - x, new_pos[1] - y)
            
            connections = {}
            for name, instance in instances:
                connections.update(instance.updateConnectionsId(translate_id))
                if getattr(instance, "setexecutionOrderId", None) is not None:
                    instance.setexecutionOrderId(0)
                instance.translate(*diff)
                element.addinstance(name, instance)
            
            return new_id, connections
                
    # Return the current pou editing informations
    def GetEditedElementInstanceInfos(self, tagname, id = None, exclude = [], debug = False):
        infos = {}
        instance = None
        element = self.GetEditedElement(tagname, debug)
        if element is not None:
            # if id is defined
            if id is not None:
                instance = element.getinstance(id)
            else:
                instance = element.getrandomInstance(exclude)
        if instance is not None:
            infos = instance.getinfos()
            if infos["type"] in ["input", "output", "inout"]:
                var_type = self.GetEditedElementVarValueType(tagname, infos["specific_values"]["name"], debug)
                infos["specific_values"]["value_type"] = var_type
            return infos
        return None
    
    def ClearEditedElementExecutionOrder(self, tagname):
        element = self.GetEditedElement(tagname)
        if element is not None:
            element.resetexecutionOrder()
    
    def ResetEditedElementExecutionOrder(self, tagname):
        element = self.GetEditedElement(tagname)
        if element is not None:
            element.compileexecutionOrder()
    
    # Return the variable type of the given pou
    def GetEditedElementVarValueType(self, tagname, varname, debug = False):
        project = self.GetProject(debug)
        if project is not None:
            words = tagname.split("::")
            if words[0] in ["P","T","A"]:
                pou = self.Project.getpou(words[1])
                if pou is not None:
                    if words[0] == "T" and varname == words[2]:
                        return "BOOL"
                    if words[1] == varname:
                        return self.GetPouInterfaceReturnType(pou)
                    for type, varlist in pou.getvars():
                        for var in varlist.getvariable():
                            if var.getname() == varname:
                                vartype_content = var.gettype().getcontent()
                                if vartype_content["name"] == "derived":
                                    return vartype_content["value"].getname()
                                elif vartype_content["name"] in ["string", "wstring"]:
                                    return vartype_content["name"].upper()
                                else:
                                    return vartype_content["name"]
        return None
    
    def SetConnectionWires(self, connection, connector):
        wires = connector.GetWires()
        idx = 0
        for wire, handle in wires:
            points = wire.GetPoints(handle != 0)
            if handle == 0:
                result = wire.GetConnectedInfos(-1)
            else:
                result = wire.GetConnectedInfos(0)
            if result != None:
                refLocalId, formalParameter = result
                connections = connection.getconnections()
                if connections is None or len(connection.getconnections()) <= idx:
                    connection.addconnection()
                connection.setconnectionId(idx, refLocalId)
                connection.setconnectionPoints(idx, points)
                if formalParameter != "":
                    connection.setconnectionParameter(idx, formalParameter)
                else:
                    connection.setconnectionParameter(idx, None)
                idx += 1
    
    def AddEditedElementPouVar(self, tagname, type, name, location="", description=""):
        if self.Project is not None:
            words = tagname.split("::")
            if words[0] in ['P', 'T', 'A']:
                pou = self.Project.getpou(words[1])
                if pou is not None:
                    pou.addpouLocalVar(type, name, location, description)
    
    def AddEditedElementPouExternalVar(self, tagname, type, name):
        if self.Project is not None:
            words = tagname.split("::")
            if words[0] in ['P', 'T', 'A']:
                pou = self.Project.getpou(words[1])
                if pou is not None:
                    pou.addpouExternalVar(type, name)
            
    def ChangeEditedElementPouVar(self, tagname, old_type, old_name, new_type, new_name):
        if self.Project is not None:
            words = tagname.split("::")
            if words[0] in ['P', 'T', 'A']:
                pou = self.Project.getpou(words[1])
                if pou is not None:
                    pou.changepouVar(old_type, old_name, new_type, new_name)
    
    def RemoveEditedElementPouVar(self, tagname, type, name):
        if self.Project is not None:
            words = tagname.split("::")
            if words[0] in ['P', 'T', 'A']:
                pou = self.Project.getpou(words[1])
                if pou is not None:
                    pou.removepouVar(type, name)
    
    def AddEditedElementBlock(self, tagname, id, blocktype, blockname = None):
        element = self.GetEditedElement(tagname)
        if element is not None:
            block = plcopen.fbdObjects_block()
            block.setlocalId(id)
            block.settypeName(blocktype)
            blocktype_infos = self.GetBlockType(blocktype)
            if blocktype_infos["type"] != "function" and blockname is not None:
                block.setinstanceName(blockname)
                self.AddEditedElementPouVar(tagname, blocktype, blockname)
            element.addinstance("block", block)
            self.Project.RefreshElementUsingTree()
    
    def SetEditedElementBlockInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            block = element.getinstance(id)
            if block is None:
                return 
            old_name = block.getinstanceName()
            old_type = block.gettypeName()
            new_name = infos.get("name", old_name)
            new_type = infos.get("type", old_type)
            if new_type != old_type:
                old_typeinfos = self.GetBlockType(old_type)
                new_typeinfos = self.GetBlockType(new_type)
                if old_typeinfos is None or new_typeinfos is None:
                    self.ChangeEditedElementPouVar(tagname, old_type, old_name, new_type, new_name)
                elif new_typeinfos["type"] != old_typeinfos["type"]:
                    if new_typeinfos["type"] == "function":
                        self.RemoveEditedElementPouVar(tagname, old_type, old_name)
                    else:
                        self.AddEditedElementPouVar(tagname, new_type, new_name)
                elif new_typeinfos["type"] != "function":
                    self.ChangeEditedElementPouVar(tagname, old_type, old_name, new_type, new_name)
            elif new_name != old_name:
                self.ChangeEditedElementPouVar(tagname, old_type, old_name, new_type, new_name)
            for param, value in infos.items():
                if param == "name":
                    block.setinstanceName(value)
                elif param == "type":
                    block.settypeName(value)
                elif param == "executionOrder" and block.getexecutionOrderId() != value:
                    element.setelementExecutionOrder(block, value)
                elif param == "height":
                    block.setheight(value)
                elif param == "width":
                    block.setwidth(value)
                elif param == "x":
                    block.setx(value)
                elif param == "y":
                    block.sety(value)
                elif param == "connectors":
                    block.inputVariables.setvariable([])
                    block.outputVariables.setvariable([])
                    for connector in value["inputs"]:
                        variable = plcopen.inputVariables_variable()
                        variable.setformalParameter(connector.GetName())
                        if connector.IsNegated():
                            variable.setnegated(True)
                        if connector.GetEdge() != "none":
                            variable.setedge(connector.GetEdge())
                        position = connector.GetRelPosition()
                        variable.connectionPointIn.setrelPositionXY(position.x, position.y)
                        self.SetConnectionWires(variable.connectionPointIn, connector)
                        block.inputVariables.appendvariable(variable)
                    for connector in value["outputs"]:
                        variable = plcopen.outputVariables_variable()
                        variable.setformalParameter(connector.GetName())
                        if connector.IsNegated():
                            variable.setnegated(True)
                        if connector.GetEdge() != "none":
                            variable.setedge(connector.GetEdge())
                        position = connector.GetRelPosition()
                        variable.addconnectionPointOut()
                        variable.connectionPointOut.setrelPositionXY(position.x, position.y)
                        block.outputVariables.appendvariable(variable)
            self.Project.RefreshElementUsingTree()
        
    def AddEditedElementVariable(self, tagname, id, type):
        element = self.GetEditedElement(tagname)
        if element is not None:            
            if type == INPUT:
                name = "inVariable"
                variable = plcopen.fbdObjects_inVariable()
            elif type == OUTPUT:
                name = "outVariable"
                variable = plcopen.fbdObjects_outVariable()
            elif type == INOUT:
                name = "inOutVariable"
                variable = plcopen.fbdObjects_inOutVariable()
            variable.setlocalId(id)
            element.addinstance(name, variable)
        
    def SetEditedElementVariableInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            variable = element.getinstance(id)
            if variable is None:
                return 
            for param, value in infos.items():
                if param == "name":
                    variable.setexpression(value)    
                elif param == "executionOrder" and variable.getexecutionOrderId() != value:
                    element.setelementExecutionOrder(variable, value)
                elif param == "height":
                    variable.setheight(value)
                elif param == "width":
                    variable.setwidth(value)
                elif param == "x":
                    variable.setx(value)
                elif param == "y":
                    variable.sety(value)
                elif param == "connectors":
                    if len(value["outputs"]) > 0:
                        output = value["outputs"][0]
                        if len(value["inputs"]) > 0:
                            variable.setnegatedOut(output.IsNegated())
                            variable.setedgeOut(output.GetEdge())
                        else:
                            variable.setnegated(output.IsNegated())
                            variable.setedge(output.GetEdge())
                        position = output.GetRelPosition()
                        variable.addconnectionPointOut()
                        variable.connectionPointOut.setrelPositionXY(position.x, position.y)
                    if len(value["inputs"]) > 0:
                        input = value["inputs"][0]
                        if len(value["outputs"]) > 0:
                            variable.setnegatedIn(input.IsNegated())
                            variable.setedgeIn(input.GetEdge())
                        else:
                            variable.setnegated(input.IsNegated())
                            variable.setedge(input.GetEdge())
                        position = input.GetRelPosition()
                        variable.addconnectionPointIn()
                        variable.connectionPointIn.setrelPositionXY(position.x, position.y)
                        self.SetConnectionWires(variable.connectionPointIn, input)

    def AddEditedElementConnection(self, tagname, id, type):
        element = self.GetEditedElement(tagname)
        if element is not None:
            if type == CONNECTOR:
                name = "connector"
                connection = plcopen.commonObjects_connector()
            elif type == CONTINUATION:
                name = "continuation"
                connection = plcopen.commonObjects_continuation()
            connection.setlocalId(id)
            element.addinstance(name, connection)
        
    def SetEditedElementConnectionInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            connection = element.getinstance(id)
            if connection is None:
                return
            for param, value in infos.items():
                if param == "name":
                    connection.setname(value)    
                elif param == "height":
                    connection.setheight(value)
                elif param == "width":
                    connection.setwidth(value)
                elif param == "x":
                    connection.setx(value)
                elif param == "y":
                    connection.sety(value)
                elif param == "connector":
                    position = value.GetRelPosition()
                    if isinstance(connection, plcopen.commonObjects_continuation):
                        connection.addconnectionPointOut()
                        connection.connectionPointOut.setrelPositionXY(position.x, position.y)
                    elif isinstance(connection, plcopen.commonObjects_connector):
                        connection.addconnectionPointIn()
                        connection.connectionPointIn.setrelPositionXY(position.x, position.y)
                        self.SetConnectionWires(connection.connectionPointIn, value)

    def AddEditedElementComment(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            comment = plcopen.commonObjects_comment()
            comment.setlocalId(id)
            element.addinstance("comment", comment)
    
    def SetEditedElementCommentInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            comment = element.getinstance(id)
            for param, value in infos.items():
                if param == "content":
                    comment.setcontentText(value)
                elif param == "height":
                    comment.setheight(value)
                elif param == "width":
                    comment.setwidth(value)
                elif param == "x":
                    comment.setx(value)
                elif param == "y":
                    comment.sety(value)

    def AddEditedElementPowerRail(self, tagname, id, type):
        element = self.GetEditedElement(tagname)
        if element is not None:
            if type == LEFTRAIL:
                name = "leftPowerRail"
                powerrail = plcopen.ldObjects_leftPowerRail()
            elif type == RIGHTRAIL:
                name = "rightPowerRail"
                powerrail = plcopen.ldObjects_rightPowerRail()
            powerrail.setlocalId(id)
            element.addinstance(name, powerrail)
    
    def SetEditedElementPowerRailInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            powerrail = element.getinstance(id)
            if powerrail is None:
                return
            for param, value in infos.items():
                if param == "height":
                    powerrail.setheight(value)
                elif param == "width":
                    powerrail.setwidth(value)
                elif param == "x":
                    powerrail.setx(value)
                elif param == "y":
                    powerrail.sety(value)
                elif param == "connectors":
                    if isinstance(powerrail, plcopen.ldObjects_leftPowerRail):
                        powerrail.setconnectionPointOut([])
                        for connector in value["outputs"]:
                            position = connector.GetRelPosition()
                            connection = plcopen.leftPowerRail_connectionPointOut()
                            connection.setrelPositionXY(position.x, position.y)
                            powerrail.connectionPointOut.append(connection)
                    elif isinstance(powerrail, plcopen.ldObjects_rightPowerRail):
                        powerrail.setconnectionPointIn([])
                        for connector in value["inputs"]:
                            position = connector.GetRelPosition()
                            connection = plcopen.connectionPointIn()
                            connection.setrelPositionXY(position.x, position.y)
                            self.SetConnectionWires(connection, connector)
                            powerrail.connectionPointIn.append(connection)

    def AddEditedElementContact(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            contact = plcopen.ldObjects_contact()
            contact.setlocalId(id)
            element.addinstance("contact", contact)

    def SetEditedElementContactInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            contact = element.getinstance(id)
            if contact is None:
                return
            for param, value in infos.items():
                if param == "name":
                    contact.setvariable(value)
                elif param == "type":
                    if value == CONTACT_NORMAL:
                        contact.setnegated(False)
                        contact.setedge("none")
                    elif value == CONTACT_REVERSE:
                        contact.setnegated(True)
                        contact.setedge("none")
                    elif value == CONTACT_RISING:
                        contact.setnegated(False)
                        contact.setedge("rising")
                    elif value == CONTACT_FALLING:
                        contact.setnegated(False)
                        contact.setedge("falling")
                elif param == "height":
                    contact.setheight(value)
                elif param == "width":
                    contact.setwidth(value)
                elif param == "x":
                    contact.setx(value)
                elif param == "y":
                    contact.sety(value)
                elif param == "connectors":
                    input_connector = value["inputs"][0]
                    position = input_connector.GetRelPosition()
                    contact.addconnectionPointIn()
                    contact.connectionPointIn.setrelPositionXY(position.x, position.y)
                    self.SetConnectionWires(contact.connectionPointIn, input_connector)
                    output_connector = value["outputs"][0]
                    position = output_connector.GetRelPosition()
                    contact.addconnectionPointOut()
                    contact.connectionPointOut.setrelPositionXY(position.x, position.y)

    def AddEditedElementCoil(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            coil = plcopen.ldObjects_coil()
            coil.setlocalId(id)
            element.addinstance("coil", coil)

    def SetEditedElementCoilInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            coil = element.getinstance(id)
            if coil is None:
                return
            for param, value in infos.items():
                if param == "name":
                    coil.setvariable(value)
                elif param == "type":
                    if value == COIL_NORMAL:
                        coil.setnegated(False)
                        coil.setstorage("none")
                        coil.setedge("none")
                    elif value == COIL_REVERSE:
                        coil.setnegated(True)
                        coil.setstorage("none")
                        coil.setedge("none")
                    elif value == COIL_SET:
                        coil.setnegated(False)
                        coil.setstorage("set")
                        coil.setedge("none")
                    elif value == COIL_RESET:
                        coil.setnegated(False)
                        coil.setstorage("reset")
                        coil.setedge("none")
                    elif value == COIL_RISING:
                        coil.setnegated(False)
                        coil.setstorage("none")
                        coil.setedge("rising")
                    elif value == COIL_FALLING:
                        coil.setnegated(False)
                        coil.setstorage("none")
                        coil.setedge("falling")
                elif param == "height":
                    coil.setheight(value)
                elif param == "width":
                    coil.setwidth(value)
                elif param == "x":
                    coil.setx(value)
                elif param == "y":
                    coil.sety(value)
                elif param == "connectors":
                    input_connector = value["inputs"][0]
                    position = input_connector.GetRelPosition()
                    coil.addconnectionPointIn()
                    coil.connectionPointIn.setrelPositionXY(position.x, position.y)
                    self.SetConnectionWires(coil.connectionPointIn, input_connector)
                    output_connector = value["outputs"][0]
                    position = output_connector.GetRelPosition()
                    coil.addconnectionPointOut()
                    coil.connectionPointOut.setrelPositionXY(position.x, position.y)

    def AddEditedElementStep(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            step = plcopen.sfcObjects_step()
            step.setlocalId(id)
            element.addinstance("step", step)
    
    def SetEditedElementStepInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            step = element.getinstance(id)
            if step is None:
                return
            for param, value in infos.items():
                if param == "name":
                    step.setname(value)
                elif param == "initial":
                    step.setinitialStep(value)
                elif param == "height":
                    step.setheight(value)
                elif param == "width":
                    step.setwidth(value)
                elif param == "x":
                    step.setx(value)
                elif param == "y":
                    step.sety(value)
                elif param == "connectors":
                    if len(value["inputs"]) > 0:
                        input_connector = value["inputs"][0]
                        position = input_connector.GetRelPosition()
                        step.addconnectionPointIn()
                        step.connectionPointIn.setrelPositionXY(position.x, position.y)
                        self.SetConnectionWires(step.connectionPointIn, input_connector)
                    else:
                        step.deleteconnectionPointIn()
                    if len(value["outputs"]) > 0:
                        output_connector = value["outputs"][0]
                        position = output_connector.GetRelPosition()
                        step.addconnectionPointOut()
                        step.connectionPointOut.setrelPositionXY(position.x, position.y)
                    else:
                        step.deleteconnectionPointOut()
                elif param == "action":
                    if value:
                        position = value.GetRelPosition()
                        step.addconnectionPointOutAction()
                        step.connectionPointOutAction.setrelPositionXY(position.x, position.y)
                    else:
                        step.deleteconnectionPointOutAction()
    
    def AddEditedElementTransition(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            transition = plcopen.sfcObjects_transition()
            transition.setlocalId(id)
            element.addinstance("transition", transition)
    
    def SetEditedElementTransitionInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            transition = element.getinstance(id)
            if transition is None:
                return
            for param, value in infos.items():
                if param == "type" and value != "connection":
                    transition.setconditionContent(value, infos["condition"])
                elif param == "height":
                    transition.setheight(value)
                elif param == "width":
                    transition.setwidth(value)
                elif param == "x":
                    transition.setx(value)
                elif param == "y":
                    transition.sety(value)
                elif param == "priority":
                    if value != 0:
                        transition.setpriority(value)
                    else:
                        transition.setpriority(None)
                elif param == "connectors":
                    input_connector = value["inputs"][0]
                    position = input_connector.GetRelPosition()
                    transition.addconnectionPointIn()
                    transition.connectionPointIn.setrelPositionXY(position.x, position.y)
                    self.SetConnectionWires(transition.connectionPointIn, input_connector)
                    output_connector = value["outputs"][0]
                    position = output_connector.GetRelPosition()
                    transition.addconnectionPointOut()
                    transition.connectionPointOut.setrelPositionXY(position.x, position.y)
                elif infos.get("type", None) == "connection" and param == "connection" and value:
                    transition.setconditionContent("connection", None)
                    self.SetConnectionWires(transition.condition.content["value"], value)
    
    def AddEditedElementDivergence(self, tagname, id, type):
        element = self.GetEditedElement(tagname)
        if element is not None:
            if type == SELECTION_DIVERGENCE:
                name = "selectionDivergence"
                divergence = plcopen.sfcObjects_selectionDivergence()
            elif type == SELECTION_CONVERGENCE:
                name = "selectionConvergence"
                divergence = plcopen.sfcObjects_selectionConvergence()
            elif type == SIMULTANEOUS_DIVERGENCE:
                name = "simultaneousDivergence"
                divergence = plcopen.sfcObjects_simultaneousDivergence()
            elif type == SIMULTANEOUS_CONVERGENCE:
                name = "simultaneousConvergence"
                divergence = plcopen.sfcObjects_simultaneousConvergence()
            divergence.setlocalId(id)
            element.addinstance(name, divergence)
    
    def SetEditedElementDivergenceInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            divergence = element.getinstance(id)
            if divergence is None:
                return
            for param, value in infos.items():
                if param == "height":
                    divergence.setheight(value)
                elif param == "width":
                    divergence.setwidth(value)
                elif param == "x":
                    divergence.setx(value)
                elif param == "y":
                    divergence.sety(value)
                elif param == "connectors":
                    input_connectors = value["inputs"]
                    if isinstance(divergence, (plcopen.sfcObjects_selectionDivergence, plcopen.sfcObjects_simultaneousDivergence)):
                        position = input_connectors[0].GetRelPosition()
                        divergence.addconnectionPointIn()
                        divergence.connectionPointIn.setrelPositionXY(position.x, position.y)
                        self.SetConnectionWires(divergence.connectionPointIn, input_connectors[0])
                    else:
                        divergence.setconnectionPointIn([])
                        for input_connector in input_connectors:
                            position = input_connector.GetRelPosition()
                            if isinstance(divergence, plcopen.sfcObjects_selectionConvergence):
                                connection = plcopen.selectionConvergence_connectionPointIn()
                            else:
                                connection = plcopen.connectionPointIn()
                            connection.setrelPositionXY(position.x, position.y)
                            self.SetConnectionWires(connection, input_connector)
                            divergence.appendconnectionPointIn(connection)
                    output_connectors = value["outputs"]
                    if isinstance(divergence, (plcopen.sfcObjects_selectionConvergence, plcopen.sfcObjects_simultaneousConvergence)):
                        position = output_connectors[0].GetRelPosition()
                        divergence.addconnectionPointOut()
                        divergence.connectionPointOut.setrelPositionXY(position.x, position.y)
                    else:
                        divergence.setconnectionPointOut([])
                        for output_connector in output_connectors:
                            position = output_connector.GetRelPosition()
                            if isinstance(divergence, plcopen.sfcObjects_selectionDivergence):
                                connection = plcopen.selectionDivergence_connectionPointOut()
                            else:
                                connection = plcopen.simultaneousDivergence_connectionPointOut()
                            connection.setrelPositionXY(position.x, position.y)
                            divergence.appendconnectionPointOut(connection)
    
    def AddEditedElementJump(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            jump = plcopen.sfcObjects_jumpStep()
            jump.setlocalId(id)
            element.addinstance("jumpStep", jump)
    
    def SetEditedElementJumpInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            jump = element.getinstance(id)
            if jump is None:
                return
            for param, value in infos.items():
                if param == "target":
                    jump.settargetName(value)
                elif param == "height":
                    jump.setheight(value)
                elif param == "width":
                    jump.setwidth(value)
                elif param == "x":
                    jump.setx(value)
                elif param == "y":
                    jump.sety(value)
                elif param == "connector":
                    position = value.GetRelPosition()
                    jump.addconnectionPointIn()
                    jump.connectionPointIn.setrelPositionXY(position.x, position.y)
                    self.SetConnectionWires(jump.connectionPointIn, value)
 
    def AddEditedElementActionBlock(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            actionBlock = plcopen.commonObjects_actionBlock()
            actionBlock.setlocalId(id)
            element.addinstance("actionBlock", actionBlock)
    
    def SetEditedElementActionBlockInfos(self, tagname, id, infos):
        element = self.GetEditedElement(tagname)
        if element is not None:
            actionBlock = element.getinstance(id)
            if actionBlock is None:
                return
            for param, value in infos.items():
                if param == "actions":
                    actionBlock.setactions(value)
                elif param == "height":
                    actionBlock.setheight(value)
                elif param == "width":
                    actionBlock.setwidth(value)
                elif param == "x":
                    actionBlock.setx(value)
                elif param == "y":
                    actionBlock.sety(value)
                elif param == "connector":
                    position = value.GetRelPosition()
                    actionBlock.addconnectionPointIn()
                    actionBlock.connectionPointIn.setrelPositionXY(position.x, position.y)
                    self.SetConnectionWires(actionBlock.connectionPointIn, value)
    
    def RemoveEditedElementInstance(self, tagname, id):
        element = self.GetEditedElement(tagname)
        if element is not None:
            instance = element.getinstance(id)
            if isinstance(instance, plcopen.fbdObjects_block):
                self.RemoveEditedElementPouVar(tagname, instance.gettypeName(), instance.getinstanceName())
            element.removeinstance(id)
            self.Project.RefreshElementUsingTree()

    def GetEditedResourceVariables(self, tagname, debug = False):
        varlist = []
        words = tagname.split("::")
        for var in self.GetConfigurationGlobalVars(words[1], debug):
            if var["Type"] == "BOOL":
                varlist.append(var["Name"])
        for var in self.GetConfigurationResourceGlobalVars(words[1], words[2], debug):
            if var["Type"] == "BOOL":
                varlist.append(var["Name"])
        return varlist

    def SetEditedResourceInfos(self, tagname, tasks, instances):
        resource = self.GetEditedElement(tagname)
        if resource is not None:
            resource.settask([])
            resource.setpouInstance([])
            task_list = {}
            for task in tasks:
                new_task = plcopen.resource_task()
                new_task.setname(task["Name"])
                if task["Triggering"] == "Interrupt":
                    new_task.setsingle(task["Single"])
##                result = duration_model.match(task["Interval"]).groups()
##                if reduce(lambda x, y: x or y != None, result):
##                    values = []
##                    for value in result[:-1]:
##                        if value != None:
##                            values.append(int(value))
##                        else:
##                            values.append(0)
##                    if result[-1] is not None:
##                        values.append(int(float(result[-1]) * 1000))
##                    new_task.setinterval(datetime.time(*values))
                if task["Triggering"] == "Cyclic":
                    new_task.setinterval(task["Interval"])
                new_task.setpriority(int(task["Priority"]))
                if task["Name"] != "":
                    task_list[task["Name"]] = new_task
                resource.appendtask(new_task)
            for instance in instances:
                new_instance = plcopen.pouInstance()
                new_instance.setname(instance["Name"])
                new_instance.settypeName(instance["Type"])
                task_list.get(instance["Task"], resource).appendpouInstance(new_instance)

    def GetEditedResourceInfos(self, tagname, debug = False):
        resource = self.GetEditedElement(tagname, debug)
        if resource is not None:
            tasks = resource.gettask()
            instances = resource.getpouInstance()
            tasks_data = []
            instances_data = []
            for task in tasks:
                new_task = {}
                new_task["Name"] = task.getname()
                single = task.getsingle()
                if single is not None:
                    new_task["Single"] = single
                else:
                    new_task["Single"] = ""
                interval = task.getinterval()
                if interval is not None:
##                    text = ""
##                    if interval.hour != 0:
##                        text += "%dh"%interval.hour
##                    if interval.minute != 0:
##                        text += "%dm"%interval.minute
##                    if interval.second != 0:
##                        text += "%ds"%interval.second
##                    if interval.microsecond != 0:
##                        if interval.microsecond % 1000 != 0:
##                            text += "%.3fms"%(float(interval.microsecond) / 1000)
##                        else:
##                            text += "%dms"%(interval.microsecond / 1000)
##                    new_task["Interval"] = text
                    new_task["Interval"] = interval
                else:
                    new_task["Interval"] = ""
                if single is not None and interval is None:
                    new_task["Triggering"] = "Interrupt"
                elif interval is not None and single is None:
                    new_task["Triggering"] = "Cyclic"
                else:
                    new_task["Triggering"] = ""
                new_task["Priority"] = str(task.getpriority())
                tasks_data.append(new_task)
                for instance in task.getpouInstance():
                    new_instance = {}
                    new_instance["Name"] = instance.getname()
                    new_instance["Type"] = instance.gettypeName()
                    new_instance["Task"] = task.getname()
                    instances_data.append(new_instance)
            for instance in instances:
                new_instance = {}
                new_instance["Name"] = instance.getname()
                new_instance["Type"] = instance.gettypeName()
                new_instance["Task"] = ""
                instances_data.append(new_instance)
            return tasks_data, instances_data

    def OpenXMLFile(self, filepath):
        xmlfile = open(filepath, 'r')
        tree = minidom.parse(xmlfile)
        xmlfile.close()
        
        self.Project = plcopen.project()
        for child in tree.childNodes:
            if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "project":
                try:
                    result = self.Project.loadXMLTree(child)
                except ValueError, e:
                    return _("Project file syntax error:\n\n") + str(e)
                self.SetFilePath(filepath)
                self.Project.RefreshElementUsingTree()
                self.Project.RefreshDataTypeHierarchy()
                self.Project.RefreshCustomBlockTypes()
                self.CreateProjectBuffer(True)
                self.ProgramChunks = []
                self.ProgramOffset = 0
                self.NextCompiledProject = self.Copy(self.Project)
                self.CurrentCompiledProject = None
                self.Buffering = False
                self.CurrentElementEditing = None
                return None
        return _("No PLC project found")

    def SaveXMLFile(self, filepath = None):
        if not filepath and self.FilePath == "":
            return False
        else:
            contentheader = {"modificationDateTime": datetime.datetime(*localtime()[:6])}
            self.Project.setcontentHeader(contentheader)
            
            text = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
            extras = {"xmlns" : "http://www.plcopen.org/xml/tc6.xsd",
                      "xmlns:xhtml" : "http://www.w3.org/1999/xhtml",
                      "xmlns:xsi" : "http://www.w3.org/2001/XMLSchema-instance",
                      "xsi:schemaLocation" : "http://www.plcopen.org/xml/tc6.xsd"}
            text += self.Project.generateXMLText("project", 0, extras)
            
            if filepath:
                xmlfile = open(filepath,"w")
            else:
                xmlfile = open(self.FilePath,"w")
            xmlfile.write(text.encode("utf-8"))
            xmlfile.close()
            self.MarkProjectAsSaved()
            if filepath:
                self.SetFilePath(filepath)
            return True

#-------------------------------------------------------------------------------
#                       Search in Current Project Functions
#-------------------------------------------------------------------------------

    def SearchInProject(self, criteria):
        return self.Project.Search(criteria)

    def SearchInPou(self, tagname, criteria, debug=False):
        pou = self.GetEditedElement(tagname, debug)
        if pou is not None:
            return pou.Search(criteria)
        return []

#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the project
    """
    def Copy(self, model):
        return cPickle.loads(cPickle.dumps(model))

    def CreateProjectBuffer(self, saved):
        if self.ProjectBufferEnabled:
            self.ProjectBuffer = UndoBuffer(cPickle.dumps(self.Project), saved)
        else:
            self.ProjectBuffer = None
            self.ProjectSaved = saved

    def IsProjectBufferEnabled(self):
        return self.ProjectBufferEnabled

    def EnableProjectBuffer(self, enable):
        self.ProjectBufferEnabled = enable
        if self.Project is not None:
            if enable:
                current_saved = self.ProjectSaved
            else:
                current_saved = self.ProjectBuffer.IsCurrentSaved()
            self.CreateProjectBuffer(current_saved)

    def BufferProject(self):
        if self.ProjectBuffer is not None:
            self.ProjectBuffer.Buffering(cPickle.dumps(self.Project))
        else:
            self.ProjectSaved = False

    def StartBuffering(self):
        if self.ProjectBuffer is not None:
            self.Buffering = True
        else:
            self.ProjectSaved = False
        
    def EndBuffering(self):
        if self.ProjectBuffer is not None and self.Buffering:
            self.ProjectBuffer.Buffering(cPickle.dumps(self.Project))
            self.Buffering = False

    def MarkProjectAsSaved(self):
        self.EndBuffering()
        if self.ProjectBuffer is not None:
            self.ProjectBuffer.CurrentSaved()
        else:
            self.ProjectSaved = True
    
    # Return if project is saved
    def ProjectIsSaved(self):
        if self.ProjectBuffer is not None:
            return self.ProjectBuffer.IsCurrentSaved() and not self.Buffering
        else:
            return self.ProjectSaved

    def LoadPrevious(self):
        self.EndBuffering()
        if self.ProjectBuffer is not None:
            self.Project = cPickle.loads(self.ProjectBuffer.Previous())
    
    def LoadNext(self):
        if self.ProjectBuffer is not None:
            self.Project = cPickle.loads(self.ProjectBuffer.Next())
    
    def GetBufferState(self):
        if self.ProjectBuffer is not None:
            first = self.ProjectBuffer.IsFirst() and not self.Buffering
            last = self.ProjectBuffer.IsLast()
            return not first, not last
        return False, False
