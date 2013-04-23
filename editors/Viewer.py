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

import re
import math
import time
from types import TupleType
from threading import Lock

import wx

from plcopen.structures import *
from PLCControler import ITEM_VAR_LOCAL, ITEM_POU, ITEM_PROGRAM, ITEM_FUNCTIONBLOCK

from dialogs import *
from graphics import *
from EditorPanel import EditorPanel

SCROLLBAR_UNIT = 10
WINDOW_BORDER = 10
SCROLL_ZONE = 10

CURSORS = None

def ResetCursors():
    global CURSORS
    if CURSORS == None:
        CURSORS = [wx.NullCursor, 
                   wx.StockCursor(wx.CURSOR_HAND),
                   wx.StockCursor(wx.CURSOR_SIZENWSE),
                   wx.StockCursor(wx.CURSOR_SIZENESW),
                   wx.StockCursor(wx.CURSOR_SIZEWE),
                   wx.StockCursor(wx.CURSOR_SIZENS)]

def AppendMenu(parent, help, id, kind, text):
    if wx.VERSION >= (2, 6, 0):
        parent.Append(help=help, id=id, kind=kind, text=text)
    else:
        parent.Append(helpString=help, id=id, kind=kind, item=text)

if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 10,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 12,
             }

ZOOM_FACTORS = [math.sqrt(2) ** x for x in xrange(-6, 7)]

def GetVariableCreationFunction(variable_type):
    def variableCreationFunction(viewer, id, specific_values):
        return FBD_Variable(viewer, variable_type, 
                                    specific_values["name"], 
                                    specific_values["value_type"], 
                                    id,
                                    specific_values["executionOrder"])
    return variableCreationFunction

def GetConnectorCreationFunction(connector_type):
    def connectorCreationFunction(viewer, id, specific_values):
        return FBD_Connector(viewer, connector_type, 
                                     specific_values["name"], id)
    return connectorCreationFunction

def commentCreationFunction(viewer, id, specific_values):
    return Comment(viewer, specific_values["content"], id)

def GetPowerRailCreationFunction(powerrail_type):
    def powerRailCreationFunction(viewer, id, specific_values):
        return LD_PowerRail(viewer, powerrail_type, id, 
                                    specific_values["connectors"])
    return powerRailCreationFunction

CONTACT_TYPES = {(True, "none"): CONTACT_REVERSE,
                 (False, "rising"): CONTACT_RISING,
                 (False, "falling"): CONTACT_FALLING}

def contactCreationFunction(viewer, id, specific_values):
    contact_type = CONTACT_TYPES.get((specific_values.get("negated", False), 
                                      specific_values.get("edge", "none")),
                                     CONTACT_NORMAL)
    return LD_Contact(viewer, contact_type, specific_values["name"], id)

COIL_TYPES = {(True, "none", "none"): COIL_REVERSE,
              (False, "none", "set"): COIL_SET,
              (False, "none", "reset"): COIL_RESET,
              (False, "rising", "none"): COIL_RISING,
              (False, "falling", "none"): COIL_FALLING}

def coilCreationFunction(viewer, id, specific_values):
    coil_type = COIL_TYPES.get((specific_values.get("negated", False), 
                                specific_values.get("edge", "none"),
                                specific_values.get("storage", "none")),
                               COIL_NORMAL)
    return LD_Coil(viewer, coil_type, specific_values["name"], id)

def stepCreationFunction(viewer, id, specific_values):
    step = SFC_Step(viewer, specific_values["name"], 
                            specific_values.get("initial", False), id)
    if specific_values.get("action", None):
        step.AddAction()
        connector = step.GetActionConnector()
        connector.SetPosition(wx.Point(*specific_values["action"]["position"]))
    return step

def transitionCreationFunction(viewer, id, specific_values):
    transition = SFC_Transition(viewer, specific_values["condition_type"], 
                                        specific_values.get("condition", None), 
                                        specific_values["priority"], id)
    return transition

def GetDivergenceCreationFunction(divergence_type):
    def divergenceCreationFunction(viewer, id, specific_values):
        return SFC_Divergence(viewer, divergence_type, 
                                      specific_values["connectors"], id)
    return divergenceCreationFunction

def jumpCreationFunction(viewer, id, specific_values):
    return SFC_Jump(viewer, specific_values["target"], id)

def actionBlockCreationFunction(viewer, id, specific_values):
    return SFC_ActionBlock(viewer, specific_values["actions"], id)

ElementCreationFunctions = {
    "input": GetVariableCreationFunction(INPUT),
    "output": GetVariableCreationFunction(OUTPUT),
    "inout": GetVariableCreationFunction(INOUT),
    "connector": GetConnectorCreationFunction(CONNECTOR),
    "continuation": GetConnectorCreationFunction(CONTINUATION),
    "comment": commentCreationFunction,
    "leftPowerRail": GetPowerRailCreationFunction(LEFTRAIL),
    "rightPowerRail": GetPowerRailCreationFunction(RIGHTRAIL),
    "contact": contactCreationFunction,
    "coil": coilCreationFunction,
    "step": stepCreationFunction, 
    "transition": transitionCreationFunction,
    "selectionDivergence": GetDivergenceCreationFunction(SELECTION_DIVERGENCE), 
    "selectionConvergence": GetDivergenceCreationFunction(SELECTION_CONVERGENCE), 
    "simultaneousDivergence": GetDivergenceCreationFunction(SIMULTANEOUS_DIVERGENCE), 
    "simultaneousConvergence": GetDivergenceCreationFunction(SIMULTANEOUS_CONVERGENCE), 
    "jump": jumpCreationFunction,
    "actionBlock": actionBlockCreationFunction,
}

def sort_blocks(block_infos1, block_infos2):
    x1, y1 = block_infos1[0].GetPosition()
    x2, y2 = block_infos2[0].GetPosition()
    if y1 == y2:
        return cmp(x1, x2)
    else:
        return cmp(y1, y2)

#-------------------------------------------------------------------------------
#                       Graphic elements Viewer base class
#-------------------------------------------------------------------------------

# ID Constants for alignment menu items
[ID_VIEWERALIGNMENTMENUITEMS0, ID_VIEWERALIGNMENTMENUITEMS1,
 ID_VIEWERALIGNMENTMENUITEMS2, ID_VIEWERALIGNMENTMENUITEMS4,
 ID_VIEWERALIGNMENTMENUITEMS5, ID_VIEWERALIGNMENTMENUITEMS6,
] = [wx.NewId() for _init_coll_AlignmentMenu_Items in range(6)]

# ID Constants for contextual menu items
[ID_VIEWERCONTEXTUALMENUITEMS0, ID_VIEWERCONTEXTUALMENUITEMS1,
 ID_VIEWERCONTEXTUALMENUITEMS2, ID_VIEWERCONTEXTUALMENUITEMS3,
 ID_VIEWERCONTEXTUALMENUITEMS5, ID_VIEWERCONTEXTUALMENUITEMS6,
 ID_VIEWERCONTEXTUALMENUITEMS8, ID_VIEWERCONTEXTUALMENUITEMS9,
 ID_VIEWERCONTEXTUALMENUITEMS11, ID_VIEWERCONTEXTUALMENUITEMS12,
 ID_VIEWERCONTEXTUALMENUITEMS14, ID_VIEWERCONTEXTUALMENUITEMS16,
 ID_VIEWERCONTEXTUALMENUITEMS17,
] = [wx.NewId() for _init_coll_ContextualMenu_Items in range(13)]


class ViewerDropTarget(wx.TextDropTarget):
    
    def __init__(self, parent):
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
    
    def OnDropText(self, x, y, data):
        self.ParentWindow.Select()
        tagname = self.ParentWindow.GetTagName()
        pou_name, pou_type = self.ParentWindow.Controler.GetEditedElementType(tagname, self.ParentWindow.Debug)
        x, y = self.ParentWindow.CalcUnscrolledPosition(x, y)
        x = int(x / self.ParentWindow.ViewScale[0])
        y = int(y / self.ParentWindow.ViewScale[1])
        scaling = self.ParentWindow.Scaling
        message = None
        try:
            values = eval(data)
        except:
            message = _("Invalid value \"%s\" for viewer block")%data
            values = None
        if not isinstance(values, TupleType):
            message = _("Invalid value \"%s\" for viewer block")%data
            values = None
        if values is not None:
            if values[1] == "debug":
                pass
            elif values[1] == "program":
                message = _("Programs can't be used by other POUs!")
            elif values[1] in ["function", "functionBlock"]:
                words = tagname.split("::")
                if pou_name == values[0]:
                    message = _("\"%s\" can't use itself!")%pou_name
                elif pou_type == "function" and values[1] != "function":
                    message = _("Function Blocks can't be used in Functions!")
                elif self.ParentWindow.Controler.PouIsUsedBy(pou_name, values[0], self.ParentWindow.Debug):
                    message = _("\"%s\" is already used by \"%s\"!")%(pou_name, values[0])
                else:
                    blockname = values[2]
                    if len(values) > 3:
                        blockinputs = values[3]
                    else:
                        blockinputs = None
                    if values[1] != "function" and blockname == "":
                        blockname = self.ParentWindow.GenerateNewName(blocktype=values[0])
                    if blockname.upper() in [name.upper() for name in self.ParentWindow.Controler.GetProjectPouNames(self.ParentWindow.Debug)]:
                        message = _("\"%s\" pou already exists!")%blockname
                    elif blockname.upper() in [name.upper() for name in self.ParentWindow.Controler.GetEditedElementVariables(tagname, self.ParentWindow.Debug)]:
                        message = _("\"%s\" element for this pou already exists!")%blockname
                    else:
                        id = self.ParentWindow.GetNewId()
                        block = FBD_Block(self.ParentWindow, values[0], blockname, id, inputs = blockinputs)
                        width, height = block.GetMinSize()
                        if scaling is not None:
                            x = round(float(x) / float(scaling[0])) * scaling[0]
                            y = round(float(y) / float(scaling[1])) * scaling[1]
                            width = round(float(width) / float(scaling[0]) + 0.5) * scaling[0]
                            height = round(float(height) / float(scaling[1]) + 0.5) * scaling[1]
                        block.SetPosition(x, y)
                        block.SetSize(width, height)
                        self.ParentWindow.AddBlock(block)
                        self.ParentWindow.Controler.AddEditedElementBlock(tagname, id, values[0], blockname)
                        self.ParentWindow.RefreshBlockModel(block)
                        self.ParentWindow.RefreshBuffer()
                        self.ParentWindow.RefreshScrollBars()
                        self.ParentWindow.RefreshVisibleElements()
                        self.ParentWindow.RefreshVariablePanel()
                        self.ParentWindow.Refresh(False)
            elif values[1] == "location":
                if pou_type == "program":
                    location = values[0]
                    if not location.startswith("%"):
                        dialog = wx.SingleChoiceDialog(self.ParentWindow.ParentWindow, 
                              _("Select a variable class:"), _("Variable class"), 
                              ["Input", "Output", "Memory"], 
                              wx.DEFAULT_DIALOG_STYLE|wx.OK|wx.CANCEL)
                        if dialog.ShowModal() == wx.ID_OK:
                            selected = dialog.GetSelection()
                        else:
                            selected = None
                        dialog.Destroy()
                        if selected is None:
                            return
                        if selected == 0:
                            location = "%I" + location
                        elif selected == 1:
                            location = "%Q" + location
                        else:
                            location = "%M" + location
                    var_name = values[3]
                    if var_name.upper() in [name.upper() for name in self.ParentWindow.Controler.GetProjectPouNames(self.ParentWindow.Debug)]:
                        message = _("\"%s\" pou already exists!")%var_name
                    else:
                        if location[1] == "Q":
                            var_class = OUTPUT
                        else:
                            var_class = INPUT
                        if values[2] is not None:
                            var_type = values[2]
                        else:
                            var_type = LOCATIONDATATYPES.get(location[2], ["BOOL"])[0]
                        if not var_name.upper() in [name.upper() for name in self.ParentWindow.Controler.GetEditedElementVariables(tagname, self.ParentWindow.Debug)]:
                            self.ParentWindow.Controler.AddEditedElementPouVar(tagname, var_type, var_name, location, values[4])
                            self.ParentWindow.RefreshVariablePanel()
                            self.ParentWindow.ParentWindow.RefreshPouInstanceVariablesPanel()
                        self.ParentWindow.AddVariableBlock(x, y, scaling, var_class, var_name, var_type)
            elif values[1] == "Global":
                var_name = values[0]
                if var_name.upper() in [name.upper() for name in self.ParentWindow.Controler.GetProjectPouNames(self.ParentWindow.Debug)]:
                    message = _("\"%s\" pou already exists!")%var_name
                else:
                    if not var_name.upper() in [name.upper() for name in self.ParentWindow.Controler.GetEditedElementVariables(tagname, self.ParentWindow.Debug)]:
                        self.ParentWindow.Controler.AddEditedElementPouExternalVar(tagname, values[2], var_name)
                        self.ParentWindow.RefreshVariablePanel()
                    self.ParentWindow.AddVariableBlock(x, y, scaling, INPUT, var_name, values[2])
            elif values[1] == "Constant":
                self.ParentWindow.AddVariableBlock(x, y, scaling, INPUT, values[0], None)
            elif values[3] == tagname:
                if values[1] == "Output":
                    var_class = OUTPUT
                elif values[1] == "InOut":
                    var_class = INPUT
                else:
                    var_class = INPUT
                tree = dict([(var["Name"], var["Tree"]) for var in self.ParentWindow.Controler.GetEditedElementInterfaceVars(tagname, self.ParentWindow.Debug)]).get(values[0], None)
                if tree is not None:
                    if len(tree[0]) > 0:
                        menu = wx.Menu(title='')
                        self.GenerateTreeMenu(x, y, scaling, menu, "", var_class, [(values[0], values[2], tree)])
                        self.ParentWindow.PopupMenuXY(menu)
                    else:
                        self.ParentWindow.AddVariableBlock(x, y, scaling, var_class, values[0], values[2])
                else:
                    message = _("Unknown variable \"%s\" for this POU!") % values[0]
            else:
                message = _("Variable don't belong to this POU!")
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)

    def GenerateTreeMenu(self, x, y, scaling, menu, base_path, var_class, tree):
        for child_name, child_type, (child_tree, child_dimensions) in tree:
            if base_path:
                child_path = "%s.%s" % (base_path, child_name)
            else:
                child_path = child_name
            if len(child_dimensions) > 0:
                child_path += "[%s]" % ",".join([str(dimension[0]) for dimension in child_dimensions])
                child_name += "[]"
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=child_name)
            self.ParentWindow.Bind(wx.EVT_MENU, self.GetAddVariableBlockFunction(x, y, scaling, var_class, child_path, child_type), id=new_id)
            if len(child_tree) > 0:
                new_id = wx.NewId()
                child_menu = wx.Menu(title='')
                self.GenerateTreeMenu(x, y, scaling, child_menu, child_path, var_class, child_tree)
                menu.AppendMenu(new_id, "%s." % child_name, child_menu)
            
    def GetAddVariableBlockFunction(self, x, y, scaling, var_class, var_name, var_type):
        def AddVariableFunction(event):
            self.ParentWindow.AddVariableBlock(x, y, scaling, var_class, var_name, var_type)
        return AddVariableFunction
    
    def ShowMessage(self, message):
        message = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        message.ShowModal()
        message.Destroy()

"""
Class that implements a Viewer based on a wx.ScrolledWindow for drawing and 
manipulating graphic elements
"""

