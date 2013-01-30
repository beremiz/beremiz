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

from types import TupleType, ListType, FloatType
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
    from mpl_toolkits.mplot3d import Axes3D
    USE_MPL = True
except:
    USE_MPL = False

from graphics import DebugDataConsumer, DebugViewer, REFRESH_PERIOD
from controls import CustomGrid, CustomTable
from dialogs.ForceVariableDialog import ForceVariableDialog
from util.BitmapLibrary import GetBitmap

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
            self.Parent.RefreshView()
    
    def GetVariable(self, max_size=None):
        variable = self.Variable
        if max_size is not None:
            max_size = max(max_size, 10)
            if len(variable) > max_size:
                variable = "..." + variable[-(max_size - 3):]
        return variable
    
    def RefreshVariableType(self):
        self.VariableType = self.Parent.GetDataType(self.Variable)
        if USE_MPL:
            self.ResetData()
    
    def GetVariableType(self):
        return self.VariableType
    
    def GetData(self, start_tick=None, end_tick=None):
        if USE_MPL and self.IsNumVariable():
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
        if USE_MPL and self.IsNumVariable():
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
        if USE_MPL and self.IsNumVariable():
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
    
    def __init__(self, parent, control=None):
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
        self.ParentControl = control
    
    def __del__(self):
        self.ParentWindow = None
        self.ParentControl = None
    
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
            if isinstance(self.ParentControl, CustomGrid):
                x, y = self.ParentControl.CalcUnscrolledPosition(x, y)
                row = self.ParentControl.YToRow(y - self.ParentControl.GetColLabelSize())
                if row == wx.NOT_FOUND:
                    row = self.ParentWindow.Table.GetNumberRows()
                self.ParentWindow.InsertValue(values[0], row, force=True)
            elif self.ParentControl is not None:
                width, height = self.ParentControl.Canvas.GetSize()
                target_idx = self.ParentControl.GetIndex()
                merge_type = GRAPH_PARALLEL
                if self.ParentControl.Is3DCanvas():
                    if y > height / 2:
                        target_idx += 1
                    if len(values) > 2 and values[2] == "move":
                        self.ParentWindow.MoveGraph(values[0], target_idx)
                    else:
                        self.ParentWindow.InsertValue(values[0], target_idx, force=True)
                else:
                    ax, ay, aw, ah = self.ParentControl.Axes.get_position().bounds
                    rect = wx.Rect(ax * width, height - (ay + ah) * height,
                                   aw * width, ah * height)
                    if rect.InsideXY(x, y):
                        merge_rect = wx.Rect(ax * width, height - (ay + ah) * height,
                                             aw * width / 2., ah * height)
                        if merge_rect.InsideXY(x, y):
                            merge_type = GRAPH_ORTHOGONAL
                        wx.CallAfter(self.ParentWindow.MergeGraphs, values[0], target_idx, merge_type, force=True)
                    else:
                        if y > height / 2:
                            target_idx += 1
                        if len(values) > 2 and values[2] == "move":
                            self.ParentWindow.MoveGraph(values[0], target_idx)
                        else:
                            self.ParentWindow.InsertValue(values[0], target_idx, force=True)
            elif len(values) > 2 and values[2] == "move":
                self.ParentWindow.MoveGraph(values[0])
            else:
                self.ParentWindow.InsertValue(values[0], force=True)
            
    def ShowMessage(self, message):
        dialog = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()

