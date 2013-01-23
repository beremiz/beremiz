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
import math
import numpy

import wx
import wx.lib.buttons

try:
    import matplotlib
    matplotlib.use('WX')
    import matplotlib.pyplot
    from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
    #from matplotlib.backends.backend_wx import FigureCanvasWx as FigureCanvas
    from mpl_toolkits.mplot3d import Axes3D
    USE_MPL = True
except:
    USE_MPL = False

from graphics import DebugDataConsumer, DebugViewer, REFRESH_PERIOD
from controls import CustomGrid, CustomTable
from dialogs.ForceVariableDialog import ForceVariableDialog
from util.BitmapLibrary import GetBitmap

SECOND = 1000000000
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

ZOOM_VALUES = map(lambda x:("x %.1f" % x, x), [math.sqrt(2) ** i for i in xrange(8)])
RANGE_VALUES = map(lambda x: (str(x), x), [25 * 2 ** i for i in xrange(6)])
TIME_RANGE_VALUES = [("%ds" % i, i * SECOND) for i in (1, 2, 5, 10, 20, 30)] + \
                    [("%dm" % i, i * MINUTE) for i in (1, 2, 5, 10, 20, 30)] + \
                    [("%dh" % i, i * HOUR) for i in (1, 2, 3, 6, 12, 24)]

GRAPH_PARALLEL, GRAPH_ORTHOGONAL = range(2)

def AppendMenu(parent, help, id, kind, text):
    parent.Append(help=help, id=id, kind=kind, text=text)

def GetDebugVariablesTableColnames():
    _ = lambda x : x
    return [_("Variable"), _("Value")]
    
class VariableTableItem(DebugDataConsumer):
    
    def __init__(self, parent, variable):
        DebugDataConsumer.__init__(self)
        self.Parent = parent
        self.Variable = variable
        self.RefreshVariableType()
        self.Value = ""
        
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
    
    def GetData(self, start_tick=None, end_tick=None):
        if self.IsNumVariable():
            if len(self.Data) == 0:
                return self.Data
            
            start_idx = end_idx = None
            if start_tick is not None:
                start_idx = self.GetNearestData(start_tick, -1)
            if end_tick is not None:
                end_idx = self.GetNearestData(end_tick, 1)
            if start_idx is None:
                start_idx = 0
            if end_idx is not None:
                return self.Data[start_idx:end_idx + 1]
            else:
                return self.Data[start_idx:]
            
        return None
    
    def GetRange(self):
        return self.MinValue, self.MaxValue
    
    def ResetData(self):
        if self.IsNumVariable():
            self.Data = numpy.array([]).reshape(0, 2)
            self.MinValue = None
            self.MaxValue = None
        else:
            self.Data = None
    
    def IsNumVariable(self):
        return self.Parent.IsNumType(self.VariableType)
    
    def NewValue(self, tick, value, forced=False):
        if self.IsNumVariable():
            num_value = {True:1., False:0.}.get(value, float(value))
            if self.MinValue is None:
                self.MinValue = num_value
            else:
                self.MinValue = min(self.MinValue, num_value)
            if self.MaxValue is None:
                self.MaxValue = num_value
            else:
                self.MaxValue = max(self.MaxValue, num_value)
            self.Data = numpy.append(self.Data, [[float(tick), num_value]], axis=0)
            self.Parent.HasNewData = True
        DebugDataConsumer.NewValue(self, tick, value, forced)
    
    def SetForced(self, forced):
        if self.Forced != forced:
            self.Forced = forced
            self.Parent.HasNewData = True
    
    def SetValue(self, value):
        if (self.VariableType == "STRING" and value.startswith("'") and value.endswith("'") or
            self.VariableType == "WSTRING" and value.startswith('"') and value.endswith('"')):
            value = value[1:-1]
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

    def GetNearestData(self, tick, adjust):
        if self.IsNumVariable():
            ticks = self.Data[:, 0]
            new_cursor = numpy.argmin(abs(ticks - tick))
            if adjust == -1 and ticks[new_cursor] > tick and new_cursor > 0:
                new_cursor -= 1
            elif adjust == 1 and ticks[new_cursor] < tick and new_cursor < len(ticks):
                new_cursor += 1
            return new_cursor
        return None

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
    
    def __init__(self, parent, control):
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
        self.ParentControl = control
    
    def OnDropText(self, x, y, data):
        message = None
        try:
            values = eval(data)
        except:
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        if not isinstance(values, TupleType):
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)
        elif values is not None and values[1] == "debug":
            if self.ParentControl == self.ParentWindow.VariablesGrid:
                x, y = self.ParentWindow.VariablesGrid.CalcUnscrolledPosition(x, y)
                row = self.ParentWindow.VariablesGrid.YToRow(y - self.ParentWindow.VariablesGrid.GetColLabelSize())
                if row == wx.NOT_FOUND:
                    row = self.ParentWindow.Table.GetNumberRows()
                self.ParentWindow.InsertValue(values[0], row, force=True)
            else:
                x, y = self.ParentWindow.GraphicsCanvasWindow.CalcUnscrolledPosition(x, y)
                width, height = self.ParentWindow.GraphicsCanvas.GetSize()
                target = None
                merge_type = GRAPH_PARALLEL
                for infos in self.ParentWindow.GraphicsAxes:
                    ax, ay, aw, ah = infos["axes"].get_position().bounds
                    rect = wx.Rect(ax * width, height - (ay + ah) * height,
                                   aw * width, ah * height)
                    if rect.InsideXY(x, y):
                        target = infos
                        merge_rect = wx.Rect(ax * width, height - (ay + ah) * height,
                                             aw * width / 2., ah * height)
                        if merge_rect.InsideXY(x, y):
                            merge_type = GRAPH_ORTHOGONAL
                        break
                self.ParentWindow.MergeGraphs(values[0], target, merge_type, force=True)
            
    def ShowMessage(self, message):
        dialog = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()