class Viewer(EditorPanel, DebugViewer, DebugDataConsumer):
    
    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    
    # Add list of menu items to the given menu
    def AddMenuItems(self, menu, items):
        for item in items:
            if item is None:
                menu.AppendSeparator()
            else:
                id, kind, text, help, callback = item
                AppendMenu(menu, help=help, id=id, kind=kind, text=text)
                # Link menu event to corresponding called functions
                self.Bind(wx.EVT_MENU, callback, id=id)
    
    # Add Block Pin Menu items to the given menu
    def AddBlockPinMenuItems(self, menu, connector):
        [ID_NO_MODIFIER, ID_NEGATED, ID_RISING_EDGE, 
         ID_FALLING_EDGE] = [wx.NewId() for i in xrange(4)]
        
        # Create menu items
        self.AddMenuItems(menu, [
            (ID_NO_MODIFIER, wx.ITEM_RADIO, _(u'No Modifier'), '', self.OnNoModifierMenu),
            (ID_NEGATED, wx.ITEM_RADIO, _(u'Negated'), '', self.OnNegatedMenu),
            (ID_RISING_EDGE, wx.ITEM_RADIO, _(u'Rising Edge'), '', self.OnRisingEdgeMenu),
            (ID_FALLING_EDGE, wx.ITEM_RADIO, _(u'Falling Edge'), '', self.OnFallingEdgeMenu)])
        
        type = self.Controler.GetEditedElementType(self.TagName, self.Debug)
        menu.Enable(ID_RISING_EDGE, type != "function")
        menu.Enable(ID_FALLING_EDGE, type != "function")
        
        if connector.IsNegated():
            menu.Check(ID_NEGATED, True)
        elif connector.GetEdge() == "rising":
            menu.Check(ID_RISING_EDGE, True)
        elif connector.GetEdge() == "falling":
            menu.Check(ID_FALLING_EDGE, True)
        else:
            menu.Check(ID_NO_MODIFIER, True)
        
    # Add Alignment Menu items to the given menu
    def AddAlignmentMenuItems(self, menu):
        [ID_ALIGN_LEFT, ID_ALIGN_CENTER, ID_ALIGN_RIGHT,
         ID_ALIGN_TOP, ID_ALIGN_MIDDLE, ID_ALIGN_BOTTOM,
        ] = [wx.NewId() for i in xrange(6)]
        
        # Create menu items
        self.AddMenuItems(menu, [
            (ID_ALIGN_LEFT, wx.ITEM_NORMAL, _(u'Left'), '', self.OnAlignLeftMenu),
            (ID_ALIGN_CENTER, wx.ITEM_NORMAL, _(u'Center'), '', self.OnAlignCenterMenu), 
            (ID_ALIGN_RIGHT, wx.ITEM_NORMAL, _(u'Right'), '', self.OnAlignRightMenu),
            None,
            (ID_ALIGN_TOP, wx.ITEM_NORMAL, _(u'Top'), '', self.OnAlignTopMenu), 
            (ID_ALIGN_MIDDLE, wx.ITEM_NORMAL, _(u'Middle'), '', self.OnAlignMiddleMenu),
            (ID_ALIGN_BOTTOM, wx.ITEM_NORMAL, _(u'Bottom'), '', self.OnAlignBottomMenu)])
    
    # Add Wire Menu items to the given menu
    def AddWireMenuItems(self, menu, delete=False):
        [ID_ADD_SEGMENT, ID_DELETE_SEGMENT] = [wx.NewId() for i in xrange(2)]
        
        # Create menu items
        self.AddMenuItems(menu, [
            (ID_ADD_SEGMENT, wx.ITEM_NORMAL, _(u'Add Wire Segment'), '', self.OnAddSegmentMenu),
            (ID_DELETE_SEGMENT, wx.ITEM_NORMAL, _(u'Delete Wire Segment'), '', self.OnDeleteSegmentMenu)])
    
        menu.Enable(ID_DELETE_SEGMENT, delete)
    
    # Add Divergence Menu items to the given menu
    def AddDivergenceMenuItems(self, menu, delete=False):
        [ID_ADD_BRANCH, ID_DELETE_BRANCH] = [wx.NewId() for i in xrange(2)]
        
        # Create menu items
        self.AddMenuItems(menu, [
            (ID_ADD_BRANCH, wx.ITEM_NORMAL, _(u'Add Divergence Branch'), '', self.OnAddBranchMenu),
            (ID_DELETE_BRANCH, wx.ITEM_NORMAL, _(u'Delete Divergence Branch'), '', self.OnDeleteBranchMenu)])
        
        menu.Enable(ID_DELETE_BRANCH, delete)
    
    # Add Add Menu items to the given menu
    def AddAddMenuItems(self, menu):
        [ID_ADD_BLOCK, ID_ADD_VARIABLE, ID_ADD_CONNECTION,
         ID_ADD_COMMENT] = [wx.NewId() for i in xrange(4)]
        
        # Create menu items
        self.AddMenuItems(menu, [
            (ID_ADD_BLOCK, wx.ITEM_NORMAL, _(u'Block'), '', self.GetAddMenuCallBack(self.AddNewBlock)),
            (ID_ADD_VARIABLE, wx.ITEM_NORMAL, _(u'Variable'), '', self.GetAddMenuCallBack(self.AddNewVariable)),
            (ID_ADD_CONNECTION, wx.ITEM_NORMAL, _(u'Connection'), '', self.GetAddMenuCallBack(self.AddNewConnection)),
            None])
        
        if self.CurrentLanguage != "FBD":
            [ID_ADD_POWER_RAIL, ID_ADD_CONTACT, ID_ADD_COIL,
            ] = [wx.NewId() for i in xrange(3)]
            
            # Create menu items
            self.AddMenuItems(menu, [
                (ID_ADD_POWER_RAIL, wx.ITEM_NORMAL, _(u'Power Rail'), '', self.GetAddMenuCallBack(self.AddNewPowerRail)),
                (ID_ADD_CONTACT, wx.ITEM_NORMAL, _(u'Contact'), '', self.GetAddMenuCallBack(self.AddNewContact))])
                
            if self.CurrentLanguage != "SFC":
                self.AddMenuItems(menu, [
                     (ID_ADD_COIL, wx.ITEM_NORMAL, _(u'Coil'), '', self.GetAddMenuCallBack(self.AddNewCoil))])
            
            menu.AppendSeparator()
        
        if self.CurrentLanguage == "SFC":
            [ID_ADD_INITIAL_STEP, ID_ADD_STEP, ID_ADD_TRANSITION, 
             ID_ADD_ACTION_BLOCK, ID_ADD_DIVERGENCE, ID_ADD_JUMP,
            ] = [wx.NewId() for i in xrange(6)]
            
            # Create menu items
            self.AddMenuItems(menu, [
                (ID_ADD_INITIAL_STEP, wx.ITEM_NORMAL, _(u'Initial Step'), '', self.GetAddMenuCallBack(self.AddNewStep, True)),
                (ID_ADD_STEP, wx.ITEM_NORMAL, _(u'Step'), '', self.GetAddMenuCallBack(self.AddNewStep)),
                (ID_ADD_TRANSITION, wx.ITEM_NORMAL, _(u'Transition'), '', self.GetAddMenuCallBack(self.AddNewTransition)),
                (ID_ADD_ACTION_BLOCK, wx.ITEM_NORMAL, _(u'Action Block'), '', self.GetAddMenuCallBack(self.AddNewActionBlock)),
                (ID_ADD_DIVERGENCE, wx.ITEM_NORMAL, _(u'Divergence'), '', self.GetAddMenuCallBack(self.AddNewDivergence)),
                (ID_ADD_JUMP, wx.ITEM_NORMAL, _(u'Jump'), '', self.GetAddMenuCallBack(self.AddNewJump)),
                None])
        
        self.AddMenuItems(menu, [
             (ID_ADD_COMMENT, wx.ITEM_NORMAL, _(u'Comment'), '', self.GetAddMenuCallBack(self.AddNewComment))])
        
    # Add Default Menu items to the given menu
    def AddDefaultMenuItems(self, menu, edit=False, block=False):
        if block:
            [ID_EDIT_BLOCK, ID_DELETE, ID_ADJUST_BLOCK_SIZE] = [wx.NewId() for i in xrange(3)]
        
            # Create menu items
            self.AddMenuItems(menu, [
                 (ID_EDIT_BLOCK, wx.ITEM_NORMAL, _(u'Edit Block'), '', self.OnEditBlockMenu),
                 (ID_ADJUST_BLOCK_SIZE, wx.ITEM_NORMAL, _(u'Adjust Block Size'), '', self.OnAdjustBlockSizeMenu),
                 (ID_DELETE, wx.ITEM_NORMAL, _(u'Delete'), '', self.OnDeleteMenu)])
        
            menu.Enable(ID_EDIT_BLOCK, edit)
        
        else:
            [ID_CLEAR_EXEC_ORDER, ID_RESET_EXEC_ORDER] = [wx.NewId() for i in xrange(2)]
        
            # Create menu items
            self.AddMenuItems(menu, [
                 (ID_CLEAR_EXEC_ORDER, wx.ITEM_NORMAL, _(u'Clear Execution Order'), '', self.OnClearExecutionOrderMenu),
                 (ID_RESET_EXEC_ORDER, wx.ITEM_NORMAL, _(u'Reset Execution Order'), '', self.OnResetExecutionOrderMenu)])
            
            menu.AppendSeparator()
            
            add_menu = wx.Menu(title='')
            self.AddAddMenuItems(add_menu)
            menu.AppendMenu(-1, _(u'Add'), add_menu)
        
        menu.AppendSeparator()
        
        [ID_CUT, ID_COPY, ID_PASTE] = [wx.NewId() for i in xrange(3)]
        
        # Create menu items
        self.AddMenuItems(menu, [
             (ID_CUT, wx.ITEM_NORMAL, _(u'Cut'), '', self.GetClipboardCallBack(self.Cut)),
             (ID_COPY, wx.ITEM_NORMAL, _(u'Copy'), '', self.GetClipboardCallBack(self.Copy)),
             (ID_PASTE, wx.ITEM_NORMAL, _(u'Paste'), '', self.GetAddMenuCallBack(self.Paste))])
        
        menu.Enable(ID_CUT, block)
        menu.Enable(ID_COPY, block)
        menu.Enable(ID_PASTE, self.ParentWindow.GetCopyBuffer() is not None)
        
    def _init_Editor(self, prnt):
        self.Editor = wx.ScrolledWindow(prnt, name="Viewer", 
            pos=wx.Point(0, 0), size=wx.Size(0, 0), 
            style=wx.HSCROLL | wx.VSCROLL | wx.ALWAYS_SHOW_SB)
        self.Editor.ParentWindow = self
    
    # Create a new Viewer
    def __init__(self, parent, tagname, window, controler, debug = False, instancepath = ""):
        self.VARIABLE_PANEL_TYPE = controler.GetPouType(tagname.split("::")[1])
        
        EditorPanel.__init__(self, parent, tagname, window, controler, debug)
        DebugViewer.__init__(self, controler, debug)
        DebugDataConsumer.__init__(self)
        
        # Adding a rubberband to Viewer
        self.rubberBand = RubberBand(viewer=self)
        self.Editor.SetBackgroundColour(wx.Colour(255,255,255))
        self.Editor.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.ResetView()
        self.Scaling = None
        self.DrawGrid = True
        self.GridBrush = wx.TRANSPARENT_BRUSH
        self.PageSize = None
        self.PagePen = wx.TRANSPARENT_PEN
        self.DrawingWire = False
        self.current_id = 0
        self.TagName = tagname
        self.Highlights = []
        self.SearchParams = None
        self.SearchResults = None
        self.CurrentFindHighlight = None
        self.InstancePath = instancepath
        self.StartMousePos = None
        self.StartScreenPos = None
        self.Buffering = False
        
        # Initialize Cursors
        ResetCursors()
        self.CurrentCursor = 0
        
        # Initialize Block, Wire and Comment numbers
        self.wire_id = 0
        
        # Initialize Viewer mode to Selection mode
        self.Mode = MODE_SELECTION
        self.SavedMode = False
        self.CurrentLanguage = "FBD"
        
        if not self.Debug:
            self.Editor.SetDropTarget(ViewerDropTarget(self))
        
        self.ElementRefreshList = []
        self.ElementRefreshList_lock = Lock()
        
        dc = wx.ClientDC(self.Editor)
        font = wx.Font(faces["size"], wx.SWISS, wx.NORMAL, wx.NORMAL, faceName = faces["mono"])
        dc.SetFont(font)
        width, height = dc.GetTextExtent("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        while width > 260:
            faces["size"] -= 1
            font = wx.Font(faces["size"], wx.SWISS, wx.NORMAL, wx.NORMAL, faceName = faces["mono"])
            dc.SetFont(font)
            width, height = dc.GetTextExtent("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.SetFont(font)
        self.MiniTextDC = wx.MemoryDC()
        self.MiniTextDC.SetFont(wx.Font(faces["size"] * 0.75, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName = faces["helv"]))
        
        self.CurrentScale = None
        self.SetScale(len(ZOOM_FACTORS) / 2, False)
        
        self.RefreshHighlightsTimer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnRefreshHighlightsTimer, self.RefreshHighlightsTimer)
        
        self.ResetView()
        
        # Link Viewer event to corresponding methods
        self.Editor.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Editor.Bind(wx.EVT_LEFT_DOWN, self.OnViewerLeftDown)
        self.Editor.Bind(wx.EVT_LEFT_UP, self.OnViewerLeftUp)
        self.Editor.Bind(wx.EVT_LEFT_DCLICK, self.OnViewerLeftDClick)
        self.Editor.Bind(wx.EVT_RIGHT_DOWN, self.OnViewerRightDown)
        self.Editor.Bind(wx.EVT_RIGHT_UP, self.OnViewerRightUp)
        self.Editor.Bind(wx.EVT_MIDDLE_DOWN, self.OnViewerMiddleDown)
        self.Editor.Bind(wx.EVT_MIDDLE_UP, self.OnViewerMiddleUp)
        self.Editor.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeaveViewer)
        self.Editor.Bind(wx.EVT_MOTION, self.OnViewerMotion)
        self.Editor.Bind(wx.EVT_CHAR, self.OnChar)
        self.Editor.Bind(wx.EVT_SCROLLWIN, self.OnScrollWindow)
        self.Editor.Bind(wx.EVT_SCROLLWIN_THUMBRELEASE, self.OnScrollStop)
        self.Editor.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheelWindow)
        self.Editor.Bind(wx.EVT_SIZE, self.OnMoveWindow)
        self.Editor.Bind(wx.EVT_MOUSE_EVENTS, self.OnViewerMouseEvent)
    
    # Destructor
    def __del__(self):
        DebugViewer.__del__(self)
        self.Flush()
        self.ResetView()
        self.RefreshHighlightsTimer.Stop()
    
    def SetCurrentCursor(self, cursor):
        if self.Mode != MODE_MOTION:
            global CURSORS
            if self.CurrentCursor != cursor:
                self.CurrentCursor = cursor
                self.Editor.SetCursor(CURSORS[cursor])
    
    def GetScrolledRect(self, rect):
        rect.x, rect.y = self.Editor.CalcScrolledPosition(int(rect.x * self.ViewScale[0]), 
                                                   int(rect.y * self.ViewScale[1]))
        rect.width = int(rect.width * self.ViewScale[0]) + 2
        rect.height = int(rect.height * self.ViewScale[1]) + 2
        return rect
    
    def GetTitle(self):
        if self.Debug:
            if len(self.InstancePath) > 15:
                return "..." + self.InstancePath[-12:]
            return self.InstancePath
        return EditorPanel.GetTitle(self)
    
    def GetScaling(self):
        return self.Scaling
    
    def GetInstancePath(self, variable_base=False):
        if variable_base:
            words = self.TagName.split("::")
            if words[0] in ["A", "T"]:
                return ".".join(self.InstancePath.split(".")[:-1])
        return self.InstancePath
    
    def IsViewing(self, tagname):
        if self.Debug:
            return self.InstancePath == tagname
        return EditorPanel.IsViewing(self, tagname)
    
    # Returns a new id
    def GetNewId(self):
        self.current_id += 1
        return self.current_id
        
    def SetScale(self, scale_number, refresh=True, mouse_event=None):
        new_scale = max(0, min(scale_number, len(ZOOM_FACTORS) - 1))
        if self.CurrentScale != new_scale:
            if refresh:
                dc = self.GetLogicalDC()
            self.CurrentScale = new_scale
            self.ViewScale = (ZOOM_FACTORS[self.CurrentScale], ZOOM_FACTORS[self.CurrentScale])
            if refresh:
                self.Editor.Freeze()
                if mouse_event is None:
                    client_size = self.Editor.GetClientSize()
                    mouse_pos = wx.Point(client_size[0] / 2, client_size[1] / 2)
                    mouse_event = wx.MouseEvent(wx.EVT_MOUSEWHEEL.typeId)
                    mouse_event.m_x = mouse_pos.x
                    mouse_event.m_y = mouse_pos.y
                else:
                    mouse_pos = mouse_event.GetPosition()
                pos = mouse_event.GetLogicalPosition(dc)
                xmax = self.GetScrollRange(wx.HORIZONTAL) - self.GetScrollThumb(wx.HORIZONTAL)
                ymax = self.GetScrollRange(wx.VERTICAL) - self.GetScrollThumb(wx.VERTICAL)
                scrollx = max(0, round(pos.x * self.ViewScale[0] - mouse_pos.x) / SCROLLBAR_UNIT)
                scrolly = max(0, round(pos.y * self.ViewScale[1] - mouse_pos.y) / SCROLLBAR_UNIT)
                if scrollx > xmax or scrolly > ymax:
                    self.RefreshScrollBars(max(0, scrollx - xmax), max(0, scrolly - ymax))
                    self.Scroll(scrollx, scrolly)
                else:
                    self.Scroll(scrollx, scrolly)
                    self.RefreshScrollBars()
                self.RefreshScaling(refresh)
                self.Editor.Thaw()
    
    def GetScale(self):
        return self.CurrentScale

    def GetViewScale(self):
        return self.ViewScale

    def GetLogicalDC(self, buffered=False):
        if buffered:
            bitmap = wx.EmptyBitmap(*self.Editor.GetClientSize())
            dc = wx.MemoryDC(bitmap)
        else:
            dc = wx.ClientDC(self.Editor)
        dc.SetFont(self.GetFont())
        if wx.VERSION >= (2, 6, 0):
            self.Editor.DoPrepareDC(dc)
        else:
            self.Editor.PrepareDC(dc)
        dc.SetUserScale(self.ViewScale[0], self.ViewScale[1])
        return dc
    
    def RefreshRect(self, rect, eraseBackground=True):
        self.Editor.RefreshRect(rect, eraseBackground)
    
    def Scroll(self, x, y):
        self.Editor.Scroll(x, y)
    
    def GetScrollPos(self, orientation):
        return self.Editor.GetScrollPos(orientation)
    
    def GetScrollRange(self, orientation):
        return self.Editor.GetScrollRange(orientation)
    
    def GetScrollThumb(self, orientation):
        return self.Editor.GetScrollThumb(orientation)
    
    def CalcUnscrolledPosition(self, x, y):
        return self.Editor.CalcUnscrolledPosition(x, y)
    
    def GetViewStart(self):
        return self.Editor.GetViewStart()
    
    def GetTextExtent(self, text):
        return self.Editor.GetTextExtent(text)
    
    def GetFont(self):
        return self.Editor.GetFont()
    
    def GetMiniTextExtent(self, text):
        return self.MiniTextDC.GetTextExtent(text)
    
    def GetMiniFont(self):
        return self.MiniTextDC.GetFont()
    
