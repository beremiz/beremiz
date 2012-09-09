#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2012: Edouard TISSERANT and Laurent BESSARD
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

from types import TupleType

import wx
import wx.lib.buttons

from graphics import DebugDataConsumer, DebugViewer
from controls import CustomGrid, CustomTable
from dialogs.ForceVariableDialog import ForceVariableDialog
from util.BitmapLibrary import GetBitmap

def AppendMenu(parent, help, id, kind, text):
    parent.Append(help=help, id=id, kind=kind, text=text)

def GetDebugVariablesTableColnames():
    _ = lambda x : x
    return [_("Variable"), _("Value")]

class VariableTableItem(DebugDataConsumer):
    
    def __init__(self, parent, variable, value):
        DebugDataConsumer.__init__(self)
        self.Parent = parent
        self.Variable = variable
        self.Value = value
    
    def __del__(self):
        self.Parent = None
    
    def SetVariable(self, variable):
        if self.Parent and self.Variable != variable:
            self.Variable = variable
            self.Parent.RefreshGrid()
    
    def GetVariable(self):
        return self.Variable
    
    def SetForced(self, forced):
        if self.Forced != forced:
            self.Forced = forced
            self.Parent.HasNewData = True
    
    def SetValue(self, value):
        if self.Value != value:
            self.Value = value
            self.Parent.HasNewData = True
            
    def GetValue(self):
        return self.Value

class DebugVariableTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            return self.GetValueByName(row, self.GetColLabelValue(col, False))
        return ""
    
    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            self.SetValueByName(row, self.GetColLabelValue(col, False), value)
            
    def GetValueByName(self, row, colname):
        if row < self.GetNumberRows():
            if colname == "Variable":
                return self.data[row].GetVariable()
            elif colname == "Value":
                return self.data[row].GetValue()
        return ""

    def SetValueByName(self, row, colname, value):
        if row < self.GetNumberRows():
            if colname == "Variable":
                self.data[row].SetVariable(value)
            elif colname == "Value":
                self.data[row].SetValue(value)
    
    def IsForced(self, row):
        if row < self.GetNumberRows():
            return self.data[row].IsForced()
        return False
    
    def _updateColAttrs(self, grid):
        """
        wx.grid.Grid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                if self.GetColLabelValue(col, False) == "Value":
                    if self.IsForced(row):
                        grid.SetCellTextColour(row, col, wx.BLUE)
                    else:
                        grid.SetCellTextColour(row, col, wx.BLACK)
                grid.SetReadOnly(row, col, True)
            self.ResizeRow(grid, row)
                
    def AppendItem(self, data):
        self.data.append(data)
    
    def InsertItem(self, idx, data):
        self.data.insert(idx, data)
    
    def RemoveItem(self, idx):
        self.data.pop(idx)
    
    def MoveItem(self, idx, new_idx):
        self.data.insert(new_idx, self.data.pop(idx))
        
    def GetItem(self, idx):
        return self.data[idx]

class DebugVariableDropTarget(wx.TextDropTarget):
    
    def __init__(self, parent):
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
    
    def OnDropText(self, x, y, data):
        x, y = self.ParentWindow.VariablesGrid.CalcUnscrolledPosition(x, y)
        row = self.ParentWindow.VariablesGrid.YToRow(y - self.ParentWindow.VariablesGrid.GetColLabelSize())
        if row == wx.NOT_FOUND:
            row = self.ParentWindow.Table.GetNumberRows()
        message = None
        try:
            values = eval(data)
        except:
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        if not isinstance(values, TupleType):
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        if values is not None and values[1] == "debug":
            self.ParentWindow.InsertValue(values[0], row)
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)
            
    def ShowMessage(self, message):
        dialog = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()

class DebugVariablePanel(wx.Panel, DebugViewer):
    
    def __init__(self, parent, producer):
        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL)
        DebugViewer.__init__(self, producer, True)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(button_sizer, border=5, 
              flag=wx.ALIGN_RIGHT|wx.ALL)
        
        for name, bitmap, help in [
                ("DeleteButton", "remove_element", _("Remove debug variable")),
                ("UpButton", "up", _("Move debug variable up")),
                ("DownButton", "down", _("Move debug variable down"))]:
            button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
        
        self.VariablesGrid = CustomGrid(self, size=wx.Size(0, 150), style=wx.VSCROLL)
        self.VariablesGrid.SetDropTarget(DebugVariableDropTarget(self))
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, 
              self.OnVariablesGridCellRightClick)
        main_sizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
        
        self.SetSizer(main_sizer)
        
        self.HasNewData = False
        
        self.Table = DebugVariableTable(self, [], GetDebugVariablesTableColnames())
        self.VariablesGrid.SetTable(self.Table)
        self.VariablesGrid.SetButtons({"Delete": self.DeleteButton,
                                       "Up": self.UpButton,
                                       "Down": self.DownButton})
        
        def _AddVariable(new_row):
            return self.VariablesGrid.GetGridCursorRow()
        setattr(self.VariablesGrid, "_AddRow", _AddVariable)
        
        def _DeleteVariable(row):
            item = self.Table.GetItem(row)
            self.RemoveDataConsumer(item)
            self.Table.RemoveItem(row)
            self.RefreshGrid()
        setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
        
        def _MoveVariable(row, move):
            new_row = max(0, min(row + move, self.Table.GetNumberRows() - 1))
            if new_row != row:
                self.Table.MoveItem(row, new_row)
                self.RefreshGrid()
            return new_row
        setattr(self.VariablesGrid, "_MoveRow", _MoveVariable)
        
        self.VariablesGrid.SetRowLabelSize(0)
        
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColSize(col, 100)
        
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
    
    def RefreshNewData(self):
        if self.HasNewData:
            self.HasNewData = False
            self.RefreshGrid()
        DebugViewer.RefreshNewData(self)
    
    def RefreshGrid(self):
        self.Freeze()
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        self.Thaw()
    
    def UnregisterObsoleteData(self):
        items = [(idx, item) for idx, item in enumerate(self.Table.GetData())]
        items.reverse()
        for idx, item in items:
            iec_path = item.GetVariable().upper()
            if self.GetDataType(iec_path) is None:
                self.RemoveDataConsumer(item)
                self.Table.RemoveItem(idx)
            else:
                self.AddDataConsumer(iec_path, item)
        self.Freeze()
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        self.Thaw()
    
    def ResetGrid(self):
        self.DeleteDataConsumers()
        self.Table.Empty()
        self.Freeze()
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        self.Thaw()
    
    def GetForceVariableMenuFunction(self, iec_path, item):
        iec_type = self.GetDataType(iec_path)
        def ForceVariableFunction(event):
            if iec_type is not None:
                dialog = ForceVariableDialog(self, iec_type, str(item.GetValue()))
                if dialog.ShowModal() == wx.ID_OK:
                    self.ForceDataValue(iec_path, dialog.GetValue())
        return ForceVariableFunction

    def GetReleaseVariableMenuFunction(self, iec_path):
        def ReleaseVariableFunction(event):
            self.ReleaseDataValue(iec_path)
        return ReleaseVariableFunction
    
    def OnVariablesGridCellRightClick(self, event):
        row, col = event.GetRow(), event.GetCol()
        if self.Table.GetColLabelValue(col, False) == "Value":
            iec_path = self.Table.GetValueByName(row, "Variable").upper()

            menu = wx.Menu(title='')
            
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Force value"))
            self.Bind(wx.EVT_MENU, self.GetForceVariableMenuFunction(iec_path.upper(), self.Table.GetItem(row)), id=new_id)
            
            new_id = wx.NewId()
            AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("Release value"))
            self.Bind(wx.EVT_MENU, self.GetReleaseVariableMenuFunction(iec_path.upper()), id=new_id)
            
            if self.Table.IsForced(row):
                menu.Enable(new_id, True)
            else:
                menu.Enable(new_id, False)
            
            self.PopupMenu(menu)
            
            menu.Destroy()
        event.Skip()
    
    def InsertValue(self, iec_path, idx = None, force=False):
        if idx is None:
            idx = self.Table.GetNumberRows()
        for item in self.Table.GetData():
            if iec_path == item.GetVariable():
                return
        item = VariableTableItem(self, iec_path, "")
        result = self.AddDataConsumer(iec_path.upper(), item)
        if result is not None or force:
            self.Table.InsertItem(idx, item)
            self.RefreshGrid()
        
    def GetDebugVariables(self):
        return [item.GetVariable() for item in self.Table.GetData()]
