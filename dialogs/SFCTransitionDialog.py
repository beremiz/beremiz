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
#                          Edit Transition Content Dialog
#-------------------------------------------------------------------------------

class SFCTransitionDialog(wx.Dialog):
    
    def __init__(self, parent, controller, connection):
        self.Connection = connection
        
        wx.Dialog.__init__(self, parent, 
              size=wx.Size(350, 300), title=_('Edit transition'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=8, vgap=5)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
                              flag=wx.GROW|wx.RIGHT)
        
        type_label = wx.StaticText(self, label=_('Type:'))
        left_gridsizer.AddWindow(type_label, flag=wx.GROW)
        
        self.ReferenceRadioButton = wx.RadioButton(self,
              label=_('Reference'), style=wx.RB_GROUP)
        self.ReferenceRadioButton.SetValue(True)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.ReferenceRadioButton)
        left_gridsizer.AddWindow(self.ReferenceRadioButton, flag=wx.GROW)
        
        self.Reference = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnReferenceChanged, self.Reference)
        left_gridsizer.AddWindow(self.Reference, flag=wx.GROW)
        
        self.InlineRadioButton = wx.RadioButton(self, label=_('Inline'))
        self.InlineRadioButton.SetValue(False)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.InlineRadioButton)
        left_gridsizer.AddWindow(self.InlineRadioButton, flag=wx.GROW)
        
        self.Inline = wx.TextCtrl(self)
        self.Inline.Enable(False)
        self.Bind(wx.EVT_TEXT, self.OnInlineChanged, self.Inline)
        left_gridsizer.AddWindow(self.Inline, flag=wx.GROW)
        
        self.ConnectionRadioButton = wx.RadioButton(self, label=_('Connection'))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, self.ConnectionRadioButton)
        self.ConnectionRadioButton.SetValue(False)
        if not self.Connection:
            self.ConnectionRadioButton.Hide()
        left_gridsizer.AddWindow(self.ConnectionRadioButton, flag=wx.GROW)
        
        priority_label = wx.StaticText(self, label=_('Priority:'))
        left_gridsizer.AddWindow(priority_label, flag=wx.GROW)
        
        self.Priority = wx.SpinCtrl(self, min=0, style=wx.SP_ARROW_KEYS)
        self.Bind(wx.EVT_TEXT, self.OnPriorityChanged, self.Priority)
        left_gridsizer.AddWindow(self.Priority, flag=wx.GROW)
        
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
        setattr(self.Preview, "RefreshTransitionModel", lambda x:None)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
              button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Transition = None
        self.MinTransitionSize = None
        
        self.Element = SFC_Transition(self.Preview)
        
        self.ReferenceRadioButton.SetFocus()
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def SetElementSize(self, size):
        min_width, min_height = self.Element.GetMinSize()
        width, height = max(min_width, size[0]), max(min_height, size[1])
        self.Element.SetSize(width, height)
    
    def OnOK(self, event):
        error = []
        if self.ReferenceRadioButton.GetValue() and self.Reference.GetStringSelection() == "":
            error.append(_("Reference"))
        if self.InlineRadioButton.GetValue() and self.Inline.GetValue() == "":
            error.append(_("Inline"))
        if len(error) > 0:
            text = ""
            for i, item in enumerate(error):
                if i == 0:
                    text += item
                elif i == len(error) - 1:
                    text += _(" and %s")%item
                else:
                    text += _(", %s")%item 
            dialog = wx.MessageDialog(self, _("Form isn't complete. %s must be filled!")%text, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)

    def OnTypeChanged(self, event):
        if self.ReferenceRadioButton.GetValue():
            self.Element.SetType("reference", self.Reference.GetStringSelection())
            self.Reference.Enable(True)
            self.Inline.Enable(False)
        elif self.InlineRadioButton.GetValue():
            self.Element.SetType("inline", self.Inline.GetValue())
            self.Reference.Enable(False)
            self.Inline.Enable(True)
        else:
            self.Element.SetType("connection")
            self.Reference.Enable(False)
            self.Inline.Enable(False)
        self.RefreshPreview()
        event.Skip()

    def OnReferenceChanged(self, event):
        self.Element.SetType("reference", self.Reference.GetStringSelection())
        self.RefreshPreview()
        event.Skip()

    def OnInlineChanged(self, event):
        self.Element.SetType("inline", self.Inline.GetValue())
        self.RefreshPreview()
        event.Skip()

    def OnPriorityChanged(self, event):
        self.Element.SetPriority(int(self.Priority.GetValue()))
        self.RefreshPreview()
        event.Skip()

    def SetTransitions(self, transitions):
        self.Reference.Append("")
        for transition in transitions:
            self.Reference.Append(transition)

    def SetValues(self, values):
        if values["type"] == "reference":
            self.ReferenceRadioButton.SetValue(True)
            self.InlineRadioButton.SetValue(False)
            self.ConnectionRadioButton.SetValue(False)
            self.Reference.Enable(True)
            self.Inline.Enable(False)
            self.Reference.SetStringSelection(values["value"])
            self.Element.SetType("reference", values["value"])
        elif values["type"] == "inline":
            self.ReferenceRadioButton.SetValue(False)
            self.InlineRadioButton.SetValue(True)
            self.ConnectionRadioButton.SetValue(False)
            self.Reference.Enable(False)
            self.Inline.Enable(True)
            self.Inline.SetValue(values["value"])
            self.Element.SetType("inline", values["value"])
        elif values["type"] == "connection" and self.Connection:
            self.ReferenceRadioButton.SetValue(False)
            self.InlineRadioButton.SetValue(False)
            self.ConnectionRadioButton.SetValue(True)
            self.Reference.Enable(False)
            self.Inline.Enable(False)
            self.Element.SetType("connection")
        self.Priority.SetValue(values["priority"])
        self.Element.SetPriority(values["priority"])
        self.RefreshPreview()
        
    def GetValues(self):
        values = {"priority" : int(self.Priority.GetValue())}
        if self.ReferenceRadioButton.GetValue():
            values["type"] = "reference"
            values["value"] = self.Reference.GetStringSelection()
        elif self.InlineRadioButton.GetValue():
            values["type"] = "inline"
            values["value"] = self.Inline.GetValue()
        else:
            values["type"] = "connection"
            values["value"] = None
        return values

    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        clientsize = self.Preview.GetClientSize()
        posx, posy = self.Element.GetPosition()
        rect = self.Element.GetBoundingBox()
        diffx, diffy = posx - rect.x, posy - rect.y
        self.Element.SetPosition((clientsize.width - rect.width) / 2 + diffx, (clientsize.height - rect.height) / 2 + diffy)
        self.Element.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