#-------------------------------------------------------------------------------
#                         Element management functions
#-------------------------------------------------------------------------------

    def AddBlock(self, block):
        self.Blocks[block.GetId()] = block
        
    def AddWire(self, wire):
        self.wire_id += 1
        self.Wires[wire] = self.wire_id
        
    def AddComment(self, comment):
        self.Comments[comment.GetId()] = comment

    def IsBlock(self, block):
        if block is not None:
            return self.Blocks.get(block.GetId(), False)
        return False
        
    def IsWire(self, wire):
        return self.Wires.get(wire, False)
        
    def IsComment(self, comment):
        if comment is not None:
            return self.Comments.get(comment.GetId(), False)
        return False

    def RemoveBlock(self, block):
        self.Blocks.pop(block.GetId())
        
    def RemoveWire(self, wire):
        self.Wires.pop(wire)
        
    def RemoveComment(self, comment):
        self.Comments.pop(comment.GetId())

    def GetElements(self, sort_blocks=False, sort_wires=False, sort_comments=False):
        blocks = self.Blocks.values()
        wires = self.Wires.keys()
        comments = self.Comments.values()
        if sort_blocks:
            blocks.sort(lambda x, y: cmp(x.GetId(), y.GetId()))
        if sort_wires:
            wires.sort(lambda x, y: cmp(self.Wires[x], self.Wires[y]))
        if sort_comments:
            comments.sort(lambda x, y: cmp(x.GetId(), y.GetId()))
        return blocks + wires + comments

    def GetConnectorByName(self, name):
        for block in self.Blocks.itervalues():
            if isinstance(block, FBD_Connector) and\
               block.GetType() == CONNECTOR and\
               block.GetName() == name:
                return block
        return None
    
    def RefreshVisibleElements(self, xp = None, yp = None):
        x, y = self.Editor.CalcUnscrolledPosition(0, 0)
        if xp is not None:
            x = xp * self.Editor.GetScrollPixelsPerUnit()[0]
        if yp is not None:
            y = yp * self.Editor.GetScrollPixelsPerUnit()[1]
        width, height = self.Editor.GetClientSize()
        screen = wx.Rect(int(x / self.ViewScale[0]), int(y / self.ViewScale[1]),
                         int(width / self.ViewScale[0]), int(height / self.ViewScale[1]))
        for comment in self.Comments.itervalues():
            comment.TestVisible(screen)
        for wire in self.Wires.iterkeys():
            wire.TestVisible(screen)
        for block in self.Blocks.itervalues():
            block.TestVisible(screen)
    
    def GetElementIECPath(self, element):
        iec_path = None
        instance_path = self.GetInstancePath(True)
        if isinstance(element, Wire) and element.EndConnected is not None:
            block = element.EndConnected.GetParentBlock()
            if isinstance(block, FBD_Block):
                blockname = block.GetName()
                connectorname = element.EndConnected.GetName()
                if blockname != "":
                    iec_path = "%s.%s.%s"%(instance_path, blockname, connectorname)
                else:
                    if connectorname == "":
                        iec_path = "%s.%s%d"%(instance_path, block.GetType(), block.GetId())
                    else:
                        iec_path = "%s.%s%d_%s"%(instance_path, block.GetType(), block.GetId(), connectorname)
            elif isinstance(block, FBD_Variable):
                iec_path = "%s.%s"%(instance_path, block.GetName())
            elif isinstance(block, FBD_Connector):
                connection = self.GetConnectorByName(block.GetName())
                if connection is not None:
                    connector = connection.GetConnector()
                    if len(connector.Wires) == 1:
                        iec_path = self.GetElementIECPath(connector.Wires[0][0])
        elif isinstance(element, LD_Contact):
            iec_path = "%s.%s"%(instance_path, element.GetName())
        elif isinstance(element, SFC_Step):
            iec_path = "%s.%s.X"%(instance_path, element.GetName())
        elif isinstance(element, SFC_Transition):
            connectors = element.GetConnectors()
            previous_steps = self.GetPreviousSteps(connectors["inputs"])
            next_steps = self.GetNextSteps(connectors["outputs"])
            iec_path = "%s.%s->%s"%(instance_path, ",".join(previous_steps), ",".join(next_steps))
        return iec_path
       
#-------------------------------------------------------------------------------
#                              Reset functions
#-------------------------------------------------------------------------------

    # Resets Viewer lists
    def ResetView(self):
        self.Blocks = {}
        self.Wires = {}
        self.Comments = {}
        self.Subscribed = {}
        self.SelectedElement = None
        self.HighlightedElement = None
        self.ToolTipElement = None
    
    def Flush(self):
        self.DeleteDataConsumers()
        for block in self.Blocks.itervalues():
            block.Flush()
    
    # Remove all elements
    def CleanView(self):
        for block in self.Blocks.itervalues():
            block.Clean()
        self.ResetView()
    
    # Changes Viewer mode
    def SetMode(self, mode):
        if self.Mode != mode or mode == MODE_SELECTION:    
            if self.Mode == MODE_MOTION:
                wx.CallAfter(self.Editor.SetCursor, wx.NullCursor)
            self.Mode = mode
            self.SavedMode = False
        else:
            self.SavedMode = True
        # Reset selection
        if self.Mode != MODE_SELECTION and self.SelectedElement:
            self.SelectedElement.SetSelected(False)
            self.SelectedElement = None
        if self.Mode == MODE_MOTION:
            wx.CallAfter(self.Editor.SetCursor, wx.StockCursor(wx.CURSOR_HAND))
            self.SavedMode = True
        
    # Return current drawing mode
    def GetDrawingMode(self):
        return self.ParentWindow.GetDrawingMode()
    
    # Buffer the last model state
    def RefreshBuffer(self):
        self.Controler.BufferProject()
        if self.ParentWindow:
            self.ParentWindow.RefreshTitle()
            self.ParentWindow.RefreshFileMenu()
            self.ParentWindow.RefreshEditMenu()
    
    def StartBuffering(self):
        if not self.Buffering:
            self.Buffering = True
            self.Controler.StartBuffering()
            if self.ParentWindow:
                self.ParentWindow.RefreshTitle()
                self.ParentWindow.RefreshFileMenu()
                self.ParentWindow.RefreshEditMenu()
    
    def ResetBuffer(self):
        if self.Buffering:
            self.Controler.EndBuffering()
            self.Buffering = False
    
    def GetBufferState(self):
        if not self.Debug:
            return self.Controler.GetBufferState()
        return False, False
    
    def Undo(self):
        if not self.Debug:
            self.Controler.LoadPrevious()
            self.ParentWindow.CloseTabsWithoutModel()
            
    def Redo(self):
        if not self.Debug:
            self.Controler.LoadNext()
            self.ParentWindow.CloseTabsWithoutModel()
        
    def HasNoModel(self):
        if not self.Debug:
            return self.Controler.GetEditedElement(self.TagName) is None
        return False
    
    # Refresh the current scaling
    def RefreshScaling(self, refresh=True):
        properties = self.Controler.GetProjectProperties(self.Debug)
        scaling = properties["scaling"][self.CurrentLanguage]
        if scaling[0] != 0 and scaling[1] != 0:
            self.Scaling = scaling
            if self.DrawGrid:
                width = max(2, int(scaling[0] * self.ViewScale[0]))
                height = max(2, int(scaling[1] * self.ViewScale[1]))
                bitmap = wx.EmptyBitmap(width, height)
                dc = wx.MemoryDC(bitmap)
                dc.SetBackground(wx.Brush(self.Editor.GetBackgroundColour()))
                dc.Clear()
                dc.SetPen(MiterPen(wx.Colour(180, 180, 180)))
                dc.DrawPoint(0, 0)
                self.GridBrush = wx.BrushFromBitmap(bitmap)
            else:
                self.GridBrush = wx.TRANSPARENT_BRUSH
        else:
            self.Scaling = None
            self.GridBrush = wx.TRANSPARENT_BRUSH
        page_size = properties["pageSize"]
        if page_size != (0, 0):
            self.PageSize = map(int, page_size)
            self.PagePen = MiterPen(wx.Colour(180, 180, 180))
        else:
            self.PageSize = None
            self.PagePen = wx.TRANSPARENT_PEN
        if refresh:
            self.RefreshVisibleElements()
            self.Refresh(False)
        
        
#-------------------------------------------------------------------------------
#                          Refresh functions
#-------------------------------------------------------------------------------
    
    VALUE_TRANSLATION = {True: _("Active"), False: _("Inactive")}

    def SetValue(self, value):
        if self.Value != value:
            self.Value = value
            
            xstart, ystart = self.GetViewStart()
            window_size = self.Editor.GetClientSize()
            refresh_rect = self.GetRedrawRect()
            if (xstart * SCROLLBAR_UNIT <= refresh_rect.x + refresh_rect.width and 
                xstart * SCROLLBAR_UNIT + window_size[0] >= refresh_rect.x and
                ystart * SCROLLBAR_UNIT <= refresh_rect.y + refresh_rect.height and 
                ystart * SCROLLBAR_UNIT + window_size[1] >= refresh_rect.y):
                self.ElementNeedRefresh(self)
    
    def GetRedrawRect(self):
        dc = self.GetLogicalDC()
        ipw, iph = dc.GetTextExtent(_("Debug: %s") % self.InstancePath)
        vw, vh = 0, 0
        for value in self.VALUE_TRANSLATION.itervalues():
            w, h = dc.GetTextExtent("(%s)" % value)
            vw = max(vw, w)
            vh = max(vh, h)
        return wx.Rect(ipw + 4, 2, vw, vh)
    
    def ElementNeedRefresh(self, element):
        self.ElementRefreshList_lock.acquire()
        self.ElementRefreshList.append(element)
        self.ElementRefreshList_lock.release()
        
    def RefreshNewData(self):
        refresh_rect = None
        self.ElementRefreshList_lock.acquire()
        for element in self.ElementRefreshList:
            if refresh_rect is None:
                refresh_rect = element.GetRedrawRect()
            else:
                refresh_rect.Union(element.GetRedrawRect())
        self.ElementRefreshList = []
        self.ElementRefreshList_lock.release()
        
        if refresh_rect is not None:
            self.RefreshRect(self.GetScrolledRect(refresh_rect), False)
        else:
            DebugViewer.RefreshNewData(self)
        
    # Refresh Viewer elements
    def RefreshView(self, variablepanel=True, selection=None):
        EditorPanel.RefreshView(self, variablepanel)
        
        if self.TagName.split("::")[0] == "A":
            self.AddDataConsumer("%s.Q" % self.InstancePath.upper(), self)
        
        if self.ToolTipElement is not None:
            self.ToolTipElement.ClearToolTip()
            self.ToolTipElement = None
        
        self.Inhibit(True)
        self.current_id = 0
        # Start by reseting Viewer
        self.Flush()
        self.ResetView()
        self.ResetBuffer()
        instance = {}
        # List of ids of already loaded blocks
        ids = []
        # Load Blocks until they are all loaded
        while instance is not None:
            instance = self.Controler.GetEditedElementInstanceInfos(self.TagName, exclude = ids, debug = self.Debug)
            if instance is not None:
                self.loadInstance(instance, ids, selection)
        self.RefreshScrollBars()
        
        for wire in self.Wires:
            if not wire.IsConnectedCompatible():
                wire.SetValid(False)
            if self.Debug:
                iec_path = self.GetElementIECPath(wire)
                if iec_path is None:
                    block = wire.EndConnected.GetParentBlock()
                    if isinstance(block, LD_PowerRail):
                        wire.SetValue(True)
                elif self.AddDataConsumer(iec_path.upper(), wire) is None:
                    wire.SetValue("undefined")

        if self.Debug:
            for block in self.Blocks.itervalues():
                block.SpreadCurrent()
                iec_path = self.GetElementIECPath(block)
                if iec_path is not None:
                    self.AddDataConsumer(iec_path.upper(), block)

        self.Inhibit(False)
        self.RefreshVisibleElements()
        self.ShowHighlights()
        self.Refresh(False)
    
    def GetPreviousSteps(self, connectors):
        steps = []
        for connector in connectors:
            for wire, handle in connector.GetWires():
                previous = wire.GetOtherConnected(connector).GetParentBlock()
                if isinstance(previous, SFC_Step):
                    steps.append(previous.GetName())
                elif isinstance(previous, SFC_Divergence) and previous.GetType() in [SIMULTANEOUS_CONVERGENCE, SELECTION_DIVERGENCE]:
                    connectors = previous.GetConnectors()
                    steps.extend(self.GetPreviousSteps(connectors["inputs"]))
        return steps
    
    def GetNextSteps(self, connectors):
        steps = []
        for connector in connectors:
            for wire, handle in connector.GetWires():
                next = wire.GetOtherConnected(connector).GetParentBlock()
                if isinstance(next, SFC_Step):
                    steps.append(next.GetName())
                elif isinstance(next, SFC_Jump):
                    steps.append(next.GetTarget())
                elif isinstance(next, SFC_Divergence) and next.GetType() in [SIMULTANEOUS_DIVERGENCE, SELECTION_CONVERGENCE]:
                    connectors = next.GetConnectors()
                    steps.extend(self.GetNextSteps(connectors["outputs"]))
        return steps
    
    def GetMaxSize(self):
        maxx = maxy = 0
        for element in self.GetElements():
            bbox = element.GetBoundingBox()
            maxx = max(maxx, bbox.x + bbox.width)
            maxy = max(maxy, bbox.y + bbox.height)
        return maxx, maxy
    
    def RefreshScrollBars(self, width_incr=0, height_incr=0):
        xstart, ystart = self.GetViewStart()
        window_size = self.Editor.GetClientSize()
        maxx, maxy = self.GetMaxSize()
        maxx = max(maxx + WINDOW_BORDER, (xstart * SCROLLBAR_UNIT + window_size[0]) / self.ViewScale[0])
        maxy = max(maxy + WINDOW_BORDER, (ystart * SCROLLBAR_UNIT + window_size[1]) / self.ViewScale[1])
        if self.rubberBand.IsShown():
            extent = self.rubberBand.GetCurrentExtent()
            maxx = max(maxx, extent.x + extent.width)
            maxy = max(maxy, extent.y + extent.height)
        maxx = int(maxx * self.ViewScale[0])
        maxy = int(maxy * self.ViewScale[1])
        self.Editor.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
            round(maxx / SCROLLBAR_UNIT) + width_incr, round(maxy / SCROLLBAR_UNIT) + height_incr, 
            xstart, ystart, True)
    
    def EnsureVisible(self, block):
        xstart, ystart = self.GetViewStart()
        window_size = self.Editor.GetClientSize()
        block_bbx = block.GetBoundingBox()
        
        screen_minx, screen_miny = xstart * SCROLLBAR_UNIT, ystart * SCROLLBAR_UNIT
        screen_maxx, screen_maxy = screen_minx + window_size[0], screen_miny + window_size[1]
        block_minx = int(block_bbx.x * self.ViewScale[0]) 
        block_miny = int(block_bbx.y * self.ViewScale[1])
        block_maxx = int(round((block_bbx.x + block_bbx.width) * self.ViewScale[0]))
        block_maxy = int(round((block_bbx.y + block_bbx.height) * self.ViewScale[1]))
        
        xpos, ypos = xstart, ystart
        if block_minx < screen_minx and block_maxx < screen_maxx:
            xpos -= (screen_minx - block_minx) / SCROLLBAR_UNIT + 1
        elif block_maxx > screen_maxx and block_minx > screen_minx:
            xpos += (block_maxx - screen_maxx) / SCROLLBAR_UNIT + 1
        if block_miny < screen_miny and block_maxy < screen_maxy:
            ypos -= (screen_miny - block_miny) / SCROLLBAR_UNIT + 1
        elif block_maxy > screen_maxy and block_miny > screen_miny:
            ypos += (block_maxy - screen_maxy) / SCROLLBAR_UNIT + 1
        self.Scroll(xpos, ypos)
    
    def SelectInGroup(self, element):
        element.SetSelected(True)
        if self.SelectedElement is None:
            self.SelectedElement = element
        elif isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.SelectElement(element)
        else:
            group = Graphic_Group(self)
            group.SelectElement(self.SelectedElement)
            group.SelectElement(element)
            self.SelectedElement = group
        
    # Load instance from given informations
    def loadInstance(self, instance, ids, selection):
        ids.append(instance["id"])
        self.current_id = max(self.current_id, instance["id"])
        creation_function = ElementCreationFunctions.get(instance["type"], None)
        connectors = {"inputs" : [], "outputs" : []}
        specific_values = instance["specific_values"]
        if creation_function is not None:
            element = creation_function(self, instance["id"], specific_values)
            if isinstance(element, SFC_Step):
                if len(instance["inputs"]) > 0:
                    element.AddInput()
                else:
                    element.RemoveInput()
                if len(instance["outputs"]) > 0:
                    element.AddOutput()
            if isinstance(element, SFC_Transition) and specific_values["condition_type"] == "connection":
                connector = element.GetConditionConnector()
                self.CreateWires(connector, instance["id"], specific_values["connection"]["links"], ids, selection)
        else:
            executionControl = False
            for input in instance["inputs"]:
                if input["negated"]:
                    connectors["inputs"].append((input["name"], None, "negated"))
                elif input["edge"]:
                    connectors["inputs"].append((input["name"], None, input["edge"]))
                else:
                    connectors["inputs"].append((input["name"], None, "none"))
            for output in instance["outputs"]:
                if output["negated"]:
                    connectors["outputs"].append((output["name"], None, "negated"))
                elif output["edge"]:
                    connectors["outputs"].append((output["name"], None, output["edge"]))
                else:
                    connectors["outputs"].append((output["name"], None, "none"))
            if len(connectors["inputs"]) > 0 and connectors["inputs"][0][0] == "EN":
                connectors["inputs"].pop(0)
                executionControl = True
            if len(connectors["outputs"]) > 0 and connectors["outputs"][0][0] == "ENO":
                connectors["outputs"].pop(0)
                executionControl = True
            if specific_values["name"] is None:
                specific_values["name"] = ""
            element = FBD_Block(self, instance["type"], specific_values["name"], 
                      instance["id"], len(connectors["inputs"]), 
                      connectors=connectors, executionControl=executionControl, 
                      executionOrder=specific_values["executionOrder"])
        if isinstance(element, Comment):
            self.AddComment(element)
        else:
            self.AddBlock(element)
            connectors = element.GetConnectors()
        element.SetPosition(instance["x"], instance["y"])
        element.SetSize(instance["width"], instance["height"])
        for i, output_connector in enumerate(instance["outputs"]):
            if i < len(connectors["outputs"]):
                connector = connectors["outputs"][i]
                if output_connector.get("negated", False):
                    connector.SetNegated(True)
                if output_connector.get("edge", "none") != "none":
                    connector.SetEdge(output_connector["edge"])
                connector.SetPosition(wx.Point(*output_connector["position"]))
        for i, input_connector in enumerate(instance["inputs"]):
            if i < len(connectors["inputs"]):
                connector = connectors["inputs"][i]
                connector.SetPosition(wx.Point(*input_connector["position"]))
                if input_connector.get("negated", False):
                    connector.SetNegated(True)
                if input_connector.get("edge", "none") != "none":
                    connector.SetEdge(input_connector["edge"])
                self.CreateWires(connector, instance["id"], input_connector["links"], ids, selection)
        if selection is not None and selection[0].get(instance["id"], False):
            self.SelectInGroup(element)

    def CreateWires(self, start_connector, id, links, ids, selection=None):
        for link in links:
            refLocalId = link["refLocalId"]
            if refLocalId is not None:
                if refLocalId not in ids:
                    new_instance = self.Controler.GetEditedElementInstanceInfos(self.TagName, refLocalId, debug = self.Debug)
                    if new_instance is not None:
                        self.loadInstance(new_instance, ids, selection)
                connected = self.FindElementById(refLocalId)
                if connected is not None:
                    points = link["points"]
                    end_connector = connected.GetConnector(wx.Point(points[-1][0], points[-1][1]), link["formalParameter"])
                    if end_connector is not None:
                        wire = Wire(self)
                        wire.SetPoints(points)
                        start_connector.Connect((wire, 0), False)
                        end_connector.Connect((wire, -1), False)
                        wire.ConnectStartPoint(None, start_connector)
                        wire.ConnectEndPoint(None, end_connector)
                        self.AddWire(wire)
                        if selection is not None and (\
                           selection[1].get((id, refLocalId), False) or \
                           selection[1].get((refLocalId, id), False)):
                            self.SelectInGroup(wire)

    def IsOfType(self, type, reference):
        return self.Controler.IsOfType(type, reference, self.Debug)
    
    def IsEndType(self, type):
        return self.Controler.IsEndType(type)

    def GetBlockType(self, type, inputs = None):
        return self.Controler.GetBlockType(type, inputs, self.Debug)

