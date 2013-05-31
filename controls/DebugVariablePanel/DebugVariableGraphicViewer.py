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
from time import time as gettime
import numpy

import wx

import matplotlib
matplotlib.use('WX')
import matplotlib.pyplot
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import _convert_agg_to_wx_bitmap
from matplotlib.backends.backend_agg import FigureCanvasAgg
from mpl_toolkits.mplot3d import Axes3D

from editors.DebugViewer import REFRESH_PERIOD

from DebugVariableItem import DebugVariableItem
from DebugVariableViewer import *
from GraphButton import GraphButton

GRAPH_PARALLEL, GRAPH_ORTHOGONAL = range(2)

#CANVAS_SIZE_TYPES
[SIZE_MINI, SIZE_MIDDLE, SIZE_MAXI] = [0, 100, 200]

DEFAULT_CANVAS_HEIGHT = 200.
CANVAS_BORDER = (20., 10.)
CANVAS_PADDING = 8.5
VALUE_LABEL_HEIGHT = 17.
AXES_LABEL_HEIGHT = 12.75

COLOR_CYCLE = ['r', 'b', 'g', 'm', 'y', 'k']
CURSOR_COLOR = '#800080'

def OrthogonalData(item, start_tick, end_tick):
    data = item.GetData(start_tick, end_tick)
    min_value, max_value = item.GetValueRange()
    if min_value is not None and max_value is not None:
        center = (min_value + max_value) / 2.
        range = max(1.0, max_value - min_value)
    else:
        center = 0.5
        range = 1.0
    return data, center - range * 0.55, center + range * 0.55

