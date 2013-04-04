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

import os
import re
from types import TupleType, StringType, UnicodeType

import wx
import wx.grid
import wx.lib.buttons

from plcopen.structures import LOCATIONDATATYPES, TestIdentifier, IEC_KEYWORDS
from graphics.GraphicCommons import REFRESH_HIGHLIGHT_PERIOD, ERROR_HIGHLIGHT
from dialogs.ArrayTypeDialog import ArrayTypeDialog
from CustomGrid import CustomGrid
from CustomTable import CustomTable
from LocationCellEditor import LocationCellEditor
from util.BitmapLibrary import GetBitmap

#-------------------------------------------------------------------------------
#                                 Helpers
#-------------------------------------------------------------------------------

def AppendMenu(parent, help, id, kind, text):
    if wx.VERSION >= (2, 6, 0):
        parent.Append(help=help, id=id, kind=kind, text=text)
    else:
        parent.Append(helpString=help, id=id, kind=kind, item=text)

[TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU, DISPLAYMENU, PROJECTTREE, 
 POUINSTANCEVARIABLESPANEL, LIBRARYTREE, SCALING, PAGETITLES
] = range(10)

def GetVariableTableColnames(location):
    _ = lambda x : x
    if location:
    	return ["#", _("Name"), _("Class"), _("Type"), _("Location"), _("Initial Value"), _("Option"), _("Documentation")]
    return ["#", _("Name"), _("Class"), _("Type"), _("Initial Value"), _("Option"), _("Documentation")]

def GetOptions(constant=True, retain=True, non_retain=True):
    _ = lambda x : x
    options = [""]
    if constant:
        options.append(_("Constant"))
    if retain:
        options.append(_("Retain"))
    if non_retain:
        options.append(_("Non-Retain"))
    return options
OPTIONS_DICT = dict([(_(option), option) for option in GetOptions()])

def GetFilterChoiceTransfer():
    _ = lambda x : x
    return {_("All"): _("All"), _("Interface"): _("Interface"), 
            _("   Input"): _("Input"), _("   Output"): _("Output"), _("   InOut"): _("InOut"), 
            _("   External"): _("External"), _("Variables"): _("Variables"), _("   Local"): _("Local"),
            _("   Temp"): _("Temp"), _("Global"): _("Global")}#, _("Access") : _("Access")}
VARIABLE_CHOICES_DICT = dict([(_(_class), _class) for _class in GetFilterChoiceTransfer().iterkeys()])
VARIABLE_CLASSES_DICT = dict([(_(_class), _class) for _class in GetFilterChoiceTransfer().itervalues()])

CheckOptionForClass = {"Local": lambda x: x,
                       "Temp": lambda x: "",
                       "Input": lambda x: {"Retain": "Retain", "Non-Retain": "Non-Retain"}.get(x, ""),
                       "InOut": lambda x: "",
                       "Output": lambda x: {"Retain": "Retain", "Non-Retain": "Non-Retain"}.get(x, ""),
                       "Global": lambda x: {"Constant": "Constant", "Retain": "Retain"}.get(x, ""),
                       "External": lambda x: {"Constant": "Constant"}.get(x, "")
                      }

LOCATION_MODEL = re.compile("((?:%[IQM](?:\*|(?:[XBWLD]?[0-9]+(?:\.[0-9]+)*)))?)$")

#-------------------------------------------------------------------------------
#                            Variables Panel Table
#-------------------------------------------------------------------------------