#-------------------------------------------------------------------------------
#                          Search Element functions
#-------------------------------------------------------------------------------

    def FindBlock(self, event):
        dc = self.GetLogicalDC()
        pos = event.GetLogicalPosition(dc)
        for block in self.Blocks.itervalues():
            if block.HitTest(pos) or block.TestHandle(event) != (0, 0):
                return block
        return None
    
    def FindWire(self, event):
        dc = self.GetLogicalDC()
        pos = event.GetLogicalPosition(dc)
        for wire in self.Wires:
            if wire.HitTest(pos) or wire.TestHandle(event) != (0, 0):
                return wire
        return None
    
    def FindElement(self, event, exclude_group = False, connectors = True):
        dc = self.GetLogicalDC()
        pos = event.GetLogicalPosition(dc)
        if self.SelectedElement and not (exclude_group and isinstance(self.SelectedElement, Graphic_Group)):
            if self.SelectedElement.HitTest(pos, connectors) or self.SelectedElement.TestHandle(event) != (0, 0):
                return self.SelectedElement
        for element in self.GetElements():
            if element.HitTest(pos, connectors) or element.TestHandle(event) != (0, 0):
                return element
        return None
    
    def FindBlockConnector(self, pos, direction = None, exclude = None):
        for block in self.Blocks.itervalues():
            result = block.TestConnector(pos, direction, exclude)
            if result:
                return result
        return None
    
    def FindElementById(self, id):
        block = self.Blocks.get(id, None)
        if block is not None:
            return block
        comment = self.Comments.get(id, None)
        if comment is not None:
            return comment
        return None
    
    def SearchElements(self, bbox):
        elements = []
        for element in self.GetElements():
            if element.IsInSelection(bbox):
                elements.append(element)
        return elements

    def SelectAll(self):
        if self.SelectedElement is not None:
            self.SelectedElement.SetSelected(False)
        self.SelectedElement = Graphic_Group(self)
        for element in self.GetElements():
            self.SelectedElement.SelectElement(element)
        self.SelectedElement.SetSelected(True)
    
#-------------------------------------------------------------------------------
#                           Popup menu functions
#-------------------------------------------------------------------------------

    def GetForceVariableMenuFunction(self, iec_path, element):
        iec_type = self.GetDataType(iec_path)
        def ForceVariableFunction(event):
            if iec_type is not None:
                dialog = ForceVariableDialog(self.ParentWindow, iec_type, str(element.GetValue()))
                if dialog.ShowModal() == wx.ID_OK:
                    self.ParentWindow.AddDebugVariable(iec_path)
                    self.ForceDataValue(iec_path, dialog.GetValue())
        return ForceVariableFunction

    def GetReleaseVariableMenuFunction(self, iec_path):
        def ReleaseVariableFunction(event):
            self.ReleaseDataValue(iec_path)
        return ReleaseVariableFunction

    def GetChangeVariableTypeMenuFunction(self, type):
        def ChangeVariableTypeMenu(event):
            self.ChangeVariableType(self.SelectedElement, type)
        return ChangeVariableTypeMenu

    def GetChangeConnectionTypeMenuFunction(self, type):
        def ChangeConnectionTypeMenu(event):
            self.ChangeConnectionType(self.SelectedElement, type)
        return ChangeConnectionTypeMenu

    def PopupForceMenu(self):
        iec_path = self.GetElementIECPath(self.SelectedElement)
        if iec_path is not None:
            menu = wx.Menu(title='')
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Force value"))
            self.Bind(wx.EVT_MENU, self.GetForceVariableMenuFunction(iec_path.upper(), self.SelectedElement), id=new_id)
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Release value"))
            self.Bind(wx.EVT_MENU, self.GetReleaseVariableMenuFunction(iec_path.upper()), id=new_id)
            if self.SelectedElement.IsForced():
                menu.Enable(new_id, True)
            else:
                menu.Enable(new_id, False)
            self.Editor.PopupMenu(menu)
            menu.Destroy()

    def PopupBlockMenu(self, connector = None):
        menu = wx.Menu(title='')
        if connector is not None and connector.IsCompatible("BOOL"):
            self.AddBlockPinMenuItems(menu, connector)
        else:
            edit = self.SelectedElement.GetType() in self.Controler.GetProjectPouNames(self.Debug)
            self.AddDefaultMenuItems(menu, block=True, edit=edit)
        self.Editor.PopupMenu(menu)
        menu.Destroy()
    
    def PopupVariableMenu(self):
        menu = wx.Menu(title='')
        variable_type = self.SelectedElement.GetType()
        for type_label, type in [(_("Input"), INPUT),
                                 (_("Output"), OUTPUT),
                                 (_("InOut"), INOUT)]:
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_RADIO, text=type_label)
            self.Bind(wx.EVT_MENU, self.GetChangeVariableTypeMenuFunction(type), id=new_id)
            if type == variable_type:
                menu.Check(new_id, True)
        menu.AppendSeparator()
        self.AddDefaultMenuItems(menu, block=True)
        self.Editor.PopupMenu(menu)
        menu.Destroy()
    
    def PopupConnectionMenu(self):
        menu = wx.Menu(title='')
        connection_type = self.SelectedElement.GetType()
        for type_label, type in [(_("Connector"), CONNECTOR),
                                 (_("Continuation"), CONTINUATION)]:
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_RADIO, text=type_label)
            self.Bind(wx.EVT_MENU, self.GetChangeConnectionTypeMenuFunction(type), id=new_id)
            if type == connection_type:
                menu.Check(new_id, True)
        menu.AppendSeparator()
        self.AddDefaultMenuItems(menu, block=True)
        self.Editor.PopupMenu(menu)
        menu.Destroy()
    
    def PopupWireMenu(self, delete=True):
        menu = wx.Menu(title='')
        self.AddWireMenuItems(menu, delete)
        menu.AppendSeparator()
        self.AddDefaultMenuItems(menu, block=True)
        self.Editor.PopupMenu(menu)
        menu.Destroy()
        
    def PopupDivergenceMenu(self, connector):
        menu = wx.Menu(title='')
        self.AddDivergenceMenuItems(menu, connector)
        menu.AppendSeparator()
        self.AddDefaultMenuItems(menu, block=True)
        self.Editor.PopupMenu(menu)
        menu.Destroy()
    
    def PopupGroupMenu(self):
        menu = wx.Menu(title='')
        align_menu = wx.Menu(title='')
        self.AddAlignmentMenuItems(align_menu)
        menu.AppendMenu(-1, _(u'Alignment'), align_menu)
        menu.AppendSeparator()
        self.AddDefaultMenuItems(menu, block=True)
        self.Editor.PopupMenu(menu)
        menu.Destroy()
        
    def PopupDefaultMenu(self, block=True):
        menu = wx.Menu(title='')
        self.AddDefaultMenuItems(menu, block=block)
        self.Editor.PopupMenu(menu)
        menu.Destroy()

#-------------------------------------------------------------------------------
#                            Menu items functions
#-------------------------------------------------------------------------------

    def OnAlignLeftMenu(self, event):
        if self.SelectedElement is not None and isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.AlignElements(ALIGN_LEFT, None)
            self.RefreshBuffer()
            self.Refresh(False)
    
    def OnAlignCenterMenu(self, event):
        if self.SelectedElement is not None and isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.AlignElements(ALIGN_CENTER, None)
            self.RefreshBuffer()
            self.Refresh(False)
    
    def OnAlignRightMenu(self, event):
        if self.SelectedElement is not None and isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.AlignElements(ALIGN_RIGHT, None)
            self.RefreshBuffer()
            self.Refresh(False)
    
    def OnAlignTopMenu(self, event):
        if self.SelectedElement is not None and isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.AlignElements(None, ALIGN_TOP)
            self.RefreshBuffer()
            self.Refresh(False)
    
    def OnAlignMiddleMenu(self, event):
        if self.SelectedElement is not None and isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.AlignElements(None, ALIGN_MIDDLE)
            self.RefreshBuffer()
            self.Refresh(False)
    
    def OnAlignBottomMenu(self, event):
        if self.SelectedElement is not None and isinstance(self.SelectedElement, Graphic_Group):
            self.SelectedElement.AlignElements(None, ALIGN_BOTTOM)
            self.RefreshBuffer()
            self.Refresh(False)
        
    def OnNoModifierMenu(self, event):
        if self.SelectedElement is not None and self.IsBlock(self.SelectedElement):
            self.SelectedElement.SetConnectorNegated(False)
            self.SelectedElement.Refresh()
            self.RefreshBuffer()
    
    def OnNegatedMenu(self, event):
        if self.SelectedElement is not None and self.IsBlock(self.SelectedElement):
            self.SelectedElement.SetConnectorNegated(True)
            self.SelectedElement.Refresh()
            self.RefreshBuffer()

    def OnRisingEdgeMenu(self, event):
        if self.SelectedElement is not None and self.IsBlock(self.SelectedElement):
            self.SelectedElement.SetConnectorEdge("rising")
            self.SelectedElement.Refresh()
            self.RefreshBuffer()

    def OnFallingEdgeMenu(self, event):
        if self.SelectedElement is not None and self.IsBlock(self.SelectedElement):
            self.SelectedElement.SetConnectorEdge("falling")
            self.SelectedElement.Refresh()
            self.RefreshBuffer()

    def OnAddSegmentMenu(self, event):
        if self.SelectedElement is not None and self.IsWire(self.SelectedElement):
            self.SelectedElement.AddSegment()
            self.SelectedElement.Refresh()

    def OnDeleteSegmentMenu(self, event):
        if self.SelectedElement is not None and self.IsWire(self.SelectedElement):
            self.SelectedElement.DeleteSegment()
            self.SelectedElement.Refresh()

    def OnAddBranchMenu(self, event):
        if self.SelectedElement is not None and self.IsBlock(self.SelectedElement):
            self.AddDivergenceBranch(self.SelectedElement)

    def OnDeleteBranchMenu(self, event):
        if self.SelectedElement is not None and self.IsBlock(self.SelectedElement):
            self.RemoveDivergenceBranch(self.SelectedElement)

    def OnEditBlockMenu(self, event):
        if self.SelectedElement is not None:
            self.ParentWindow.EditProjectElement(ITEM_POU, "P::%s"%self.SelectedElement.GetType())

    def OnAdjustBlockSizeMenu(self, event):
        if self.SelectedElement is not None:
            movex, movey = self.SelectedElement.SetBestSize(self.Scaling)
            self.SelectedElement.RefreshModel(True)
            self.RefreshBuffer()
            self.RefreshRect(self.GetScrolledRect(self.SelectedElement.GetRedrawRect(movex, movey)), False)

    def OnDeleteMenu(self, event):
        if self.SelectedElement is not None:
            self.SelectedElement.Delete()
            self.SelectedElement = None
            self.RefreshBuffer()
            self.Refresh(False)

    def OnClearExecutionOrderMenu(self, event):
        self.Controler.ClearEditedElementExecutionOrder(self.TagName)
        self.RefreshBuffer()
        self.RefreshView()
        
    def OnResetExecutionOrderMenu(self, event):
        self.Controler.ResetEditedElementExecutionOrder(self.TagName)
        self.RefreshBuffer()
        self.RefreshView()

    def GetAddMenuCallBack(self, func, *args):
        def AddMenuCallBack(event):
            wx.CallAfter(func, self.rubberBand.GetCurrentExtent(), *args)
        return AddMenuCallBack

    def GetClipboardCallBack(self, func):
        def ClipboardCallback(event):
            wx.CallAfter(func)
        return ClipboardCallback