SCROLLBAR_UNIT = 10

def NextTick(variables):
    next_tick = None
    for var_name, data in variables:
        if len(data) > 0:
            if next_tick is None:
                next_tick = data[0][0]
            else:
                next_tick = min(next_tick, data[0][0])
    return next_tick

def OrthogonalData(item, start_tick, end_tick):
    data = item.GetData(start_tick, end_tick)
    min_value, max_value = item.GetRange()
    if min_value is not None and max_value is not None:
        center = (min_value + max_value) / 2.
        range = max(1.0, max_value - min_value)
    else:
        center = 0.5
        range = 1.0
    return data, center - range * 0.55, center + range * 0.55 
    
class DebugVariablePanel(wx.SplitterWindow, DebugViewer):
    
    def __init__(self, parent, producer, window):
        wx.SplitterWindow.__init__(self, parent, style=wx.SP_3D)
        
        self.ParentWindow = window
        
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
        self.VariablesGrid.SetDropTarget(DebugVariableDropTarget(self, self.VariablesGrid))
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, 
              self.OnVariablesGridCellRightClick)
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, 
              self.OnVariablesGridCellLeftClick)
        main_panel_sizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
        
        self.MainPanel.SetSizer(main_panel_sizer)
        
        self.HasNewData = False
        self.Ticks = numpy.array([])
        self.RangeValues = None
        self.StartTick = 0
        self.Fixed = False
        self.Force = False
        
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
            for infos in self.GraphicsAxes:
                if item in infos["items"]:
                    if len(infos["items"]) == 1:
                        self.GraphicsAxes.remove(infos)
                    else:
                        infos["items"].remove(item)
                    break
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
        
        self.GridColSizes = [200, 100]
        
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColSize(col, self.GridColSizes[col])
        
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        
        if USE_MPL:
            self.GraphicsPanel = wx.Panel(self, style=wx.TAB_TRAVERSAL)
            
            self.GraphicsPanelSizer = wx.BoxSizer(wx.VERTICAL)
            
            graphics_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.GraphicsPanelSizer.AddSizer(graphics_button_sizer, border=5, flag=wx.GROW|wx.ALL)
            
            range_label = wx.StaticText(self.GraphicsPanel, label=_('Range:'))
            graphics_button_sizer.AddWindow(range_label, flag=wx.ALIGN_CENTER_VERTICAL)
            
            self.CanvasRange = wx.ComboBox(self.GraphicsPanel, style=wx.CB_READONLY)
            self.Bind(wx.EVT_COMBOBOX, self.OnRangeChanged, self.CanvasRange)
            graphics_button_sizer.AddWindow(self.CanvasRange, 1, 
                  border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
            
            for name, bitmap, help in [
                ("ResetButton", "reset", _("Clear the graph values")),
                ("CurrentButton", "current", _("Go to current value")),
                ("ExportGraphButton", "export_graph", _("Export graph values to clipboard"))]:
                button = wx.lib.buttons.GenBitmapButton(self.GraphicsPanel, 
                      bitmap=GetBitmap(bitmap), 
                      size=wx.Size(28, 28), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
                graphics_button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
            
            self.CanvasPosition = wx.ScrollBar(self.GraphicsPanel, 
                  size=wx.Size(0, 16), style=wx.SB_HORIZONTAL)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_THUMBTRACK, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_LINEUP, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_LINEDOWN, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_PAGEUP, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.CanvasPosition.Bind(wx.EVT_SCROLL_PAGEDOWN, 
                  self.OnPositionChanging, self.CanvasPosition)
            self.GraphicsPanelSizer.AddWindow(self.CanvasPosition, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
            
            self.GraphicsCanvasWindow = wx.ScrolledWindow(self.GraphicsPanel, style=wx.HSCROLL|wx.VSCROLL)
            self.GraphicsCanvasWindow.Bind(wx.EVT_SIZE, self.OnGraphicsCanvasWindowResize)
            self.GraphicsPanelSizer.AddWindow(self.GraphicsCanvasWindow, 1, flag=wx.GROW)
            
            graphics_canvas_window_sizer = wx.BoxSizer(wx.VERTICAL)
            
            self.GraphicsFigure = matplotlib.figure.Figure()
            self.GraphicsAxes = []
            
            self.GraphicsCanvas = FigureCanvas(self.GraphicsCanvasWindow, -1, self.GraphicsFigure)
            self.GraphicsCanvas.mpl_connect("button_press_event", self.OnGraphicsCanvasClick)
            self.GraphicsCanvas.SetDropTarget(DebugVariableDropTarget(self, self.GraphicsCanvas))
            graphics_canvas_window_sizer.AddWindow(self.GraphicsCanvas, 1, flag=wx.GROW)
            
            self.GraphicsCanvasWindow.SetSizer(graphics_canvas_window_sizer)
            
            self.Graphics3DFigure = matplotlib.figure.Figure()
            self.Graphics3DFigure.subplotpars.update(left=0.0, right=1.0, bottom=0.0, top=1.0)
            
            self.LastMotionTime = gettime()
            self.Graphics3DAxes = self.Graphics3DFigure.gca(projection='3d')
            self.Graphics3DAxes.set_color_cycle(['b'])
            setattr(self.Graphics3DAxes, "_on_move", self.OnGraphics3DMotion)
            
            self.Graphics3DCanvas = FigureCanvas(self.GraphicsPanel, -1, self.Graphics3DFigure)
            self.Graphics3DCanvas.SetMinSize(wx.Size(1, 1))
            self.GraphicsPanelSizer.AddWindow(self.Graphics3DCanvas, 1, flag=wx.GROW)
            
            self.Graphics3DAxes.mouse_init()
            
            self.GraphicsPanel.SetSizer(self.GraphicsPanelSizer)
            
            self.SplitHorizontally(self.MainPanel, self.GraphicsPanel, -200)
        
        else:
            self.Initialize(self.MainPanel)
        
        self.ResetGraphics()
        self.RefreshCanvasRange()
        self.RefreshScrollBar()
        
    def SetDataProducer(self, producer):
        DebugViewer.SetDataProducer(self, producer)
        
        if self.DataProducer is not None:
            self.Ticktime = self.DataProducer.GetTicktime()
            self.RefreshCanvasRange()
        else:
            self.Ticktime = 0
    
    def RefreshNewData(self, *args, **kwargs):
        if self.HasNewData or self.Force:
            self.HasNewData = False
            self.RefreshGrid(only_values=True)
        DebugViewer.RefreshNewData(self, *args, **kwargs)
    
    def NewDataAvailable(self, tick, *args, **kwargs):
        if tick is not None:
            self.Ticks = numpy.append(self.Ticks, [tick])
            if not self.Fixed or tick < self.StartTick + self.CurrentRange:
                self.StartTick = max(self.StartTick, tick - self.CurrentRange)
        DebugViewer.NewDataAvailable(self, tick, *args, **kwargs)
    
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
        
        self.RefreshScrollBar()
        
        self.Thaw()
        
        if USE_MPL:
        
            if not self.Fixed or self.Force:
                self.Force = False
                
                # Refresh graphics
                start_tick, end_tick = self.StartTick, self.StartTick + self.CurrentRange
                for infos in self.GraphicsAxes:
                    
                    if infos["type"] == GRAPH_PARALLEL:
                        min_value = max_value = None
                        
                        for idx, item in enumerate(infos["items"]):
                            data = item.GetData(start_tick, end_tick)
                            if data is not None:
                                item_min_value, item_max_value = item.GetRange()
                                if min_value is None:
                                    min_value = item_min_value
                                elif item_min_value is not None:
                                    min_value = min(min_value, item_min_value)
                                if max_value is None:
                                    max_value = item_max_value
                                elif item_max_value is not None:
                                    max_value = max(max_value, item_max_value)
                                
                                if len(infos["plots"]) <= idx:
                                    infos["plots"].append(
                                        infos["axes"].plot(data[:, 0], data[:, 1])[0])
                                else:
                                    infos["plots"][idx].set_data(data[:, 0], data[:, 1])
                        
                        if min_value is not None and max_value is not None:
                            y_center = (min_value + max_value) / 2.
                            y_range = max(1.0, max_value - min_value)
                        else:
                            y_center = 0.5
                            y_range = 1.0
                        x_min, x_max = start_tick, end_tick
                        y_min, y_max = y_center - y_range * 0.55, y_center + y_range * 0.55
                    
                    else:
                        min_start_tick = reduce(max, [item.GetData()[0, 0] 
                                                      for item in infos["items"]
                                                      if len(item.GetData()) > 0], 0)
                        start_tick = max(self.StartTick, min_start_tick)
                        end_tick = max(self.StartTick + self.CurrentRange, min_start_tick)
                        x_data, x_min, x_max = OrthogonalData(infos["items"][0], start_tick, end_tick)
                        y_data, y_min, y_max = OrthogonalData(infos["items"][1], start_tick, end_tick)
                        length = 0
                        if x_data is not None and y_data is not None:  
                            length = min(len(x_data), len(y_data))
                        if len(infos["items"]) < 3:
                            if x_data is not None and y_data is not None:
                                if len(infos["plots"]) == 0:
                                    infos["plots"].append(
                                        infos["axes"].plot(x_data[:, 1][:length], 
                                                           y_data[:, 1][:length])[0])
                                else:
                                    infos["plots"][0].set_data(
                                        x_data[:, 1][:length], 
                                        y_data[:, 1][:length])
                        else:
                            while len(infos["axes"].lines) > 0:
                                infos["axes"].lines.pop()
                            z_data, z_min, z_max = OrthogonalData(infos["items"][2], start_tick, end_tick)
                            if x_data is not None and y_data is not None and z_data is not None:
                                length = min(length, len(z_data))
                                infos["axes"].plot(x_data[:, 1][:length],
                                                   y_data[:, 1][:length],
                                                   zs = z_data[:, 1][:length])
                            infos["axes"].set_zlim(z_min, z_max)
                    
                    infos["axes"].set_xlim(x_min, x_max)
                    infos["axes"].set_ylim(y_min, y_max)
                
            plot2d = plot3d = 0
            for infos in self.GraphicsAxes:
                labels = ["%s: %s" % (item.GetVariable(), item.GetValue())
                          for item in infos["items"]]
                if infos["type"] == GRAPH_PARALLEL:
                    infos["axes"].legend(infos["plots"], labels, 
                        loc="upper left", frameon=False,
                        prop={'size':'small'})
                    plot2d += 1
                else:
                    infos["axes"].set_xlabel(labels[0], fontdict={'size':'small'})
                    infos["axes"].set_ylabel(labels[1], fontdict={'size':'small'})
                    if len(labels) > 2:
                        infos["axes"].set_zlabel(labels[2], fontdict={'size':'small'})
                        plot3d += 1
                    else:
                        plot2d += 1
            
            if plot2d > 0:
                self.GraphicsCanvas.draw()
            if plot3d > 0:
                self.Graphics3DCanvas.draw()
            
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
        if self.DataProducer is not None:
            self.Ticktime = self.DataProducer.GetTicktime()
            self.RefreshCanvasRange()
    
    def ResetGrid(self):
        self.DeleteDataConsumers()
        self.Table.Empty()
        self.Freeze()
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        self.Thaw()
        self.ResetGraphics()
    
    def RefreshCanvasRange(self):
        if self.Ticktime == 0 and self.RangeValues != RANGE_VALUES:
            self.RangeValues = RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(RANGE_VALUES[0][0])
            self.CurrentRange = RANGE_VALUES[0][1]
            self.RefreshGrid(True)
        elif self.Ticktime != 0 and self.RangeValues != TIME_RANGE_VALUES:
            self.RangeValues = TIME_RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in TIME_RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(TIME_RANGE_VALUES[0][0])
            self.CurrentRange = TIME_RANGE_VALUES[0][1] / self.Ticktime
            self.RefreshGrid(True)
    
    def RefreshScrollBar(self):
        if len(self.Ticks) > 0:
            pos = int(self.StartTick - self.Ticks[0])
            range = int(self.Ticks[-1] - self.Ticks[0])
        else:
            pos = 0
            range = 0
        self.CanvasPosition.SetScrollbar(pos, self.CurrentRange, range, self.CurrentRange)
    
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
    
    def OnVariablesGridCellLeftClick(self, event):
        if event.GetCol() == 0:
            row = event.GetRow()
            data = wx.TextDataObject(str((self.Table.GetValueByName(row, "Variable"), "debug")))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        event.Skip()
    
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
    
    def RefreshRange(self):
        if len(self.Ticks) > 0:
            if self.Fixed and self.Ticks[-1] - self.Ticks[0] < self.CurrentRange:
                self.Fixed = False
            if self.Fixed:
                self.StartTick = min(self.StartTick, self.Ticks[-1] - self.CurrentRange)
            else:
                self.StartTick = max(self.Ticks[0], self.Ticks[-1] - self.CurrentRange)
        self.Force = True
        self.RefreshGrid(True)
    
    def OnRangeChanged(self, event):
        try:
            if self.Ticktime == 0:
                self.CurrentRange = self.RangeValues[self.CanvasRange.GetSelection()][1]
            else:
                self.CurrentRange = self.RangeValues[self.CanvasRange.GetSelection()][1] / self.Ticktime
        except ValueError, e:
            self.CanvasRange.SetValue(str(self.CurrentRange))
        wx.CallAfter(self.RefreshRange)
        event.Skip()
    
    def OnResetButton(self, event):
        self.StartTick = 0
        self.Fixed = False
        for item in self.Table.GetData():
            item.ResetData()
        self.RefreshGrid(True)
        event.Skip()

    def OnCurrentButton(self, event):
        if len(self.Ticks) > 0:
            self.StartTick = max(self.Ticks[0], self.Ticks[-1] - self.CurrentRange)
            self.Fixed = False
            self.Force = True
            self.RefreshGrid(True)
        event.Skip()
    
    def CopyDataToClipboard(self, variables):
        text = "tick;%s;\n" % ";".join([var_name for var_name, data in variables])
        next_tick = NextTick(variables)
        while next_tick is not None:
            values = []
            for var_name, data in variables:
                if len(data) > 0:
                    if next_tick == data[0][0]:
                        values.append("%.3f" % data.pop(0)[1])
                    else:
                        values.append("")
                else:
                    values.append("")
            text += "%d;%s;\n" % (next_tick, ";".join(values))
            next_tick = NextTick(variables)
        self.ParentWindow.SetCopyBuffer(text)
    
    def OnExportGraphButton(self, event):
        variables = []
        for item in self.Table.GetData():
            if item.IsNumVariable():
                variables.append((item.GetVariable(), [entry for entry in item.GetData()]))
        wx.CallAfter(self.CopyDataToClipboard, variables)
        event.Skip()
    
    def OnPositionChanging(self, event):
        if len(self.Ticks) > 0:
            self.StartTick = self.Ticks[0] + event.GetPosition()
            self.Fixed = True
            self.Force = True
            wx.CallAfter(self.NewDataAvailable, None, True)
        event.Skip()
    
    def InsertValue(self, iec_path, idx = None, force=False):
        if idx is None:
            idx = self.Table.GetNumberRows()
        for item in self.Table.GetData():
            if iec_path == item.GetVariable():
                return
        item = VariableTableItem(self, iec_path)
        result = self.AddDataConsumer(iec_path.upper(), item)
        if result is not None or force:
            self.Table.InsertItem(idx, item)
            if item.IsNumVariable():
                self.GraphicsAxes.append({
                    "items": [item],
                    "axes": None,
                    "type": GRAPH_PARALLEL,
                    "plots": []})
            self.ResetGraphics()
            self.RefreshGrid()
    
    def MergeGraphs(self, source, target_infos, merge_type, force=False):
        source_item = None
        for item in self.Table.GetData():
            if item.GetVariable() == source:
                source_item = item
        if source_item is None:
            item = VariableTableItem(self, source)
            if item.IsNumVariable():
                result = self.AddDataConsumer(source.upper(), item)
                if result is not None or force:
                    self.Table.InsertItem(self.Table.GetNumberRows(), item)
                    source_item = item
        if source_item is not None:
            source_infos = None
            for infos in self.GraphicsAxes:
                if source_item in infos["items"]:
                    source_infos = infos
                    break
            if target_infos is None and source_infos is None:
                self.GraphicsAxes.append({
                    "items": [source_item],
                    "axes": None,
                    "type": GRAPH_PARALLEL,
                    "plots": []})
                
                self.ResetGraphics()
                self.RefreshGrid()
            
            elif target_infos is not None:
                if (merge_type == GRAPH_PARALLEL and target_infos["type"] != merge_type or
                    merge_type == GRAPH_ORTHOGONAL and 
                    (target_infos["type"] == GRAPH_PARALLEL and len(target_infos["items"]) > 1 or
                     target_infos["type"] == GRAPH_ORTHOGONAL and len(target_infos["items"]) >= 3)):
                    return
                
                if source_infos is not None:
                    source_infos["items"].remove(source_item)
                    if len(source_infos["items"]) == 0:
                        self.GraphicsAxes.remove(source_infos)
                
                target_infos["items"].append(source_item)
                target_infos["type"] = merge_type
                
                self.ResetGraphics()
                self.RefreshGrid()
            
    def GetDebugVariables(self):
        return [item.GetVariable() for item in self.Table.GetData()]
    
    def OnGraphicsCanvasClick(self, event):
        for infos in self.GraphicsAxes:
            if infos["axes"] == event.inaxes:
                if len(infos["items"]) == 1:
                    data = wx.TextDataObject(str((infos["items"][0].GetVariable(), "debug")))
                    dragSource = wx.DropSource(self.GraphicsCanvas)
                    dragSource.SetData(data)
                    dragSource.DoDragDrop()
                    if self.GraphicsCanvas.HasCapture():
                        self.GraphicsCanvas.ReleaseMouse()
                break
    
    def ResetGraphicsValues(self):
        self.Ticks = numpy.array([])
        self.StartTick = 0
        for item in self.Table.GetData():
            item.ResetData()
    
    def ResetGraphics(self):
        if USE_MPL:
            self.GraphicsFigure.clear()
            
            axes_num = 0
            for infos in self.GraphicsAxes:
                if infos["type"] != GRAPH_ORTHOGONAL or len(infos["items"]) < 3:
                    axes_num += 1
            if axes_num == len(self.GraphicsAxes):
                self.Graphics3DCanvas.Hide()
            else:
                self.Graphics3DCanvas.Show()
            self.GraphicsPanelSizer.Layout()
            idx = 1
            for infos in self.GraphicsAxes:
                if infos["type"] != GRAPH_ORTHOGONAL or len(infos["items"]) < 3:
                    axes = self.GraphicsFigure.add_subplot(axes_num, 1, idx)
                    infos["axes"] = axes
                else:
                    infos["axes"] = self.Graphics3DAxes
                infos["plots"] = []
                idx += 1
            self.RefreshGraphicsCanvasWindowScrollbars()
            self.GraphicsCanvas.draw()
    
    def OnGraphics3DMotion(self, event):
        current_time = gettime()
        if current_time - self.LastMotionTime > REFRESH_PERIOD:
            self.LastMotionTime = current_time
            Axes3D._on_move(self.Graphics3DAxes, event)
    
    def RefreshGraphicsCanvasWindowScrollbars(self):
        xstart, ystart = self.GraphicsCanvasWindow.GetViewStart()
        window_size = self.GraphicsCanvasWindow.GetClientSize()
        vwidth, vheight = (window_size[0], (len(self.GraphicsAxes) + 1) * 100)
        self.GraphicsCanvas.SetMinSize(wx.Size(vwidth, vheight))
        posx = max(0, min(xstart, (vwidth - window_size[0]) / SCROLLBAR_UNIT))
        posy = max(0, min(ystart, (vheight - window_size[1]) / SCROLLBAR_UNIT))
        self.GraphicsCanvasWindow.Scroll(posx, posy)
        self.GraphicsCanvasWindow.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                vwidth / SCROLLBAR_UNIT, vheight / SCROLLBAR_UNIT, posx, posy)
    
    def OnGraphicsCanvasWindowResize(self, event):
        self.RefreshGraphicsCanvasWindowScrollbars()
        event.Skip()
