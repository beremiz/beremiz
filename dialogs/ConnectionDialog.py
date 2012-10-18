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
#                          Create New Connection Dialog
#-------------------------------------------------------------------------------

class ConnectionDialog(wx.Dialog):
    
    def __init__(self, parent, controller, apply_button=False):
        wx.Dialog.__init__(self, parent,
              size=wx.Size(350, 220), title=_('Connection Properties'))
        
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
        
        self.ConnectorRadioButton = wx.RadioButton(self, 
              label=_('Connector'), style=wx.RB_GROUP)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.ConnectorRadioButton)
        self.ConnectorRadioButton.SetValue(True)
        left_gridsizer.AddWindow(self.ConnectorRadioButton, flag=wx.GROW)
        
        self.ConnectionRadioButton = wx.RadioButton(self, label=_('Continuation'))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.ConnectionRadioButton)
        left_gridsizer.AddWindow(self.ConnectionRadioButton, flag=wx.GROW)
        
        name_label = wx.StaticText(self, label=_('Name:'))
        left_gridsizer.AddWindow(name_label, flag=wx.GROW)
        
        self.ConnectionName = wx.TextCtrl(self)
        self.Bind(wx.EVT_TEXT, self.OnNameChanged, self.ConnectionName)
        left_gridsizer.AddWindow(self.ConnectionName, flag=wx.GROW)
        
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
        self.Bind(wx.EVT_BUTTON, self.OnOK, button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        if apply_button:
            self.ApplyToAllButton = wx.Button(self, label=_("Propagate Name"))
            self.ApplyToAllButton.SetToolTipString(
                _("Apply name modification to all continuations with the same name"))
            self.Bind(wx.EVT_BUTTON, self.OnApplyToAll, self.ApplyToAllButton)
            button_sizer.AddWindow(self.ApplyToAllButton)
        
        self.SetSizer(main_sizer)
        
        self.Connection = None
        self.MinConnectionSize = None
        
        self.PouNames = []
        self.PouElementNames = []
        
        self.ConnectorRadioButton.SetFocus()
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def SetMinConnectionSize(self, size):
        self.MinConnectionSize = size
    
    def SetValues(self, values):
        for name, value in values.items():
            if name == "type":
                if value == CONNECTOR:
                    self.ConnectorRadioButton.SetValue(True)
                elif value == CONTINUATION:
                    self.ConnectionRadioButton.SetValue(True)
            elif name == "name":
                self.ConnectionName.SetValue(value)
        self.RefreshPreview()
    
    def GetValues(self):
        values = {}
        if self.ConnectorRadioButton.GetValue():
            values["type"] = CONNECTOR
        else:
            values["type"] = CONTINUATION
        values["name"] = self.ConnectionName.GetValue()
        values["width"], values["height"] = self.Connection.GetSize()
        return values

    def SetPouNames(self, pou_names):
        self.PouNames = [pou_name.upper() for pou_name in pou_names]
        
    def SetPouElementNames(self, element_names):
        self.PouElementNames = [element_name.upper() for element_name in element_names]
    
    def TestName(self):
        message = None
        connection_name = self.ConnectionName.GetValue()
        if connection_name == "":
            message = _("Form isn't complete. Name must be filled!")
        elif not TestIdentifier(connection_name):
            message = _("\"%s\" is not a valid identifier!") % connection_name
        elif connection_name.upper() in IEC_KEYWORDS:
            message = _("\"%s\" is a keyword. It can't be used!") % connection_name
        elif connection_name.upper() in self.PouNames:
            message = _("\"%s\" pou already exists!") % connection_name
        elif connection_name.upper() in self.PouElementNames:
            message = _("\"%s\" element for this pou already exists!") % connection_name
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
            return False
        return True
        
    def OnOK(self, event):
        if self.TestName():
            self.EndModal(wx.ID_OK)

    def OnApplyToAll(self, event):
        if self.TestName():
            self.EndModal(wx.ID_YESTOALL)

    def OnTypeChanged(self, event):
        self.RefreshPreview()
        event.Skip()

    def OnNameChanged(self, event):
        self.RefreshPreview()
        event.Skip()
        
    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        if self.ConnectorRadioButton.GetValue():
            self.Connection = FBD_Connector(self.Preview, CONNECTOR, self.ConnectionName.GetValue())
        else:
            self.Connection = FBD_Connector(self.Preview, CONTINUATION, self.ConnectionName.GetValue())
        width, height = self.MinConnectionSize
        min_width, min_height = self.Connection.GetMinSize()
        width, height = max(min_width, width), max(min_height, height)
        self.Connection.SetSize(width, height)
        clientsize = self.Preview.GetClientSize()
        x = (clientsize.width - width) / 2
        y = (clientsize.height - height) / 2
        self.Connection.SetPosition(x, y)
        self.Connection.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