#-------------------------------------------------------------------------------
#                          Mouse event functions
#-------------------------------------------------------------------------------

    def OnViewerMouseEvent(self, event):
        if not event.Entering():
            self.ResetBuffer()
            element = None
            if not event.Leaving() and not event.LeftUp() and not event.LeftDClick():
                element = self.FindElement(event, True, False)
            if self.ToolTipElement is not None:
                self.ToolTipElement.ClearToolTip()
            self.ToolTipElement = element
            if self.ToolTipElement is not None:
                tooltip_pos = self.Editor.ClientToScreen(event.GetPosition())
                tooltip_pos.x += 10
                tooltip_pos.y += 10
                self.ToolTipElement.CreateToolTip(tooltip_pos)
        event.Skip()
    
    def OnViewerLeftDown(self, event):
        self.Editor.CaptureMouse()
        if self.Mode == MODE_SELECTION:
            dc = self.GetLogicalDC()
            pos = event.GetLogicalPosition(dc)
            if event.ShiftDown() and not event.ControlDown() and self.SelectedElement is not None:
                element = self.FindElement(event, True)
                if element is not None:
                    if isinstance(self.SelectedElement, Graphic_Group):
                        self.SelectedElement.SetSelected(False)
                        self.SelectedElement.SelectElement(element)
                    elif self.SelectedElement is not None:
                        group = Graphic_Group(self)
                        group.SelectElement(self.SelectedElement)
                        group.SelectElement(element)
                        self.SelectedElement = group
                    elements = self.SelectedElement.GetElements()
                    if len(elements) == 0:
                        self.SelectedElement = element
                    elif len(elements) == 1:
                        self.SelectedElement = elements[0]
                    self.SelectedElement.SetSelected(True)
                else:
                    self.rubberBand.Reset()
                    self.rubberBand.OnLeftDown(event, dc, self.Scaling)
            else:
                element = self.FindElement(event)
                if not self.Debug and (element is None or element.TestHandle(event) == (0, 0)):
                    connector = self.FindBlockConnector(pos)
                else:
                    connector = None
                if not self.Debug and self.DrawingWire:
                    self.DrawingWire = False
                    if self.SelectedElement is not None:
                        if element is None or element.TestHandle(event) == (0, 0):
                            connector = self.FindBlockConnector(pos, self.SelectedElement.GetConnectionDirection())
                        if connector is not None:
                            event.Dragging = lambda : True
                            self.SelectedElement.OnMotion(event, dc, self.Scaling)
                        if self.SelectedElement.EndConnected is not None:
                            self.SelectedElement.ResetPoints()
                            self.SelectedElement.GeneratePoints()
                            self.SelectedElement.RefreshModel()
                            self.SelectedElement.SetSelected(True)
                            element = self.SelectedElement
                            self.RefreshBuffer()
                        else:
                            rect = self.SelectedElement.GetRedrawRect()
                            self.SelectedElement.Delete()
                            self.SelectedElement = None
                            element = None
                            self.RefreshRect(self.GetScrolledRect(rect), False)
                elif not self.Debug and connector is not None and not event.ControlDown():
                    self.DrawingWire = True
                    scaled_pos = GetScaledEventPosition(event, dc, self.Scaling)
                    if (connector.GetDirection() == EAST):
                        wire = Wire(self, [wx.Point(pos.x, pos.y), EAST], [wx.Point(scaled_pos.x, scaled_pos.y), WEST])
                    else:
                        wire = Wire(self, [wx.Point(pos.x, pos.y), WEST], [wx.Point(scaled_pos.x, scaled_pos.y), EAST])
                    wire.oldPos = scaled_pos
                    wire.Handle = (HANDLE_POINT, 0)
                    wire.ProcessDragging(0, 0, event, None)
                    wire.Handle = (HANDLE_POINT, 1)
                    self.AddWire(wire)
                    if self.SelectedElement is not None:
                        self.SelectedElement.SetSelected(False)
                    self.SelectedElement = wire
                    if self.HighlightedElement is not None:
                        self.HighlightedElement.SetHighlighted(False)
                    self.HighlightedElement = wire
                    self.RefreshVisibleElements()
                    self.SelectedElement.SetHighlighted(True)
                else:
                    if self.SelectedElement is not None and self.SelectedElement != element:
                        self.SelectedElement.SetSelected(False)
                        self.SelectedElement = None
                    if element is not None:
                        self.SelectedElement = element
                        if self.Debug:
                            self.StartMousePos = event.GetPosition()
                            Graphic_Element.OnLeftDown(self.SelectedElement, event, dc, self.Scaling)
                        else:
                            self.SelectedElement.OnLeftDown(event, dc, self.Scaling)
                        self.SelectedElement.Refresh()
                    else:
                        self.rubberBand.Reset()
                        self.rubberBand.OnLeftDown(event, dc, self.Scaling)
        elif self.Mode in [MODE_BLOCK, MODE_VARIABLE, MODE_CONNECTION, MODE_COMMENT, 
                           MODE_CONTACT, MODE_COIL, MODE_POWERRAIL, MODE_INITIALSTEP, 
                           MODE_STEP, MODE_TRANSITION, MODE_DIVERGENCE, MODE_JUMP, MODE_ACTION]:
            self.rubberBand.Reset()
            self.rubberBand.OnLeftDown(event, self.GetLogicalDC(), self.Scaling)
        elif self.Mode == MODE_MOTION:
            self.StartMousePos = event.GetPosition()
            self.StartScreenPos = self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL)
        event.Skip()

    def OnViewerLeftUp(self, event):
        self.StartMousePos = None
        if self.rubberBand.IsShown():
            if self.Mode == MODE_SELECTION:
                new_elements = self.SearchElements(self.rubberBand.GetCurrentExtent())
                self.rubberBand.OnLeftUp(event, self.GetLogicalDC(), self.Scaling)
                if event.ShiftDown() and self.SelectedElement is not None:
                    if isinstance(self.SelectedElement, Graphic_Group):
                        elements = self.SelectedElement.GetElements()
                    else:
                        elements = [self.SelectedElement]
                    for element in elements:
                        if element not in new_elements:
                            new_elements.append(element)
                if len(new_elements) == 1:
                    self.SelectedElement = new_elements[0]
                    self.SelectedElement.SetSelected(True)
                elif len(new_elements) > 1:
                    self.SelectedElement = Graphic_Group(self)
                    self.SelectedElement.SetElements(new_elements)
                    self.SelectedElement.SetSelected(True)
            else:
                bbox = self.rubberBand.GetCurrentExtent()
                self.rubberBand.OnLeftUp(event, self.GetLogicalDC(), self.Scaling)                
                if self.Mode == MODE_BLOCK:
                    wx.CallAfter(self.AddNewBlock, bbox)
                elif self.Mode == MODE_VARIABLE:
                    wx.CallAfter(self.AddNewVariable, bbox)
                elif self.Mode == MODE_CONNECTION:
                    wx.CallAfter(self.AddNewConnection, bbox)
                elif self.Mode == MODE_COMMENT:
                    wx.CallAfter(self.AddNewComment, bbox)
                elif self.Mode == MODE_CONTACT:
                    wx.CallAfter(self.AddNewContact, bbox)
                elif self.Mode == MODE_COIL:
                    wx.CallAfter(self.AddNewCoil, bbox)
                elif self.Mode == MODE_POWERRAIL:
                    wx.CallAfter(self.AddNewPowerRail, bbox)
                elif self.Mode == MODE_INITIALSTEP:
                    wx.CallAfter(self.AddNewStep, bbox, True)
                elif self.Mode == MODE_STEP:
                    wx.CallAfter(self.AddNewStep, bbox, False)
                elif self.Mode == MODE_TRANSITION:
                    wx.CallAfter(self.AddNewTransition, bbox)
                elif self.Mode == MODE_DIVERGENCE:
                    wx.CallAfter(self.AddNewDivergence, bbox)
                elif self.Mode == MODE_JUMP:
                    wx.CallAfter(self.AddNewJump, bbox)
                elif self.Mode == MODE_ACTION:
                    wx.CallAfter(self.AddNewActionBlock, bbox)
        elif self.Mode == MODE_SELECTION and self.SelectedElement is not None:
            dc = self.GetLogicalDC()
            if not self.Debug and self.DrawingWire:
                pos = event.GetLogicalPosition(dc)
                connector = self.FindBlockConnector(pos, self.SelectedElement.GetConnectionDirection())
                if self.SelectedElement.EndConnected is not None:
                    self.DrawingWire = False
                    self.SelectedElement.StartConnected.HighlightParentBlock(False)
                    self.SelectedElement.EndConnected.HighlightParentBlock(False)
                    self.SelectedElement.ResetPoints()
                    self.SelectedElement.OnMotion(event, dc, self.Scaling)
                    self.SelectedElement.GeneratePoints()
                    self.SelectedElement.RefreshModel()
                    self.SelectedElement.SetSelected(True)
                    self.SelectedElement.HighlightPoint(pos)
                    self.RefreshBuffer()
                elif connector is None or self.SelectedElement.GetDragging():
                    self.DrawingWire = False
                    rect = self.SelectedElement.GetRedrawRect()
                    wire = self.SelectedElement
                    self.SelectedElement = self.SelectedElement.StartConnected.GetParentBlock()
                    self.SelectedElement.SetSelected(True)
                    rect.Union(self.SelectedElement.GetRedrawRect())
                    wire.Delete()
                    self.RefreshRect(self.GetScrolledRect(rect), False)
            else:
                if self.Debug:
                    Graphic_Element.OnLeftUp(self.SelectedElement, event, dc, self.Scaling)
                else:
                    self.SelectedElement.OnLeftUp(event, dc, self.Scaling)
                wx.CallAfter(self.SetCurrentCursor, 0)
        elif self.Mode == MODE_MOTION:
            self.StartMousePos = None
            self.StartScreenPos = None
        if self.Mode != MODE_SELECTION and not self.SavedMode:
            wx.CallAfter(self.ParentWindow.ResetCurrentMode)
        if self.Editor.HasCapture():
            self.Editor.ReleaseMouse()
        event.Skip()
    
    def OnViewerMiddleDown(self, event):
        self.Editor.CaptureMouse()
        self.StartMousePos = event.GetPosition()
        self.StartScreenPos = self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL)
        event.Skip()
        
    def OnViewerMiddleUp(self, event):
        self.StartMousePos = None
        self.StartScreenPos = None
        if self.Editor.HasCapture():
            self.Editor.ReleaseMouse()
        event.Skip()
    
    def OnViewerRightDown(self, event):
        self.Editor.CaptureMouse()
        if self.Mode == MODE_SELECTION:
            element = self.FindElement(event)
            if self.SelectedElement is not None and self.SelectedElement != element:
                self.SelectedElement.SetSelected(False)
                self.SelectedElement = None
            if element is not None:
                self.SelectedElement = element
                if self.Debug:
                    Graphic_Element.OnRightDown(self.SelectedElement, event, self.GetLogicalDC(), self.Scaling)
                else:
                    self.SelectedElement.OnRightDown(event, self.GetLogicalDC(), self.Scaling)
                self.SelectedElement.Refresh()
        event.Skip()
    
    def OnViewerRightUp(self, event):
        dc = self.GetLogicalDC()
        self.rubberBand.Reset()
        self.rubberBand.OnLeftDown(event, dc, self.Scaling)
        self.rubberBand.OnLeftUp(event, dc, self.Scaling)
        if self.SelectedElement is not None:
            if self.Debug:
                Graphic_Element.OnRightUp(self.SelectedElement, event, self.GetLogicalDC(), self.Scaling)
            else:
                self.SelectedElement.OnRightUp(event, self.GetLogicalDC(), self.Scaling)
            wx.CallAfter(self.SetCurrentCursor, 0)
        elif not self.Debug:
            self.PopupDefaultMenu(False)
        if self.Editor.HasCapture():
            self.Editor.ReleaseMouse()
        event.Skip()
    
    def OnViewerLeftDClick(self, event):
        element = self.FindElement(event, connectors=False)
        if self.Mode == MODE_SELECTION and element is not None:
            if self.SelectedElement is not None and self.SelectedElement != element:
                self.SelectedElement.SetSelected(False)
            if self.HighlightedElement is not None and self.HighlightedElement != element:
                self.HighlightedElement.SetHighlighted(False)
                    
            self.SelectedElement = element
            self.HighlightedElement = element
            self.SelectedElement.SetHighlighted(True)
            
            if self.Debug:
                if isinstance(self.SelectedElement, FBD_Block):
                    instance_type = self.SelectedElement.GetType()
                    pou_type = {
                        "program": ITEM_PROGRAM,
                        "functionBlock": ITEM_FUNCTIONBLOCK,
                    }.get(self.Controler.GetPouType(instance_type))
                    if pou_type is not None and instance_type in self.Controler.GetProjectPouNames(self.Debug):
                        self.ParentWindow.OpenDebugViewer(pou_type, 
                            "%s.%s"%(self.GetInstancePath(True), self.SelectedElement.GetName()),
                            self.Controler.ComputePouName(instance_type))
                else:
                    iec_path = self.GetElementIECPath(self.SelectedElement)
                    if iec_path is not None:
                        if isinstance(self.SelectedElement, Wire):
                            if self.SelectedElement.EndConnected is not None:
                                self.ParentWindow.OpenDebugViewer(ITEM_VAR_LOCAL, iec_path, 
                                        self.SelectedElement.EndConnected.GetType())
                        else:
                            self.ParentWindow.OpenDebugViewer(ITEM_VAR_LOCAL, iec_path, "BOOL")
            elif event.ControlDown() and not event.ShiftDown():
                if not isinstance(self.SelectedElement, Graphic_Group):
                    if isinstance(self.SelectedElement, FBD_Block):
                        instance_type = self.SelectedElement.GetType()
                    else:
                        instance_type = None
                    if instance_type in self.Controler.GetProjectPouNames(self.Debug):
                        self.ParentWindow.EditProjectElement(ITEM_POU, 
                                self.Controler.ComputePouName(instance_type))
                    else:
                        self.SelectedElement.OnLeftDClick(event, self.GetLogicalDC(), self.Scaling)
            elif event.ControlDown() and event.ShiftDown():
                movex, movey = self.SelectedElement.SetBestSize(self.Scaling)
                self.SelectedElement.RefreshModel()
                self.RefreshBuffer()
                self.RefreshRect(self.GetScrolledRect(self.SelectedElement.GetRedrawRect(movex, movey)), False)
            else:
                self.SelectedElement.OnLeftDClick(event, self.GetLogicalDC(), self.Scaling)
        event.Skip()
    
    def OnViewerMotion(self, event):
        if self.Editor.HasCapture() and not event.Dragging():
            return
        refresh = False
        dc = self.GetLogicalDC()
        pos = GetScaledEventPosition(event, dc, self.Scaling)
        if event.MiddleIsDown() or self.Mode == MODE_MOTION:
            if self.StartMousePos is not None and self.StartScreenPos is not None:
                new_pos = event.GetPosition()
                xmax = self.GetScrollRange(wx.HORIZONTAL) - self.GetScrollThumb(wx.HORIZONTAL)
                ymax = self.GetScrollRange(wx.VERTICAL) - self.GetScrollThumb(wx.VERTICAL)
                scrollx = max(0, self.StartScreenPos[0] - (new_pos[0] - self.StartMousePos[0]) / SCROLLBAR_UNIT)
                scrolly = max(0, self.StartScreenPos[1] - (new_pos[1] - self.StartMousePos[1]) / SCROLLBAR_UNIT)
                if scrollx > xmax or scrolly > ymax:
                    self.RefreshScrollBars(max(0, scrollx - xmax), max(0, scrolly - ymax))
                    self.Scroll(scrollx, scrolly)
                else:
                    self.Scroll(scrollx, scrolly)
                    self.RefreshScrollBars()
                self.RefreshVisibleElements()
        else:
            if not event.Dragging():
                highlighted = self.FindElement(event, connectors=False) 
                if self.HighlightedElement is not None and self.HighlightedElement != highlighted:
                    self.HighlightedElement.SetHighlighted(False)
                    self.HighlightedElement = None
                if highlighted is not None:
                    if isinstance(highlighted, (Wire, Graphic_Group)):
                        highlighted.HighlightPoint(pos)
                    if self.HighlightedElement != highlighted:
                        highlighted.SetHighlighted(True)
                self.HighlightedElement = highlighted
            if self.rubberBand.IsShown():
                self.rubberBand.OnMotion(event, dc, self.Scaling)
            elif not self.Debug and self.Mode == MODE_SELECTION and self.SelectedElement is not None:
                if self.DrawingWire:
                    connector = self.FindBlockConnector(pos, self.SelectedElement.GetConnectionDirection(), self.SelectedElement.EndConnected)
                    if not connector or self.SelectedElement.EndConnected == None:
                        self.SelectedElement.ResetPoints()
                        movex, movey = self.SelectedElement.OnMotion(event, dc, self.Scaling)
                        self.SelectedElement.GeneratePoints()
                        if movex != 0 or movey != 0:
                            self.RefreshRect(self.GetScrolledRect(self.SelectedElement.GetRedrawRect(movex, movey)), False)
                    else:
                        self.SelectedElement.HighlightPoint(pos)
                else:
                    movex, movey = self.SelectedElement.OnMotion(event, dc, self.Scaling)
                    if movex != 0 or movey != 0:
                        self.RefreshRect(self.GetScrolledRect(self.SelectedElement.GetRedrawRect(movex, movey)), False)
            elif self.Debug and self.StartMousePos is not None and event.Dragging():
                pos = event.GetPosition()
                if abs(self.StartMousePos.x - pos.x) > 5 or abs(self.StartMousePos.y - pos.y) > 5:
                    iec_path = self.GetElementIECPath(self.SelectedElement)
                    if iec_path is not None:
                        self.StartMousePos = None
                        if self.HighlightedElement is not None:
                            self.HighlightedElement.SetHighlighted(False)
                            self.HighlightedElement = None
                        data = wx.TextDataObject(str((iec_path, "debug")))
                        dragSource = wx.DropSource(self.Editor)
                        dragSource.SetData(data)
                        dragSource.DoDragDrop()
                        if self.Editor.HasCapture():
                            self.Editor.ReleaseMouse()
                        wx.CallAfter(self.SetCurrentCursor, 0)
            self.UpdateScrollPos(event)
        event.Skip()

    def OnLeaveViewer(self, event):
        if self.StartScreenPos is None:
            self.StartMousePos = None
        if self.SelectedElement is not None and self.SelectedElement.GetDragging():
            event.Skip()
        elif self.HighlightedElement is not None:
            self.HighlightedElement.SetHighlighted(False)
            self.HighlightedElement = None
        event.Skip()

    def UpdateScrollPos(self, event):
        if (event.Dragging() and self.SelectedElement is not None) or self.rubberBand.IsShown():
            position = event.GetPosition()
            move_window = wx.Point()
            window_size = self.Editor.GetClientSize()
            xstart, ystart = self.GetViewStart()
            if position.x < SCROLL_ZONE and xstart > 0:
                move_window.x = -1
            elif position.x > window_size[0] - SCROLL_ZONE:
                move_window.x = 1
            if position.y < SCROLL_ZONE and ystart > 0:
                move_window.y = -1
            elif position.y > window_size[1] - SCROLL_ZONE:
                move_window.y = 1
            if move_window.x != 0 or move_window.y != 0:
                self.RefreshVisibleElements(xp = xstart + move_window.x, yp = ystart + move_window.y)
                self.Scroll(xstart + move_window.x, ystart + move_window.y)
                self.RefreshScrollBars(move_window.x, move_window.y)

#-------------------------------------------------------------------------------
#                          Keyboard event functions
#-------------------------------------------------------------------------------

    ARROW_KEY_MOVE = {
        wx.WXK_LEFT: (-1, 0),
        wx.WXK_RIGHT: (1, 0),
        wx.WXK_UP: (0, -1),
        wx.WXK_DOWN: (0, 1),
    }

    def OnChar(self, event):
        xpos, ypos = self.GetScrollPos(wx.HORIZONTAL), self.GetScrollPos(wx.VERTICAL)
        xmax = self.GetScrollRange(wx.HORIZONTAL) - self.GetScrollThumb(wx.HORIZONTAL)
        ymax = self.GetScrollRange(wx.VERTICAL) - self.GetScrollThumb(wx.VERTICAL)
        keycode = event.GetKeyCode()
        if self.Scaling is not None:
            scaling = self.Scaling
        else:
            scaling = (8, 8)
        if not self.Debug and keycode == wx.WXK_DELETE and self.SelectedElement is not None:
            rect = self.SelectedElement.GetRedrawRect(1, 1)
            self.SelectedElement.Delete()
            self.SelectedElement = None
            self.RefreshBuffer()
            self.RefreshScrollBars()
            wx.CallAfter(self.SetCurrentCursor, 0)
            self.RefreshRect(self.GetScrolledRect(rect), False)
        elif not self.Debug and keycode == wx.WXK_RETURN and self.SelectedElement is not None:
            self.SelectedElement.OnLeftDClick(event, self.GetLogicalDC(), self.Scaling)
        elif self.ARROW_KEY_MOVE.has_key(keycode):
            move = self.ARROW_KEY_MOVE[keycode]
            if event.ControlDown() and event.ShiftDown():
                self.Scroll({-1: 0, 0: xpos, 1: xmax}[move[0]],
                            {-1: 0, 0: ypos, 1: ymax}[move[1]])
                self.RefreshVisibleElements()
            elif event.ControlDown():
                self.Scroll(xpos + move[0], ypos + move[1])
                self.RefreshScrollBars()
                self.RefreshVisibleElements()
            elif not self.Debug and self.SelectedElement is not None:
                movex, movey = move
                if not event.AltDown() or event.ShiftDown():
                    movex *= scaling[0]
                    movey *= scaling[1] 
                    if event.ShiftDown() and not event.AltDown():
                        movex *= 10
                        movey *= 10
                self.SelectedElement.Move(movex, movey)
                self.StartBuffering()
                self.SelectedElement.RefreshModel()
                self.RefreshScrollBars()
                self.RefreshVisibleElements()
                self.RefreshRect(self.GetScrolledRect(self.SelectedElement.GetRedrawRect(movex, movey)), False)
        elif not self.Debug and keycode == wx.WXK_SPACE and self.SelectedElement is not None and self.SelectedElement.Dragging:
            if self.IsBlock(self.SelectedElement) or self.IsComment(self.SelectedElement):
                block = self.CopyBlock(self.SelectedElement, wx.Point(*self.SelectedElement.GetPosition()))
                event = wx.MouseEvent()
                event.m_x, event.m_y = self.Editor.ScreenToClient(wx.GetMousePosition())
                dc = self.GetLogicalDC()
                self.SelectedElement.OnLeftUp(event, dc, self.Scaling)
                self.SelectedElement.SetSelected(False)
                block.OnLeftDown(event, dc, self.Scaling)
                self.SelectedElement = block
                self.SelectedElement.SetSelected(True)
                self.RefreshVariablePanel()
                self.RefreshVisibleElements()
            else:
                event.Skip()
        elif keycode == ord("+"):
            self.SetScale(self.CurrentScale + 1)
            self.ParentWindow.RefreshDisplayMenu()
        elif keycode == ord("-"):
            self.SetScale(self.CurrentScale - 1)
            self.ParentWindow.RefreshDisplayMenu()
        else:
            event.Skip()

