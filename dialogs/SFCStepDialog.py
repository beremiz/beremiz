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
#                          Edit Step Content Dialog
#-------------------------------------------------------------------------------

class SFCStepDialog(wx.Dialog):
    
    def __init__(self, parent, controller, initial = False):
        wx.Dialog.__init__(self, parent, title=_('Edit Step'), 
              size=wx.Size(400, 250))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=6, vgap=5)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
                              flag=wx.GROW|wx.RIGHT)
        
        name_label = wx.StaticText(self, label=_('Name:'))
        left_gridsizer.AddWindow(name_label, flag=wx.GROW)
        
        self.StepName = wx.TextCtrl(self)
        self.Bind(wx.EVT_TEXT, self.OnNameChanged, self.StepName)
        left_gridsizer.AddWindow(self.StepName, flag=wx.GROW)
        
        connectors_label = wx.StaticText(self, label=_('Connectors:'))
        left_gridsizer.AddWindow(connectors_label, flag=wx.GROW)
        
        self.Input = wx.CheckBox(self, label=_("Input"))
        self.Bind(wx.EVT_CHECKBOX, self.OnConnectorsChanged, self.Input)
        left_gridsizer.AddWindow(self.Input, flag=wx.GROW)
        
        self.Output = wx.CheckBox(self, label=_("Output"))
        self.Bind(wx.EVT_CHECKBOX, self.OnConnectorsChanged, self.Output)
        left_gridsizer.AddWindow(self.Output, flag=wx.GROW)
        
        self.Action = wx.CheckBox(self, label=_("Action"))
        self.Bind(wx.EVT_CHECKBOX, self.OnConnectorsChanged, self.Action)
        left_gridsizer.AddWindow(self.Action, flag=wx.GROW)
        
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
        setattr(self.Preview, "RefreshStepModel", lambda x:None)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        button_sizer = self.CreateButtonSizer(
                  wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
                  button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Step = None
        self.Initial = initial
        self.MinStepSize = None
    
        self.PouNames = []
        self.Variables = []
        self.StepNames = []
        
        self.StepName.SetFocus()
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def OnOK(self, event):
        message = None
        step_name = self.StepName.GetValue()
        if step_name == "":
            message = _("You must type a name!")
        elif not TestIdentifier(step_name):
            message = _("\"%s\" is not a valid identifier!") % step_name
        elif step_name.upper() in IEC_KEYWORDS:
            message = _("\"%s\" is a keyword. It can't be used!") % step_name
        elif step_name.upper() in self.PouNames:
            message = _("A POU named \"%s\" already exists!") % step_name
        elif step_name.upper() in self.Variables:
            message = _("A variable with \"%s\" as name already exists in this pou!") % step_name
        elif step_name.upper() in self.StepNames:
            message = _("\"%s\" step already exists!") % step_name
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()    
        else:
            self.EndModal(wx.ID_OK)
    
    def SetMinStepSize(self, size):
        self.MinStepSize = size

    def SetPouNames(self, pou_names):
        self.PouNames = [pou_name.upper() for pou_name in pou_names]

    def SetVariables(self, variables):
        self.Variables = [var["Name"].upper() for var in variables]

    def SetStepNames(self, step_names):
        self.StepNames = [step_name.upper() for step_name in step_names]

    def SetValues(self, values):
        value_name = values.get("name", None)
        if value_name:
            self.StepName.SetValue(value_name)
        else:
            self.StepName.SetValue("")
        self.Input.SetValue(values.get("input", False))
        self.Output.SetValue(values.get("output", False))
        self.Action.SetValue(values.get("action", False))
        self.RefreshPreview()
        
    def GetValues(self):
        values = {}
        values["name"] = self.StepName.GetValue()
        values["input"] = self.Input.IsChecked()
        values["output"] = self.Output.IsChecked()
        values["action"] = self.Action.IsChecked()
        values["width"], values["height"] = self.Step.GetSize()
        return values
    
    def OnConnectorsChanged(self, event):
        self.RefreshPreview()
        event.Skip()

    def OnNameChanged(self, event):
        self.RefreshPreview()
        event.Skip()
    
    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        self.Step = SFC_Step(self.Preview, self.StepName.GetValue(), self.Initial)
        if self.Input.IsChecked():
            self.Step.AddInput()
        else:
            self.Step.RemoveInput()
        if self.Output.IsChecked():
            self.Step.AddOutput()
        else:
            self.Step.RemoveOutput()
        if self.Action.IsChecked():
            self.Step.AddAction()    
        else:
            self.Step.RemoveAction()
        width, height = self.MinStepSize
        min_width, min_height = self.Step.GetMinSize()
        width, height = max(min_width, width), max(min_height, height)
        self.Step.SetSize(width, height)
        clientsize = self.Preview.GetClientSize()
        x = (clientsize.width - width) / 2
        y = (clientsize.height - height) / 2
        self.Step.SetPosition(x, y)
        self.Step.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
