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

import numpy
import math

import wx
import wx.lib.plot as plot
import wx.lib.buttons

from graphics.GraphicCommons import DebugViewer, MODE_SELECTION, MODE_MOTION
from EditorPanel import EditorPanel
from util.BitmapLibrary import GetBitmap

colours = ['blue', 'red', 'green', 'yellow', 'orange', 'purple', 'brown', 'cyan',
           'pink', 'grey']
markers = ['circle', 'dot', 'square', 'triangle', 'triangle_down', 'cross', 'plus', 'circle']


#-------------------------------------------------------------------------------
#                       Debug Variable Graphic Viewer class
#-------------------------------------------------------------------------------

SECOND = 1000000000
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

ZOOM_VALUES = map(lambda x:("x %.1f" % x, x), [math.sqrt(2) ** i for i in xrange(8)])
RANGE_VALUES = map(lambda x: (str(x), x), [25 * 2 ** i for i in xrange(6)])
TIME_RANGE_VALUES = [("%ds" % i, i * SECOND) for i in (1, 2, 5, 10, 20, 30)] + \
                    [("%dm" % i, i * MINUTE) for i in (1, 2, 5, 10, 20, 30)] + \
                    [("%dh" % i, i * HOUR) for i in (1, 2, 3, 6, 12, 24)]

