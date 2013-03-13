#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2013: Edouard TISSERANT and Laurent BESSARD
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

from datetime import datetime

import wx

from graphics import DebugViewer, REFRESH_PERIOD
from targets.typemapping import LogLevelsCount, LogLevels
from util.BitmapLibrary import GetBitmap

SPEED_VALUES = [10, 5, 2, 1, 0, -1, -2, -5, -10]

class MyScrollBar(wx.Panel):
    
    def __init__(self, parent, size):
        wx.Panel.__init__(self, parent, size=size)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
        self.Bind(wx.EVT_MOTION, self.OnMotion)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        self.ThumbPosition = SPEED_VALUES.index(0)
        self.ThumbScrolling = False
    
    def GetRangeRect(self):
        width, height = self.GetClientSize()
        return wx.Rect(0, width, width, height - 2 * width)
    
    def GetThumbRect(self):
        width, height = self.GetClientSize()
        range_rect = self.GetRangeRect()
        if self.Parent.IsMessagePanelTop():
            thumb_start = 0
        else:
            thumb_start = int(float(self.ThumbPosition * range_rect.height) / len(SPEED_VALUES))
        if self.Parent.IsMessagePanelBottom():
            thumb_end = range_rect.height
        else:
            thumb_end = int(float((self.ThumbPosition + 1) * range_rect.height) / len(SPEED_VALUES))
        return wx.Rect(1, range_rect.y + thumb_start, width - 1, thumb_end - thumb_start)
    
    def OnLeftDown(self, event):
        self.CaptureMouse()
        posx, posy = event.GetPosition()
        width, height = self.GetClientSize()
        range_rect = self.GetRangeRect()
        thumb_rect = self.GetThumbRect()
        if range_rect.InsideXY(posx, posy):
            if thumb_rect.InsideXY(posx, posy):
                self.ThumbScrolling = True
            elif posy < thumb_rect.y:
                self.Parent.ScrollPageUp()
            elif posy > thumb_rect.y + thumb_rect.height:
                self.Parent.ScrollPageDown()
        elif posy < width:
            self.Parent.SetScrollSpeed(1)
        elif posy > height - width:
            self.Parent.SetScrollSpeed(-1)
        event.Skip()
        
    def OnLeftUp(self, event):
        self.ThumbScrolling = False
        self.ThumbPosition = SPEED_VALUES.index(0)
        self.Parent.SetScrollSpeed(SPEED_VALUES[self.ThumbPosition])
        self.Refresh()
        if self.HasCapture():
            self.ReleaseMouse()
        event.Skip()
        
    def OnMotion(self, event):
        if event.Dragging() and self.ThumbScrolling:
            posx, posy = event.GetPosition()
            width, height = self.GetClientSize()
            range_rect = self.GetRangeRect()
            if range_rect.InsideXY(posx, posy):
                new_thumb_position = int(float(posy - range_rect.y) * len(SPEED_VALUES) / range_rect.height)
                thumb_rect = self.GetThumbRect()
                if self.ThumbPosition == SPEED_VALUES.index(0):
                    if thumb_rect.y == width:
                        new_thumb_position = max(new_thumb_position, SPEED_VALUES.index(0))
                    if thumb_rect.y + thumb_rect.height == height - width:
                        new_thumb_position = min(new_thumb_position, SPEED_VALUES.index(0))
                if new_thumb_position != self.ThumbPosition:
                    self.ThumbPosition = new_thumb_position
                    self.Parent.SetScrollSpeed(SPEED_VALUES[new_thumb_position])
                    self.Refresh()
        event.Skip()
    
    def OnResize(self, event):
        self.Refresh()
        event.Skip()
    
    def OnPaint(self, event):
        dc = wx.BufferedPaintDC(self)
        dc.Clear()
        dc.BeginDrawing()
        
        dc.SetPen(wx.GREY_PEN)
        dc.SetBrush(wx.GREY_BRUSH)
        
        width, height = self.GetClientSize()
        
        dc.DrawPolygon([wx.Point(width / 2, 1),
                        wx.Point(1, width - 2),
                        wx.Point(width - 1, width - 2)])
        
        dc.DrawPolygon([wx.Point(width / 2, height - 1),
                        wx.Point(2, height - width + 1),
                        wx.Point(width - 1, height - width + 1)])
        
        thumb_rect = self.GetThumbRect()
        dc.DrawRectangle(thumb_rect.x, thumb_rect.y, 
                         thumb_rect.width, thumb_rect.height)
        
        dc.EndDrawing()
        event.Skip()