if USE_MPL:
    SECOND = 1000000000
    MINUTE = 60 * SECOND
    HOUR = 60 * MINUTE
    
    ZOOM_VALUES = map(lambda x:("x %.1f" % x, x), [math.sqrt(2) ** i for i in xrange(8)])
    RANGE_VALUES = map(lambda x: (str(x), x), [25 * 2 ** i for i in xrange(6)])
    TIME_RANGE_VALUES = [("%ds" % i, i * SECOND) for i in (1, 2, 5, 10, 20, 30)] + \
                        [("%dm" % i, i * MINUTE) for i in (1, 2, 5, 10, 20, 30)] + \
                        [("%dh" % i, i * HOUR) for i in (1, 2, 3, 6, 12, 24)]
    
    GRAPH_PARALLEL, GRAPH_ORTHOGONAL = range(2)
    
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
    
    class DebugVariableViewer(wx.Panel):
        
        def AddViewer(self):
            pass
        
        def AddButtons(self):
            pass
        
        def __init__(self, parent, window, items=[]):
            wx.Panel.__init__(self, parent)
            self.SetBackgroundColour(wx.WHITE)
            self.SetDropTarget(DebugVariableDropTarget(window, self))
            
            self.ParentWindow = window
            self.Items = items
            
            self.MainSizer = wx.FlexGridSizer(cols=2, hgap=0, rows=1, vgap=0)
            self.AddViewer()
            self.AddButtons()
            self.MainSizer.AddGrowableCol(0)
            
            self.SetSizer(self.MainSizer)
        
        def __del__(self):
            self.ParentWindow = None
            
        def GetIndex(self):
            return self.ParentWindow.GetViewerIndex(self)
        
        def GetItem(self, variable):
            for item in self.Items:
                if item.GetVariable() == variable:
                    return item
            return None
        
        def GetItems(self):
            return self.Items
        
        def GetVariables(self):
            if len(self.Items) > 1:
                variables = [item.GetVariable() for item in self.Items]
                if self.GraphType == GRAPH_ORTHOGONAL:
                    return tuple(variables)
                return variables
            return self.Items[0].GetVariable()
        
        def AddItem(self, item):
            self.Items.append(item)
    
        def RemoveItem(self, item):
            if item in self.Items:
                self.Items.remove(item)
            
        def Clear(self):
            for item in self.Items:
                self.ParentWindow.RemoveDataConsumer(item)
            self.Items = []
        
        def IsEmpty(self):
            return len(self.Items) == 0
        
        def UnregisterObsoleteData(self):
            for item in self.Items[:]:
                iec_path = item.GetVariable().upper()
                if self.ParentWindow.GetDataType(iec_path) is None:
                    self.ParentWindow.RemoveDataConsumer(item)
                    self.RemoveItem(item)
                else:
                    self.ParentWindow.AddDataConsumer(iec_path, item)
                    item.RefreshVariableType()
        
        def ResetData(self):
            for item in self.Items:
                item.ResetData()
        
        def Refresh(self):
            pass
    
        def OnForceButton(self, event):
            if len(self.Items) == 1:
                wx.CallAfter(self.ForceValue, self.Items[0])
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(20))
                    self.Bind(wx.EVT_MENU, 
                        self.GetForceVariableMenuFunction(item),
                        id=new_id)
                self.PopupMenu(menu)
            event.Skip()
        
        def OnReleaseButton(self, event):
            if len(self.Items) == 1:
                wx.CallAfter(self.ReleaseValue, self.Items[0])
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(20))
                    self.Bind(wx.EVT_MENU, 
                        self.GetReleaseVariableMenuFunction(item),
                        id=new_id)
                
                self.PopupMenu(menu)
            event.Skip()
        
        def OnDeleteButton(self, event):
            if len(self.Items) == 1:
                wx.CallAfter(self.ParentWindow.DeleteValue, self, self.Items[0])
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(20))
                    self.Bind(wx.EVT_MENU, 
                        self.GetDeleteValueMenuFunction(item),
                        id=new_id)
                
                new_id = wx.NewId()
                AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("All"))
                self.Bind(wx.EVT_MENU, self.OnDeleteAllValuesMenu, id=new_id)
                
                self.PopupMenu(menu)
            event.Skip()
    
        def GetForceVariableMenuFunction(self, item):
            def ForceVariableFunction(event):
                self.ForceValue(item)
            return ForceVariableFunction
        
        def GetReleaseVariableMenuFunction(self, item):
            def ReleaseVariableFunction(event):
                self.ReleaseValue(item)
            return ReleaseVariableFunction
        
        def GetDeleteValueMenuFunction(self, item):
            def DeleteValueFunction(event):
                self.ParentWindow.DeleteValue(self, item)
            return DeleteValueFunction
        
        def ForceValue(self, item):
            iec_path = item.GetVariable().upper()
            iec_type = self.ParentWindow.GetDataType(iec_path)
            if iec_type is not None:
                dialog = ForceVariableDialog(self, iec_type, str(item.GetValue()))
                if dialog.ShowModal() == wx.ID_OK:
                    self.ParentWindow.ForceDataValue(iec_path, dialog.GetValue())
        
        def ReleaseValue(self, item):
            iec_path = item.GetVariable().upper()
            self.ParentWindow.ReleaseDataValue(iec_path)
        
        def OnDeleteAllValuesMenu(self, event):
            wx.CallAfter(self.ParentWindow.DeleteValue, self)
        
    class DebugVariableText(DebugVariableViewer):
        
        def AddViewer(self):
            viewer_sizer = wx.FlexGridSizer(cols=2, hgap=0, rows=1, vgap=0)
            viewer_sizer.AddGrowableCol(0)
            self.MainSizer.AddSizer(viewer_sizer, border=5, 
                flag=wx.ALL|wx.GROW|wx.ALIGN_CENTER_VERTICAL)
            
            variable_name_label = wx.TextCtrl(self, size=wx.Size(0, -1),
                value=self.Items[0].GetVariable(), style=wx.TE_READONLY|wx.TE_RIGHT|wx.NO_BORDER)
            variable_name_label.SetSelection(variable_name_label.GetLastPosition(), -1)
            viewer_sizer.AddWindow(variable_name_label, flag=wx.GROW)
            
            self.ValueLabel = wx.TextCtrl(self,
                size=wx.Size(100, -1), style=wx.TE_READONLY|wx.TE_RIGHT|wx.NO_BORDER)
            viewer_sizer.AddWindow(self.ValueLabel, 
                border=5, flag=wx.LEFT)
        
        def AddButtons(self):
            button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.MainSizer.AddSizer(button_sizer, border=5, 
                flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
            
            buttons = [
                ("ForceButton", "force", _("Force value")),
                ("ReleaseButton", "release", _("Release value")),
                ("DeleteButton", "remove_element", _("Remove debug variable"))]
            
            for name, bitmap, help in buttons:
                button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                      size=wx.Size(28, 28), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
                button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
    
        def Refresh(self):
            self.ValueLabel.ChangeValue(self.Items[0].GetValue())
            if self.Items[0].IsForced():
                self.ValueLabel.SetForegroundColour(wx.BLUE)
            else:
                self.ValueLabel.SetForegroundColour(wx.BLACK)
            self.ValueLabel.SetSelection(self.ValueLabel.GetLastPosition(), -1)
    
    class DebugVariableGraphic(DebugVariableViewer):
        
        def __init__(self, parent, window, items, graph_type):
            DebugVariableViewer.__init__(self, parent, window, items)
        
            self.GraphType = graph_type
            
            self.ResetGraphics()
        
        def AddViewer(self):
            self.Figure = matplotlib.figure.Figure(facecolor='w')
            
            self.Canvas = FigureCanvas(self, -1, self.Figure)
            self.Canvas.SetMinSize(wx.Size(200, 200))
            self.Canvas.SetDropTarget(DebugVariableDropTarget(self.ParentWindow, self))
            self.Canvas.Bind(wx.EVT_LEFT_DOWN, self.OnCanvasClick)
            
            self.MainSizer.AddWindow(self.Canvas, flag=wx.GROW)
        
        def AddButtons(self):
            button_sizer = wx.BoxSizer(wx.VERTICAL)
            self.MainSizer.AddSizer(button_sizer, border=5, 
                flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
            
            buttons = [
                ("ForceButton", "force", _("Force value")),
                ("ReleaseButton", "release", _("Release value")),
                ("SplitButton", "split", _("Split graphs")),
                ("DeleteButton", "remove_element", _("Remove debug variable"))]
            
            for name, bitmap, help in buttons:
                button = wx.lib.buttons.GenBitmapButton(self, bitmap=GetBitmap(bitmap), 
                      size=wx.Size(28, 28), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
                button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
    
        def OnCanvasClick(self, event):
            x, y = event.GetPosition()
            width, height = self.Canvas.GetSize()
            if len(self.Items) == 1:
                ax, ay, aw, ah = self.Axes.get_position().bounds
                rect = wx.Rect(ax * width, height - (ay + ah) * height,
                               aw * width, ah * height)
                if rect.InsideXY(x, y):
                    self.DoDragDrop(0)
                    return
            elif self.Legend is not None:
                item_idx = None
                for i, t in enumerate(self.Legend.get_texts()):
                    (x0, y0), (x1, y1) = t.get_window_extent().get_points()
                    rect = wx.Rect(x0, height - y1, x1 - x0, y1 - y0)
                    if rect.InsideXY(x, y):
                        item_idx = i
                        break
                if item_idx is not None:
                    self.DoDragDrop(item_idx)
                    return
            event.Skip()
        
        def DoDragDrop(self, item_idx):
            data = wx.TextDataObject(str((self.Items[item_idx].GetVariable(), "debug", "move")))
            dragSource = wx.DropSource(self.Canvas)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
            
        def OnMotion(self, event):
            if self.Is3DCanvas():
                current_time = gettime()
                if current_time - self.LastMotionTime > REFRESH_PERIOD:
                    self.LastMotionTime = current_time
                    Axes3D._on_move(self.Axes, event)
        
        def OnSplitButton(self, event):
            if len(self.Items) == 2 or self.GraphType == GRAPH_ORTHOGONAL:
                wx.CallAfter(self.ParentWindow.SplitGraphs, self)
            else:
                menu = wx.Menu(title='')
                for item in self.Items:
                    new_id = wx.NewId()
                    AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, 
                        text=item.GetVariable(20))
                    self.Bind(wx.EVT_MENU, 
                        self.GetSplitGraphMenuFunction(item),
                        id=new_id)
                
                new_id = wx.NewId()
                AppendMenu(menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=_("All"))
                self.Bind(wx.EVT_MENU, self.OnSplitAllGraphsMenu, id=new_id)
                
                self.PopupMenu(menu)
            event.Skip()
        
        def ResetGraphics(self):
            self.Figure.clear()
            if self.Is3DCanvas():
                self.Axes = self.Figure.gca(projection='3d')
                self.Axes.set_color_cycle(['b'])
                self.LastMotionTime = gettime()
                setattr(self.Axes, "_on_move", self.OnMotion)
                self.Axes.mouse_init()
            else:
                self.Axes = self.Figure.gca()
                if self.GraphType == GRAPH_ORTHOGONAL:
                    self.Figure.subplotpars.update(bottom=0.15)
            self.Plots = []
            self.SplitButton.Enable(len(self.Items) > 1)
            
        def AddItem(self, item):
            DebugVariableViewer.AddItem(self, item)
            self.ResetGraphics()
            
        def RemoveItem(self, item):
            DebugVariableViewer.RemoveItem(self, item)
            if not self.IsEmpty():
                self.ResetGraphics()
        
        def UnregisterObsoleteData(self):
            DebugVariableViewer.UnregisterObsoleteData(self)
            if not self.IsEmpty():
                self.ResetGraphics()
        
        def Is3DCanvas(self):
            return self.GraphType == GRAPH_ORTHOGONAL and len(self.Items) == 3
        
        def Refresh(self, refresh_graphics=True):
            
            if refresh_graphics:
                start_tick, end_tick = self.ParentWindow.GetRange()
                
                if self.GraphType == GRAPH_PARALLEL:    
                    min_value = max_value = None
                    
                    for idx, item in enumerate(self.Items):
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
                            
                            if len(self.Plots) <= idx:
                                self.Plots.append(
                                    self.Axes.plot(data[:, 0], data[:, 1])[0])
                            else:
                                self.Plots[idx].set_data(data[:, 0], data[:, 1])
                        
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
                                                  for item in self.Items
                                                  if len(item.GetData()) > 0], 0)
                    start_tick = max(start_tick, min_start_tick)
                    end_tick = max(end_tick, min_start_tick)
                    x_data, x_min, x_max = OrthogonalData(self.Items[0], start_tick, end_tick)
                    y_data, y_min, y_max = OrthogonalData(self.Items[1], start_tick, end_tick)
                    length = 0
                    if x_data is not None and y_data is not None:  
                        length = min(len(x_data), len(y_data))
                    if len(self.Items) < 3:
                        if x_data is not None and y_data is not None:
                            if len(self.Plots) == 0:
                                self.Plots.append(
                                    self.Axes.plot(x_data[:, 1][:length], 
                                                   y_data[:, 1][:length])[0])
                            else:
                                self.Plots[0].set_data(
                                    x_data[:, 1][:length], 
                                    y_data[:, 1][:length])
                    else:
                        while len(self.Axes.lines) > 0:
                            self.Axes.lines.pop()
                        z_data, z_min, z_max = OrthogonalData(self.Items[2], start_tick, end_tick)
                        if x_data is not None and y_data is not None and z_data is not None:
                            length = min(length, len(z_data))
                            self.Axes.plot(x_data[:, 1][:length],
                                           y_data[:, 1][:length],
                                           zs = z_data[:, 1][:length])
                        self.Axes.set_zlim(z_min, z_max)
                
                self.Axes.set_xlim(x_min, x_max)
                self.Axes.set_ylim(y_min, y_max)
            
            labels = ["%s: %s" % (item.GetVariable(40), item.GetValue())
                      for item in self.Items]
            colors = [{True: 'b', False: 'k'}[item.IsForced()] for item in self.Items]
            if self.GraphType == GRAPH_PARALLEL:
                self.Legend = self.Axes.legend(self.Plots, labels, 
                    loc="upper left", frameon=False,
                    prop={'size':'small'})
                for t, color in zip(self.Legend.get_texts(), colors):
                    t.set_color(color)
            else:
                self.Legend = None
                self.Axes.set_xlabel(labels[0], fontdict={'size':'small','color':colors[0]})
                self.Axes.set_ylabel(labels[1], fontdict={'size':'small','color':colors[1]})
                if len(labels) > 2:
                    self.Axes.set_zlabel(labels[2], fontdict={'size':'small','color':colors[2]})
            self.Canvas.draw()
        
        def GetSplitGraphMenuFunction(self, item):
            def SplitGraphFunction(event):
                self.ParentWindow.SplitGraphs(self, item)
            return SplitGraphFunction
        
        def OnSplitAllGraphsMenu(self, event):
            self.ParentWindow.SplitGraphs(self)
    
