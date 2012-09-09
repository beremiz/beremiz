#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

class CustomTree(wx.TreeCtrl):
    
    def __init__(self, *args, **kwargs):
        wx.TreeCtrl.__init__(self, *args, **kwargs)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        
        self.BackgroundBitmap = None
        self.BackgroundAlign = wx.ALIGN_LEFT|wx.ALIGN_TOP
        
        self.AddMenu = None
        self.Enabled = False
        
        if wx.Platform == '__WXMSW__':
            self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)
        else:
            self.Bind(wx.EVT_PAINT, self.OnPaint)
            self.Bind(wx.EVT_SIZE, self.OnResize)
            self.Bind(wx.EVT_SCROLL, self.OnScroll)
        self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
    
    def SetBackgroundBitmap(self, bitmap, align):
        self.BackgroundBitmap = bitmap
        self.BackgroundAlign = align
    
    def SetAddMenu(self, add_menu):
        self.AddMenu = add_menu
    
    def Enable(self, enabled):
        self.Enabled = enabled
    
    def GetBitmapRect(self):
        client_size = self.GetClientSize()
        bitmap_size = self.BackgroundBitmap.GetSize()
        
        if self.BackgroundAlign & wx.ALIGN_RIGHT:
            x = client_size[0] - bitmap_size[0]
        elif self.BackgroundAlign & wx.ALIGN_CENTER_HORIZONTAL:
            x = (client_size[0] - bitmap_size[0]) / 2
        else:
            x = 0
        
        if self.BackgroundAlign & wx.ALIGN_BOTTOM:
            y = client_size[1] - bitmap_size[1]
        elif self.BackgroundAlign & wx.ALIGN_CENTER_VERTICAL:
            y = (client_size[1] - bitmap_size[1]) / 2
        else:
            y = 0
        
        return wx.Rect(x, y, bitmap_size[0], bitmap_size[1])
    
    def RefreshBackground(self, refresh_base=False):
        dc = wx.ClientDC(self)
        dc.Clear()
        
        bitmap_rect = self.GetBitmapRect()
        dc.DrawBitmap(self.BackgroundBitmap, bitmap_rect.x, bitmap_rect.y)
        
        if refresh_base:
            self.Refresh(False)
    
    def OnEraseBackground(self, event):
        self.RefreshBackground(True)
    
    def OnLeftUp(self, event):
        if self.Enabled:
            pos = event.GetPosition()
            item, flags = self.HitTest(pos)
            
            bitmap_rect = self.GetBitmapRect()
            if (bitmap_rect.InsideXY(pos.x, pos.y) or 
                flags & wx.TREE_HITTEST_NOWHERE) and self.AddMenu is not None:
                self.PopupMenuXY(self.AddMenu, pos.x, pos.y)
        event.Skip()

    def OnScroll(self, event):
        self.RefreshBackground(True)
        event.Skip()

    def OnResize(self, event):
        self.RefreshBackground(True)
        event.Skip()
    
    def OnPaint(self, event):
        self.RefreshBackground()
        event.Skip()