#-------------------------------------------------------------------------------
#                  Model adding functions from Drop Target
#-------------------------------------------------------------------------------

    def AddVariableBlock(self, x, y, scaling, var_class, var_name, var_type):
        id = self.GetNewId()
        variable = FBD_Variable(self, var_class, var_name, var_type, id)
        width, height = variable.GetMinSize()
        if scaling is not None:
            x = round(float(x) / float(scaling[0])) * scaling[0]
            y = round(float(y) / float(scaling[1])) * scaling[1]
            width = round(float(width) / float(scaling[0]) + 0.5) * scaling[0]
            height = round(float(height) / float(scaling[1]) + 0.5) * scaling[1]
        variable.SetPosition(x, y)
        variable.SetSize(width, height)
        self.AddBlock(variable)
        self.Controler.AddEditedElementVariable(self.GetTagName(), id, var_class)
        self.RefreshVariableModel(variable)
        self.RefreshBuffer()
        self.RefreshScrollBars()
        self.RefreshVisibleElements()
        self.Refresh(False)

#-------------------------------------------------------------------------------
#                          Model adding functions
#-------------------------------------------------------------------------------

    def GetScaledSize(self, width, height):
        if self.Scaling is not None:
            width = round(float(width) / float(self.Scaling[0]) + 0.4) * self.Scaling[0]
            height = round(float(height) / float(self.Scaling[1]) + 0.4) * self.Scaling[1]
        return width, height
    
    def AddNewBlock(self, bbox):
        dialog = FBDBlockDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetBlockList(self.Controler.GetBlockTypes(self.TagName, self.Debug))
        dialog.SetPouNames(self.Controler.GetProjectPouNames(self.Debug))
        dialog.SetPouElementNames(self.Controler.GetEditedElementVariables(self.TagName, self.Debug))
        dialog.SetMinBlockSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            values.setdefault("name", "")
            block = FBD_Block(self, values["type"], values["name"], id, 
                    values["extension"], values["inputs"], 
                    executionControl = values["executionControl"],
                    executionOrder = values["executionOrder"])
            block.SetPosition(bbox.x, bbox.y)
            block.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            self.AddBlock(block)
            self.Controler.AddEditedElementBlock(self.TagName, id, values["type"], values.get("name", None))
            self.RefreshBlockModel(block)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            self.RefreshVariablePanel()
            self.ParentWindow.RefreshPouInstanceVariablesPanel()
            block.Refresh()
        dialog.Destroy()
    
    def AddNewVariable(self, bbox):
        words = self.TagName.split("::")
        if words[0] == "T":
            dialog = FBDVariableDialog(self.ParentWindow, self.Controler, words[2])
        else:
            dialog = FBDVariableDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetMinVariableSize((bbox.width, bbox.height))
        varlist = []
        vars = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        if vars:
            for var in vars:
                if var["Edit"]:
                    varlist.append((var["Name"], var["Class"], var["Type"]))
        returntype = self.Controler.GetEditedElementInterfaceReturnType(self.TagName, self.Debug)
        if returntype:
            varlist.append((self.Controler.GetEditedElementName(self.TagName), "Output", returntype))
        dialog.SetVariables(varlist)
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            variable = FBD_Variable(self, values["type"], values["name"], values["value_type"], id)
            variable.SetPosition(bbox.x, bbox.y)
            variable.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            self.AddBlock(variable)
            self.Controler.AddEditedElementVariable(self.TagName, id, values["type"])
            self.RefreshVariableModel(variable)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            variable.Refresh()
        dialog.Destroy()

    def AddNewConnection(self, bbox):
        dialog = ConnectionDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetPouNames(self.Controler.GetProjectPouNames(self.Debug))
        dialog.SetPouElementNames(self.Controler.GetEditedElementVariables(self.TagName, self.Debug))
        dialog.SetMinConnectionSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            connection = FBD_Connector(self, values["type"], values["name"], id)
            connection.SetPosition(bbox.x, bbox.y)
            connection.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            self.AddBlock(connection)
            self.Controler.AddEditedElementConnection(self.TagName, id, values["type"])
            self.RefreshConnectionModel(connection)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            connection.Refresh()
        dialog.Destroy()

    def AddNewComment(self, bbox):
        if wx.VERSION >= (2, 5, 0):
            dialog = wx.TextEntryDialog(self.ParentWindow, _("Edit comment"), _("Please enter comment text"), "", wx.OK|wx.CANCEL|wx.TE_MULTILINE)
        else:
            dialog = wx.TextEntryDialog(self.ParentWindow, _("Edit comment"), _("Please enter comment text"), "", wx.OK|wx.CANCEL)
        dialog.SetClientSize(wx.Size(400, 200))
        if dialog.ShowModal() == wx.ID_OK:
            value = dialog.GetValue()
            id = self.GetNewId()
            comment = Comment(self, value, id)
            comment.SetPosition(bbox.x, bbox.y)
            min_width, min_height = comment.GetMinSize()
            comment.SetSize(*self.GetScaledSize(max(min_width,bbox.width),max(min_height,bbox.height)))
            self.AddComment(comment)
            self.Controler.AddEditedElementComment(self.TagName, id)
            self.RefreshCommentModel(comment)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            comment.Refresh()
        dialog.Destroy()

    def AddNewContact(self, bbox):
        dialog = LDElementDialog(self.ParentWindow, self.Controler, "contact")
        dialog.SetPreviewFont(self.GetFont())
        varlist = []
        vars = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        if vars:
            for var in vars:
                if var["Type"] == "BOOL":
                    varlist.append(var["Name"])
        dialog.SetVariables(varlist)
        dialog.SetValues({"name":"","type":CONTACT_NORMAL})
        dialog.SetElementSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            contact = LD_Contact(self, values["type"], values["name"], id)
            contact.SetPosition(bbox.x, bbox.y)
            contact.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            self.AddBlock(contact)
            self.Controler.AddEditedElementContact(self.TagName, id)
            self.RefreshContactModel(contact)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            contact.Refresh()
        dialog.Destroy()

    def AddNewCoil(self, bbox):
        dialog = LDElementDialog(self.ParentWindow, self.Controler, "coil")
        dialog.SetPreviewFont(self.GetFont())
        varlist = []
        vars = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        if vars:
            for var in vars:
                if var["Class"] != "Input" and var["Type"] == "BOOL":
                    varlist.append(var["Name"])
        returntype = self.Controler.GetEditedElementInterfaceReturnType(self.TagName, self.Debug)
        if returntype == "BOOL":
            varlist.append(self.Controler.GetEditedElementName(self.TagName))
        dialog.SetVariables(varlist)
        dialog.SetValues({"name":"","type":COIL_NORMAL})
        dialog.SetElementSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            coil = LD_Coil(self, values["type"], values["name"], id)
            coil.SetPosition(bbox.x, bbox.y)
            coil.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            self.AddBlock(coil)
            self.Controler.AddEditedElementCoil(self.TagName, id)
            self.RefreshCoilModel(coil)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            coil.Refresh()
        dialog.Destroy()

    def AddNewPowerRail(self, bbox):
        dialog = LDPowerRailDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetMinSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            powerrail = LD_PowerRail(self, values["type"], id, values["number"])
            powerrail.SetPosition(bbox.x, bbox.y)
            powerrail.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            self.AddBlock(powerrail)
            self.Controler.AddEditedElementPowerRail(self.TagName, id, values["type"])
            self.RefreshPowerRailModel(powerrail)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            powerrail.Refresh()
        dialog.Destroy()

    def AddNewStep(self, bbox, initial = False):
        dialog = SFCStepDialog(self.ParentWindow, self.Controler, initial)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetPouNames(self.Controler.GetProjectPouNames(self.Debug))
        dialog.SetVariables(self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug))
        dialog.SetStepNames([block.GetName() for block in self.Blocks.itervalues() if isinstance(block, SFC_Step)])
        dialog.SetMinStepSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            step = SFC_Step(self, values["name"], initial, id)
            if values["input"]:
                step.AddInput()
            else:
                step.RemoveInput()
            if values["output"]:
                step.AddOutput()
            else:
                step.RemoveOutput()
            if values["action"]:
                step.AddAction()    
            else:
                step.RemoveAction()
            step.SetPosition(bbox.x, bbox.y)
            min_width, min_height = step.GetMinSize()
            step.SetSize(*self.GetScaledSize(max(bbox.width, min_width), max(bbox.height, min_height)))
            self.AddBlock(step)
            self.Controler.AddEditedElementStep(self.TagName, id)
            self.RefreshStepModel(step)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            step.Refresh()
        dialog.Destroy()

    def AddNewTransition(self, bbox):
        dialog = SFCTransitionDialog(self.ParentWindow, self.Controler, self.GetDrawingMode() == FREEDRAWING_MODE)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetTransitions(self.Controler.GetEditedElementTransitions(self.TagName, self.Debug))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            transition = SFC_Transition(self, values["type"], values["value"], values["priority"], id)
            transition.SetPosition(bbox.x, bbox.y)
            min_width, min_height = transition.GetMinSize()
            transition.SetSize(*self.GetScaledSize(max(bbox.width, min_width), max(bbox.height, min_height)))
            self.AddBlock(transition)
            self.Controler.AddEditedElementTransition(self.TagName, id)
            self.RefreshTransitionModel(transition)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            transition.Refresh()
        dialog.Destroy()

    def AddNewDivergence(self, bbox):
        dialog = SFCDivergenceDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetMinSize((bbox.width, bbox.height))
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            values = dialog.GetValues()
            divergence = SFC_Divergence(self, values["type"], values["number"], id)
            divergence.SetPosition(bbox.x, bbox.y)
            min_width, min_height = divergence.GetMinSize(True)
            divergence.SetSize(*self.GetScaledSize(max(bbox.width, min_width), max(bbox.height, min_height)))
            self.AddBlock(divergence)
            self.Controler.AddEditedElementDivergence(self.TagName, id, values["type"])
            self.RefreshDivergenceModel(divergence)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            divergence.Refresh()
        dialog.Destroy()

    def AddNewJump(self, bbox):
        choices = []
        for block in self.Blocks.itervalues():
            if isinstance(block, SFC_Step):
                choices.append(block.GetName())
        dialog = wx.SingleChoiceDialog(self.ParentWindow, 
              _("Add a new jump"), _("Please choose a target"), 
              choices, wx.DEFAULT_DIALOG_STYLE|wx.OK|wx.CANCEL)
        if dialog.ShowModal() == wx.ID_OK:
            id = self.GetNewId()
            value = dialog.GetStringSelection()
            jump = SFC_Jump(self, value, id)
            jump.SetPosition(bbox.x, bbox.y)
            min_width, min_height = jump.GetMinSize()
            jump.SetSize(*self.GetScaledSize(max(bbox.width, min_width), max(bbox.height, min_height)))
            self.AddBlock(jump)
            self.Controler.AddEditedElementJump(self.TagName, id)
            self.RefreshJumpModel(jump)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            jump.Refresh()
        dialog.Destroy()

    def AddNewActionBlock(self, bbox):
        dialog = ActionBlockDialog(self.ParentWindow)
        dialog.SetQualifierList(self.Controler.GetQualifierTypes())
        dialog.SetActionList(self.Controler.GetEditedElementActions(self.TagName, self.Debug))
        dialog.SetVariableList(self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug))
        if dialog.ShowModal() == wx.ID_OK:
            actions = dialog.GetValues()
            id = self.GetNewId()
            actionblock = SFC_ActionBlock(self, actions, id)
            actionblock.SetPosition(bbox.x, bbox.y)
            min_width, min_height = actionblock.GetMinSize()
            actionblock.SetSize(*self.GetScaledSize(max(bbox.width, min_width), max(bbox.height, min_height)))
            self.AddBlock(actionblock)
            self.Controler.AddEditedElementActionBlock(self.TagName, id)
            self.RefreshActionBlockModel(actionblock)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            actionblock.Refresh()
        dialog.Destroy()

