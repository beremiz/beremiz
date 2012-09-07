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
from controls.LibraryPanel import LibraryPanel

#-------------------------------------------------------------------------------
#                          Create New Block Dialog
#-------------------------------------------------------------------------------

class FBDBlockDialog(wx.Dialog):
    
    def __init__(self, parent, controller):
        wx.Dialog.__init__(self, parent,
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
        self.LibraryPanel.SetController(controller)
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
        
        preview_label = wx.StaticText(self, label=_('Preview:'))
        right_gridsizer.AddWindow(preview_label, flag=wx.GROW)

        self.Preview = wx.Panel(self,
              style=wx.TAB_TRAVERSAL|wx.SIMPLE_BORDER)
        self.Preview.SetBackgroundColour(wx.Colour(255,255,255))
        setattr(self.Preview, "GetDrawingMode", lambda:FREEDRAWING_MODE)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "GetBlockType", controller.GetBlockType)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Controller = controller
        
        self.BlockName.SetValue("")
        self.BlockName.Enable(False)
        self.Inputs.Enable(False)
        self.Block = None
        self.MinBlockSize = None
        self.First = True
        
        self.PouNames = []
        self.PouElementNames = []
        
        self.LibraryPanel.SetFocus()
    
    def __del__(self):
        self.Controller = None
    
    def SetBlockList(self, blocklist):
        self.LibraryPanel.SetBlockList(blocklist)
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def OnOK(self, event):
        message = None
        selected = self.LibraryPanel.GetSelectedBlock()
        block_name = self.BlockName.GetValue()
        name_enabled = self.BlockName.IsEnabled()
        if selected is None:
            message = _("Form isn't complete. Valid block type must be selected!")
        elif name_enabled and block_name == "":
            message = _("Form isn't complete. Name must be filled!")
        elif name_enabled and not TestIdentifier(block_name):
            message = _("\"%s\" is not a valid identifier!") % block_name
        elif name_enabled and block_name.upper() in IEC_KEYWORDS:
            message = _("\"%s\" is a keyword. It can't be used!") % block_name
        elif name_enabled and block_name.upper() in self.PouNames:
            message = _("\"%s\" pou already exists!") % block_name
        elif name_enabled and block_name.upper() in self.PouElementNames:
            message = _("\"%s\" element for this pou already exists!") % block_name
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)

    def SetMinBlockSize(self, size):
        self.MinBlockSize = size

    def SetPouNames(self, pou_names):
        self.PouNames = [pou_name.upper() for pou_name in pou_names]
        
    def SetPouElementNames(self, element_names):
        self.PouElementNames = [element_name.upper() for element_name in element_names]
        
    def SetValues(self, values):
        blocktype = values.get("type", None)
        if blocktype is not None:
            self.LibraryPanel.SelectTreeItem(blocktype, values.get("inputs", None))
        for name, value in values.items():
            if name == "name":
                self.BlockName.SetValue(value)
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
        if values is not None:
            blocktype = self.Controller.GetBlockType(values["type"], values["inputs"])
        else:
            blocktype = None
        if blocktype is not None:
            self.Inputs.SetValue(len(blocktype["inputs"]))
            self.Inputs.Enable(blocktype["extensible"])
            self.BlockName.Enable(blocktype["type"] != "function")
            wx.CallAfter(self.RefreshPreview)
        else:
            self.BlockName.Enable(False)
            self.Inputs.Enable(False)
            self.Inputs.SetValue(2)
            wx.CallAfter(self.ErasePreview)
    
    def OnNameChanged(self, event):
        if self.BlockName.IsEnabled():
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
    
    def ErasePreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.Clear()
        self.Block = None
        
    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
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
            width, height = self.MinBlockSize
            min_width, min_height = self.Block.GetMinSize()
            width, height = max(min_width, width), max(min_height, height)
            self.Block.SetSize(width, height)
            clientsize = self.Preview.GetClientSize()
            x = (clientsize.width - width) / 2
            y = (clientsize.height - height) / 2
            self.Block.SetPosition(x, y)
            self.Block.Draw(dc)
        else:
            self.Block = None        

    def OnPaint(self, event):
        if self.Block is not None:
            self.RefreshPreview()
        event.Skip()
