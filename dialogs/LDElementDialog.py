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

import wx

from graphics import *

#-------------------------------------------------------------------------------
#                        Edit Ladder Element Properties Dialog
#-------------------------------------------------------------------------------

class LDElementDialog(wx.Dialog):
    
    def __init__(self, parent, controller, type):
        if type == "contact":
            wx.Dialog.__init__(self, parent, size=wx.Size(350, 260),
                  title=_("Edit Contact Values"))
        else:
            wx.Dialog.__init__(self, parent, size=wx.Size(350, 310),
                  title=_("Edit Coil Values"))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        if type == "contact":
            left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=7, vgap=0)
        else:
            left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=9, vgap=0)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        modifier_label = wx.StaticText(self, label=_('Modifier:'))
        left_gridsizer.AddWindow(modifier_label, border=5, flag=wx.GROW|wx.BOTTOM)
        
        self.Normal = wx.RadioButton(self, label=_("Normal"), style=wx.RB_GROUP)
        self.Normal.SetValue(True)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.Normal)
        left_gridsizer.AddWindow(self.Normal, flag=wx.GROW)
        
        self.Negated = wx.RadioButton(self, label=_("Negated"))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.Negated)
        left_gridsizer.AddWindow(self.Negated, flag=wx.GROW)
        
        if type != "contact":
            self.Set = wx.RadioButton(self, label=_("Set"))
            self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.Set)
            left_gridsizer.AddWindow(self.Set, flag=wx.GROW)
            
            self.Reset = wx.RadioButton(self, label=_("Reset"))
            self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.Reset)
            left_gridsizer.AddWindow(self.Reset, flag=wx.GROW)
            
        self.RisingEdge = wx.RadioButton(self, label=_("Rising Edge"))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.RisingEdge)
        left_gridsizer.AddWindow(self.RisingEdge, flag=wx.GROW)
        
        self.FallingEdge = wx.RadioButton(self, label=_("Falling Edge"))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.FallingEdge)
        left_gridsizer.AddWindow(self.FallingEdge, flag=wx.GROW)
        
        element_name_label = wx.StaticText(self, label=_('Name:'))
        left_gridsizer.AddWindow(element_name_label, border=5, flag=wx.GROW|wx.TOP)
        
        self.ElementName = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnNameChanged, self.ElementName)
        left_gridsizer.AddWindow(self.ElementName, border=5, flag=wx.GROW|wx.TOP)
        
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
        
        if type == "contact":
            self.Element = LD_Contact(self.Preview, CONTACT_NORMAL, "")
        else:
            self.Element = LD_Coil(self.Preview, COIL_NORMAL, "")
        
        self.Type = type
        
        self.Normal.SetFocus()
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def SetElementSize(self, size):
        min_width, min_height = self.Element.GetMinSize()
        width, height = max(min_width, size[0]), max(min_height, size[1])
        self.Element.SetSize(width, height)
        
    def SetVariables(self, vars):
        self.ElementName.Clear()
        for name in vars:
            self.ElementName.Append(name)
        self.ElementName.Enable(self.ElementName.GetCount() > 0)

    def SetValues(self, values):
        for name, value in values.items():
            if name == "name":
                self.Element.SetName(value)
                self.ElementName.SetStringSelection(value)
            elif name == "type":
                self.Element.SetType(value)
                if self.Type == "contact":
                    if value == CONTACT_NORMAL:
                        self.Normal.SetValue(True)
                    elif value == CONTACT_REVERSE:
                        self.Negated.SetValue(True)
                    elif value == CONTACT_RISING:
                        self.RisingEdge.SetValue(True)
                    elif value == CONTACT_FALLING:
                        self.FallingEdge.SetValue(True)
                elif self.Type == "coil":
                    if value == COIL_NORMAL:
                        self.Normal.SetValue(True)
                    elif value == COIL_REVERSE:
                        self.Negated.SetValue(True)
                    elif value == COIL_SET:
                        self.Set.SetValue(True)
                    elif value == COIL_RESET:
                        self.Reset.SetValue(True)
                    elif value == COIL_RISING:
                        self.RisingEdge.SetValue(True)
                    elif value == COIL_FALLING:
                        self.FallingEdge.SetValue(True)

    def GetValues(self):
        values = {}
        values["name"] = self.Element.GetName()
        values["type"] = self.Element.GetType()
        values["width"], values["height"] = self.Element.GetSize()
        return values

    def OnTypeChanged(self, event):
        if self.Type == "contact":
            if self.Normal.GetValue():
                self.Element.SetType(CONTACT_NORMAL)
            elif self.Negated.GetValue():
                self.Element.SetType(CONTACT_REVERSE)
            elif self.RisingEdge.GetValue():
                self.Element.SetType(CONTACT_RISING)
            elif self.FallingEdge.GetValue():
                self.Element.SetType(CONTACT_FALLING)
        elif self.Type == "coil":
            if self.Normal.GetValue():
                self.Element.SetType(COIL_NORMAL)
            elif self.Negated.GetValue():
                self.Element.SetType(COIL_REVERSE)
            elif self.Set.GetValue():
                self.Element.SetType(COIL_SET)
            elif self.Reset.GetValue():
                self.Element.SetType(COIL_RESET)
            elif self.RisingEdge.GetValue():
                self.Element.SetType(COIL_RISING)
            elif self.FallingEdge.GetValue():
                self.Element.SetType(COIL_FALLING)
        self.RefreshPreview()
        event.Skip()

    def OnNameChanged(self, event):
        self.Element.SetName(self.ElementName.GetStringSelection())
        self.RefreshPreview()
        event.Skip()

    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        clientsize = self.Preview.GetClientSize()
        width, height = self.Element.GetSize()
        self.Element.SetPosition((clientsize.width - width) / 2, (clientsize.height - height) / 2)
        self.Element.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