#-------------------------------------------------------------------------------
#                          Edit element content functions
#-------------------------------------------------------------------------------

    def EditBlockContent(self, block):
        dialog = FBDBlockDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetBlockList(self.Controler.GetBlockTypes(self.TagName, self.Debug))
        dialog.SetPouNames(self.Controler.GetProjectPouNames(self.Debug))
        variable_names = self.Controler.GetEditedElementVariables(self.TagName, self.Debug)
        if block.GetName() != "":
            variable_names.remove(block.GetName())
        dialog.SetPouElementNames(variable_names)
        dialog.SetMinBlockSize(block.GetSize())
        old_values = {"name" : block.GetName(), 
                      "type" : block.GetType(), 
                      "extension" : block.GetExtension(), 
                      "inputs" : block.GetInputTypes(), 
                      "executionControl" : block.GetExecutionControl(), 
                      "executionOrder" : block.GetExecutionOrder()}
        dialog.SetValues(old_values)
        if dialog.ShowModal() == wx.ID_OK:
            new_values = dialog.GetValues()
            rect = block.GetRedrawRect(1, 1)
            if "name" in new_values:
                block.SetName(new_values["name"])
            else:
                block.SetName("")
            block.SetSize(*self.GetScaledSize(new_values["width"], new_values["height"]))
            block.SetType(new_values["type"], new_values["extension"], executionControl = new_values["executionControl"])
            block.SetExecutionOrder(new_values["executionOrder"])
            rect = rect.Union(block.GetRedrawRect())
            self.RefreshBlockModel(block)
            self.RefreshBuffer()
            if old_values["executionOrder"] != new_values["executionOrder"]:
                self.RefreshView(selection=({block.GetId(): True}, {}))
            else:
                self.RefreshScrollBars()
                self.RefreshVisibleElements()
                block.Refresh(rect)
            self.RefreshVariablePanel()
            self.ParentWindow.RefreshPouInstanceVariablesPanel()
        dialog.Destroy()

    def EditVariableContent(self, variable):
        words = self.TagName.split("::")
        if words[0] == "T":
            dialog = FBDVariableDialog(self.ParentWindow, self.Controler, words[2])
        else:
            dialog = FBDVariableDialog(self.ParentWindow, self.Controler)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetMinVariableSize(variable.GetSize())
        varlist = []
        vars = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        if vars:
            for var in vars:
                if var["Edit"]:
                    varlist.append((var["Name"], var["Class"], var["Type"]))
        returntype = self.Controler.GetEditedElementInterfaceReturnType(self.TagName, self.Debug)
        if returntype:
            varlist.append((self.Controler.GetEditedElementName(self.TagName), "Output", returntype))
        dialog.SetVariables(varlist)
        old_values = {"name" : variable.GetName(), "type" : variable.GetType(), 
            "executionOrder" : variable.GetExecutionOrder()}
        dialog.SetValues(old_values)
        if dialog.ShowModal() == wx.ID_OK:
            new_values = dialog.GetValues()
            rect = variable.GetRedrawRect(1, 1)
            variable.SetName(new_values["name"])
            variable.SetType(new_values["type"], new_values["value_type"])
            variable.SetSize(*self.GetScaledSize(new_values["width"], new_values["height"]))
            variable.SetExecutionOrder(new_values["executionOrder"])
            rect = rect.Union(variable.GetRedrawRect())
            if old_values["type"] != new_values["type"]:
                id = variable.GetId()
                self.Controler.RemoveEditedElementInstance(self.TagName, id)
                self.Controler.AddEditedElementVariable(self.TagName, id, new_values["type"])
            self.RefreshVariableModel(variable)
            self.RefreshBuffer()
            if old_values["executionOrder"] != new_values["executionOrder"]:
                self.RefreshView(selection=({variable.GetId(): True}, {}))
            else:
                self.RefreshVisibleElements()
                self.RefreshScrollBars()
                variable.Refresh(rect)
        dialog.Destroy()

    def EditConnectionContent(self, connection):
        dialog = ConnectionDialog(self.ParentWindow, self.Controler, True)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetPouNames(self.Controler.GetProjectPouNames(self.Debug))
        dialog.SetPouElementNames(self.Controler.GetEditedElementVariables(self.TagName, self.Debug))
        dialog.SetMinConnectionSize(connection.GetSize())
        values = {"name" : connection.GetName(), "type" : connection.GetType()}
        dialog.SetValues(values)
        result = dialog.ShowModal()
        dialog.Destroy()
        if result in [wx.ID_OK, wx.ID_YESTOALL]:
            old_type = connection.GetType()
            old_name = connection.GetName()
            values = dialog.GetValues()
            rect = connection.GetRedrawRect(1, 1)
            connection.SetName(values["name"])
            connection.SetType(values["type"])
            connection.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            rect = rect.Union(connection.GetRedrawRect())
            if old_type != values["type"]:
                id = connection.GetId()
                self.Controler.RemoveEditedElementInstance(self.TagName, id)
                self.Controler.AddEditedElementConnection(self.TagName, id, values["type"])
            self.RefreshConnectionModel(connection)
            if old_name != values["name"] and result == wx.ID_YESTOALL:
                self.Controler.UpdateEditedElementUsedVariable(self.TagName, old_name, values["name"])
                self.RefreshBuffer()
                self.RefreshView(selection=({connection.GetId(): True}, {}))
            else:
                self.RefreshBuffer()
                self.RefreshScrollBars()
                self.RefreshVisibleElements()
                connection.Refresh(rect)
        
    def EditContactContent(self, contact):
        dialog = LDElementDialog(self.ParentWindow, self.Controler, "contact")
        dialog.SetPreviewFont(self.GetFont())
        varlist = []
        vars = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        if vars:
            for var in vars:
                if var["Type"] == "BOOL":
                    varlist.append(var["Name"])
        dialog.SetVariables(varlist)
        values = {"name" : contact.GetName(), "type" : contact.GetType()}
        dialog.SetValues(values)
        dialog.SetElementSize(contact.GetSize())
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.GetValues()
            rect = contact.GetRedrawRect(1, 1)
            contact.SetName(values["name"])
            contact.SetType(values["type"])
            contact.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            rect = rect.Union(contact.GetRedrawRect())
            self.RefreshContactModel(contact)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            contact.Refresh(rect)
        dialog.Destroy()

    def EditCoilContent(self, coil):
        dialog = LDElementDialog(self.ParentWindow, self.Controler, "coil")
        dialog.SetPreviewFont(self.GetFont())
        varlist = []
        vars = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        if vars:
            for var in vars:
                if var["Class"] != "Input" and var["Type"] == "BOOL":
                    varlist.append(var["Name"])
        returntype = self.Controler.GetEditedElementInterfaceReturnType(self.TagName, self.Debug)
        if returntype == "BOOL":
            varlist.append(self.Controler.GetEditedElementName(self.TagName))
        dialog.SetVariables(varlist)
        values = {"name" : coil.GetName(), "type" : coil.GetType()}
        dialog.SetValues(values)
        dialog.SetElementSize(coil.GetSize())
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.GetValues()
            rect = coil.GetRedrawRect(1, 1)
            coil.SetName(values["name"])
            coil.SetType(values["type"])
            coil.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            rect = rect.Union(coil.GetRedrawRect())
            self.RefreshCoilModel(coil)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            coil.Refresh(rect)
        dialog.Destroy()

    def EditPowerRailContent(self, powerrail):
        connectors = powerrail.GetConnectors()
        type = powerrail.GetType()
        if type == LEFTRAIL:
            pin_number = len(connectors["outputs"])
        else:
            pin_number = len(connectors["inputs"])
        dialog = LDPowerRailDialog(self.ParentWindow, self.Controler, type, pin_number)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetMinSize(powerrail.GetSize())
        if dialog.ShowModal() == wx.ID_OK:
            old_type = powerrail.GetType()
            values = dialog.GetValues()
            rect = powerrail.GetRedrawRect(1, 1)
            powerrail.SetType(values["type"], values["number"])
            powerrail.SetSize(*self.GetScaledSize(values["width"], values["height"]))
            rect = rect.Union(powerrail.GetRedrawRect())
            if old_type != values["type"]:
                id = powerrail.GetId()
                self.Controler.RemoveEditedElementInstance(self.TagName, id)
                self.Controler.AddEditedElementPowerRail(self.TagName, id, values["type"])
            self.RefreshPowerRailModel(powerrail)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            powerrail.Refresh(rect)
        dialog.Destroy()

    def EditStepContent(self, step):
        dialog = SFCStepDialog(self.ParentWindow, self.Controler, step.GetInitial())
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetPouNames(self.Controler.GetProjectPouNames(self.Debug))
        dialog.SetVariables(self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug))
        dialog.SetStepNames([block.GetName() for block in self.Blocks.itervalues() if isinstance(block, SFC_Step) and block.GetName() != step.GetName()])
        dialog.SetMinStepSize(step.GetSize())
        values = {"name" : step.GetName()}
        connectors = step.GetConnectors()
        values["input"] = len(connectors["inputs"]) > 0
        values["output"] = len(connectors["outputs"]) > 0
        values["action"] = step.GetActionConnector() != None
        dialog.SetValues(values)
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.GetValues()
            rect = step.GetRedrawRect(1, 1)
            step.SetName(values["name"])
            if values["input"]:
                step.AddInput()
            else:
                step.RemoveInput()
            if values["output"]:
                step.AddOutput()
            else:
                step.RemoveOutput()
            if values["action"]:
                step.AddAction()    
            else:
                step.RemoveAction()
            step.UpdateSize(*self.GetScaledSize(values["width"], values["height"]))
            rect = rect.Union(step.GetRedrawRect())
            self.RefreshStepModel(step)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            step.Refresh(rect)
        
    def EditTransitionContent(self, transition):
        dialog = SFCTransitionDialog(self.ParentWindow, self.Controler, self.GetDrawingMode() == FREEDRAWING_MODE)
        dialog.SetPreviewFont(self.GetFont())
        dialog.SetTransitions(self.Controler.GetEditedElementTransitions(self.TagName, self.Debug))
        dialog.SetValues({"type":transition.GetType(),"value":transition.GetCondition(), "priority":transition.GetPriority()})
        dialog.SetElementSize(transition.GetSize())
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.GetValues()
            rect = transition.GetRedrawRect(1, 1)
            transition.SetType(values["type"],values["value"])
            transition.SetPriority(values["priority"])
            rect = rect.Union(transition.GetRedrawRect())
            self.RefreshTransitionModel(transition)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            transition.Refresh(rect)
        dialog.Destroy()

    def EditJumpContent(self, jump):
        choices = []
        for block in self.Blocks.itervalues():
            if isinstance(block, SFC_Step):
                choices.append(block.GetName())
        dialog = wx.SingleChoiceDialog(self.ParentWindow, 
              _("Edit jump target"), _("Please choose a target"), 
              choices, wx.DEFAULT_DIALOG_STYLE|wx.OK|wx.CANCEL)
        dialog.SetSelection(choices.index(jump.GetTarget()))
        if dialog.ShowModal() == wx.ID_OK:
            value = dialog.GetStringSelection()
            rect = jump.GetRedrawRect(1, 1)
            jump.SetTarget(value)
            rect = rect.Union(jump.GetRedrawRect())
            self.RefreshJumpModel(jump)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            jump.Refresh(rect)
        dialog.Destroy()

    def EditActionBlockContent(self, actionblock):
        dialog = ActionBlockDialog(self.ParentWindow)
        dialog.SetQualifierList(self.Controler.GetQualifierTypes())
        dialog.SetActionList(self.Controler.GetEditedElementActions(self.TagName, self.Debug))
        dialog.SetVariableList(self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug))
        dialog.SetValues(actionblock.GetActions())
        if dialog.ShowModal() == wx.ID_OK:
            actions = dialog.GetValues()
            rect = actionblock.GetRedrawRect(1, 1)
            actionblock.SetActions(actions)
            actionblock.SetSize(*self.GetScaledSize(*actionblock.GetSize()))
            rect = rect.Union(actionblock.GetRedrawRect())
            self.RefreshActionBlockModel(actionblock)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            actionblock.Refresh(rect)
        dialog.Destroy()

    def EditCommentContent(self, comment):
        if wx.VERSION >= (2, 5, 0):
            dialog = wx.TextEntryDialog(self.ParentWindow, _("Edit comment"), _("Please enter comment text"), comment.GetContent(), wx.OK|wx.CANCEL|wx.TE_MULTILINE)
        else:
            dialog = wx.TextEntryDialog(self.ParentWindow, _("Edit comment"), _("Please enter comment text"), comment.GetContent(), wx.OK|wx.CANCEL)
        dialog.SetClientSize(wx.Size(400, 200))
        if dialog.ShowModal() == wx.ID_OK:
            value = dialog.GetValue()
            rect = comment.GetRedrawRect(1, 1)
            comment.SetContent(value)
            comment.SetSize(*self.GetScaledSize(*comment.GetSize()))
            rect = rect.Union(comment.GetRedrawRect())
            self.RefreshCommentModel(comment)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            comment.Refresh(rect)
        dialog.Destroy()

#-------------------------------------------------------------------------------
#                          Model update functions
#-------------------------------------------------------------------------------

    def RefreshBlockModel(self, block):
        blockid = block.GetId()
        infos = {}
        infos["type"] = block.GetType()
        infos["name"] = block.GetName()
        if self.CurrentLanguage == "FBD":
            infos["executionOrder"] = block.GetExecutionOrder()
        infos["x"], infos["y"] = block.GetPosition()
        infos["width"], infos["height"] = block.GetSize()
        infos["connectors"] = block.GetConnectors()
        self.Controler.SetEditedElementBlockInfos(self.TagName, blockid, infos)
    
    def ChangeVariableType(self, variable, new_type):
        old_type = variable.GetType()
        rect = variable.GetRedrawRect(1, 1)
        if old_type != new_type:
            variable.SetType(new_type, variable.GetValueType())
            id = variable.GetId()
            self.Controler.RemoveEditedElementInstance(self.TagName, id)
            self.Controler.AddEditedElementVariable(self.TagName, id, new_type)
            self.RefreshVariableModel(variable)
            self.RefreshBuffer()
            self.RefreshVisibleElements()
            self.RefreshScrollBars()
            variable.Refresh(rect.Union(variable.GetRedrawRect()))
    
    def RefreshVariableModel(self, variable):
        variableid = variable.GetId()
        infos = {}
        infos["name"] = variable.GetName()
        if self.CurrentLanguage == "FBD":
            infos["executionOrder"] = variable.GetExecutionOrder()
        infos["x"], infos["y"] = variable.GetPosition()
        infos["width"], infos["height"] = variable.GetSize()
        infos["connectors"] = variable.GetConnectors()
        self.Controler.SetEditedElementVariableInfos(self.TagName, variableid, infos)

    def ChangeConnectionType(self, connection, new_type):
        old_type = connection.GetType()
        rect = connection.GetRedrawRect(1, 1)
        if old_type != new_type:
            connection.SetType(new_type)
            id = connection.GetId()
            self.Controler.RemoveEditedElementInstance(self.TagName, id)
            self.Controler.AddEditedElementConnection(self.TagName, id, new_type)
            self.RefreshConnectionModel(connection)
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVisibleElements()
            connection.Refresh(rect.Union(connection.GetRedrawRect()))

    def RefreshConnectionModel(self, connection):
        connectionid = connection.GetId()
        infos = {}
        infos["name"] = connection.GetName()
        infos["x"], infos["y"] = connection.GetPosition()
        infos["width"], infos["height"] = connection.GetSize()
        infos["connector"] = connection.GetConnector()
        self.Controler.SetEditedElementConnectionInfos(self.TagName, connectionid, infos)

    def RefreshCommentModel(self, comment):
        commentid = comment.GetId()
        infos = {}
        infos["content"] = comment.GetContent()
        infos["x"], infos["y"] = comment.GetPosition()
        infos["width"], infos["height"] = comment.GetSize()
        self.Controler.SetEditedElementCommentInfos(self.TagName, commentid, infos)

    def RefreshPowerRailModel(self, powerrail):
        powerrailid = powerrail.GetId()
        infos = {}
        infos["x"], infos["y"] = powerrail.GetPosition()
        infos["width"], infos["height"] = powerrail.GetSize()
        infos["connectors"] = powerrail.GetConnectors()
        self.Controler.SetEditedElementPowerRailInfos(self.TagName, powerrailid, infos)

    def RefreshContactModel(self, contact):
        contactid = contact.GetId()
        infos = {}
        infos["name"] = contact.GetName()
        infos["type"] = contact.GetType()
        infos["x"], infos["y"] = contact.GetPosition()
        infos["width"], infos["height"] = contact.GetSize()
        infos["connectors"] = contact.GetConnectors()
        self.Controler.SetEditedElementContactInfos(self.TagName, contactid, infos)

    def RefreshCoilModel(self, coil):
        coilid = coil.GetId()
        infos = {}
        infos["name"] = coil.GetName()
        infos["type"] = coil.GetType()
        infos["x"], infos["y"] = coil.GetPosition()
        infos["width"], infos["height"] = coil.GetSize()
        infos["connectors"] = coil.GetConnectors()
        self.Controler.SetEditedElementCoilInfos(self.TagName, coilid, infos)

    def RefreshStepModel(self, step):
        stepid = step.GetId()
        infos = {}
        infos["name"] = step.GetName()
        infos["initial"] = step.GetInitial()
        infos["x"], infos["y"] = step.GetPosition()
        infos["width"], infos["height"] = step.GetSize()
        infos["connectors"] = step.GetConnectors()
        infos["action"] = step.GetActionConnector()
        self.Controler.SetEditedElementStepInfos(self.TagName, stepid, infos)

    def RefreshTransitionModel(self, transition):
        transitionid = transition.GetId()
        infos = {}
        infos["type"] = transition.GetType()
        infos["priority"] = transition.GetPriority()
        infos["condition"] = transition.GetCondition()
        infos["x"], infos["y"] = transition.GetPosition()
        infos["width"], infos["height"] = transition.GetSize()
        infos["connectors"] = transition.GetConnectors()
        infos["connection"] = transition.GetConditionConnector()
        self.Controler.SetEditedElementTransitionInfos(self.TagName, transitionid, infos)

    def RefreshDivergenceModel(self, divergence):
        divergenceid = divergence.GetId()
        infos = {}
        infos["x"], infos["y"] = divergence.GetPosition()
        infos["width"], infos["height"] = divergence.GetSize()
        infos["connectors"] = divergence.GetConnectors()
        self.Controler.SetEditedElementDivergenceInfos(self.TagName, divergenceid, infos)

    def RefreshJumpModel(self, jump):
        jumpid = jump.GetId()
        infos = {}
        infos["target"] = jump.GetTarget()
        infos["x"], infos["y"] = jump.GetPosition()
        infos["width"], infos["height"] = jump.GetSize()
        infos["connector"] = jump.GetConnector()
        self.Controler.SetEditedElementJumpInfos(self.TagName, jumpid, infos)

    def RefreshActionBlockModel(self, actionblock):
        actionblockid = actionblock.GetId()
        infos = {}
        infos["actions"] = actionblock.GetActions()
        infos["x"], infos["y"] = actionblock.GetPosition()
        infos["width"], infos["height"] = actionblock.GetSize()
        infos["connector"] = actionblock.GetConnector()
        self.Controler.SetEditedElementActionBlockInfos(self.TagName, actionblockid, infos)


#-------------------------------------------------------------------------------
#                          Model delete functions
#-------------------------------------------------------------------------------


    def DeleteBlock(self, block):
        elements = []
        for output in block.GetConnectors()["outputs"]:
            for element in output.GetConnectedBlocks():
                if element not in elements:
                    elements.append(element)
        block.Clean()
        self.RemoveBlock(block)
        self.Controler.RemoveEditedElementInstance(self.TagName, block.GetId())
        for element in elements:
            element.RefreshModel()
        wx.CallAfter(self.RefreshVariablePanel)
        wx.CallAfter(self.ParentWindow.RefreshPouInstanceVariablesPanel)
        
    def DeleteVariable(self, variable):
        connectors = variable.GetConnectors()
        if len(connectors["outputs"]) > 0:
            elements = connectors["outputs"][0].GetConnectedBlocks()
        else:
            elements = []
        variable.Clean()
        self.RemoveBlock(variable)
        self.Controler.RemoveEditedElementInstance(self.TagName, variable.GetId())
        for element in elements:
            element.RefreshModel()

    def DeleteConnection(self, connection):
        if connection.GetType() == CONTINUATION:
            elements = connection.GetConnector().GetConnectedBlocks()
        else:
            elements = []
        connection.Clean()
        self.RemoveBlock(connection)
        self.Controler.RemoveEditedElementInstance(self.TagName, connection.GetId())
        for element in elements:
            element.RefreshModel()

    def DeleteComment(self, comment):
        self.RemoveComment(comment)
        self.Controler.RemoveEditedElementInstance(self.TagName, comment.GetId())

    def DeleteWire(self, wire):
        if wire in self.Wires:
            connected = wire.GetConnected()
            wire.Clean()
            self.RemoveWire(wire)
            for connector in connected:
                connector.RefreshParentBlock()

    def DeleteContact(self, contact):
        connectors = contact.GetConnectors()
        elements = connectors["outputs"][0].GetConnectedBlocks()
        contact.Clean()
        self.RemoveBlock(contact)
        self.Controler.RemoveEditedElementInstance(self.TagName, contact.GetId())
        for element in elements:
            element.RefreshModel()

    def DeleteCoil(self, coil):
        connectors = coil.GetConnectors()
        elements = connectors["outputs"][0].GetConnectedBlocks()
        coil.Clean()
        self.RemoveBlock(coil)
        self.Controler.RemoveEditedElementInstance(self.TagName, coil.GetId())
        for element in elements:
            element.RefreshModel()

    def DeletePowerRail(self, powerrail):
        elements = []
        if powerrail.GetType() == LEFTRAIL:
            connectors = powerrail.GetConnectors()
            for connector in connectors["outputs"]:
                for element in connector.GetConnectedBlocks():
                    if element not in elements:
                        elements.append(element)
        powerrail.Clean()
        self.RemoveBlock(powerrail)
        self.Controler.RemoveEditedElementInstance(self.TagName, powerrail.GetId())
        for element in elements:
            element.RefreshModel()

    def DeleteStep(self, step):
        elements = []
        connectors = step.GetConnectors()
        action_connector = step.GetActionConnector()
        if len(connectors["outputs"]) > 0:
            for element in connectors["outputs"][0].GetConnectedBlocks():
                if element not in elements:
                    elements.append(element)
        if action_connector is not None:
            for element in action_connector.GetConnectedBlocks():
                if element not in elements:
                    elements.append(element)
        step.Clean()
        self.RemoveBlock(step)
        self.Controler.RemoveEditedElementInstance(self.TagName, step.GetId())
        for element in elements:
            element.RefreshModel()
            
    def DeleteTransition(self, transition):
        elements = []
        connectors = transition.GetConnectors()
        for element in connectors["outputs"][0].GetConnectedBlocks():
            if element not in elements:
                elements.append(element)
        transition.Clean()
        self.RemoveBlock(transition)
        self.Controler.RemoveEditedElementInstance(self.TagName, transition.GetId())
        for element in elements:
            element.RefreshModel()

    def DeleteDivergence(self, divergence):
        elements = []
        connectors = divergence.GetConnectors()
        for output in connectors["outputs"]:
            for element in output.GetConnectedBlocks():
                if element not in elements:
                    elements.append(element)
        divergence.Clean()
        self.RemoveBlock(divergence)
        self.Controler.RemoveEditedElementInstance(self.TagName, divergence.GetId())
        for element in elements:
            element.RefreshModel()
    
    def DeleteJump(self, jump):
        jump.Clean()
        self.RemoveBlock(jump)
        self.Controler.RemoveEditedElementInstance(self.TagName, jump.GetId())
    
    def DeleteActionBlock(self, actionblock):
        actionblock.Clean()
        self.RemoveBlock(actionblock)
        self.Controler.RemoveEditedElementInstance(self.TagName, actionblock.GetId())