class VariableTable(CustomTable):
    
    """
    A custom wx.grid.Grid Table using user supplied data
    """
    def __init__(self, parent, data, colnames):
        # The base class must be initialized *first*
        CustomTable.__init__(self, parent, data, colnames)
        self.old_value = None
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            if col == 0:
                return self.data[row]["Number"]
            colname = self.GetColLabelValue(col, False)
            value = self.data[row].get(colname, "")
            if colname == "Type" and isinstance(value, TupleType):
                if value[0] == "array":
                    return "ARRAY [%s] OF %s" % (",".join(map(lambda x : "..".join(x), value[2])), value[1])
            if not isinstance(value, (StringType, UnicodeType)):
                value = str(value)
            if colname in ["Class", "Option"]:
                return _(value)
            return value
    
    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            colname = self.GetColLabelValue(col, False)
            if colname == "Name":
                self.old_value = self.data[row][colname]
            elif colname == "Class":
                value = VARIABLE_CLASSES_DICT[value]
                self.SetValueByName(row, "Option", CheckOptionForClass[value](self.GetValueByName(row, "Option")))
                if value == "External":
                    self.SetValueByName(row, "Initial Value", "")
            elif colname == "Option":
                value = OPTIONS_DICT[value]
            self.data[row][colname] = value

    def GetOldValue(self):
        return self.old_value

    def _updateColAttrs(self, grid):
        """
        wx.grid.Grid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        for row in range(self.GetNumberRows()):
            var_class = self.GetValueByName(row, "Class")
            var_type = self.GetValueByName(row, "Type")
            row_highlights = self.Highlights.get(row, {})
            for col in range(self.GetNumberCols()):
                editor = None
                renderer = None
                colname = self.GetColLabelValue(col, False)
                if self.Parent.Debug:
                    grid.SetReadOnly(row, col, True)
                else:
                    if colname == "Option":
                        options = GetOptions(constant = var_class in ["Local", "External", "Global"],
                                             retain = self.Parent.ElementType != "function" and var_class in ["Local", "Input", "Output", "Global"],
                                             non_retain = self.Parent.ElementType != "function" and var_class in ["Local", "Input", "Output"])
                        if len(options) > 1:
                            editor = wx.grid.GridCellChoiceEditor()
                            editor.SetParameters(",".join(map(_, options)))
                        else:
                            grid.SetReadOnly(row, col, True)
                    elif col != 0 and self.GetValueByName(row, "Edit"):
                        grid.SetReadOnly(row, col, False)
                        if colname == "Name":
                            if self.Parent.PouIsUsed and var_class in ["Input", "Output", "InOut"]:
                                grid.SetReadOnly(row, col, True)
                            else:
                                editor = wx.grid.GridCellTextEditor()
                                renderer = wx.grid.GridCellStringRenderer()
                        elif colname == "Initial Value":
                            if var_class not in ["External", "InOut"]:
                                if self.Parent.Controler.IsEnumeratedType(var_type):
                                    editor = wx.grid.GridCellChoiceEditor()
                                    editor.SetParameters(",".join(self.Parent.Controler.GetEnumeratedDataValues(var_type)))
                                else:
                                    editor = wx.grid.GridCellTextEditor()
                                renderer = wx.grid.GridCellStringRenderer()
                            else:
                                grid.SetReadOnly(row, col, True)
                        elif colname == "Location":
                            if var_class in ["Local", "Global"] and self.Parent.Controler.IsLocatableType(var_type):
                                editor = LocationCellEditor(self, self.Parent.Controler)
                                renderer = wx.grid.GridCellStringRenderer()
                            else:
                                grid.SetReadOnly(row, col, True)
                        elif colname == "Class":
                            if len(self.Parent.ClassList) == 1 or self.Parent.PouIsUsed and var_class in ["Input", "Output", "InOut"]:
                                grid.SetReadOnly(row, col, True)
                            else:
                                editor = wx.grid.GridCellChoiceEditor()
                                excluded = []
                                if self.Parent.PouIsUsed:
                                    excluded.extend(["Input","Output","InOut"])
                                if self.Parent.IsFunctionBlockType(var_type):
                                    excluded.extend(["Local","Temp"])
                                editor.SetParameters(",".join([_(choice) for choice in self.Parent.ClassList if choice not in excluded]))
                    elif colname != "Documentation":
                        grid.SetReadOnly(row, col, True)
                
                grid.SetCellEditor(row, col, editor)
                grid.SetCellRenderer(row, col, renderer)
                
                if colname == "Location" and LOCATION_MODEL.match(self.GetValueByName(row, colname)) is None:
                    highlight_colours = ERROR_HIGHLIGHT
                else:
                    highlight_colours = row_highlights.get(colname.lower(), [(wx.WHITE, wx.BLACK)])[-1]
                grid.SetCellBackgroundColour(row, col, highlight_colours[0])
                grid.SetCellTextColour(row, col, highlight_colours[1])
            self.ResizeRow(grid, row)

#-------------------------------------------------------------------------------
#                         Variable Panel Drop Target
#-------------------------------------------------------------------------------   

class VariableDropTarget(wx.TextDropTarget):
    '''
    This allows dragging a variable location from somewhere to the Location
    column of a variable row.
    
    The drag source should be a TextDataObject containing a Python tuple like:
        ('%ID0.0.0', 'location', 'REAL')
    
    c_ext/CFileEditor.py has an example of this (you can drag a C extension
    variable to the Location column of the variable panel).
    '''
    def __init__(self, parent):
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
    
    def OnDropText(self, x, y, data):
        self.ParentWindow.ParentWindow.Select()
        x, y = self.ParentWindow.VariablesGrid.CalcUnscrolledPosition(x, y)
        col = self.ParentWindow.VariablesGrid.XToCol(x)
        row = self.ParentWindow.VariablesGrid.YToRow(y - self.ParentWindow.VariablesGrid.GetColLabelSize())
        message = None
        element_type = self.ParentWindow.ElementType
        try:
            values = eval(data)    
        except:
            message = _("Invalid value \"%s\" for variable grid element")%data
            values = None
        if not isinstance(values, TupleType):
            message = _("Invalid value \"%s\" for variable grid element")%data
            values = None
        if values is not None:
            if col != wx.NOT_FOUND and row != wx.NOT_FOUND:
                colname = self.ParentWindow.Table.GetColLabelValue(col, False)
                if colname == "Location" and values[1] == "location":
                    if not self.ParentWindow.Table.GetValueByName(row, "Edit"):
                        message = _("Can't give a location to a function block instance")
                    elif self.ParentWindow.Table.GetValueByName(row, "Class") not in ["Local", "Global"]:
                        message = _("Can only give a location to local or global variables")
                    else:
                        location = values[0]
                        variable_type = self.ParentWindow.Table.GetValueByName(row, "Type")
                        base_type = self.ParentWindow.Controler.GetBaseType(variable_type)
                        
                        if values[2] is not None:
                            base_location_type = self.ParentWindow.Controler.GetBaseType(values[2])
                            if values[2] != variable_type and base_type != base_location_type:
                                message = _("Incompatible data types between \"%s\" and \"%s\"")%(values[2], variable_type)
                        
                        if message is None:
                            if not location.startswith("%"):
                                if location[0].isdigit() and base_type != "BOOL":
                                    message = _("Incompatible size of data between \"%s\" and \"BOOL\"")%location
                                elif location[0] not in LOCATIONDATATYPES:
                                    message = _("Unrecognized data size \"%s\"")%location[0]
                                elif base_type not in LOCATIONDATATYPES[location[0]]:
                                    message = _("Incompatible size of data between \"%s\" and \"%s\"")%(location, variable_type)
                                else:
                                    dialog = wx.SingleChoiceDialog(self.ParentWindow.ParentWindow.ParentWindow, 
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
                                        
                            if message is None:
                                self.ParentWindow.Table.SetValue(row, col, location)
                                self.ParentWindow.Table.ResetView(self.ParentWindow.VariablesGrid)
                                self.ParentWindow.SaveValues()
                elif colname == "Initial Value" and values[1] == "Constant":
                    if not self.ParentWindow.Table.GetValueByName(row, "Edit"):
                        message = _("Can't set an initial value to a function block instance")
                    else:
                        self.ParentWindow.Table.SetValue(row, col, values[0])
                        self.ParentWindow.Table.ResetView(self.ParentWindow.VariablesGrid)
                        self.ParentWindow.SaveValues()
            elif (element_type not in ["config", "resource"] and values[1] == "Global" and self.ParentWindow.Filter in ["All", "Interface", "External"] or
                  element_type in ["config", "resource"] and values[1] == "location"):
                if values[1] == "location":
                    var_name = values[3]
                else:
                    var_name = values[0]
                tagname = self.ParentWindow.GetTagName()
                if var_name.upper() in [name.upper() for name in self.ParentWindow.Controler.GetProjectPouNames(self.ParentWindow.Debug)]:
                    message = _("\"%s\" pou already exists!")%var_name
                elif not var_name.upper() in [name.upper() for name in self.ParentWindow.Controler.GetEditedElementVariables(tagname, self.ParentWindow.Debug)]:
                    var_infos = self.ParentWindow.DefaultValue.copy()
                    var_infos["Name"] = var_name
                    var_infos["Type"] = values[2]
                    if values[1] == "location":
                        var_infos["Class"] = "Global"
                        var_infos["Location"] = values[0]
                    else:
                        var_infos["Class"] = "External"
                    var_infos["Number"] = len(self.ParentWindow.Values)
                    self.ParentWindow.Values.append(var_infos)
                    self.ParentWindow.SaveValues()
                    self.ParentWindow.RefreshValues()
        
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)
    
    def ShowMessage(self, message):
        message = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        message.ShowModal()
        message.Destroy()

#-------------------------------------------------------------------------------
#                               Variable Panel
#-------------------------------------------------------------------------------   

class VariablePanel(wx.Panel):
    
    def __init__(self, parent, window, controler, element_type, debug=False):
        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL)
        
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=10, rows=2, vgap=0)
        self.MainSizer.AddGrowableCol(0)
        self.MainSizer.AddGrowableRow(1)
        
        controls_sizer = wx.FlexGridSizer(cols=10, hgap=5, rows=1, vgap=5)
        controls_sizer.AddGrowableCol(5)
        controls_sizer.AddGrowableRow(0)
        self.MainSizer.AddSizer(controls_sizer, border=5, flag=wx.GROW|wx.ALL)
        
        self.ReturnTypeLabel = wx.StaticText(self, label=_('Return Type:'))
        controls_sizer.AddWindow(self.ReturnTypeLabel, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.ReturnType = wx.ComboBox(self,
              size=wx.Size(145, -1), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnReturnTypeChanged, self.ReturnType)
        controls_sizer.AddWindow(self.ReturnType)
        
        self.DescriptionLabel = wx.StaticText(self, label=_('Description:'))
        controls_sizer.AddWindow(self.DescriptionLabel, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.Description = wx.TextCtrl(self,
              size=wx.Size(250, -1), style=wx.TE_PROCESS_ENTER)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnDescriptionChanged, self.Description)
        self.Description.Bind(wx.EVT_KILL_FOCUS, self.OnDescriptionChanged)
        controls_sizer.AddWindow(self.Description) 
        
        class_filter_label = wx.StaticText(self, label=_('Class Filter:'))
        controls_sizer.AddWindow(class_filter_label, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.ClassFilter = wx.ComboBox(self, 
              size=wx.Size(145, -1), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnClassFilter, self.ClassFilter)
        controls_sizer.AddWindow(self.ClassFilter)
        
        for name, bitmap, help in [
                ("AddButton", "add_element", _("Add variable")),
                ("DeleteButton", "remove_element", _("Remove variable")),
                ("UpButton", "up", _("Move variable up")),
                ("DownButton", "down", _("Move variable down"))]:
            button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            controls_sizer.AddWindow(button)
        
        self.VariablesGrid = CustomGrid(self, style=wx.VSCROLL)
        self.VariablesGrid.SetDropTarget(VariableDropTarget(self))
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, 
              self.OnVariablesGridCellChange)
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, 
              self.OnVariablesGridCellLeftClick)
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, 
              self.OnVariablesGridEditorShown)
        self.MainSizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
        
        self.SetSizer(self.MainSizer)
        
        self.ParentWindow = window
        self.Controler = controler
        self.ElementType = element_type
        self.Debug = debug
        
        self.RefreshHighlightsTimer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnRefreshHighlightsTimer, 
              self.RefreshHighlightsTimer)
        
        self.Filter = "All"
        self.FilterChoices = []
        self.FilterChoiceTransfer = GetFilterChoiceTransfer()
        
        self.DefaultValue = {
             "Name" : "", 
             "Class" : "", 
             "Type" : "INT", 
             "Location" : "",
             "Initial Value" : "", 
             "Option" : "",
             "Documentation" : "", 
             "Edit" : True
        }

        if element_type in ["config", "resource"]:
            self.DefaultTypes = {"All" : "Global"}
        else:
            self.DefaultTypes = {"All" : "Local", "Interface" : "Input", "Variables" : "Local"}

        if element_type in ["config", "resource"] \
        or element_type in ["program", "transition", "action"]:
            # this is an element that can have located variables
            self.Table = VariableTable(self, [], GetVariableTableColnames(True))

            if element_type in ["config", "resource"]:
                self.FilterChoices = ["All", "Global"]#,"Access"]
            else:
                self.FilterChoices = ["All",
                                        "Interface", "   Input", "   Output", "   InOut", "   External",
                                        "Variables", "   Local", "   Temp"]#,"Access"]

            # these condense the ColAlignements list
            l = wx.ALIGN_LEFT
            c = wx.ALIGN_CENTER 

            #                      Num  Name    Class   Type    Loc     Init    Option   Doc
            self.ColSizes       = [40,  80,     70,     80,     80,     80,     100,     80]
            self.ColAlignements = [c,   l,      l,      l,      l,      l,      l,       l]

        else:
            # this is an element that cannot have located variables
            self.Table = VariableTable(self, [], GetVariableTableColnames(False))

            if element_type == "function":
                self.FilterChoices = ["All",
                                        "Interface", "   Input", "   Output", "   InOut",
                                        "Variables", "   Local"]
            else:
                self.FilterChoices = ["All",
                                        "Interface", "   Input", "   Output", "   InOut", "   External",
                                        "Variables", "   Local", "   Temp"]

            # these condense the ColAlignements list
            l = wx.ALIGN_LEFT
            c = wx.ALIGN_CENTER 

            #                      Num  Name    Class   Type    Init    Option   Doc
            self.ColSizes       = [40,  80,     70,     80,     80,     100,     160]
            self.ColAlignements = [c,   l,      l,      l,      l,      l,       l]

        for choice in self.FilterChoices:
            self.ClassFilter.Append(_(choice))

        reverse_transfer = {}
        for filter, choice in self.FilterChoiceTransfer.items():
            reverse_transfer[choice] = filter
        self.ClassFilter.SetStringSelection(_(reverse_transfer[self.Filter]))
        self.RefreshTypeList()

        self.VariablesGrid.SetTable(self.Table)
        self.VariablesGrid.SetButtons({"Add": self.AddButton,
                                       "Delete": self.DeleteButton,
                                       "Up": self.UpButton,
                                       "Down": self.DownButton})
        self.VariablesGrid.SetEditable(not self.Debug)
        
        def _AddVariable(new_row):
            if not self.PouIsUsed or self.Filter not in ["Interface", "Input", "Output", "InOut"]:
                row_content = self.DefaultValue.copy()
                if self.Filter in self.DefaultTypes:
                    row_content["Class"] = self.DefaultTypes[self.Filter]
                else:
                    row_content["Class"] = self.Filter
                if self.Filter == "All" and len(self.Values) > 0:
                    self.Values.insert(new_row, row_content)
                else:
                    self.Values.append(row_content)
                    new_row = self.Table.GetNumberRows()
                self.SaveValues()
                self.RefreshValues()
                return new_row
            return self.VariablesGrid.GetGridCursorRow()
        setattr(self.VariablesGrid, "_AddRow", _AddVariable)
        
        def _DeleteVariable(row):
            if (self.Table.GetValueByName(row, "Edit") and 
                (not self.PouIsUsed or self.Table.GetValueByName(row, "Class") not in ["Input", "Output", "InOut"])):
                self.Values.remove(self.Table.GetRow(row))
                self.SaveValues()
                self.RefreshValues()
        setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
            
        def _MoveVariable(row, move):
            if (self.Filter == "All" and 
                (not self.PouIsUsed or self.Table.GetValueByName(row, "Class") not in ["Input", "Output", "InOut"])):
                new_row = max(0, min(row + move, len(self.Values) - 1))
                if new_row != row:
                    self.Values.insert(new_row, self.Values.pop(row))
                    self.SaveValues()
                    self.RefreshValues()
                return new_row
            return row
        setattr(self.VariablesGrid, "_MoveRow", _MoveVariable)
        
        def _RefreshButtons():
            if self:
                table_length = len(self.Table.data)
                row_class = None
                row_edit = True
                row = 0
                if table_length > 0:
                    row = self.VariablesGrid.GetGridCursorRow()
                    row_edit = self.Table.GetValueByName(row, "Edit")
                    if self.PouIsUsed:
                        row_class = self.Table.GetValueByName(row, "Class")
                self.AddButton.Enable(not self.Debug and (not self.PouIsUsed or self.Filter not in ["Interface", "Input", "Output", "InOut"]))
                self.DeleteButton.Enable(not self.Debug and (table_length > 0 and row_edit and row_class not in ["Input", "Output", "InOut"]))
                self.UpButton.Enable(not self.Debug and (table_length > 0 and row > 0 and self.Filter == "All" and row_class not in ["Input", "Output", "InOut"]))
                self.DownButton.Enable(not self.Debug and (table_length > 0 and row < table_length - 1 and self.Filter == "All" and row_class not in ["Input", "Output", "InOut"]))
        setattr(self.VariablesGrid, "RefreshButtons", _RefreshButtons)
        
        self.VariablesGrid.SetRowLabelSize(0)
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(self.ColAlignements[col], wx.ALIGN_CENTRE)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColMinimalWidth(col, self.ColSizes[col])
            self.VariablesGrid.AutoSizeColumn(col, False)
    
    def __del__(self):
        self.RefreshHighlightsTimer.Stop()
    
    def SetTagName(self, tagname):
        self.TagName = tagname
    
    def GetTagName(self):
        return self.TagName
    
    def IsFunctionBlockType(self, name):
        bodytype = self.Controler.GetEditedElementBodyType(self.TagName)
        pouname, poutype = self.Controler.GetEditedElementType(self.TagName)
        if poutype != "function" and bodytype in ["ST", "IL"]:
            return False
        else:
            return name in self.Controler.GetFunctionBlockTypes(self.TagName)
    
    def RefreshView(self):
        self.PouNames = self.Controler.GetProjectPouNames(self.Debug)
        returnType = None
        description = None
        
        words = self.TagName.split("::")
        if self.ElementType == "config":
            self.PouIsUsed = False
            self.Values = self.Controler.GetConfigurationGlobalVars(words[1], self.Debug)
        elif self.ElementType == "resource":
            self.PouIsUsed = False
            self.Values = self.Controler.GetConfigurationResourceGlobalVars(words[1], words[2], self.Debug)
        else:
            if self.ElementType == "function":
                self.ReturnType.Clear()
                for data_type in self.Controler.GetDataTypes(self.TagName, debug=self.Debug):
                    self.ReturnType.Append(data_type)
                returnType = self.Controler.GetEditedElementInterfaceReturnType(self.TagName)
            description = self.Controler.GetPouDescription(words[1])
            self.PouIsUsed = self.Controler.PouIsUsed(words[1])
            self.Values = self.Controler.GetEditedElementInterfaceVars(self.TagName, self.Debug)
        
        if returnType is not None:
            self.ReturnType.SetStringSelection(returnType)
            self.ReturnType.Enable(not self.Debug)
            self.ReturnTypeLabel.Show()
            self.ReturnType.Show()
        else:
            self.ReturnType.Enable(False)
            self.ReturnTypeLabel.Hide()
            self.ReturnType.Hide()
        
        if description is not None:
            self.Description.SetValue(description)
            self.Description.Enable(not self.Debug)
            self.DescriptionLabel.Show()
            self.Description.Show()
        else:
            self.Description.Enable(False)
            self.DescriptionLabel.Hide()
            self.Description.Hide()
        
        self.RefreshValues()
        self.VariablesGrid.RefreshButtons()
        self.MainSizer.Layout()
    
    def OnReturnTypeChanged(self, event):
        words = self.TagName.split("::")
        self.Controler.SetPouInterfaceReturnType(words[1], self.ReturnType.GetStringSelection())
        self.Controler.BufferProject()
        self.ParentWindow.RefreshView(variablepanel = False)
        self.ParentWindow._Refresh(TITLE, FILEMENU, EDITMENU, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
        event.Skip()
    
    def OnDescriptionChanged(self, event):
        words = self.TagName.split("::")
        old_description = self.Controler.GetPouDescription(words[1])
        new_description = self.Description.GetValue()
        if new_description != old_description:
            self.Controler.SetPouDescription(words[1], new_description)
            self.ParentWindow._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
        event.Skip()
    
    def OnClassFilter(self, event):
        self.Filter = self.FilterChoiceTransfer[VARIABLE_CHOICES_DICT[self.ClassFilter.GetStringSelection()]]
        self.RefreshTypeList()
        self.RefreshValues()
        self.VariablesGrid.RefreshButtons()
        event.Skip()

    def RefreshTypeList(self):
        if self.Filter == "All":
            self.ClassList = [self.FilterChoiceTransfer[choice] for choice in self.FilterChoices if self.FilterChoiceTransfer[choice] not in ["All","Interface","Variables"]]
        elif self.Filter == "Interface":
            self.ClassList = ["Input","Output","InOut","External"]
        elif self.Filter == "Variables":
            self.ClassList = ["Local","Temp"]
        else:
            self.ClassList = [self.Filter]

    def OnVariablesGridCellChange(self, event):
        row, col = event.GetRow(), event.GetCol()
        colname = self.Table.GetColLabelValue(col, False)
        value = self.Table.GetValue(row, col)
        message = None
        
        if colname == "Name" and value != "":
            if not TestIdentifier(value):
                message = _("\"%s\" is not a valid identifier!") % value
            elif value.upper() in IEC_KEYWORDS:
                message = _("\"%s\" is a keyword. It can't be used!") % value
            elif value.upper() in self.PouNames:
                message = _("A POU named \"%s\" already exists!") % value
            elif value.upper() in [var["Name"].upper() for var in self.Values if var != self.Table.data[row]]:
                message = _("A variable with \"%s\" as name already exists in this pou!") % value
            else:
                self.SaveValues(False)
                old_value = self.Table.GetOldValue()
                if old_value != "":
                    self.Controler.UpdateEditedElementUsedVariable(self.TagName, old_value, value)
                self.Controler.BufferProject()
                wx.CallAfter(self.ParentWindow.RefreshView, False)
                self.ParentWindow._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
        else:
            self.SaveValues()
            if colname == "Class":
                wx.CallAfter(self.ParentWindow.RefreshView, False)
            elif colname == "Location":
                wx.CallAfter(self.ParentWindow.RefreshView)
            
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
            event.Veto()
        else:
            event.Skip()
    
    def OnVariablesGridEditorShown(self, event):
        row, col = event.GetRow(), event.GetCol() 

        label_value = self.Table.GetColLabelValue(col, False)
        if label_value == "Type":
            type_menu = wx.Menu(title='')   # the root menu

            # build a submenu containing standard IEC types
            base_menu = wx.Menu(title='')
            for base_type in self.Controler.GetBaseTypes():
                new_id = wx.NewId()
                AppendMenu(base_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=base_type)
                self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(base_type), id=new_id)

            type_menu.AppendMenu(wx.NewId(), _("Base Types"), base_menu)

            # build a submenu containing user-defined types
            datatype_menu = wx.Menu(title='')
            datatypes = self.Controler.GetDataTypes(basetypes = False, confnodetypes = False)
            for datatype in datatypes:
                new_id = wx.NewId()
                AppendMenu(datatype_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=datatype)
                self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(datatype), id=new_id)

            type_menu.AppendMenu(wx.NewId(), _("User Data Types"), datatype_menu)
            
            for category in self.Controler.GetConfNodeDataTypes():
               
               if len(category["list"]) > 0:
                   # build a submenu containing confnode types
                   confnode_datatype_menu = wx.Menu(title='')
                   for datatype in category["list"]:
                       new_id = wx.NewId()
                       AppendMenu(confnode_datatype_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=datatype)
                       self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(datatype), id=new_id)
                   
                   type_menu.AppendMenu(wx.NewId(), category["name"], confnode_datatype_menu)

            # build a submenu containing function block types
            bodytype = self.Controler.GetEditedElementBodyType(self.TagName)
            pouname, poutype = self.Controler.GetEditedElementType(self.TagName)
            classtype = self.Table.GetValueByName(row, "Class")
            
            new_id = wx.NewId()
            AppendMenu(type_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Array"))
            self.Bind(wx.EVT_MENU, self.VariableArrayTypeFunction, id=new_id)
            
            if classtype in ["Input", "Output", "InOut", "External", "Global"] or \
            poutype != "function" and bodytype in ["ST", "IL"]:
                functionblock_menu = wx.Menu(title='')
                fbtypes = self.Controler.GetFunctionBlockTypes(self.TagName)
                for functionblock_type in fbtypes:
                    new_id = wx.NewId()
                    AppendMenu(functionblock_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=functionblock_type)
                    self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(functionblock_type), id=new_id)

                type_menu.AppendMenu(wx.NewId(), _("Function Block Types"), functionblock_menu)

            rect = self.VariablesGrid.BlockToDeviceRect((row, col), (row, col))
            corner_x = rect.x + rect.width
            corner_y = rect.y + self.VariablesGrid.GetColLabelSize()

            # pop up this new menu
            self.VariablesGrid.PopupMenuXY(type_menu, corner_x, corner_y)
            type_menu.Destroy()
            event.Veto()
        else:
            event.Skip()
    
    def GetVariableTypeFunction(self, base_type):
        def VariableTypeFunction(event):
            row = self.VariablesGrid.GetGridCursorRow()
            self.Table.SetValueByName(row, "Type", base_type)
            self.Table.ResetView(self.VariablesGrid)
            self.SaveValues(False)
            self.ParentWindow.RefreshView(variablepanel = False)
            self.Controler.BufferProject()
            self.ParentWindow._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
        return VariableTypeFunction
    
    def VariableArrayTypeFunction(self, event):
        row = self.VariablesGrid.GetGridCursorRow()
        dialog = ArrayTypeDialog(self, 
                                 self.Controler.GetDataTypes(self.TagName), 
                                 self.Table.GetValueByName(row, "Type"))
        if dialog.ShowModal() == wx.ID_OK:
            self.Table.SetValueByName(row, "Type", dialog.GetValue())
            self.Table.ResetView(self.VariablesGrid)
            self.SaveValues(False)
            self.ParentWindow.RefreshView(variablepanel = False)
            self.Controler.BufferProject()
            self.ParentWindow._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)
        dialog.Destroy()
    
    def OnVariablesGridCellLeftClick(self, event):
        row = event.GetRow()
        if not self.Debug and (event.GetCol() == 0 and self.Table.GetValueByName(row, "Edit")):
            var_name = self.Table.GetValueByName(row, "Name")
            var_class = self.Table.GetValueByName(row, "Class")
            var_type = self.Table.GetValueByName(row, "Type")
            data = wx.TextDataObject(str((var_name, var_class, var_type, self.TagName)))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        event.Skip()
    
    def RefreshValues(self):
        data = []
        for num, variable in enumerate(self.Values):
            if variable["Class"] in self.ClassList:
                variable["Number"] = num + 1
                data.append(variable)
        self.Table.SetData(data)
        self.Table.ResetView(self.VariablesGrid)
            
    def SaveValues(self, buffer = True):
        words = self.TagName.split("::")
        if self.ElementType == "config":
            self.Controler.SetConfigurationGlobalVars(words[1], self.Values)
        elif self.ElementType == "resource":
            self.Controler.SetConfigurationResourceGlobalVars(words[1], words[2], self.Values)
        else:
            if self.ReturnType.IsEnabled():
                self.Controler.SetPouInterfaceReturnType(words[1], self.ReturnType.GetStringSelection())
            self.Controler.SetPouInterfaceVars(words[1], self.Values)
        if buffer:
            self.Controler.BufferProject()
            self.ParentWindow._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES, POUINSTANCEVARIABLESPANEL, LIBRARYTREE)            

#-------------------------------------------------------------------------------
#                        Highlights showing functions
#-------------------------------------------------------------------------------

    def OnRefreshHighlightsTimer(self, event):
        self.Table.ResetView(self.VariablesGrid)
        event.Skip()

    def AddVariableHighlight(self, infos, highlight_type):
        if isinstance(infos[0], TupleType):
            for i in xrange(*infos[0]):
                self.Table.AddHighlight((i,) + infos[1:], highlight_type)
            cell_visible = infos[0][0]
        else:
            self.Table.AddHighlight(infos, highlight_type)
            cell_visible = infos[0]
        colnames = [colname.lower() for colname in self.Table.colnames]
        self.VariablesGrid.MakeCellVisible(cell_visible, colnames.index(infos[1]))
        self.RefreshHighlightsTimer.Start(int(REFRESH_HIGHLIGHT_PERIOD * 1000), oneShot=True)

    def RemoveVariableHighlight(self, infos, highlight_type):
        if isinstance(infos[0], TupleType):
            for i in xrange(*infos[0]):
                self.Table.RemoveHighlight((i,) + infos[1:], highlight_type)
        else:
            self.Table.RemoveHighlight(infos, highlight_type)
        self.RefreshHighlightsTimer.Start(int(REFRESH_HIGHLIGHT_PERIOD * 1000), oneShot=True)

    def ClearHighlights(self, highlight_type=None):
        self.Table.ClearHighlights(highlight_type)
        self.Table.ResetView(self.VariablesGrid)