DATE_INFO_SIZE = 10
MESSAGE_INFO_SIZE = 30

class LogMessage:
    
    def __init__(self, tv_sec, tv_nsec, level, level_bitmap, msg):
        self.Date = datetime.fromtimestamp(tv_sec)
        self.Seconds = self.Date.second + tv_nsec * 1e-9
        self.Date = self.Date.replace(second=0)
        self.Level = level
        self.LevelBitmap = level_bitmap
        self.Message = msg
        self.DrawDate = True
    
    def __cmp__(self, other):
        if self.Date == other.Date:
            return cmp(self.Seconds, other.Seconds)
        return cmp(self.Date, other.Date)
    
    def Draw(self, dc, offset, width, draw_date):
        if draw_date:
            datetime_text = self.Date.strftime("%d/%m/%y %H:%M")
            dw, dh = dc.GetTextExtent(datetime_text)
            dc.DrawText(datetime_text, (width - dw) / 2, offset + (DATE_INFO_SIZE - dh) / 2)
            offset += DATE_INFO_SIZE
        
        seconds_text = "%12.9f" % self.Seconds
        sw, sh = dc.GetTextExtent(seconds_text)
        dc.DrawText(seconds_text, 5, offset + (MESSAGE_INFO_SIZE - sh) / 2)
        
        bw, bh = self.LevelBitmap.GetWidth(), self.LevelBitmap.GetHeight()
        dc.DrawBitmap(self.LevelBitmap, 10 + sw, offset + (MESSAGE_INFO_SIZE - bh) / 2)
        
        mw, mh = dc.GetTextExtent(self.Message)
        dc.DrawText(self.Message, 15 + sw + bw, offset + (MESSAGE_INFO_SIZE - mh) / 2)
        
    def GetHeight(self, draw_date):
        if draw_date:
            return DATE_INFO_SIZE + MESSAGE_INFO_SIZE
        return MESSAGE_INFO_SIZE

SECOND = 1
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR

CHANGE_TIMESTAMP_BUTTONS = [(_("1d"), DAY),
                            (_("1h"), HOUR),
                            (_("1m"), MINUTE),
                            (_("1s"), SECOND)]
REVERSE_CHANGE_TIMESTAMP_BUTTONS = CHANGE_TIMESTAMP_BUTTONS[:]
REVERSE_CHANGE_TIMESTAMP_BUTTONS.reverse()