#-------------------------------------------------------------------------------
#                            Editing functions
#-------------------------------------------------------------------------------
    
    def Cut(self):
        if not self.Debug and (self.IsBlock(self.SelectedElement) or self.IsComment(self.SelectedElement) or isinstance(self.SelectedElement, Graphic_Group)):
            blocks, wires = self.SelectedElement.GetDefinition()
            text = self.Controler.GetEditedElementInstancesCopy(self.TagName, blocks, wires, self.Debug)
            self.ParentWindow.SetCopyBuffer(text)
            rect = self.SelectedElement.GetRedrawRect(1, 1)
            self.SelectedElement.Delete()
            self.SelectedElement = None
            self.RefreshBuffer()
            self.RefreshScrollBars()
            self.RefreshVariablePanel()
            self.ParentWindow.RefreshPouInstanceVariablesPanel()
            self.RefreshRect(self.GetScrolledRect(rect), False)
        
    def Copy(self):
        if not self.Debug and (self.IsBlock(self.SelectedElement) or self.IsComment(self.SelectedElement) or isinstance(self.SelectedElement, Graphic_Group)):
            blocks, wires = self.SelectedElement.GetDefinition()
            text = self.Controler.GetEditedElementInstancesCopy(self.TagName, blocks, wires, self.Debug)
            self.ParentWindow.SetCopyBuffer(text)
            
    def Paste(self, bbx=None):
        if not self.Debug:
            element = self.ParentWindow.GetCopyBuffer()
            if bbx is None:
                mouse_pos = self.Editor.ScreenToClient(wx.GetMousePosition())
                middle = wx.Rect(0, 0, *self.Editor.GetClientSize()).InsideXY(mouse_pos.x, mouse_pos.y)
                if middle:
                    x, y = self.CalcUnscrolledPosition(mouse_pos.x, mouse_pos.y)
                else:
                    x, y = self.CalcUnscrolledPosition(0, 0)
                new_pos = [int(x / self.ViewScale[0]), int(y / self.ViewScale[1])]
            else:
                middle = True
                new_pos = [bbx.x, bbx.y]
            result = self.Controler.PasteEditedElementInstances(self.TagName, element, new_pos, middle, self.Debug)
            if not isinstance(result, (StringType, UnicodeType)):
                self.RefreshBuffer()
                self.RefreshView(selection=result)
                self.RefreshVariablePanel()
                self.ParentWindow.RefreshPouInstanceVariablesPanel()
            else:
                message = wx.MessageDialog(self.Editor, result, "Error", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()

    def CanAddElement(self, block):
        if isinstance(block, Graphic_Group):
            return block.CanAddBlocks(self)
        elif self.CurrentLanguage == "SFC":
            return True
        elif self.CurrentLanguage == "LD" and not isinstance(block, (SFC_Step, SFC_Transition, SFC_Divergence, SFC_Jump, SFC_ActionBlock)):
            return True
        elif self.CurrentLanguage == "FBD" and isinstance(block, (FBD_Block, FBD_Variable, FBD_Connector, Comment)):
            return True
        return False

    def GenerateNewName(self, element=None, blocktype=None, exclude={}):
        if element is not None and isinstance(element, SFC_Step):
            format = "Step%d"
        else:
            if element is not None:
                blocktype = element.GetType()
            if blocktype is None:
                blocktype = "Block"
            format = "%s%%d" % blocktype
        return self.Controler.GenerateNewName(self.TagName, None, format, exclude, self.Debug)

    def IsNamedElement(self, element):
        return isinstance(element, FBD_Block) and element.GetName() != "" or isinstance(element, SFC_Step)

    def CopyBlock(self, element, pos):
        if isinstance(element, Graphic_Group):
            block = element.Clone(self, pos=pos)
        else:
            new_id = self.GetNewId()
            if self.IsNamedElement(element):
                name = self.GenerateNewName(element)
                block = element.Clone(self, new_id, name, pos)
            else:
                name = None
                block = element.Clone(self, new_id, pos=pos)
            self.AddBlockInModel(block)
        return block
    
    def AddBlockInModel(self, block):
        if isinstance(block, Comment):
            self.AddComment(block)
            self.Controler.AddEditedElementComment(self.TagName, block.GetId())
            self.RefreshCommentModel(block)
        else:
            self.AddBlock(block)
            if isinstance(block, FBD_Block):
                self.Controler.AddEditedElementBlock(self.TagName, block.GetId(), block.GetType(), block.GetName())
                self.RefreshBlockModel(block)
            elif isinstance(block, FBD_Variable):
                self.Controler.AddEditedElementVariable(self.TagName, block.GetId(), block.GetType())
                self.RefreshVariableModel(block)
            elif isinstance(block, FBD_Connector):
                self.Controler.AddEditedElementConnection(self.TagName, block.GetId(), block.GetType())
                self.RefreshConnectionModel(block)
            elif isinstance(block, LD_Contact):
                self.Controler.AddEditedElementContact(self.TagName, block.GetId())
                self.RefreshContactModel(block)
            elif isinstance(block, LD_Coil):
                self.Controler.AddEditedElementCoil(self.TagName, block.GetId())
                self.RefreshCoilModel(block)
            elif isinstance(block, LD_PowerRail):
                self.Controler.AddEditedElementPowerRail(self.TagName, block.GetId(), block.GetType())
                self.RefreshPowerRailModel(block)
            elif isinstance(block, SFC_Step):
                self.Controler.AddEditedElementStep(self.TagName, block.GetId())
                self.RefreshStepModel(block)    
            elif isinstance(block, SFC_Transition):
                self.Controler.AddEditedElementTransition(self.TagName, block.GetId())
                self.RefreshTransitionModel(block)       
            elif isinstance(block, SFC_Divergence):
                self.Controler.AddEditedElementDivergence(self.TagName, block.GetId(), block.GetType())
                self.RefreshDivergenceModel(block)
            elif isinstance(block, SFC_Jump):
                self.Controler.AddEditedElementJump(self.TagName, block.GetId())
                self.RefreshJumpModel(block)       
            elif isinstance(block, SFC_ActionBlock):
                self.Controler.AddEditedElementActionBlock(self.TagName, block.GetId())
                self.RefreshActionBlockModel(block)

#-------------------------------------------------------------------------------
#                         Find and Replace functions
#-------------------------------------------------------------------------------

    def Find(self, direction, search_params):
        if self.SearchParams != search_params:
            self.ClearHighlights(SEARCH_RESULT_HIGHLIGHT)
            
            self.SearchParams = search_params
            criteria = {
                "raw_pattern": search_params["find_pattern"], 
                "pattern": re.compile(search_params["find_pattern"]),
                "case_sensitive": search_params["case_sensitive"],
                "regular_expression": search_params["regular_expression"],
                "filter": "all"}
            
            self.SearchResults = []
            blocks = []
            for infos, start, end, text in self.Controler.SearchInPou(self.TagName, criteria, self.Debug):
                if infos[1] in ["var_local", "var_input", "var_output", "var_inout"]:
                    self.SearchResults.append((infos[1:], start, end, SEARCH_RESULT_HIGHLIGHT))
                else:
                    block = self.Blocks.get(infos[2])
                    if block is not None:
                        blocks.append((block, (infos[1:], start, end, SEARCH_RESULT_HIGHLIGHT)))
            blocks.sort(sort_blocks)
            self.SearchResults.extend([infos for block, infos in blocks])
            self.CurrentFindHighlight = None
        
        if len(self.SearchResults) > 0:
            if self.CurrentFindHighlight is not None:
                old_idx = self.SearchResults.index(self.CurrentFindHighlight)
                if self.SearchParams["wrap"]:
                    idx = (old_idx + direction) % len(self.SearchResults)
                else:
                    idx = max(0, min(old_idx + direction, len(self.SearchResults) - 1))
                if idx != old_idx:
                    self.RemoveHighlight(*self.CurrentFindHighlight)
                    self.CurrentFindHighlight = self.SearchResults[idx]
                    self.AddHighlight(*self.CurrentFindHighlight)
            else:
                self.CurrentFindHighlight = self.SearchResults[0]
                self.AddHighlight(*self.CurrentFindHighlight)
            
        else:
            if self.CurrentFindHighlight is not None:
                self.RemoveHighlight(*self.CurrentFindHighlight)
            self.CurrentFindHighlight = None
        
#-------------------------------------------------------------------------------
#                        Highlights showing functions
#-------------------------------------------------------------------------------

    def OnRefreshHighlightsTimer(self, event):
        self.RefreshView()
        event.Skip()

    def ClearHighlights(self, highlight_type=None):
        EditorPanel.ClearHighlights(self, highlight_type)
        
        if highlight_type is None:
            self.Highlights = []
        else:
            self.Highlights = [(infos, start, end, highlight) for (infos, start, end, highlight) in self.Highlights if highlight != highlight_type]
        self.RefreshView()

    def AddHighlight(self, infos, start, end, highlight_type):
        EditorPanel.AddHighlight(self, infos, start, end, highlight_type)
        
        self.Highlights.append((infos, start, end, highlight_type))
        if infos[0] not in ["var_local", "var_input", "var_output", "var_inout"]:
            block = self.Blocks.get(infos[1])
            if block is not None:
                self.EnsureVisible(block)
            self.RefreshHighlightsTimer.Start(int(REFRESH_HIGHLIGHT_PERIOD * 1000), oneShot=True)
    
    def RemoveHighlight(self, infos, start, end, highlight_type):
        EditorPanel.RemoveHighlight(self, infos, start, end, highlight_type)
        
        if (infos, start, end, highlight_type) in self.Highlights:
            self.Highlights.remove((infos, start, end, highlight_type))
            self.RefreshHighlightsTimer.Start(int(REFRESH_HIGHLIGHT_PERIOD * 1000), oneShot=True)
    
    def ShowHighlights(self):
        for infos, start, end, highlight_type in self.Highlights:
            if infos[0] in ["comment", "io_variable", "block", "connector", "coil", "contact", "step", "transition", "jump", "action_block"]:
                block = self.FindElementById(infos[1])
                if block is not None:
                    block.AddHighlight(infos[2:], start, end, highlight_type)
        
#-------------------------------------------------------------------------------
#                            Drawing functions
#-------------------------------------------------------------------------------

    def OnScrollWindow(self, event):
        if self.Editor.HasCapture() and self.StartMousePos:
            return
        if wx.Platform == '__WXMSW__':
            wx.CallAfter(self.RefreshVisibleElements)
        elif event.GetOrientation() == wx.HORIZONTAL:
            self.RefreshVisibleElements(xp = event.GetPosition())
        else:
            self.RefreshVisibleElements(yp = event.GetPosition())
        event.Skip()

    def OnScrollStop(self, event):
        self.RefreshScrollBars()
        event.Skip()

    def OnMouseWheelWindow(self, event):
        if self.StartMousePos is None or self.StartScreenPos is None:
            rotation = event.GetWheelRotation() / event.GetWheelDelta()
            if event.ShiftDown():
                x, y = self.GetViewStart()
                xp = max(0, min(x - rotation * 3, self.Editor.GetVirtualSize()[0] / self.Editor.GetScrollPixelsPerUnit()[0]))
                self.RefreshVisibleElements(xp = xp)
                self.Scroll(xp, y)
            elif event.ControlDown():
                dc = self.GetLogicalDC()
                self.SetScale(self.CurrentScale + rotation, mouse_event = event)
                self.ParentWindow.RefreshDisplayMenu()
            else:
                x, y = self.GetViewStart()
                yp = max(0, min(y - rotation * 3, self.Editor.GetVirtualSize()[1] / self.Editor.GetScrollPixelsPerUnit()[1]))
                self.RefreshVisibleElements(yp = yp)
                self.Scroll(x, yp)
        
    def OnMoveWindow(self, event):
        self.RefreshScrollBars()
        self.RefreshVisibleElements()
        event.Skip()

    def DoDrawing(self, dc, printing = False):
        if printing:
            if getattr(dc, "printing", False):
                font = wx.Font(self.GetFont().GetPointSize(), wx.MODERN, wx.NORMAL, wx.NORMAL)
                dc.SetFont(font)
            else:
                dc.SetFont(self.GetFont())
        else:
            dc.SetBackground(wx.Brush(self.Editor.GetBackgroundColour()))
            dc.Clear()
            dc.BeginDrawing()
        if self.Scaling is not None and self.DrawGrid and not printing:
            dc.SetPen(wx.TRANSPARENT_PEN)
            dc.SetBrush(self.GridBrush)
            xstart, ystart = self.GetViewStart()
            window_size = self.Editor.GetClientSize()
            width, height = self.Editor.GetVirtualSize()
            width = int(max(width, xstart * SCROLLBAR_UNIT + window_size[0]) / self.ViewScale[0])
            height = int(max(height, ystart * SCROLLBAR_UNIT + window_size[1]) / self.ViewScale[1])
            dc.DrawRectangle(1, 1, width, height)
        if self.PageSize is not None and not printing:
            dc.SetPen(self.PagePen)
            xstart, ystart = self.GetViewStart()
            window_size = self.Editor.GetClientSize()
            for x in xrange(self.PageSize[0] - (xstart * SCROLLBAR_UNIT) % self.PageSize[0], int(window_size[0] / self.ViewScale[0]), self.PageSize[0]):
                dc.DrawLine(xstart * SCROLLBAR_UNIT + x + 1, int(ystart * SCROLLBAR_UNIT / self.ViewScale[0]), 
                            xstart * SCROLLBAR_UNIT + x + 1, int((ystart * SCROLLBAR_UNIT + window_size[1]) / self.ViewScale[0]))
            for y in xrange(self.PageSize[1] - (ystart * SCROLLBAR_UNIT) % self.PageSize[1], int(window_size[1] / self.ViewScale[1]), self.PageSize[1]):
                dc.DrawLine(int(xstart * SCROLLBAR_UNIT / self.ViewScale[0]), ystart * SCROLLBAR_UNIT + y + 1, 
                            int((xstart * SCROLLBAR_UNIT + window_size[0]) / self.ViewScale[1]), ystart * SCROLLBAR_UNIT + y + 1)
        
        # Draw all elements
        for comment in self.Comments.itervalues():
            if comment != self.SelectedElement and (comment.IsVisible() or printing):
                comment.Draw(dc)
        for wire in self.Wires.iterkeys():
            if wire != self.SelectedElement and (wire.IsVisible() or printing):
                 if not self.Debug or wire.GetValue() != True:
                    wire.Draw(dc)
        if self.Debug:
            for wire in self.Wires.iterkeys():
                if wire != self.SelectedElement and (wire.IsVisible() or printing) and wire.GetValue() == True:
                    wire.Draw(dc)
        for block in self.Blocks.itervalues():
            if block != self.SelectedElement and (block.IsVisible() or printing):
                block.Draw(dc)
        
        if self.SelectedElement is not None and (self.SelectedElement.IsVisible() or printing):
            self.SelectedElement.Draw(dc)
        
        if not printing:
            if self.Debug:
                is_action = self.TagName.split("::")[0] == "A"
                text = _("Debug: %s") % self.InstancePath
                if is_action and self.Value is not None:
                    text += " ("
                dc.DrawText(text, 2, 2)
                if is_action and self.Value is not None:
                    value_text = self.VALUE_TRANSLATION[self.Value]
                    tw, th = dc.GetTextExtent(text)
                    if self.Value:
                        dc.SetTextForeground(wx.GREEN)
                    dc.DrawText(value_text, tw + 2, 2)
                    if self.Value:
                        dc.SetTextForeground(wx.BLACK)
                    vw, vh = dc.GetTextExtent(value_text)
                    dc.DrawText(")", tw + vw + 4, 2)
            if self.rubberBand.IsShown():
                self.rubberBand.Draw(dc)
            dc.EndDrawing()

    def OnPaint(self, event):
        dc = self.GetLogicalDC(True)
        self.DoDrawing(dc)
        wx.BufferedPaintDC(self.Editor, dc.GetAsBitmap())
        if self.Debug:
            DebugViewer.RefreshNewData(self)
        event.Skip()