class GraphicViewer(EditorPanel, DebugViewer):

    def _init_Editor(self, prnt):
        self.Editor = wx.Panel(prnt)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        self.Canvas = plot.PlotCanvas(self.Editor, name='Canvas')
        def _axisInterval(spec, lower, upper):
            if spec == 'border':
                if lower == upper:
                    return lower - 0.5, upper + 0.5
                else:
                    border = (upper - lower) * 0.05
                    return lower - border, upper + border
            else:
                return plot.PlotCanvas._axisInterval(self.Canvas, spec, lower, upper)
        self.Canvas._axisInterval = _axisInterval
        self.Canvas.SetYSpec('border')
        self.Canvas.canvas.Bind(wx.EVT_LEFT_DOWN, self.OnCanvasLeftDown)
        self.Canvas.canvas.Bind(wx.EVT_LEFT_UP, self.OnCanvasLeftUp)
        self.Canvas.canvas.Bind(wx.EVT_MIDDLE_DOWN, self.OnCanvasMiddleDown)
        self.Canvas.canvas.Bind(wx.EVT_MIDDLE_UP, self.OnCanvasMiddleUp)
        self.Canvas.canvas.Bind(wx.EVT_MOTION, self.OnCanvasMotion)
        self.Canvas.canvas.Bind(wx.EVT_SIZE, self.OnCanvasResize)
        main_sizer.AddWindow(self.Canvas, 0, border=0, flag=wx.GROW)
        
        range_sizer = wx.FlexGridSizer(cols=10, hgap=5, rows=1, vgap=0)
        range_sizer.AddGrowableCol(5)
        range_sizer.AddGrowableRow(0)
        main_sizer.AddSizer(range_sizer, 0, border=5, flag=wx.GROW|wx.ALL)
        
        range_label = wx.StaticText(self.Editor, label=_('Range:'))
        range_sizer.AddWindow(range_label, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.CanvasRange = wx.ComboBox(self.Editor, 
              size=wx.Size(100, 28), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnRangeChanged, self.CanvasRange)
        range_sizer.AddWindow(self.CanvasRange, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        
        zoom_label = wx.StaticText(self.Editor, label=_('Zoom:'))
        range_sizer.AddWindow(zoom_label, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.CanvasZoom = wx.ComboBox(self.Editor, 
              size=wx.Size(70, 28), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnZoomChanged, self.CanvasZoom)
        range_sizer.AddWindow(self.CanvasZoom, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        
        position_label = wx.StaticText(self.Editor, label=_('Position:'))
        range_sizer.AddWindow(position_label, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.CanvasPosition = wx.ScrollBar(self.Editor, 
              size=wx.Size(0, 16), style=wx.SB_HORIZONTAL)
        self.CanvasPosition.SetScrollbar(0, 10, 100, 10)
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
        range_sizer.AddWindow(self.CanvasPosition, 0, border=5, flag=wx.GROW|wx.ALL)
        
        self.ResetButton = wx.lib.buttons.GenBitmapButton(self.Editor, 
              bitmap=GetBitmap("reset"), size=wx.Size(28, 28), style=wx.NO_BORDER)
        self.ResetButton.SetToolTipString(_("Clear the graph values"))
        self.Bind(wx.EVT_BUTTON, self.OnResetButton, self.ResetButton)
        range_sizer.AddWindow(self.ResetButton, 0, border=0, flag=0)
        
        self.CurrentButton = wx.lib.buttons.GenBitmapButton(self.Editor, 
              bitmap=GetBitmap("current"), size=wx.Size(28, 28), style=wx.NO_BORDER)
        self.CurrentButton.SetToolTipString(_("Go to current value"))
        self.Bind(wx.EVT_BUTTON, self.OnCurrentButton, self.CurrentButton)
        range_sizer.AddWindow(self.CurrentButton, 0, border=0, flag=0)
        
        self.ResetZoomOffsetButton = wx.lib.buttons.GenBitmapButton(self.Editor, 
              bitmap=GetBitmap("fit"), size=wx.Size(28, 28), style=wx.NO_BORDER)
        self.ResetZoomOffsetButton.SetToolTipString(_("Reset zoom and offset"))
        self.Bind(wx.EVT_BUTTON, self.OnResetZoomOffsetButton, 
              self.ResetZoomOffsetButton)
        range_sizer.AddWindow(self.ResetZoomOffsetButton, 0, border=0, flag=0)
        
        self.ExportGraphButton = wx.lib.buttons.GenBitmapButton(self.Editor, 
              bitmap=GetBitmap("export_graph"), size=wx.Size(28, 28), style=wx.NO_BORDER)
        self.ExportGraphButton.SetToolTipString(_("Export graph values to clipboard"))
        self.Bind(wx.EVT_BUTTON, self.OnExportGraphButtonClick, 
                self.ExportGraphButton)
        range_sizer.AddWindow(self.ExportGraphButton, 0, border=0, flag=0)
        
        self.Editor.SetSizer(main_sizer)

        self.Editor.Bind(wx.EVT_MOUSEWHEEL, self.OnCanvasMouseWheel)

    def __init__(self, parent, window, producer, instancepath = ""):
        EditorPanel.__init__(self, parent, "", window, None)
        DebugViewer.__init__(self, producer, True, False)
        
        self.InstancePath = instancepath
        self.RangeValues = None
        self.CursorIdx = None
        self.LastCursor = None
        self.CurrentMousePos = None
        self.CurrentMotionValue = None
        self.Dragging = False
        
        # Initialize Viewer mode to Selection mode
        self.Mode = MODE_SELECTION
        
        self.Data = numpy.array([]).reshape(0, 2)
        self.StartTick = 0
        self.StartIdx = 0
        self.EndIdx = 0
        self.MinValue = None
        self.MaxValue = None
        self.YCenter = 0
        self.CurrentZoom = 1.0
        self.Fixed = False
        self.Ticktime = self.DataProducer.GetTicktime()
        self.RefreshCanvasRange()
        
        for zoom_txt, zoom in ZOOM_VALUES:
            self.CanvasZoom.Append(zoom_txt)
        self.CanvasZoom.SetSelection(0)
        
        self.AddDataConsumer(self.InstancePath.upper(), self)
    
    def __del__(self):
        DebugViewer.__del__(self)
        self.RemoveDataConsumer(self)
    
    def GetTitle(self):
        if len(self.InstancePath) > 15:
            return "..." + self.InstancePath[-12:]
        return self.InstancePath
    
    # Changes Viewer mode
    def SetMode(self, mode):
        if self.Mode != mode or mode == MODE_SELECTION:    
            if self.Mode == MODE_MOTION:
                wx.CallAfter(self.Canvas.canvas.SetCursor, wx.NullCursor)
            self.Mode = mode
        if self.Mode == MODE_MOTION:
            wx.CallAfter(self.Canvas.canvas.SetCursor, wx.StockCursor(wx.CURSOR_HAND))
        
    def ResetView(self, register=False):
        self.Data = numpy.array([]).reshape(0, 2)
        self.StartTick = 0
        self.StartIdx = 0
        self.EndIdx = 0
        self.MinValue = None
        self.MaxValue = None
        self.CursorIdx = None
        self.Fixed = False
        self.Ticktime = self.DataProducer.GetTicktime()
        if register:
            self.AddDataConsumer(self.InstancePath.upper(), self)
        self.ResetLastCursor()
        self.RefreshCanvasRange()
        self.RefreshView()
    
    def RefreshNewData(self, *args, **kwargs):
        self.RefreshView(*args, **kwargs)
        DebugViewer.RefreshNewData(self)
    
    def GetNearestData(self, tick, adjust):
        ticks = self.Data[:, 0]
        new_cursor = numpy.argmin(abs(ticks - tick))
        if adjust == -1 and ticks[new_cursor] > tick and new_cursor > 0:
            new_cursor -= 1
        elif adjust == 1 and ticks[new_cursor] < tick and new_cursor < len(ticks):
            new_cursor += 1
        return new_cursor
    
    def GetBounds(self):
        if self.StartIdx is None or self.EndIdx is None:
            self.StartIdx = self.GetNearestData(self.StartTick, -1)
            self.EndIdx = self.GetNearestData(self.StartTick + self.CurrentRange, 1)
    
    def ResetBounds(self):
        self.StartIdx = None
        self.EndIdx = None
    
    def RefreshCanvasRange(self):
        if self.Ticktime == 0 and self.RangeValues != RANGE_VALUES:
            self.RangeValues = RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(RANGE_VALUES[0][0])
            self.CurrentRange = RANGE_VALUES[0][1]
        elif self.RangeValues != TIME_RANGE_VALUES:
            self.RangeValues = TIME_RANGE_VALUES
            self.CanvasRange.Clear()
            for text, value in TIME_RANGE_VALUES:
                self.CanvasRange.Append(text)
            self.CanvasRange.SetStringSelection(TIME_RANGE_VALUES[0][0])
            self.CurrentRange = TIME_RANGE_VALUES[0][1] / self.Ticktime
        
    def RefreshView(self, force=False):
        self.Freeze()
        if force or not self.Fixed or (len(self.Data) > 0 and self.StartTick + self.CurrentRange > self.Data[-1, 0]):
            if (self.MinValue is not None and 
                self.MaxValue is not None and 
                self.MinValue != self.MaxValue):
                Yrange = float(self.MaxValue - self.MinValue) / self.CurrentZoom
            else:
                Yrange = 2. / self.CurrentZoom
            
            if not force and not self.Fixed and len(self.Data) > 0:
                self.YCenter = max(self.Data[-1, 1] - Yrange / 2, 
                               min(self.YCenter, 
                                   self.Data[-1, 1] + Yrange / 2))
            
            var_name = self.InstancePath.split(".")[-1]
            
            self.GetBounds()
            self.VariableGraphic = plot.PolyLine(self.Data[self.StartIdx:self.EndIdx + 1], 
                                                 legend=var_name, colour=colours[0])
            self.GraphicsObject = plot.PlotGraphics([self.VariableGraphic], _("%s Graphics") % var_name, _("Tick"), _("Values"))
            self.Canvas.Draw(self.GraphicsObject, 
                             xAxis=(self.StartTick, self.StartTick + self.CurrentRange),
                             yAxis=(self.YCenter - Yrange * 1.1 / 2., self.YCenter + Yrange * 1.1 / 2.))
        
            # Reset and draw cursor 
            self.ResetLastCursor()
            self.RefreshCursor()
        
        self.RefreshScrollBar()
        
        self.Thaw()
    
    def GetInstancePath(self):
        return self.InstancePath
    
    def IsViewing(self, tagname):
        return self.InstancePath == tagname
    
    def NewValue(self, tick, value, forced=False):
        value = {True:1., False:0.}.get(value, float(value))
        self.Data = numpy.append(self.Data, [[float(tick), value]], axis=0)
        if self.MinValue is None:
            self.MinValue = value
        else:
            self.MinValue = min(self.MinValue, value)
        if self.MaxValue is None:
            self.MaxValue = value
        else:
            self.MaxValue = max(self.MaxValue, value)
        if not self.Fixed or tick < self.StartTick + self.CurrentRange:
            self.GetBounds()
            while int(self.Data[self.StartIdx, 0]) < tick - self.CurrentRange:
                self.StartIdx += 1
            self.EndIdx += 1
            self.StartTick = self.Data[self.StartIdx, 0]
        self.NewDataAvailable(None)
    
    def RefreshScrollBar(self):
        if len(self.Data) > 0:
            self.GetBounds()
            pos = int(self.Data[self.StartIdx, 0] - self.Data[0, 0])
            range = int(self.Data[-1, 0] - self.Data[0, 0])
        else:
            pos = 0
            range = 0
        self.CanvasPosition.SetScrollbar(pos, self.CurrentRange, range, self.CurrentRange)

    def RefreshRange(self):
        if len(self.Data) > 0:
            if self.Fixed and self.Data[-1, 0] - self.Data[0, 0] < self.CurrentRange:
                self.Fixed = False
            self.ResetBounds()
            if self.Fixed:
                self.StartTick = min(self.StartTick, self.Data[-1, 0] - self.CurrentRange)
            else:
                self.StartTick = max(self.Data[0, 0], self.Data[-1, 0] - self.CurrentRange)
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
    
    def OnZoomChanged(self, event):
        self.CurrentZoom = ZOOM_VALUES[self.CanvasZoom.GetSelection()][1]
        wx.CallAfter(self.RefreshView, True)
        event.Skip()
    
    def OnPositionChanging(self, event):
        if len(self.Data) > 0:
            self.ResetBounds()
            self.StartTick = self.Data[0, 0] + event.GetPosition()
            self.Fixed = True
            self.NewDataAvailable(None, True)
        event.Skip()

    def OnResetButton(self, event):
        self.Fixed = False
        self.ResetView()
        event.Skip()

    def OnCurrentButton(self, event):
        if len(self.Data) > 0:
            self.ResetBounds()
            self.StartTick = max(self.Data[0, 0], self.Data[-1, 0] - self.CurrentRange)
            self.Fixed = False
            self.NewDataAvailable(None, True)
        event.Skip()
    
    def OnResetZoomOffsetButton(self, event):
        if len(self.Data) > 0:
            self.YCenter = (self.MaxValue + self.MinValue) / 2
        else:
            self.YCenter = 0.0
        self.CurrentZoom = 1.0
        self.CanvasZoom.SetSelection(0)
        wx.CallAfter(self.RefreshView, True)
        event.Skip()
    
    def OnExportGraphButtonClick(self, event):
        data_copy = self.Data[:]
        text = "tick;%s;\n" % self.InstancePath
        for tick, value in data_copy:
            text += "%d;%.3f;\n" % (tick, value)
        self.ParentWindow.SetCopyBuffer(text)
        event.Skip()

    def OnCanvasLeftDown(self, event):
        self.Fixed = True
        self.Canvas.canvas.CaptureMouse()
        if len(self.Data) > 0:
            if self.Mode == MODE_SELECTION:
                self.Dragging = True
                pos = self.Canvas.PositionScreenToUser(event.GetPosition())
                self.CursorIdx = self.GetNearestData(pos[0], -1)
                self.RefreshCursor()
            elif self.Mode == MODE_MOTION:
                self.GetBounds()
                self.CurrentMousePos = event.GetPosition()
                self.CurrentMotionValue = self.Data[self.StartIdx, 0]
        event.Skip()
    
    def OnCanvasLeftUp(self, event):
        self.Dragging = False
        if self.Mode == MODE_MOTION:
            self.CurrentMousePos = None
            self.CurrentMotionValue = None
        if self.Canvas.canvas.HasCapture():
            self.Canvas.canvas.ReleaseMouse()
        event.Skip()
    
    def OnCanvasMiddleDown(self, event):
        self.Fixed = True
        self.Canvas.canvas.CaptureMouse()
        if len(self.Data) > 0:
            self.GetBounds()
            self.CurrentMousePos = event.GetPosition()
            self.CurrentMotionValue = self.Data[self.StartIdx, 0]
        event.Skip()
        
    def OnCanvasMiddleUp(self, event):
        self.CurrentMousePos = None
        self.CurrentMotionValue = None
        if self.Canvas.canvas.HasCapture():
            self.Canvas.canvas.ReleaseMouse()
        event.Skip()
        
    def OnCanvasMotion(self, event):
        if self.Mode == MODE_SELECTION and self.Dragging:
            pos = self.Canvas.PositionScreenToUser(event.GetPosition())
            graphics, xAxis, yAxis = self.Canvas.last_draw
            self.CursorIdx = self.GetNearestData(max(xAxis[0], min(pos[0], xAxis[1])), -1)
            self.RefreshCursor()
        elif self.CurrentMousePos is not None and len(self.Data) > 0:
            oldpos = self.Canvas.PositionScreenToUser(self.CurrentMousePos)
            newpos = self.Canvas.PositionScreenToUser(event.GetPosition())
            self.CurrentMotionValue += oldpos[0] - newpos[0]
            self.YCenter += oldpos[1] - newpos[1]
            self.ResetBounds()
            self.StartTick = max(self.Data[0, 0], min(self.CurrentMotionValue, self.Data[-1, 0] - self.CurrentRange))
            self.CurrentMousePos = event.GetPosition()
            self.NewDataAvailable(None, True)
        event.Skip()

    def OnCanvasMouseWheel(self, event):
        if self.CurrentMousePos is None:
            rotation = event.GetWheelRotation() / event.GetWheelDelta()
            if event.ShiftDown():
                current = self.CanvasRange.GetSelection()
                new = max(0, min(current - rotation, len(self.RangeValues) - 1))
                if new != current:
                    if self.Ticktime == 0:
                        self.CurrentRange = self.RangeValues[new][1]
                    else:
                        self.CurrentRange = self.RangeValues[new][1] / self.Ticktime
                    self.CanvasRange.SetStringSelection(self.RangeValues[new][0])
                    wx.CallAfter(self.RefreshRange)
            else:
                current = self.CanvasZoom.GetSelection()
                new = max(0, min(current + rotation, len(ZOOM_VALUES) - 1))
                if new != current:
                    self.CurrentZoom = ZOOM_VALUES[new][1]
                    self.CanvasZoom.SetStringSelection(ZOOM_VALUES[new][0])
                    wx.CallAfter(self.RefreshView, True)
        event.Skip()

    def OnCanvasResize(self, event):
        self.ResetLastCursor()
        wx.CallAfter(self.RefreshCursor)
        event.Skip()

    ## Reset the last cursor
    def ResetLastCursor(self):
        self.LastCursor = None

    ## Draw the cursor on graphic
    #  @param dc The draw canvas
    #  @param cursor The cursor parameters
    def DrawCursor(self, dc, cursor, value):
        if self.StartTick <= cursor <= self.StartTick + self.CurrentRange:
            # Prepare temporary dc for drawing
            width = self.Canvas._Buffer.GetWidth()
            height = self.Canvas._Buffer.GetHeight()
            tmp_Buffer = wx.EmptyBitmap(width, height)
            dcs = wx.MemoryDC()
            dcs.SelectObject(tmp_Buffer)
            dcs.Clear()
            dcs.BeginDrawing()
            
            dcs.SetPen(wx.Pen(wx.RED))
            dcs.SetBrush(wx.Brush(wx.RED, wx.SOLID))
            dcs.SetFont(self.Canvas._getFont(self.Canvas._fontSizeAxis))
            
            # Calculate clipping region
            graphics, xAxis, yAxis = self.Canvas.last_draw
            p1 = numpy.array([xAxis[0], yAxis[0]])
            p2 = numpy.array([xAxis[1], yAxis[1]])
            cx, cy, cwidth, cheight = self.Canvas._point2ClientCoord(p1, p2)
            
            px, py = self.Canvas.PositionUserToScreen((float(cursor), 0.))
            
            # Draw line cross drawing for diaplaying time cursor
            dcs.DrawLine(px, cy + 1, px, cy + cheight - 1)
            
            lines = ("X:%d\nY:%f" % (cursor, value)).splitlines()
            
            wtext = 0
            for line in lines:
                w, h = dcs.GetTextExtent(line)
                wtext = max(wtext, w)
            
            offset = 0
            for line in lines:
                # Draw time cursor date
                dcs.DrawText(line, min(px + 3, cx + cwidth - wtext), cy + 3 + offset)
                w, h = dcs.GetTextExtent(line)
                offset += h
            
            dcs.EndDrawing()
    
            #this will erase if called twice
            dc.Blit(0, 0, width, height, dcs, 0, 0, wx.EQUIV)  #(NOT src) XOR dst
    
    ## Refresh the variable cursor.
    #  @param dc The draw canvas
    def RefreshCursor(self, dc=None):
        if self:
            if dc is None:
                dc = wx.BufferedDC(wx.ClientDC(self.Canvas.canvas), self.Canvas._Buffer)
            
            # Erase previous time cursor if drawn
            if self.LastCursor is not None:
                self.DrawCursor(dc, *self.LastCursor)
            
            # Draw new time cursor
            if self.CursorIdx is not None:
                self.LastCursor = self.Data[self.CursorIdx]
                self.DrawCursor(dc, *self.LastCursor)
