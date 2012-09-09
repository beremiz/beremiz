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

from graphics import *

#-------------------------------------------------------------------------------
#                      Edit Ladder Power Rail Properties Dialog
#-------------------------------------------------------------------------------

class LDPowerRailDialog(wx.Dialog):
    
    def __init__(self, parent, controller, type = LEFTRAIL, number = 1):
        wx.Dialog.__init__(self, parent, size=wx.Size(350, 260),
              title=_('Power Rail Properties'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=5, vgap=5)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        type_label = wx.StaticText(self, label=_('Type:'))
        left_gridsizer.AddWindow(type_label, flag=wx.GROW)
        
        self.LeftPowerRail = wx.RadioButton(self,
              label=_('Left PowerRail'), style=wx.RB_GROUP)
        self.LeftPowerRail.SetValue(True)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.LeftPowerRail)
        left_gridsizer.AddWindow(self.LeftPowerRail, flag=wx.GROW)
        
        self.RightPowerRail = wx.RadioButton(self, label=_('Right PowerRail'))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.RightPowerRail)
        left_gridsizer.AddWindow(self.RightPowerRail, flag=wx.GROW)
        
        pin_number_label = wx.StaticText(self, label=_('Pin number:'))
        left_gridsizer.AddWindow(pin_number_label, flag=wx.GROW)
        
        self.PinNumber = wx.SpinCtrl(self, min=1, max=50,
              style=wx.SP_ARROW_KEYS)
        self.Bind(wx.EVT_SPINCTRL, self.OnPinNumberChanged, self.PinNumber)
        left_gridsizer.AddWindow(self.PinNumber, flag=wx.GROW)
        
        right_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        right_gridsizer.AddGrowableCol(0)
        right_gridsizer.AddGrowableRow(1)
        column_sizer.AddSizer(right_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.LEFT)
        
        preview_label = wx.StaticText(self, label=_('Preview:'))
        right_gridsizer.AddWindow(preview_label, flag=wx.GROW)
        
        self.Preview = wx.Panel(self,
              style=wx.TAB_TRAVERSAL|wx.SIMPLE_BORDER)
        self.Preview.SetBackgroundColour(wx.Colour(255,255,255))
        setattr(self.Preview, "GetDrawingMode", lambda:FREEDRAWING_MODE)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Type = type
        if type == LEFTRAIL:
            self.LeftPowerRail.SetValue(True)
        elif type == RIGHTRAIL:
            self.RightPowerRail.SetValue(True)
        self.PinNumber.SetValue(number)
        
        self.PowerRailMinSize = (0, 0)
        self.PowerRail = None
        
        self.LeftPowerRail.SetFocus()

    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)

    def SetMinSize(self, size):
        self.PowerRailMinSize = size
        self.RefreshPreview()    

    def GetValues(self):
        values = {}
        values["type"] = self.Type
        values["number"] = self.PinNumber.GetValue()
        values["width"], values["height"] = self.PowerRail.GetSize()
        return values

    def OnTypeChanged(self, event):
        if self.LeftPowerRail.GetValue():
            self.Type = LEFTRAIL
        elif self.RightPowerRail.GetValue():
            self.Type = RIGHTRAIL
        self.RefreshPreview()
        event.Skip()

    def OnPinNumberChanged(self, event):
        self.RefreshPreview()
        event.Skip()

    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        self.PowerRail = LD_PowerRail(self.Preview, self.Type, connectors = self.PinNumber.GetValue())
        min_width, min_height = 2, LD_LINE_SIZE * self.PinNumber.GetValue()
        width, height = max(min_width, self.PowerRailMinSize[0]), max(min_height, self.PowerRailMinSize[1])
        self.PowerRail.SetSize(width, height)
        clientsize = self.Preview.GetClientSize()
        self.PowerRail.SetPosition((clientsize.width - width) / 2, (clientsize.height - height) / 2)
        self.PowerRail.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