class DebugVariableDropTarget(wx.TextDropTarget):
    
    def __init__(self, parent, window):
        wx.TextDropTarget.__init__(self)
        self.ParentControl = parent
        self.ParentWindow = window
        
    def __del__(self):
        self.ParentControl = None
        self.ParentWindow = None
        
    def OnDragOver(self, x, y, d):
        self.ParentControl.OnMouseDragging(x, y)
        return wx.TextDropTarget.OnDragOver(self, x, y, d)
        
    def OnDropText(self, x, y, data):
        message = None
        try:
            values = eval(data)
            if not isinstance(values, TupleType):
                raise ValueError
        except:
            message = _("Invalid value \"%s\" for debug variable")%data
            values = None
        
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)
        
        elif values[1] == "debug":
            width, height = self.ParentControl.GetSize()
            target_idx = self.ParentControl.GetIndex()
            merge_type = GRAPH_PARALLEL
            if self.ParentControl.Is3DCanvas():
                if y > height / 2:
                    target_idx += 1
                if len(values) > 1 and values[2] == "move":
                    self.ParentWindow.MoveValue(values[0], target_idx)
                else:
                    self.ParentWindow.InsertValue(values[0], target_idx, force=True)
                
            else:
                rect = self.ParentControl.GetAxesBoundingBox()
                if rect.InsideXY(x, y):
                    merge_rect = wx.Rect(rect.x, rect.y, rect.width / 2., rect.height)
                    if merge_rect.InsideXY(x, y):
                        merge_type = GRAPH_ORTHOGONAL
                    wx.CallAfter(self.ParentWindow.MergeGraphs, values[0], target_idx, merge_type, force=True)
                else:
                    if y > height / 2:
                        target_idx += 1
                    if len(values) > 2 and values[2] == "move":
                        self.ParentWindow.MoveValue(values[0], target_idx)
                    else:
                        self.ParentWindow.InsertValue(values[0], target_idx, force=True)
    
    def OnLeave(self):
        self.ParentWindow.ResetHighlight()
        return wx.TextDropTarget.OnLeave(self)
    
    def ShowMessage(self, message):
        dialog = wx.MessageDialog(self.ParentWindow, message, _("Error"), wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()


class DebugVariableGraphicViewer(DebugVariableViewer, FigureCanvas):
    
    def __init__(self, parent, window, items, graph_type):
        DebugVariableViewer.__init__(self, window, items)
        
        self.CanvasSize = SIZE_MINI
        self.GraphType = graph_type
        self.CursorTick = None
        self.MouseStartPos = None
        self.StartCursorTick = None
        self.CanvasStartSize = None
        self.ContextualButtons = []
        self.ContextualButtonsItem = None
        
        self.Figure = matplotlib.figure.Figure(facecolor='w')
        self.Figure.subplotpars.update(top=0.95, left=0.1, bottom=0.1, right=0.95)
        
        FigureCanvas.__init__(self, parent, -1, self.Figure)
        self.SetWindowStyle(wx.WANTS_CHARS)
        self.SetBackgroundColour(wx.WHITE)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnEnter)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeave)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        canvas_size = self.GetCanvasMinSize()
        self.SetMinSize(canvas_size)
        self.SetDropTarget(DebugVariableDropTarget(self, window))
        self.mpl_connect('button_press_event', self.OnCanvasButtonPressed)
        self.mpl_connect('motion_notify_event', self.OnCanvasMotion)
        self.mpl_connect('button_release_event', self.OnCanvasButtonReleased)
        self.mpl_connect('scroll_event', self.OnCanvasScroll)
        
        for size, bitmap in zip([SIZE_MINI, SIZE_MIDDLE, SIZE_MAXI],
                                ["minimize_graph", "middle_graph", "maximize_graph"]):
            self.Buttons.append(GraphButton(0, 0, bitmap, self.GetOnChangeSizeButton(size)))
        for bitmap, callback in [("export_graph_mini", self.OnExportGraphButton),
                                 ("delete_graph", self.OnCloseButton)]:
            self.Buttons.append(GraphButton(0, 0, bitmap, callback))
        
        self.ResetGraphics()
        self.RefreshLabelsPosition(canvas_size.height)
        self.ShowButtons(False)
    
    def draw(self, drawDC=None):
        FigureCanvasAgg.draw(self)

        self.bitmap = _convert_agg_to_wx_bitmap(self.get_renderer(), None)
        self.bitmap.UseAlpha() 
        width, height = self.GetSize()
        bbox = self.GetAxesBoundingBox()
        
        destDC = wx.MemoryDC()
        destDC.SelectObject(self.bitmap)
        
        destGC = wx.GCDC(destDC)
        
        destGC.BeginDrawing()
        if self.Highlight == HIGHLIGHT_RESIZE:
            destGC.SetPen(HIGHLIGHT_RESIZE_PEN)
            destGC.SetBrush(HIGHLIGHT_RESIZE_BRUSH)
            destGC.DrawRectangle(0, height - 5, width, 5)
        else:
            destGC.SetPen(HIGHLIGHT_DROP_PEN)
            destGC.SetBrush(HIGHLIGHT_DROP_BRUSH)
            if self.Highlight == HIGHLIGHT_LEFT:
                destGC.DrawRectangle(bbox.x, bbox.y, 
                                     bbox.width / 2, bbox.height)
            elif self.Highlight == HIGHLIGHT_RIGHT:
                destGC.DrawRectangle(bbox.x + bbox.width / 2, bbox.y, 
                                     bbox.width / 2, bbox.height)
        
        self.DrawCommonElements(destGC, self.GetButtons())
        
        destGC.EndDrawing()
        
        self._isDrawn = True
        self.gui_repaint(drawDC=drawDC)
    
    def GetButtons(self):
        return self.Buttons + self.ContextualButtons
    
    def PopupContextualButtons(self, item, rect, style=wx.RIGHT):
        if self.ContextualButtonsItem is not None and item != self.ContextualButtonsItem:
            self.DismissContextualButtons()
        
        if self.ContextualButtonsItem is None:
            self.ContextualButtonsItem = item
            
            if self.ContextualButtonsItem.IsForced():
                self.ContextualButtons.append(
                    GraphButton(0, 0, "release", self.OnReleaseButton))
            for bitmap, callback in [("force", self.OnForceButton),
                                     ("export_graph_mini", self.OnExportItemGraphButton),
                                     ("delete_graph", self.OnRemoveItemButton)]:
                self.ContextualButtons.append(GraphButton(0, 0, bitmap, callback))
            
            offset = 0
            buttons = self.ContextualButtons[:]
            if style in [wx.TOP, wx.LEFT]:
                 buttons.reverse()
            for button in buttons:
                w, h = button.GetSize()
                if style in [wx.LEFT, wx.RIGHT]:
                    x = rect.x + (- w - offset
                                if style == wx.LEFT
                                else rect.width + offset)
                    y = rect.y + (rect.height - h) / 2
                    offset += w
                else:
                    x = rect.x + (rect.width - w ) / 2
                    y = rect.y + (- h - offset
                                  if style == wx.TOP
                                  else rect.height + offset)
                    offset += h
                button.SetPosition(x, y)
            self.ParentWindow.ForceRefresh()
    
    def DismissContextualButtons(self):
        if self.ContextualButtonsItem is not None:
            self.ContextualButtonsItem = None
            self.ContextualButtons = []
            self.ParentWindow.ForceRefresh()
    
    def IsOverContextualButton(self, x, y):
        for button in self.ContextualButtons:
            if button.HitTest(x, y):
                return True
        return False
    
    def SetMinSize(self, size):
        wx.Window.SetMinSize(self, size)
        wx.CallAfter(self.RefreshButtonsPosition)
    
    def GetOnChangeSizeButton(self, size):
        def OnChangeSizeButton():
            self.CanvasSize = size
            self.SetCanvasSize(200, self.CanvasSize)
        return OnChangeSizeButton
    
    def OnExportGraphButton(self):
        self.ExportGraph()
    
    def OnForceButton(self):
        self.ForceValue(self.ContextualButtonsItem)
        self.DismissContextualButtons()
        
    def OnReleaseButton(self):
        self.ReleaseValue(self.ContextualButtonsItem)
        self.DismissContextualButtons()
    
    def OnExportItemGraphButton(self):
        self.ExportGraph(self.ContextualButtonsItem)
        self.DismissContextualButtons()
        
    def OnRemoveItemButton(self):            
        wx.CallAfter(self.ParentWindow.DeleteValue, self, 
                     self.ContextualButtonsItem)
        self.DismissContextualButtons()
    
    def OnLeave(self, event):
        if self.Highlight != HIGHLIGHT_RESIZE or self.CanvasStartSize is None:
            DebugVariableViewer.OnLeave(self, event)
        else:
            event.Skip()
    
    def RefreshLabelsPosition(self, height):
        canvas_ratio = 1. / height
        graph_ratio = 1. / ((1.0 - (CANVAS_BORDER[0] + CANVAS_BORDER[1]) * canvas_ratio) * height)
        
        self.Figure.subplotpars.update(
            top= 1.0 - CANVAS_BORDER[1] * canvas_ratio, 
            bottom= CANVAS_BORDER[0] * canvas_ratio)
        
        if self.GraphType == GRAPH_PARALLEL or self.Is3DCanvas():
            num_item = len(self.Items)
            for idx in xrange(num_item):
                if not self.Is3DCanvas():
                    self.AxesLabels[idx].set_position(
                        (0.05, 
                         1.0 - (CANVAS_PADDING + AXES_LABEL_HEIGHT * idx) * graph_ratio))
                self.Labels[idx].set_position(
                    (0.95, 
                     CANVAS_PADDING * graph_ratio + 
                     (num_item - idx - 1) * VALUE_LABEL_HEIGHT * graph_ratio))
        else:
            self.AxesLabels[0].set_position((0.1, CANVAS_PADDING * graph_ratio))
            self.Labels[0].set_position((0.95, CANVAS_PADDING * graph_ratio))
            self.AxesLabels[1].set_position((0.05, 2 * CANVAS_PADDING * graph_ratio))
            self.Labels[1].set_position((0.05, 1.0 - CANVAS_PADDING * graph_ratio))
    
        self.Figure.subplots_adjust()
    
    def GetCanvasMinSize(self):
        return wx.Size(200, 
                       CANVAS_BORDER[0] + CANVAS_BORDER[1] + 
                       2 * CANVAS_PADDING + VALUE_LABEL_HEIGHT * len(self.Items))
    
    def SetCanvasSize(self, width, height):
        height = max(height, self.GetCanvasMinSize()[1])
        self.SetMinSize(wx.Size(width, height))
        self.RefreshLabelsPosition(height)
        self.RefreshButtonsPosition()
        self.ParentWindow.RefreshGraphicsSizer()
        
    def GetAxesBoundingBox(self, absolute=False):
        width, height = self.GetSize()
        ax, ay, aw, ah = self.figure.gca().get_position().bounds
        bbox = wx.Rect(ax * width, height - (ay + ah) * height - 1,
                       aw * width + 2, ah * height + 1)
        if absolute:
            xw, yw = self.GetPosition()
            bbox.x += xw
            bbox.y += yw
        return bbox
    
    def OnCanvasButtonPressed(self, event):
        width, height = self.GetSize()
        x, y = event.x, height - event.y
        if not self.IsOverButton(x, y):
            if event.inaxes == self.Axes:
                item_idx = None
                for i, t in ([pair for pair in enumerate(self.AxesLabels)] + 
                             [pair for pair in enumerate(self.Labels)]):
                    (x0, y0), (x1, y1) = t.get_window_extent().get_points()
                    rect = wx.Rect(x0, height - y1, x1 - x0, y1 - y0)
                    if rect.InsideXY(x, y):
                        item_idx = i
                        break
                if item_idx is not None:
                    self.ShowButtons(False)
                    self.DismissContextualButtons()
                    xw, yw = self.GetPosition()
                    self.ParentWindow.StartDragNDrop(self, 
                        self.ItemsDict.values()[item_idx], x + xw, y + yw, x + xw, y + yw)
                elif not self.Is3DCanvas():
                    self.MouseStartPos = wx.Point(x, y)
                    if event.button == 1 and event.inaxes == self.Axes:
                        self.StartCursorTick = self.CursorTick
                        self.HandleCursorMove(event)
                    elif event.button == 2 and self.GraphType == GRAPH_PARALLEL:
                        width, height = self.GetSize()
                        start_tick, end_tick = self.ParentWindow.GetRange()
                        self.StartCursorTick = start_tick
            
            elif event.button == 1 and event.y <= 5:
                self.MouseStartPos = wx.Point(x, y)
                self.CanvasStartSize = self.GetSize()
    
    def OnCanvasButtonReleased(self, event):
        if self.ParentWindow.IsDragging():
            width, height = self.GetSize()
            xw, yw = self.GetPosition()
            self.ParentWindow.StopDragNDrop(
                self.ParentWindow.DraggingAxesPanel.ItemsDict.values()[0].GetVariable(),
                xw + event.x, 
                yw + height - event.y)
        else:
            self.MouseStartPos = None
            self.StartCursorTick = None
            self.CanvasStartSize = None
            width, height = self.GetSize()
            self.HandleButton(event.x, height - event.y)
            if event.y > 5 and self.SetHighlight(HIGHLIGHT_NONE):
                self.SetCursor(wx.NullCursor)
                self.ParentWindow.ForceRefresh()
    
    def OnCanvasMotion(self, event):
        width, height = self.GetSize()
        if self.ParentWindow.IsDragging():
            xw, yw = self.GetPosition()
            self.ParentWindow.MoveDragNDrop(
                xw + event.x, 
                yw + height - event.y)
        else:
            if not self.Is3DCanvas():
                if event.button == 1 and self.CanvasStartSize is None:
                    if event.inaxes == self.Axes:
                        if self.MouseStartPos is not None:
                            self.HandleCursorMove(event)
                    elif self.MouseStartPos is not None and len(self.Items) == 1:
                        xw, yw = self.GetPosition()
                        self.ParentWindow.SetCursorTick(self.StartCursorTick)
                        self.ParentWindow.StartDragNDrop(self, 
                            self.ItemsDict.values()[0],
                            event.x + xw, height - event.y + yw, 
                            self.MouseStartPos.x + xw, self.MouseStartPos.y + yw)
                elif event.button == 2 and self.GraphType == GRAPH_PARALLEL and self.MouseStartPos is not None:
                    start_tick, end_tick = self.ParentWindow.GetRange()
                    rect = self.GetAxesBoundingBox()
                    self.ParentWindow.SetCanvasPosition(
                        self.StartCursorTick + (self.MouseStartPos.x - event.x) *
                        (end_tick - start_tick) / rect.width)    
            
            if event.button == 1 and self.CanvasStartSize is not None:
                width, height = self.GetSize()
                self.SetCanvasSize(width, 
                    self.CanvasStartSize.height + height - event.y - self.MouseStartPos.y)
                
            elif event.button in [None, "up", "down"]:
                if self.GraphType == GRAPH_PARALLEL:
                    orientation = [wx.RIGHT] * len(self.AxesLabels) + [wx.LEFT] * len(self.Labels)
                elif len(self.AxesLabels) > 0:
                    orientation = [wx.RIGHT, wx.TOP, wx.LEFT, wx.BOTTOM]
                else:
                    orientation = [wx.LEFT] * len(self.Labels)
                item_idx = None
                item_style = None
                for (i, t), style in zip([pair for pair in enumerate(self.AxesLabels)] + 
                                         [pair for pair in enumerate(self.Labels)], 
                                         orientation):
                    (x0, y0), (x1, y1) = t.get_window_extent().get_points()
                    rect = wx.Rect(x0, height - y1, x1 - x0, y1 - y0)
                    if rect.InsideXY(event.x, height - event.y):
                        item_idx = i
                        item_style = style
                        break
                if item_idx is not None:
                    self.PopupContextualButtons(self.ItemsDict.values()[item_idx], rect, item_style)
                    return 
                if not self.IsOverContextualButton(event.x, height - event.y):
                    self.DismissContextualButtons()
                
                if event.y <= 5:
                    if self.SetHighlight(HIGHLIGHT_RESIZE):
                        self.SetCursor(wx.StockCursor(wx.CURSOR_SIZENS))
                        self.ParentWindow.ForceRefresh()
                else:
                    if self.SetHighlight(HIGHLIGHT_NONE):
                        self.SetCursor(wx.NullCursor)
                        self.ParentWindow.ForceRefresh()
    
    def OnCanvasScroll(self, event):
        if event.inaxes is not None and event.guiEvent.ControlDown():
            if self.GraphType == GRAPH_ORTHOGONAL:
                start_tick, end_tick = self.ParentWindow.GetRange()
                tick = (start_tick + end_tick) / 2.
            else:
                tick = event.xdata
            self.ParentWindow.ChangeRange(int(-event.step) / 3, tick)
            self.ParentWindow.VetoScrollEvent = True
    
    def RefreshHighlight(self, x, y):
        width, height = self.GetSize()
        bbox = self.GetAxesBoundingBox()
        if bbox.InsideXY(x, y) and not self.Is3DCanvas():
            rect = wx.Rect(bbox.x, bbox.y, bbox.width / 2, bbox.height)
            if rect.InsideXY(x, y):
                self.SetHighlight(HIGHLIGHT_LEFT)
            else:
                self.SetHighlight(HIGHLIGHT_RIGHT)
        elif y < height / 2:
            if self.ParentWindow.IsViewerFirst(self):
                self.SetHighlight(HIGHLIGHT_BEFORE)
            else:
                self.SetHighlight(HIGHLIGHT_NONE)
                self.ParentWindow.HighlightPreviousViewer(self)
        else:
            self.SetHighlight(HIGHLIGHT_AFTER)
    
    def OnLeave(self, event):
        if self.CanvasStartSize is None and self.SetHighlight(HIGHLIGHT_NONE):
            self.SetCursor(wx.NullCursor)
            self.ParentWindow.ForceRefresh()
        DebugVariableViewer.OnLeave(self, event)
    
    KEY_CURSOR_INCREMENT = {
        wx.WXK_LEFT: -1,
        wx.WXK_RIGHT: 1,
        wx.WXK_UP: -10,
        wx.WXK_DOWN: 10}
    def OnKeyDown(self, event):
        if self.CursorTick is not None:
            move = self.KEY_CURSOR_INCREMENT.get(event.GetKeyCode(), None)
            if move is not None:
                self.ParentWindow.MoveCursorTick(move)
        event.Skip()
    
    def HandleCursorMove(self, event):
        start_tick, end_tick = self.ParentWindow.GetRange()
        cursor_tick = None
        items = self.ItemsDict.values()
        if self.GraphType == GRAPH_ORTHOGONAL:
            x_data = items[0].GetData(start_tick, end_tick)
            y_data = items[1].GetData(start_tick, end_tick)
            if len(x_data) > 0 and len(y_data) > 0:
                length = min(len(x_data), len(y_data))
                d = numpy.sqrt((x_data[:length,1]-event.xdata) ** 2 + (y_data[:length,1]-event.ydata) ** 2)
                cursor_tick = x_data[numpy.argmin(d), 0]
        else:
            data = items[0].GetData(start_tick, end_tick)
            if len(data) > 0:
                cursor_tick = data[numpy.argmin(numpy.abs(data[:,0] - event.xdata)), 0]
        if cursor_tick is not None:
            self.ParentWindow.SetCursorTick(cursor_tick)
    
    def OnAxesMotion(self, event):
        if self.Is3DCanvas():
            current_time = gettime()
            if current_time - self.LastMotionTime > REFRESH_PERIOD:
                self.LastMotionTime = current_time
                Axes3D._on_move(self.Axes, event)
    
    def ResetGraphics(self):
        self.Figure.clear()
        if self.Is3DCanvas():
            self.Axes = self.Figure.gca(projection='3d')
            self.Axes.set_color_cycle(['b'])
            self.LastMotionTime = gettime()
            setattr(self.Axes, "_on_move", self.OnAxesMotion)
            self.Axes.mouse_init()
            self.Axes.tick_params(axis='z', labelsize='small')
        else:
            self.Axes = self.Figure.gca()
            self.Axes.set_color_cycle(COLOR_CYCLE)
        self.Axes.tick_params(axis='x', labelsize='small')
        self.Axes.tick_params(axis='y', labelsize='small')
        self.Plots = []
        self.VLine = None
        self.HLine = None
        self.Labels = []
        self.AxesLabels = []
        if not self.Is3DCanvas():
            text_func = self.Axes.text
        else:
            text_func = self.Axes.text2D
        if self.GraphType == GRAPH_PARALLEL or self.Is3DCanvas():
            num_item = len(self.Items)
            for idx in xrange(num_item):
                if num_item == 1:
                    color = 'k'
                else:
                    color = COLOR_CYCLE[idx % len(COLOR_CYCLE)]
                if not self.Is3DCanvas():
                    self.AxesLabels.append(
                        text_func(0, 0, "", size='small',
                                  verticalalignment='top', 
                                  color=color,
                                  transform=self.Axes.transAxes))
                self.Labels.append(
                    text_func(0, 0, "", size='large', 
                              horizontalalignment='right',
                              color=color,
                              transform=self.Axes.transAxes))
        else:
            self.AxesLabels.append(
                self.Axes.text(0, 0, "", size='small',
                               transform=self.Axes.transAxes))
            self.Labels.append(
                self.Axes.text(0, 0, "", size='large',
                               horizontalalignment='right',
                               transform=self.Axes.transAxes))
            self.AxesLabels.append(
                self.Axes.text(0, 0, "", size='small',
                               rotation='vertical',
                               verticalalignment='bottom',
                               transform=self.Axes.transAxes))
            self.Labels.append(
                self.Axes.text(0, 0, "", size='large',
                               rotation='vertical',
                               verticalalignment='top',
                               transform=self.Axes.transAxes))
        width, height = self.GetSize()
        self.RefreshLabelsPosition(height)
        
    def AddItem(self, item):
        DebugVariableViewer.AddItem(self, item)
        self.ResetGraphics()
        
    def RemoveItem(self, item):
        DebugVariableViewer.RemoveItem(self, item)
        if not self.ItemsIsEmpty():
            if len(self.Items) == 1:
                self.GraphType = GRAPH_PARALLEL
            self.ResetGraphics()
    
    def SubscribeAllDataConsumers(self):
        DebugVariableViewer.SubscribeAllDataConsumers(self)
        if not self.ItemsIsEmpty():
            self.ResetGraphics()
    
    def Is3DCanvas(self):
        return self.GraphType == GRAPH_ORTHOGONAL and len(self.Items) == 3
    
    def SetCursorTick(self, cursor_tick):
        self.CursorTick = cursor_tick
        
    def RefreshViewer(self, refresh_graphics=True):
        
        if refresh_graphics:
            start_tick, end_tick = self.ParentWindow.GetRange()
            
            if self.GraphType == GRAPH_PARALLEL:    
                min_value = max_value = None
                
                for idx, item in enumerate(self.Items):
                    data = item.GetData(start_tick, end_tick)
                    if data is not None:
                        item_min_value, item_max_value = item.GetValueRange()
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
                
                if self.CursorTick is not None and start_tick <= self.CursorTick <= end_tick:
                    if self.VLine is None:
                        self.VLine = self.Axes.axvline(self.CursorTick, color=CURSOR_COLOR)
                    else:
                        self.VLine.set_xdata((self.CursorTick, self.CursorTick))
                    self.VLine.set_visible(True)
                else:
                    if self.VLine is not None:
                        self.VLine.set_visible(False)
            else:
                min_start_tick = reduce(max, [item.GetData()[0, 0] 
                                              for item in self.Items
                                              if len(item.GetData()) > 0], 0)
                start_tick = max(start_tick, min_start_tick)
                end_tick = max(end_tick, min_start_tick)
                items = self.ItemsDict.values()
                x_data, x_min, x_max = OrthogonalData(items[0], start_tick, end_tick)
                y_data, y_min, y_max = OrthogonalData(items[1], start_tick, end_tick)
                if self.CursorTick is not None:
                    x_cursor, x_forced = items[0].GetValue(self.CursorTick, raw=True)
                    y_cursor, y_forced = items[1].GetValue(self.CursorTick, raw=True)
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
                    
                    if self.CursorTick is not None and start_tick <= self.CursorTick <= end_tick:
                        if self.VLine is None:
                            self.VLine = self.Axes.axvline(x_cursor, color=CURSOR_COLOR)
                        else:
                            self.VLine.set_xdata((x_cursor, x_cursor))
                        if self.HLine is None:
                            self.HLine = self.Axes.axhline(y_cursor, color=CURSOR_COLOR)
                        else:
                            self.HLine.set_ydata((y_cursor, y_cursor))
                        self.VLine.set_visible(True)
                        self.HLine.set_visible(True)
                    else:
                        if self.VLine is not None:
                            self.VLine.set_visible(False)
                        if self.HLine is not None:
                            self.HLine.set_visible(False)
                else:
                    while len(self.Axes.lines) > 0:
                        self.Axes.lines.pop()
                    z_data, z_min, z_max = OrthogonalData(items[2], start_tick, end_tick)
                    if self.CursorTick is not None:
                        z_cursor, z_forced = items[2].GetValue(self.CursorTick, raw=True)
                    if x_data is not None and y_data is not None and z_data is not None:
                        length = min(length, len(z_data))
                        self.Axes.plot(x_data[:, 1][:length],
                                       y_data[:, 1][:length],
                                       zs = z_data[:, 1][:length])
                    self.Axes.set_zlim(z_min, z_max)
                    if self.CursorTick is not None and start_tick <= self.CursorTick <= end_tick:
                        for kwargs in [{"xs": numpy.array([x_min, x_max])},
                                       {"ys": numpy.array([y_min, y_max])},
                                       {"zs": numpy.array([z_min, z_max])}]:
                            for param, value in [("xs", numpy.array([x_cursor, x_cursor])),
                                                 ("ys", numpy.array([y_cursor, y_cursor])),
                                                 ("zs", numpy.array([z_cursor, z_cursor]))]:
                                kwargs.setdefault(param, value)
                            kwargs["color"] = CURSOR_COLOR
                            self.Axes.plot(**kwargs)
                
            self.Axes.set_xlim(x_min, x_max)
            self.Axes.set_ylim(y_min, y_max)
        
        variable_name_mask = self.ParentWindow.GetVariableNameMask()
        if self.CursorTick is not None:
            values, forced = apply(zip, [item.GetValue(self.CursorTick) for item in self.Items])
        else:
            values, forced = apply(zip, [(item.GetValue(), item.IsForced()) for item in self.Items])
        labels = [item.GetVariable(variable_name_mask) for item in self.Items]
        styles = map(lambda x: {True: 'italic', False: 'normal'}[x], forced)
        if self.Is3DCanvas():
            for idx, label_func in enumerate([self.Axes.set_xlabel, 
                                              self.Axes.set_ylabel,
                                              self.Axes.set_zlabel]):
                label_func(labels[idx], fontdict={'size': 'small','color': COLOR_CYCLE[idx]})
        else:
            for label, text in zip(self.AxesLabels, labels):
                label.set_text(text)
        for label, value, style in zip(self.Labels, values, styles):
            label.set_text(value)
            label.set_style(style)
        
        self.draw()

    def ExportGraph(self, item=None):
        if item is not None:
            variables = [(item, [entry for entry in item.GetData()])]
        else:
            variables = [(item, [entry for entry in item.GetData()])
                         for item in self.Items]
        self.ParentWindow.CopyDataToClipboard(variables)