class LogViewer(DebugViewer, wx.Panel):
    
    def __init__(self, parent, window):
        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER)
        DebugViewer.__init__(self, None, False, False)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        filter_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(filter_sizer, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW)
        
        self.MessageFilter = wx.ComboBox(self, style=wx.CB_READONLY)
        self.MessageFilter.Append(_("All"))
        levels = LogLevels[:3]
        levels.reverse()
        for level in levels:
            self.MessageFilter.Append(_(level))
        self.Bind(wx.EVT_COMBOBOX, self.OnMessageFilterChanged, self.MessageFilter)
        filter_sizer.AddWindow(self.MessageFilter, 1, border=5, flag=wx.RIGHT|wx.GROW)
        
        self.SearchMessage = wx.SearchCtrl(self)
        self.SearchMessage.ShowSearchButton(True)
        self.Bind(wx.EVT_TEXT, self.OnSearchMessageChanged, self.SearchMessage)
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, 
              self.OnSearchMessageButtonClick, self.SearchMessage)
        filter_sizer.AddWindow(self.SearchMessage, 3, flag=wx.GROW)
        
        message_panel_sizer = wx.FlexGridSizer(cols=3, hgap=0, rows=1, vgap=0)
        message_panel_sizer.AddGrowableCol(1)
        message_panel_sizer.AddGrowableRow(0)
        main_sizer.AddSizer(message_panel_sizer, border=5, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.GROW)
        
        buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        for label, callback in [(_("First"), self.OnFirstButton)] + \
                               [("+" + text, self.GenerateOnDurationButton(duration)) 
                                for text, duration in CHANGE_TIMESTAMP_BUTTONS] +\
                               [("-" + text, self.GenerateOnDurationButton(-duration)) 
                                for text, duration in REVERSE_CHANGE_TIMESTAMP_BUTTONS] + \
                               [(_("Last"), self.OnLastButton)]:
            button = wx.Button(self, label=label)
            self.Bind(wx.EVT_BUTTON, callback, button)
            buttons_sizer.AddWindow(button, 1, wx.ALIGN_CENTER_VERTICAL)
        message_panel_sizer.AddSizer(buttons_sizer, flag=wx.GROW)
        
        self.MessagePanel = wx.Panel(self)
        if wx.Platform == '__WXMSW__':
            self.Font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName='Courier New')
        else:
            self.Font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName='Courier')    
        self.MessagePanel.Bind(wx.EVT_PAINT, self.OnMessagePanelPaint)
        self.MessagePanel.Bind(wx.EVT_SIZE, self.OnMessagePanelResize)
        message_panel_sizer.AddWindow(self.MessagePanel, flag=wx.GROW)
        
        self.MessageScrollBar = MyScrollBar(self, wx.Size(16, -1))
        message_panel_sizer.AddWindow(self.MessageScrollBar, flag=wx.GROW)
        
        self.SetSizer(main_sizer)
    
        self.MessageFilter.SetSelection(0)
        self.LogSource = None
        self.ResetLogMessages()
        self.ParentWindow = window
    
        self.LevelIcons = [GetBitmap("LOG_" + level) for level in LogLevels]
        self.LevelFilters = [range(i) for i in xrange(4, 0, -1)]
        self.CurrentFilter = self.LevelFilters[0]
        
        self.ScrollSpeed = 0
        self.ScrollTimer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnScrollTimer, self.ScrollTimer)
    
    def __del__(self):
        self.ScrollTimer.Stop()
    
    def ResetLogMessages(self):
        self.previous_log_count = [None]*LogLevelsCount
        self.OldestMessages = []
        self.LogMessages = []
        self.CurrentMessage = None
        self.HasNewData = False
    
    def SetLogSource(self, log_source):
        self.LogSource = log_source
        if log_source is not None:
            self.ResetLogMessages()
            self.RefreshView()
    
    def GetLogMessageFromSource(self, msgidx, level):
        if self.LogSource is not None:
            answer = self.LogSource.GetLogMessage(level, msgidx)
            if answer is not None:
                msg, tick, tv_sec, tv_nsec = answer
                return LogMessage(tv_sec, tv_nsec, level, self.LevelIcons[level], msg)
        return None
    
    def SetLogCounters(self, log_count):
        new_messages = []
        for level, count, prev in zip(xrange(LogLevelsCount), log_count, self.previous_log_count):
            if count is not None and prev != count:
                if prev is None:
                    dump_end = count - 2
                else:
                    dump_end = prev - 1
                for msgidx in xrange(count-1, dump_end,-1):
                    new_message = self.GetLogMessageFromSource(msgidx, level)
                    if new_message is not None:
                        if prev is None:
                            self.OldestMessages.append((msgidx, new_message))
                            if len(new_messages) == 0 or new_message > new_messages[0]:
                                new_messages = [new_message]
                        else:
                            new_messages.insert(0, new_message)
                    else:
                        if prev is None:
                            self.OldestMessages.append((-1, None))
                        break
                self.previous_log_count[level] = count
        new_messages.sort()
        if len(new_messages) > 0:
            self.HasNewData = True
            old_length = len(self.LogMessages)
            for new_message in new_messages:
                self.LogMessages.append(new_message)
            if self.CurrentMessage is None or self.CurrentMessage == old_length - 1:
                self.CurrentMessage = len(self.LogMessages) - 1
            self.NewDataAvailable(None)
    
    def GetNextMessage(self, msgidx, levels=range(4)):
        while msgidx < len(self.LogMessages) - 1:
            message = self.LogMessages[msgidx + 1]
            if message.Level in levels:
                return message, msgidx + 1
            msgidx += 1
        return None, None
            
    def GetPreviousMessage(self, msgidx, levels=range(4)):
        message = None
        while 0 < msgidx < len(self.LogMessages):
            message = self.LogMessages[msgidx - 1]
            if message.Level in levels:
                return message, msgidx - 1
            msgidx -= 1
        if len(self.LogMessages) > 0:
            message = self.LogMessages[0]
            while message is not None:
                level = message.Level
                oldest_msgidx, oldest_message = self.OldestMessages[level]
                if oldest_msgidx > 0:
                    old_message = self.GetLogMessageFromSource(oldest_msgidx - 1, level)
                    if old_message is not None:
                        self.OldestMessages[level] = (oldest_msgidx - 1, old_message)
                    else:
                        self.OldestMessages[level] = (-1, None)
                else:
                    self.OldestMessages[level] = (-1, None)
                message = None
                for idx, msg in self.OldestMessages:
                    if msg is not None and (message is None or msg > message):
                        message = msg
                if message is not None:
                    self.LogMessages.insert(0, message)
                    if self.CurrentMessage is not None:
                        self.CurrentMessage += 1
                    else:
                        self.CurrentMessage = 0
                    if message.Level in levels:
                        return message, 0
        return None, None
    
    def RefreshNewData(self, *args, **kwargs):
        if self.HasNewData:
            self.HasNewData = False
            self.RefreshView()
        DebugViewer.RefreshNewData(self, *args, **kwargs)
    
    def RefreshView(self):
        width, height = self.MessagePanel.GetClientSize()
        bitmap = wx.EmptyBitmap(width, height)
        dc = wx.BufferedDC(wx.ClientDC(self.MessagePanel), bitmap)
        dc.Clear()
        dc.SetFont(self.Font)
        dc.BeginDrawing()
        
        if self.CurrentMessage is not None:
            message_idx = self.CurrentMessage
            message = self.LogMessages[message_idx]
            draw_date = True
            offset = 5
            while offset < height and message is not None:
                message.Draw(dc, offset, width, draw_date)
                offset += message.GetHeight(draw_date)
                
                previous_message, message_idx = self.GetPreviousMessage(message_idx, self.CurrentFilter)
                if previous_message is not None:
                    draw_date = message.Date != previous_message.Date
                message = previous_message
        
        dc.EndDrawing()
        
        self.MessageScrollBar.Refresh()
    
    def OnMessageFilterChanged(self, event):
        self.CurrentFilter = self.LevelFilters[self.MessageFilter.GetSelection()]
        if len(self.LogMessages) > 0:
            self.CurrentMessage = len(self.LogMessages) - 1
            message = self.LogMessages[self.CurrentMessage]
            while message is not None and message.Level not in self.CurrentFilter:
                message, self.CurrentMessage = self.GetPreviousMessage(self.CurrentMessage, self.CurrentFilter)
            self.RefreshView()
        event.Skip()
    
    def IsMessagePanelTop(self, message_idx=None):
        if message_idx is None:
            message_idx = self.CurrentMessage
        if message_idx is not None:
            return self.GetNextMessage(message_idx, self.CurrentFilter)[0] is None
        return True
    
    def IsMessagePanelBottom(self, message_idx=None):
        if message_idx is None:
            message_idx = self.CurrentMessage
        if message_idx is not None:
            width, height = self.MessagePanel.GetClientSize()
            offset = 5
            message = self.LogMessages[message_idx]
            draw_date = True
            while message is not None and offset < height:
                offset += message.GetHeight(draw_date)
                previous_message, message_idx = self.GetPreviousMessage(message_idx, self.CurrentFilter)
                if previous_message is not None:
                    draw_date = message.Date != previous_message.Date
                message = previous_message
            return offset < height
        return True
    
    def ScrollMessagePanel(self, scroll):
        if self.CurrentMessage is not None:
            message = self.LogMessages[self.CurrentMessage]
            while scroll > 0 and message is not None:
                message, msgidx = self.GetNextMessage(self.CurrentMessage, self.CurrentFilter)
                if message is not None:
                    self.CurrentMessage = msgidx
                    scroll -= 1
            while scroll < 0 and message is not None and not self.IsMessagePanelBottom():
                message, msgidx = self.GetPreviousMessage(self.CurrentMessage, self.CurrentFilter)
                if message is not None:
                    self.CurrentMessage = msgidx
                    scroll += 1
            self.RefreshView()
        
    def OnSearchMessageChanged(self, event):
        event.Skip()
        
    def OnSearchMessageButtonClick(self, event):
        event.Skip()
    
    def OnFirstButton(self, event):
        if len(self.LogMessages) > 0:
            self.CurrentMessage = len(self.LogMessages) - 1
            message = self.LogMessages[self.CurrentMessage]
            if message.Level not in self.CurrentFilter:
                message, self.CurrentMessage = self.GetPreviousMessage(self.CurrentMessage, self.CurrentFilter)
            self.RefreshView()
        event.Skip()
        
    def OnLastButton(self, event):
        if len(self.LogMessages) > 0:
            message_idx = 0
            message = self.LogMessages[message_idx]
            if message.Level not in self.CurrentFilter:
                next_message, msgidx = self.GetNextMessage(message_idx, self.CurrentFilter)
                if next_message is not None:
                    message_idx = msgidx
                    message = next_message
            while message is not None:
                message, msgidx = self.GetPreviousMessage(message_idx, self.CurrentFilter)
                if message is not None:
                    message_idx = msgidx
            message = self.LogMessages[message_idx]
            if message.Level in self.CurrentFilter:
                while message is not None:
                    message, msgidx = self.GetNextMessage(message_idx, self.CurrentFilter)
                    if message is not None:
                        if not self.IsMessagePanelBottom(msgidx):
                            break
                        message_idx = msgidx
                self.CurrentMessage = message_idx
            else:
                self.CurrentMessage = None
            self.RefreshView()
        event.Skip()
    
    def GenerateOnDurationButton(self, duration):
        def OnDurationButton(event):
            event.Skip()
        return OnDurationButton
    
    def OnMessagePanelPaint(self, event):
        self.RefreshView()
        event.Skip()
    
    def OnMessagePanelResize(self, event):
        self.RefreshView()
        event.Skip()
    
    def OnScrollTimer(self, event):
        if self.ScrollSpeed != 0:
            speed_norm = abs(self.ScrollSpeed)
            if speed_norm <= 5:
                self.ScrollMessagePanel(speed_norm / self.ScrollSpeed)
                period = REFRESH_PERIOD * 5000 / speed_norm
            else:
                self.ScrollMessagePanel(self.ScrollSpeed / 5)
                period = REFRESH_PERIOD * 1000
            self.ScrollTimer.Start(period, True)
        event.Skip()
    
    def SetScrollSpeed(self, speed):
        if speed == 0:
            self.ScrollTimer.Stop()
        else:
            if not self.ScrollTimer.IsRunning():
                speed_norm = abs(speed)
                if speed_norm <= 5:
                    self.ScrollMessagePanel(speed_norm / speed)
                    period = REFRESH_PERIOD * 5000 / speed_norm
                else:
                    period = REFRESH_PERIOD * 1000
                    self.ScrollMessagePanel(speed / 5)
                self.ScrollTimer.Start(period, True)
        self.ScrollSpeed = speed    
    
    def ScrollPageUp(self):
        pass

    def ScrollPageDown(self):
        pass
