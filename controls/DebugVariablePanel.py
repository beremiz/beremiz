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

from types import TupleType, FloatType
from time import time as gettime
import numpy

import wx
import wx.lib.buttons
import matplotlib
matplotlib.use('WX')
import matplotlib.pyplot
from matplotlib.backends.backend_wx import FigureCanvasWx as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D

from graphics import DebugDataConsumer, DebugViewer, REFRESH_PERIOD
from controls import CustomGrid, CustomTable
from dialogs.ForceVariableDialog import ForceVariableDialog
from util.BitmapLibrary import GetBitmap

def AppendMenu(parent, help, id, kind, text):
    parent.Append(help=help, id=id, kind=kind, text=text)

def GetDebugVariablesTableColnames():
    _ = lambda x : x
    return [_("Variable"), _("Value"), _("3DAxis")]

class VariableTableItem(DebugDataConsumer):
    
    def __init__(self, parent, variable):
        DebugDataConsumer.__init__(self)
        self.Parent = parent
        self.Variable = variable
        self.RefreshVariableType()
        self.Value = ""
        self.Axis3D = False
    
    def __del__(self):
        self.Parent = None
    
    def SetVariable(self, variable):
        if self.Parent and self.Variable != variable:
            self.Variable = variable
            self.RefreshVariableType()
            self.Parent.RefreshGrid()
    
    def GetVariable(self):
        return self.Variable
    
    def RefreshVariableType(self):
        self.VariableType = self.Parent.GetDataType(self.Variable)
        self.ResetData()
    
    def GetVariableType(self):
        return self.VariableType
    
    def GetData(self):
        return self.Data
    
    def ResetData(self):
        if self.IsNumVariable():
            self.Data = numpy.array([]).reshape(0, 2)
        else:
            self.Data = None
    
    def IsNumVariable(self):
        return self.Parent.IsNumType(self.VariableType)
    
    def NewValue(self, tick, value, forced=False):
        if self.IsNumVariable():
            value = {True:1., False:0.}.get(value, float(value))
            self.Data = numpy.append(self.Data, [[float(tick), value]], axis=0)
            self.Parent.HasNewData = True
        DebugDataConsumer.NewValue(self, tick, value, forced)
    
    def SetForced(self, forced):
        if self.Forced != forced:
            self.Forced = forced
            self.Parent.HasNewData = True
    
    def SetValue(self, value):
        if self.Value != value:
            self.Value = value
            self.Parent.HasNewData = True
            
    def GetValue(self):
        if self.VariableType == "STRING":
            return "'%s'" % self.Value
        elif self.VariableType == "WSTRING":
            return "\"%s\"" % self.Value
        elif isinstance(self.Value, FloatType):
            return "%.6g" % self.Value
        return self.Value

    def SetAxis3D(self, axis_3d):
        if self.IsNumVariable():
            self.Axis3D = axis_3d
        
    def GetAxis3D(self):
        if self.IsNumVariable():
            return self.Axis3D
        return ""

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
            elif colname == "3DAxis":
                return self.data[row].GetAxis3D()
        return ""

    def SetValueByName(self, row, colname, value):
        if row < self.GetNumberRows():
            if colname == "Variable":
                self.data[row].SetVariable(value)
            elif colname == "Value":
                self.data[row].SetValue(value)
            elif colname == "3DAxis":
                self.data[row].SetAxis3D(value)
    
    def IsForced(self, row):
        if row < self.GetNumberRows():
            return self.data[row].IsForced()
        return False
    
    def IsNumVariable(self, row):
        if row < self.GetNumberRows():
            return self.data[row].IsNumVariable()
        return False
    
    def _updateColAttrs(self, grid):
        """
        wx.grid.Grid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                colname = self.GetColLabelValue(col, False)
                if colname == "3DAxis":
                    if self.IsNumVariable(row):
                        grid.SetCellRenderer(row, col, wx.grid.GridCellBoolRenderer())
                        grid.SetCellEditor(row, col, wx.grid.GridCellBoolEditor())
                        grid.SetReadOnly(row, col, False)
                    else:
                        grid.SetReadOnly(row, col, True)
                else:
                    if colname == "Value":
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

SCROLLBAR_UNIT = 10

class DebugVariablePanel(wx.SplitterWindow, DebugViewer):
    
    def __init__(self, parent, producer):
        wx.SplitterWindow.__init__(self, parent, style=wx.SP_3D)
        DebugViewer.__init__(self, producer, True)
        
        self.SetSashGravity(0.5)
        self.SetNeedUpdating(True)
        self.SetMinimumPaneSize(1)
        
        self.MainPanel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        
        main_panel_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        main_panel_sizer.AddGrowableCol(0)
        main_panel_sizer.AddGrowableRow(1)
        
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_panel_sizer.AddSizer(button_sizer, border=5, 
              flag=wx.ALIGN_RIGHT|wx.ALL)
        
        for name, bitmap, help in [
                ("DeleteButton", "remove_element", _("Remove debug variable")),
                ("UpButton", "up", _("Move debug variable up")),
                ("DownButton", "down", _("Move debug variable down"))]:
            button = wx.lib.buttons.GenBitmapButton(self.MainPanel, bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
        
        self.VariablesGrid = CustomGrid(self.MainPanel, size=wx.Size(-1, 150), style=wx.VSCROLL)
        self.VariablesGrid.SetDropTarget(DebugVariableDropTarget(self))
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, 
              self.OnVariablesGridCellRightClick)
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, 
              self.OnVariablesGridCellChange)
        main_panel_sizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
        
        self.MainPanel.SetSizer(main_panel_sizer)
        
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
            self.ResetGraphics()
            self.RefreshGrid()
        setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
        
        def _MoveVariable(row, move):
            new_row = max(0, min(row + move, self.Table.GetNumberRows() - 1))
            if new_row != row:
                self.Table.MoveItem(row, new_row)
                self.ResetGraphics()
                self.RefreshGrid()
            return new_row
        setattr(self.VariablesGrid, "_MoveRow", _MoveVariable)
        
        self.VariablesGrid.SetRowLabelSize(0)
        
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            if self.Table.GetColLabelValue(col, False) == "3DAxis":
                attr.SetAlignment(wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            else:
                attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColSize(col, 100)
        
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        
        self.GraphicsPanel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
        
        graphics_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.GraphicsCanvasWindow = wx.ScrolledWindow(self.GraphicsPanel, style=wx.HSCROLL|wx.VSCROLL)
        self.GraphicsCanvasWindow.Bind(wx.EVT_SIZE, self.OnGraphicsCanvasWindowResize)
        graphics_panel_sizer.AddWindow(self.GraphicsCanvasWindow, 1, flag=wx.GROW)
        
        graphics_canvas_window_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.GraphicsFigure = matplotlib.figure.Figure()
        self.GraphicsFigure.subplots_adjust(hspace=0)
        self.GraphicsAxes = []
        
        self.GraphicsCanvas = FigureCanvas(self.GraphicsCanvasWindow, -1, self.GraphicsFigure)
        graphics_canvas_window_sizer.AddWindow(self.GraphicsCanvas, 1, flag=wx.GROW)
        
        self.GraphicsCanvasWindow.SetSizer(graphics_canvas_window_sizer)
        
        self.Graphics3DFigure = matplotlib.figure.Figure()
        self.Graphics3DFigure.subplotpars.update(left=0.0, right=1.0, bottom=0.0, top=1.0)
        
        self.LastMotionTime = gettime()
        self.Graphics3DAxes = self.Graphics3DFigure.gca(projection='3d')
        self.Graphics3DAxes.set_color_cycle(['b'])
        setattr(self.Graphics3DAxes, "_on_move", self.OnGraphics3DMotion)
        
        self.Graphics3DCanvas = FigureCanvas(self.GraphicsPanel, -1, self.Graphics3DFigure)
        self.Graphics3DCanvas.SetMinSize(wx.Size(0, 0))
        graphics_panel_sizer.AddWindow(self.Graphics3DCanvas, 1, flag=wx.GROW)
        
        self.Graphics3DAxes.mouse_init()
        
        self.GraphicsPanel.SetSizer(graphics_panel_sizer)
        
        self.SplitHorizontally(self.MainPanel, self.GraphicsPanel, -200)
        
        self.ResetGraphics()
    
    def RefreshNewData(self):
        if self.HasNewData:
            self.HasNewData = False
            self.RefreshGrid(only_values=True)
        DebugViewer.RefreshNewData(self)
    
    def RefreshGrid(self, only_values=False):
        self.Freeze()
        if only_values:
            for col in xrange(self.Table.GetNumberCols()):
                if self.Table.GetColLabelValue(col, False) == "Value":
                    for row in xrange(self.Table.GetNumberRows()):
                        self.VariablesGrid.SetCellValue(row, col, str(self.Table.GetValueByName(row, "Value")))
        else:
            self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        
        # Refresh graphics
        idx = 0
        for item in self.Table.GetData():
            data = item.GetData()
            if data is not None:
                self.GraphicsAxes[idx].clear()
                self.GraphicsAxes[idx].plot(data[:, 0], data[:, 1])
                idx += 1
        self.GraphicsCanvas.draw()
                
        # Refresh 3D graphics
        while len(self.Graphics3DAxes.lines) > 0:
            self.Graphics3DAxes.lines.pop()
        if self.Axis3DValues is not None:
            self.Graphics3DAxes.plot(
                self.Axis3DValues[0][1].GetData()[self.Axis3DValues[0][0]:, 1],
                self.Axis3DValues[1][1].GetData()[self.Axis3DValues[1][0]:, 1],
                zs = self.Axis3DValues[2][1].GetData()[self.Axis3DValues[2][0]:, 1])
        self.Graphics3DCanvas.draw()
        
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
                item.RefreshVariableType()
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
        self.ResetGraphics()
    
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
    
    def OnVariablesGridCellChange(self, event):
        row, col = event.GetRow(), event.GetCol()
        if self.Table.GetColLabelValue(col, False) == "3DAxis":
            wx.CallAfter(self.Reset3DGraphics)
        event.Skip()
    
    def InsertValue(self, iec_path, idx = None, force=False, axis3D=False):
        if idx is None:
            idx = self.Table.GetNumberRows()
        for item in self.Table.GetData():
            if iec_path == item.GetVariable():
                return
        item = VariableTableItem(self, iec_path)
        result = self.AddDataConsumer(iec_path.upper(), item)
        if result is not None or force:
            self.Table.InsertItem(idx, item)
            item.SetAxis3D(int(axis3D))
            self.ResetGraphics()
            self.RefreshGrid()
            
    def GetDebugVariables(self):
        return [item.GetVariable() for item in self.Table.GetData()]
    
    def GetAxis3D(self):
        return [item.GetVariable() for item in self.Table.GetData() if item.GetAxis3D()]
    
    def ResetGraphicsValues(self):
        for item in self.Table.GetData():
            item.ResetData()
    
    def ResetGraphics(self):
        self.GraphicsFigure.clear()
        self.GraphicsAxes = []
        
        axes_num = 0
        for item in self.Table.GetData():    
            if item.IsNumVariable():
                axes_num += 1
        
        for idx in xrange(axes_num):
            if idx == 0:
                axes = self.GraphicsFigure.add_subplot(axes_num, 1, idx + 1)
            else:
                axes = self.GraphicsFigure.add_subplot(axes_num, 1, idx + 1, sharex=self.GraphicsAxes[0])
            self.GraphicsAxes.append(axes)
        
        self.RefreshGraphicsCanvasWindowScrollbars()
        self.GraphicsCanvas.draw()
        
        self.Reset3DGraphics()
    
    def Reset3DGraphics(self):
        axis = [item for item in self.Table.GetData() if item.GetAxis3D()]
        if len(axis) == 3:
            max_tick = None
            xaxis, yaxis, zaxis = [item.GetData() for item in axis]
            if len(xaxis) > 0 and len(yaxis) > 0 and len(zaxis) > 0:
                max_tick = max(xaxis[0, 0], yaxis[0, 0], zaxis[0, 0])
            if max_tick is not None:
                self.Axis3DValues = [(numpy.argmin(abs(item.GetData()[:, 0] - max_tick)), item)
                                     for item in axis]
            else:
               self.Axis3DValues = [(0, item) for item in axis]
        else:
            self.Axis3DValues = None
    
    def OnGraphics3DMotion(self, event):
        current_time = gettime()
        if current_time - self.LastMotionTime > REFRESH_PERIOD:
            self.LastMotionTime = current_time
            Axes3D._on_move(self.Graphics3DAxes, event)

    def RefreshGraphicsCanvasWindowScrollbars(self):
        xstart, ystart = self.GraphicsCanvasWindow.GetViewStart()
        window_size = self.GraphicsCanvasWindow.GetClientSize()
        vwidth, vheight = (window_size[0], (len(self.GraphicsAxes) + 1) * 50)
        self.GraphicsCanvas.SetMinSize(wx.Size(vwidth, vheight))
        posx = max(0, min(xstart, (vwidth - window_size[0]) / SCROLLBAR_UNIT))
        posy = max(0, min(ystart, (vheight - window_size[1]) / SCROLLBAR_UNIT))
        self.GraphicsCanvasWindow.Scroll(posx, posy)
        self.GraphicsCanvasWindow.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                vwidth / SCROLLBAR_UNIT, vheight / SCROLLBAR_UNIT, posx, posy)
    
    def OnGraphicsCanvasWindowResize(self, event):
        self.RefreshGraphicsCanvasWindowScrollbars()
        event.Skip()
