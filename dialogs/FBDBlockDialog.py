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

import re

import wx

from graphics.FBD_Objects import FBD_Block
from controls.LibraryPanel import LibraryPanel
from BlockPreviewDialog import BlockPreviewDialog

#-------------------------------------------------------------------------------
#                          Create New Block Dialog
#-------------------------------------------------------------------------------

class FBDBlockDialog(BlockPreviewDialog):
    
    def __init__(self, parent, controller, tagname):
        BlockPreviewDialog.__init__(self, parent, controller, tagname,
              size=wx.Size(600, 450), title=_('Block Properties'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=4, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        type_staticbox = wx.StaticBox(self, label=_('Type:'))
        left_staticboxsizer = wx.StaticBoxSizer(type_staticbox, wx.VERTICAL)
        column_sizer.AddSizer(left_staticboxsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        self.LibraryPanel = LibraryPanel(self)
        setattr(self.LibraryPanel, "_OnTreeItemSelected", 
              self.OnLibraryTreeItemSelected)
        left_staticboxsizer.AddWindow(self.LibraryPanel, 1, border=5, 
              flag=wx.GROW|wx.TOP)
        
        right_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=5)
        right_gridsizer.AddGrowableCol(0)
        right_gridsizer.AddGrowableRow(2)
        column_sizer.AddSizer(right_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.LEFT)
        
        top_right_gridsizer = wx.FlexGridSizer(cols=2, hgap=0, rows=4, vgap=5)
        top_right_gridsizer.AddGrowableCol(1)
        right_gridsizer.AddSizer(top_right_gridsizer, flag=wx.GROW)
        
        name_label = wx.StaticText(self, label=_('Name:'))
        top_right_gridsizer.AddWindow(name_label, 
              flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.BlockName = wx.TextCtrl(self)
        self.Bind(wx.EVT_TEXT, self.OnNameChanged, self.BlockName)
        top_right_gridsizer.AddWindow(self.BlockName, flag=wx.GROW)
        
        inputs_label = wx.StaticText(self, label=_('Inputs:'))
        top_right_gridsizer.AddWindow(inputs_label, 
              flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.Inputs = wx.SpinCtrl(self, min=2, max=20,
              style=wx.SP_ARROW_KEYS)
        self.Bind(wx.EVT_SPINCTRL, self.OnInputsChanged, self.Inputs)
        top_right_gridsizer.AddWindow(self.Inputs, flag=wx.GROW)
        
        execution_order_label = wx.StaticText(self, label=_('Execution Order:'))
        top_right_gridsizer.AddWindow(execution_order_label, 
              flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.ExecutionOrder = wx.SpinCtrl(self, min=0, style=wx.SP_ARROW_KEYS)
        self.Bind(wx.EVT_SPINCTRL, self.OnExecutionOrderChanged, self.ExecutionOrder)
        top_right_gridsizer.AddWindow(self.ExecutionOrder, flag=wx.GROW)
                
        execution_control_label = wx.StaticText(self, label=_('Execution Control:'))
        top_right_gridsizer.AddWindow(execution_control_label, 
              flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.ExecutionControl = wx.CheckBox(self)
        self.Bind(wx.EVT_CHECKBOX, self.OnExecutionOrderChanged, self.ExecutionControl)
        top_right_gridsizer.AddWindow(self.ExecutionControl, flag=wx.GROW)
        
        right_gridsizer.AddWindow(self.PreviewLabel, flag=wx.GROW)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        main_sizer.AddSizer(self.ButtonSizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.BlockName.SetValue("")
        self.BlockName.Enable(False)
        self.Inputs.Enable(False)
        self.CurrentBlockName = None
        
        self.LibraryPanel.SetBlockList(controller.GetBlockTypes(tagname))
        self.LibraryPanel.SetFocus()
    
    def OnOK(self, event):
        message = None
        selected = self.LibraryPanel.GetSelectedBlock()
        block_name = self.BlockName.GetValue()
        name_enabled = self.BlockName.IsEnabled()
        if selected is None:
            message = _("Form isn't complete. Valid block type must be selected!")
        elif name_enabled and block_name == "":
            message = _("Form isn't complete. Name must be filled!")
        if message is not None:
            self.ShowMessage(message)
        elif not name_enabled or self.TestBlockName(block_name):
            BlockPreviewDialog.OnOK(self, event)

    def SetValues(self, values):
        blocktype = values.get("type", None)
        default_name_model = re.compile("%s[0-9]+" % blocktype)
        if blocktype is not None:
            self.LibraryPanel.SelectTreeItem(blocktype, 
                                             values.get("inputs", None))
        for name, value in values.items():
            if name == "name":
                if value != "":
                    self.DefaultBlockName = value
                    if default_name_model.match(value) is None:
                        self.CurrentBlockName = value
                self.BlockName.ChangeValue(value)
            elif name == "extension":
                self.Inputs.SetValue(value)
            elif name == "executionOrder":
                self.ExecutionOrder.SetValue(value)
            elif name == "executionControl":
                   self.ExecutionControl.SetValue(value)
        self.RefreshPreview()

    def GetValues(self):
        values = self.LibraryPanel.GetSelectedBlock()
        if self.BlockName.IsEnabled() and self.BlockName.GetValue() != "":
            values["name"] = self.BlockName.GetValue()
        values["width"], values["height"] = self.Block.GetSize()
        values["extension"] = self.Inputs.GetValue()
        values["executionOrder"] = self.ExecutionOrder.GetValue()
        values["executionControl"] = self.ExecutionControl.GetValue()
        return values
        
    def OnLibraryTreeItemSelected(self, event):
        values = self.LibraryPanel.GetSelectedBlock()
        blocktype = (self.Controller.GetBlockType(values["type"], 
                                                  values["inputs"])
                     if values is not None else None)
        
        if blocktype is not None:
            self.Inputs.SetValue(len(blocktype["inputs"]))
            self.Inputs.Enable(blocktype["extensible"])
        else:
            self.Inputs.SetValue(2)
            self.Inputs.Enable(False)
        
        if blocktype is not None and blocktype["type"] != "function":
            self.BlockName.Enable(True)
            self.BlockName.ChangeValue(
                self.CurrentBlockName
                if self.CurrentBlockName is not None
                else self.Controller.GenerateNewName(
                    self.TagName, None, values["type"]+"%d", 0))
        else:
            self.BlockName.Enable(False)
            self.BlockName.ChangeValue("")
        
        self.RefreshPreview()
    
    def OnNameChanged(self, event):
        if self.BlockName.IsEnabled():
            self.CurrentBlockName = self.BlockName.GetValue()
            self.RefreshPreview()
        event.Skip()
    
    def OnInputsChanged(self, event):
        if self.Inputs.IsEnabled():
            self.RefreshPreview()
        event.Skip()
    
    def OnExecutionOrderChanged(self, event):
        self.RefreshPreview()
        event.Skip()
    
    def OnExecutionControlChanged(self, event):
        self.RefreshPreview()
        event.Skip()
    
    def RefreshPreview(self):
        values = self.LibraryPanel.GetSelectedBlock()
        if values is not None:
            if self.BlockName.IsEnabled():
                blockname = self.BlockName.GetValue()
            else:
                blockname = ""
            self.Block = FBD_Block(self.Preview, values["type"], 
                    blockname, 
                    extension = self.Inputs.GetValue(), 
                    inputs = values["inputs"], 
                    executionControl = self.ExecutionControl.GetValue(), 
                    executionOrder = self.ExecutionOrder.GetValue())
        else:
            self.Block = None 
        BlockPreviewDialog.RefreshPreview(self)
