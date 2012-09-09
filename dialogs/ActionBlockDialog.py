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

import wx
import wx.grid
import wx.lib.buttons

from controls import CustomGrid, CustomTable
from util.BitmapLibrary import GetBitmap

#-------------------------------------------------------------------------------
#                                  Helpers
#-------------------------------------------------------------------------------

def GetActionTableColnames():
    _ = lambda x: x
    return [_("Qualifier"), _("Duration"), _("Type"), _("Value"), _("Indicator")]

def GetTypeList():
    _ = lambda x: x
    return [_("Action"), _("Variable"), _("Inline")]

#-------------------------------------------------------------------------------
#                               Action Table
#-------------------------------------------------------------------------------

class ActionTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            colname = self.GetColLabelValue(col, False)
            name = str(self.data[row].get(colname, ""))
            if colname == "Type":
                return _(name)
            return name
    
    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            colname = self.GetColLabelValue(col, False)
            if colname == "Type":
                value = self.Parent.TranslateType[value]
            self.data[row][colname] = value
        
    def _updateColAttrs(self, grid):
        """
        wx.Grid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                editor = None
                renderer = None
                readonly = False
                colname = self.GetColLabelValue(col, False)
                if colname == "Qualifier":
                    editor = wx.grid.GridCellChoiceEditor()
                    editor.SetParameters(self.Parent.QualifierList)
                if colname == "Duration":
                    editor = wx.grid.GridCellTextEditor()
                    renderer = wx.grid.GridCellStringRenderer()
                    if self.Parent.DurationList[self.data[row]["Qualifier"]]:
                        readonly = False
                    else:
                        readonly = True
                        self.data[row]["Duration"] = ""
                elif colname == "Type":
                    editor = wx.grid.GridCellChoiceEditor()
                    editor.SetParameters(self.Parent.TypeList)
                elif colname == "Value":
                    type = self.data[row]["Type"]
                    if type == "Action":
                        editor = wx.grid.GridCellChoiceEditor()
                        editor.SetParameters(self.Parent.ActionList)
                    elif type == "Variable":
                        editor = wx.grid.GridCellChoiceEditor()
                        editor.SetParameters(self.Parent.VariableList)
                    elif type == "Inline":
                        editor = wx.grid.GridCellTextEditor()
                        renderer = wx.grid.GridCellStringRenderer()
                elif colname == "Indicator":
                    editor = wx.grid.GridCellChoiceEditor()
                    editor.SetParameters(self.Parent.VariableList)
                    
                grid.SetCellEditor(row, col, editor)
                grid.SetCellRenderer(row, col, renderer)
                grid.SetReadOnly(row, col, readonly)
                
                grid.SetCellBackgroundColour(row, col, wx.WHITE)
            self.ResizeRow(grid, row)

#-------------------------------------------------------------------------------
#                            Action Block Dialog
#-------------------------------------------------------------------------------

class ActionBlockDialog(wx.Dialog):
    
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent,
              size=wx.Size(500, 300), title=_('Edit action block properties'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        top_sizer = wx.FlexGridSizer(cols=5, hgap=5, rows=1, vgap=0)
        top_sizer.AddGrowableCol(0)
        top_sizer.AddGrowableRow(0)
        main_sizer.AddSizer(top_sizer, border=20,
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        actions_label = wx.StaticText(self, label=_('Actions:'))
        top_sizer.AddWindow(actions_label, flag=wx.ALIGN_BOTTOM)
        
        for name, bitmap, help in [
                ("AddButton", "add_element", _("Add action")),
                ("DeleteButton", "remove_element", _("Remove action")),
                ("UpButton", "up", _("Move action up")),
                ("DownButton", "down", _("Move action down"))]:
            button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            top_sizer.AddWindow(button)
        
        self.ActionsGrid = CustomGrid(self, size=wx.Size(0, 0), style=wx.VSCROLL)
        self.ActionsGrid.DisableDragGridSize()
        self.ActionsGrid.EnableScrolling(False, True)
        self.ActionsGrid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, 
                              self.OnActionsGridCellChange)
        main_sizer.AddSizer(self.ActionsGrid, border=20,
              flag=wx.GROW|wx.LEFT|wx.RIGHT)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Table = ActionTable(self, [], GetActionTableColnames())
        typelist = GetTypeList()       
        self.TypeList = ",".join(map(_,typelist))
        self.TranslateType = dict([(_(value), value) for value in typelist])
        self.ColSizes = [60, 90, 80, 110, 80]
        self.ColAlignements = [wx.ALIGN_LEFT, wx.ALIGN_LEFT, wx.ALIGN_LEFT, wx.ALIGN_LEFT, wx.ALIGN_LEFT]
        
        self.ActionsGrid.SetTable(self.Table)
        self.ActionsGrid.SetDefaultValue({"Qualifier" : "N", 
                                          "Duration" : "", 
                                          "Type" : "Action", 
                                          "Value" : "", 
                                          "Indicator" : ""})
        self.ActionsGrid.SetButtons({"Add": self.AddButton,
                                     "Delete": self.DeleteButton,
                                     "Up": self.UpButton,
                                     "Down": self.DownButton})
        self.ActionsGrid.SetRowLabelSize(0)
        
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(self.ColAlignements[col], wx.ALIGN_CENTRE)
            self.ActionsGrid.SetColAttr(col, attr)
            self.ActionsGrid.SetColMinimalWidth(col, self.ColSizes[col])
            self.ActionsGrid.AutoSizeColumn(col, False)
        
        self.Table.ResetView(self.ActionsGrid)
        self.ActionsGrid.SetFocus()
        self.ActionsGrid.RefreshButtons()
    
    def OnOK(self, event):
        self.ActionsGrid.CloseEditControl()
        self.EndModal(wx.ID_OK)

    def OnActionsGridCellChange(self, event):
        wx.CallAfter(self.Table.ResetView, self.ActionsGrid)
        event.Skip()
    
    def SetQualifierList(self, list):
        self.QualifierList = "," + ",".join(list)
        self.DurationList = list

    def SetVariableList(self, list):
        self.VariableList = "," + ",".join([variable["Name"] for variable in list])
        
    def SetActionList(self, list):
        self.ActionList = "," + ",".join(list)

    def SetValues(self, actions):
        for action in actions:
            row = {"Qualifier" : action["qualifier"], "Value" : action["value"]}
            if action["type"] == "reference":
                if action["value"] in self.ActionList:
                    row["Type"] = "Action"
                elif action["value"] in self.VariableList:
                    row["Type"] = "Variable"
                else:
                    row["Type"] = "Inline"
            else:
                row["Type"] = "Inline"
            if "duration" in action:
                row["Duration"] = action["duration"]
            else:
                row["Duration"] = ""
            if "indicator" in action:
                row["Indicator"] = action["indicator"]
            else:
                row["Indicator"] = ""
            self.Table.AppendRow(row)
        self.Table.ResetView(self.ActionsGrid)
        if len(actions) > 0:
            self.ActionsGrid.SetGridCursor(0, 0)
        self.ActionsGrid.RefreshButtons()
    
    def GetValues(self):
        values = []
        for data in self.Table.GetData():
            action = {"qualifier" : data["Qualifier"], "value" : data["Value"]}
            if data["Type"] in ["Action", "Variable"]:
                action["type"] = "reference"
            else:
                action["type"] = "inline"
            if data["Duration"] != "":
                action["duration"] = data["Duration"]
            if data["Indicator"] != "":
                action["indicator"] = data["Indicator"]
            values.append(action)
        return values