class DebugVariablePanel(wx.Panel, DebugViewer):
    
    def __init__(self, parent, producer, window):
        wx.Panel.__init__(self, parent, style=wx.SP_3D|wx.TAB_TRAVERSAL)
        
        self.ParentWindow = window
        
        DebugViewer.__init__(self, producer, True)
        
        self.HasNewData = False
        
        if USE_MPL:
            main_sizer = wx.BoxSizer(wx.VERTICAL)
            
            self.Ticks = numpy.array([])
            self.RangeValues = None
            self.StartTick = 0
            self.Fixed = False
            self.Force = False
            self.GraphicPanels = []
            
            graphics_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
            main_sizer.AddSizer(graphics_button_sizer, border=5, flag=wx.GROW|wx.ALL)
            
            range_label = wx.StaticText(self, label=_('Range:'))
            graphics_button_sizer.AddWindow(range_label, flag=wx.ALIGN_CENTER_VERTICAL)
            
            self.CanvasRange = wx.ComboBox(self, style=wx.CB_READONLY)
            self.Bind(wx.EVT_COMBOBOX, self.OnRangeChanged, self.CanvasRange)
            graphics_button_sizer.AddWindow(self.CanvasRange, 1, 
                  border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)
            
            for name, bitmap, help in [
                ("ResetButton", "reset", _("Clear the graph values")),
                ("CurrentButton", "current", _("Go to current value")),
                ("ExportGraphButton", "export_graph", _("Export graph values to clipboard"))]:
                button = wx.lib.buttons.GenBitmapButton(self, 
                      bitmap=GetBitmap(bitmap), 
                      size=wx.Size(28, 28), style=wx.NO_BORDER)
                button.SetToolTipString(help)
                setattr(self, name, button)
                self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
                graphics_button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
            
            self.CanvasPosition = wx.ScrollBar(self, 
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
            main_sizer.AddWindow(self.CanvasPosition, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
            
            self.GraphicsWindow = wx.ScrolledWindow(self, style=wx.HSCROLL|wx.VSCROLL)
            self.GraphicsWindow.SetDropTarget(DebugVariableDropTarget(self))
            self.GraphicsWindow.Bind(wx.EVT_SIZE, self.OnGraphicsWindowResize)
            main_sizer.AddWindow(self.GraphicsWindow, 1, flag=wx.GROW)
            
            self.GraphicsSizer = wx.BoxSizer(wx.VERTICAL)
            self.GraphicsWindow.SetSizer(self.GraphicsSizer)
            
            self.RefreshCanvasRange()
            
        else:
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
            
            self.VariablesGrid = CustomGrid(self, size=wx.Size(-1, 150), style=wx.VSCROLL)
            self.VariablesGrid.SetDropTarget(DebugVariableDropTarget(self, self.VariablesGrid))
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, 
                  self.OnVariablesGridCellRightClick)
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, 
                  self.OnVariablesGridCellLeftClick)
            main_sizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
        
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
                self.RefreshView()
            setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
            
            def _MoveVariable(row, move):
                new_row = max(0, min(row + move, self.Table.GetNumberRows() - 1))
                if new_row != row:
                    self.Table.MoveItem(row, new_row)
                    self.RefreshView()
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
        
        self.SetSizer(main_sizer)
        
    def SetDataProducer(self, producer):
        DebugViewer.SetDataProducer(self, producer)
        
        if USE_MPL:
            if self.DataProducer is not None:
                self.Ticktime = self.DataProducer.GetTicktime()
                self.RefreshCanvasRange()
            else:
                self.Ticktime = 0
    
    def RefreshNewData(self, *args, **kwargs):
        if self.HasNewData or self.Force:
            self.HasNewData = False
            self.RefreshView(only_values=True)
        DebugViewer.RefreshNewData(self, *args, **kwargs)
    
    def NewDataAvailable(self, tick, *args, **kwargs):
        if USE_MPL and tick is not None:
            self.Ticks = numpy.append(self.Ticks, [tick])
            if not self.Fixed or tick < self.StartTick + self.CurrentRange:
                self.StartTick = max(self.StartTick, tick - self.CurrentRange)
        DebugViewer.NewDataAvailable(self, tick, *args, **kwargs)
    
    def RefreshGraphicsSizer(self):
        self.GraphicsSizer.Clear()
        
        for panel in self.GraphicPanels:
            self.GraphicsSizer.AddWindow(panel, flag=wx.GROW)
            
        self.GraphicsSizer.Layout()
        self.RefreshGraphicsWindowScrollbars()
    
    def RefreshView(self, only_values=False):
        if USE_MPL:
            self.RefreshCanvasPosition()
            
            if not self.Fixed or self.Force:
                self.Force = False
                refresh_graphics = True
            else:
                refresh_graphics = False
            
            for panel in self.GraphicPanels:
                if isinstance(panel, DebugVariableGraphic):
                    panel.Refresh(refresh_graphics)
                else:
                    panel.Refresh()
        
        else:
            self.Freeze()
            
            if only_values:
                for col in xrange(self.Table.GetNumberCols()):
                    if self.Table.GetColLabelValue(col, False) == "Value":
                        for row in xrange(self.Table.GetNumberRows()):
                            self.VariablesGrid.SetCellValue(row, col, str(self.Table.GetValueByName(row, "Value")))
            else:
                self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
            
            self.Thaw()
        
    def UnregisterObsoleteData(self):
        if USE_MPL:
            if self.DataProducer is not None:
                self.Ticktime = self.DataProducer.GetTicktime()
                self.RefreshCanvasRange()
            
            for panel in self.GraphicPanels:
                panel.UnregisterObsoleteData()
            
        else:
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
    
    def ResetView(self):
        self.DeleteDataConsumers()
        if USE_MPL:
            for panel in self.GraphicPanels:
                panel.Destroy()
            self.GraphicPanels = []
            self.RefreshGraphicsSizer()
        else:
            self.Table.Empty()
            self.Freeze()
            self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
            self.Thaw()
    
    def RefreshCanvasRange(self):
        if self.Ticktime == 0 and self.RangeValues != RANGE_VALUES:
            self.RangeValues = RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(RANGE_VALUES[0][0])
            self.CurrentRange = RANGE_VALUES[0][1]
            self.RefreshView(True)
        elif self.Ticktime != 0 and self.RangeValues != TIME_RANGE_VALUES:
            self.RangeValues = TIME_RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in TIME_RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(TIME_RANGE_VALUES[0][0])
            self.CurrentRange = TIME_RANGE_VALUES[0][1] / self.Ticktime
            self.RefreshView(True)
    
    def RefreshCanvasPosition(self):
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
        self.RefreshView(True)
    
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
        for panel in self.GraphicPanels:
            panel.ResetData()
        self.RefreshView(True)
        event.Skip()

    def OnCurrentButton(self, event):
        if len(self.Ticks) > 0:
            self.StartTick = max(self.Ticks[0], self.Ticks[-1] - self.CurrentRange)
            self.Fixed = False
            self.Force = True
            self.RefreshView(True)
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
    
    def GetRange(self):
        return self.StartTick, self.StartTick + self.CurrentRange
    
    def GetViewerIndex(self, viewer):
        if viewer in self.GraphicPanels:
            return self.GraphicPanels.index(viewer)
        return None
    
    def InsertValue(self, iec_path, idx = None, force=False):
        if USE_MPL:
            for panel in self.GraphicPanels:
                if panel.GetItem(iec_path) is not None:
                    return
            if idx is None:
                idx = len(self.GraphicPanels)
        else:
            for item in self.Table.GetData():
                if iec_path == item.GetVariable():
                    return
            if idx is None:
                idx = self.Table.GetNumberRows()
        item = VariableTableItem(self, iec_path)
        result = self.AddDataConsumer(iec_path.upper(), item)
        if result is not None or force:
            
            if USE_MPL:
                if item.IsNumVariable():
                    panel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
                else:
                    panel = DebugVariableText(self.GraphicsWindow, self, [item])
                if idx is not None:
                    self.GraphicPanels.insert(idx, panel)
                else:
                    self.GraphicPanels.append(panel)
                self.RefreshGraphicsSizer()
            else:
                self.Table.InsertItem(idx, item)
            
            self.RefreshView()
    
    def MoveGraph(self, iec_path, idx = None):
        if idx is None:
            idx = len(self.GraphicPanels)
        source_panel = None
        item = None
        for panel in self.GraphicPanels:
            item = panel.GetItem(iec_path)
            if item is not None:
                source_panel = panel
                break
        if source_panel is not None:
            source_panel.RemoveItem(item)
            if source_panel.IsEmpty():
                if source_panel.Canvas.HasCapture():
                    source_panel.Canvas.ReleaseMouse()
                self.GraphicPanels.remove(source_panel)
                source_panel.Destroy()
            
            panel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
            self.GraphicPanels.insert(idx, panel)
            self.RefreshGraphicsSizer()
            self.RefreshView()
    
    def SplitGraphs(self, source_panel, item=None):
        source_idx = self.GetViewerIndex(source_panel)
        if source_idx is not None:
            
            if item is None:
                source_items = source_panel.GetItems()
                while len(source_items) > 1:
                    item = source_items.pop(-1)
                    if item.IsNumVariable():
                        panel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
                    else:
                        panel = DebugVariableText(self.GraphicsWindow, self, [item])
                    self.GraphicPanels.insert(source_idx + 1, panel)
                if isinstance(source_panel, DebugVariableGraphic):
                    source_panel.GraphType = GRAPH_PARALLEL
                    source_panel.ResetGraphics()
                    
            else:
                source_panel.RemoveItem(item)
                if item.IsNumVariable():
                    panel = DebugVariableGraphic(self.GraphicsWindow, self, [item], GRAPH_PARALLEL)
                else:
                    panel = DebugVariableText(self.GraphicsWindow, self, [item])
                self.GraphicPanels.insert(source_idx + 1, panel)
            
            self.RefreshGraphicsSizer()
            self.RefreshView()
    
    def MergeGraphs(self, source, target_idx, merge_type, force=False):
        source_item = None
        source_panel = None
        for panel in self.GraphicPanels:
            source_item = panel.GetItem(source)
            if source_item is not None:
                source_panel = panel
                break
        if source_item is None:
            item = VariableTableItem(self, source)
            if item.IsNumVariable():
                result = self.AddDataConsumer(source.upper(), item)
                if result is not None or force:
                    source_item = item
        if source_item is not None:
            target_panel = self.GraphicPanels[target_idx]
            graph_type = target_panel.GraphType
            if target_panel != source_panel:
                if (merge_type == GRAPH_PARALLEL and graph_type != merge_type or
                    merge_type == GRAPH_ORTHOGONAL and 
                    (graph_type == GRAPH_PARALLEL and len(target_panel.Items) > 1 or
                     graph_type == GRAPH_ORTHOGONAL and len(target_panel.Items) >= 3)):
                    return
                
                if source_panel is not None:
                    source_panel.RemoveItem(source_item)
                    if source_panel.IsEmpty():
                        if source_panel.Canvas.HasCapture():
                            source_panel.Canvas.ReleaseMouse()
                        self.GraphicPanels.remove(source_panel)
                        source_panel.Destroy()
                        
                target_panel.AddItem(source_item)
                target_panel.GraphType = merge_type
                target_panel.ResetGraphics()
                
                self.RefreshGraphicsSizer()
                self.RefreshView()
    
    def DeleteValue(self, source_panel, item=None):
        source_idx = self.GetViewerIndex(source_panel)
        if source_idx is not None:
            
            if item is None:
                source_panel.Clear()
                source_panel.Destroy()
                self.GraphicPanels.remove(source_panel)
                self.RefreshGraphicsSizer()
            else:
                source_panel.RemoveItem(item)
                if source_panel.IsEmpty():
                    source_panel.Destroy()
                    self.GraphicPanels.remove(source_panel)
                    self.RefreshGraphicsSizer()
            self.RefreshView()
    
    def GetDebugVariables(self):
        if USE_MPL:
            return [panel.GetVariables() for panel in self.GraphicPanels]
        else:
            return [item.GetVariable() for item in self.Table.GetData()]
    
    def SetDebugVariables(self, variables):
        if USE_MPL:
            for variable in variables:
                if isinstance(variable, (TupleType, ListType)):
                    items = []
                    for iec_path in variable:
                        item = VariableTableItem(self, iec_path)
                        if not item.IsNumVariable():
                            continue
                        self.AddDataConsumer(iec_path.upper(), item)
                        items.append(item)
                    if isinstance(variable, ListType):
                        panel = DebugVariableGraphic(self.GraphicsWindow, self, items, GRAPH_PARALLEL)
                    elif isinstance(variable, TupleType) and len(items) <= 3:
                        panel = DebugVariableGraphic(self.GraphicsWindow, self, items, GRAPH_ORTHOGONAL)
                    else:
                        continue
                    self.GraphicPanels.append(panel)
                    self.RefreshGraphicsSizer()
                else:
                    self.InsertValue(variable, force=True)
            self.RefreshView()
        else:
            for variable in variables:
                if isinstance(variable, (ListType, TupleType)):
                    for iec_path in variable:
                        self.InsertValue(iec_path, force=True)
                else:
                    self.InsertValue(variable, force=True)
    
    def ResetGraphicsValues(self):
        if USE_MPL:
            self.Ticks = numpy.array([])
            self.StartTick = 0
            for panel in self.GraphicPanels:
                panel.ResetData()

    def RefreshGraphicsWindowScrollbars(self):
        xstart, ystart = self.GraphicsWindow.GetViewStart()
        window_size = self.GraphicsWindow.GetClientSize()
        vwidth, vheight = self.GraphicsSizer.GetMinSize()
        posx = max(0, min(xstart, (vwidth - window_size[0]) / SCROLLBAR_UNIT))
        posy = max(0, min(ystart, (vheight - window_size[1]) / SCROLLBAR_UNIT))
        self.GraphicsWindow.Scroll(posx, posy)
        self.GraphicsWindow.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                vwidth / SCROLLBAR_UNIT, vheight / SCROLLBAR_UNIT, posx, posy)
    
    def OnGraphicsWindowResize(self, event):
        self.RefreshGraphicsWindowScrollbars()
        event.Skip()