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
#                                    Helpers
#-------------------------------------------------------------------------------

VARIABLE_CLASSES_DICT = {INPUT : _("Input"),
                         INOUT : _("InOut"),
                         OUTPUT : _("Output")}
VARIABLE_CLASSES_DICT_REVERSE = dict(
    [(value, key) for key, value in VARIABLE_CLASSES_DICT.iteritems()])

#-------------------------------------------------------------------------------
#                          Create New Variable Dialog
#-------------------------------------------------------------------------------

class FBDVariableDialog(wx.Dialog):

    def __init__(self, parent, controller, transition = ""):
        wx.Dialog.__init__(self, parent,
              size=wx.Size(400, 380), title=_('Variable Properties'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=4, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(2)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=6, vgap=5)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        class_label = wx.StaticText(self, label=_('Class:'))
        left_gridsizer.AddWindow(class_label, flag=wx.GROW)
        
        self.Class = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnClassChanged, self.Class)
        left_gridsizer.AddWindow(self.Class, flag=wx.GROW)
        
        expression_label = wx.StaticText(self, label=_('Expression:'))
        left_gridsizer.AddWindow(expression_label, flag=wx.GROW)
        
        self.Expression = wx.TextCtrl(self)
        self.Bind(wx.EVT_TEXT, self.OnExpressionChanged, self.Expression)
        left_gridsizer.AddWindow(self.Expression, flag=wx.GROW)
        
        execution_order_label = wx.StaticText(self, label=_('Execution Order:'))
        left_gridsizer.AddWindow(execution_order_label, flag=wx.GROW)
        
        self.ExecutionOrder = wx.SpinCtrl(self, min=0, style=wx.SP_ARROW_KEYS)
        self.Bind(wx.EVT_SPINCTRL, self.OnExecutionOrderChanged, self.ExecutionOrder)
        left_gridsizer.AddWindow(self.ExecutionOrder, flag=wx.GROW)
        
        right_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        right_gridsizer.AddGrowableCol(0)
        right_gridsizer.AddGrowableRow(1)
        column_sizer.AddSizer(right_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.LEFT)
        
        name_label = wx.StaticText(self, label=_('Name:'))
        right_gridsizer.AddWindow(name_label, flag=wx.GROW)
        
        self.VariableName = wx.ListBox(self, size=wx.Size(0, 0), 
              style=wx.LB_SINGLE|wx.LB_SORT)
        self.Bind(wx.EVT_LISTBOX, self.OnNameChanged, self.VariableName)
        right_gridsizer.AddWindow(self.VariableName, flag=wx.GROW)
        
        preview_label = wx.StaticText(self, label=_('Preview:'))
        main_sizer.AddWindow(preview_label, border=20,
              flag=wx.GROW|wx.LEFT|wx.RIGHT)
        
        self.Preview = wx.Panel(self, 
              style=wx.TAB_TRAVERSAL|wx.SIMPLE_BORDER)
        self.Preview.SetBackgroundColour(wx.Colour(255,255,255))
        setattr(self.Preview, "GetDrawingMode", lambda:FREEDRAWING_MODE)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        main_sizer.AddWindow(self.Preview, border=20,
              flag=wx.GROW|wx.LEFT|wx.RIGHT)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Transition = transition
        self.Variable = None
        self.VarList = []
        self.MinVariableSize = None
        
        for choice in VARIABLE_CLASSES_DICT.itervalues():
            self.Class.Append(choice)
        self.Class.SetStringSelection(VARIABLE_CLASSES_DICT[INPUT])

        self.RefreshNameList()
        self.Class.SetFocus()

    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)

    def RefreshNameList(self):
        selected = self.VariableName.GetStringSelection()
        var_class = VARIABLE_CLASSES_DICT_REVERSE[self.Class.GetStringSelection()]
        self.VariableName.Clear()
        self.VariableName.Append("")
        for name, var_type, value_type in self.VarList:
            if var_type != "Input" or var_class == INPUT:
                self.VariableName.Append(name)
        if selected != "" and self.VariableName.FindString(selected) != wx.NOT_FOUND:
            self.VariableName.SetStringSelection(selected)
            self.Expression.Enable(False)
        else:
            self.VariableName.SetStringSelection("")
            #self.Expression.Enable(var_class == INPUT)
        self.VariableName.Enable(self.VariableName.GetCount() > 0)
            
    def SetMinVariableSize(self, size):
        self.MinVariableSize = size

    def SetVariables(self, vars):
        self.VarList = vars
        self.RefreshNameList()

    def SetValues(self, values):
        value_type = values.get("type", None)
        value_name = values.get("name", None)
        if value_type:
            self.Class.SetStringSelection(VARIABLE_CLASSES_DICT[value_type])
            self.RefreshNameList()
        if value_name:
            if self.VariableName.FindString(value_name) != wx.NOT_FOUND:
                self.VariableName.SetStringSelection(value_name)
                self.Expression.Enable(False)
            else:
                self.Expression.SetValue(value_name)
                self.VariableName.Enable(False)
        if "executionOrder" in values:
            self.ExecutionOrder.SetValue(values["executionOrder"])
        self.RefreshPreview()
        
    def GetValues(self):
        values = {}
        values["type"] = VARIABLE_CLASSES_DICT_REVERSE[self.Class.GetStringSelection()]
        expression = self.Expression.GetValue()
        if self.Expression.IsEnabled() and expression != "":
            values["name"] = expression
        else:
            values["name"] = self.VariableName.GetStringSelection()
        values["value_type"] = None
        for var_name, var_type, value_type in self.VarList:
            if var_name == values["name"]:
                values["value_type"] = value_type
        values["width"], values["height"] = self.Variable.GetSize()
        values["executionOrder"] = self.ExecutionOrder.GetValue()
        return values

    def OnOK(self, event):
        message = None
        expression = self.Expression.GetValue()
        if self.Expression.IsEnabled():
            value = expression
        else:
            value = self.VariableName.GetStringSelection()
        if value == "":
            message = _("At least a variable or an expression must be selected!")
        elif value.upper() in IEC_KEYWORDS:
            message = _("\"%s\" is a keyword. It can't be used!") % value
        if message is not None:
            message = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            message.ShowModal()
            message.Destroy()
        else:
            self.EndModal(wx.ID_OK)

    def OnClassChanged(self, event):
        self.RefreshNameList()
        self.RefreshPreview()
        event.Skip()

    def OnNameChanged(self, event):
        if self.VariableName.GetStringSelection() != "":
            self.Expression.Enable(False)
        elif VARIABLE_CLASSES_DICT_REVERSE[self.Class.GetStringSelection()] == INPUT:
            self.Expression.Enable(True)
        self.RefreshPreview()
        event.Skip()
    
    def OnExpressionChanged(self, event):
        if self.Expression.GetValue() != "":
            self.VariableName.Enable(False)
        else:
            self.VariableName.Enable(True)
        self.RefreshPreview()
        event.Skip()
    
    def OnExecutionOrderChanged(self, event):
        self.RefreshPreview()
        event.Skip()
    
    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        expression = self.Expression.GetValue()
        if self.Expression.IsEnabled() and expression != "":
            name = expression
        else:
            name = self.VariableName.GetStringSelection()
        type = ""
        for var_name, var_type, value_type in self.VarList:
            if var_name == name:
                type = value_type
        classtype = VARIABLE_CLASSES_DICT_REVERSE[self.Class.GetStringSelection()]
        self.Variable = FBD_Variable(self.Preview, classtype, name, type, executionOrder = self.ExecutionOrder.GetValue())
        width, height = self.MinVariableSize
        min_width, min_height = self.Variable.GetMinSize()
        width, height = max(min_width, width), max(min_height, height)
        self.Variable.SetSize(width, height)
        clientsize = self.Preview.GetClientSize()
        x = (clientsize.width - width) / 2
        y = (clientsize.height - height) / 2
        self.Variable.SetPosition(x, y)
        self.Variable.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
