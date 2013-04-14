#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2012: Edouard TISSERANT and Laurent BESSARD
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
import wx.lib.buttons
import wx.lib.agw.customtreectrl as CT

try:
    import matplotlib
    matplotlib.use('WX')
    USE_MPL = True
except:
    USE_MPL = False

from PLCControler import ITEMS_VARIABLE, ITEM_CONFIGURATION, ITEM_RESOURCE, ITEM_POU, ITEM_TRANSITION, ITEM_ACTION
from util.BitmapLibrary import GetBitmap

class PouInstanceVariablesPanel(wx.Panel):
    
    def __init__(self, parent, window, controller, debug):
        wx.Panel.__init__(self, name='PouInstanceTreePanel', 
                parent=parent, pos=wx.Point(0, 0), 
                size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        
        self.ParentButton = wx.lib.buttons.GenBitmapButton(self,
              bitmap=GetBitmap("top"), size=wx.Size(28, 28), style=wx.NO_BORDER)
        self.ParentButton.SetToolTipString(_("Parent instance"))
        self.Bind(wx.EVT_BUTTON, self.OnParentButtonClick, 
                self.ParentButton)
        
        self.InstanceChoice = wx.ComboBox(self, size=wx.Size(0, 0), style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnInstanceChoiceChanged,
                self.InstanceChoice)
        self.InstanceChoice.Bind(wx.EVT_LEFT_DOWN, self.OnInstanceChoiceLeftDown)
        
        self.DebugButton = wx.lib.buttons.GenBitmapButton(self, 
              bitmap=GetBitmap("debug_instance"), size=wx.Size(28, 28), style=wx.NO_BORDER)
        self.ParentButton.SetToolTipString(_("Debug instance"))
        self.Bind(wx.EVT_BUTTON, self.OnDebugButtonClick, 
                self.DebugButton)
        
        self.VariablesList = CT.CustomTreeCtrl(self,
              style=wx.SUNKEN_BORDER,
              agwStyle=CT.TR_NO_BUTTONS|
                       CT.TR_SINGLE|
                       CT.TR_HAS_VARIABLE_ROW_HEIGHT|
                       CT.TR_HIDE_ROOT|
                       CT.TR_NO_LINES|
                       getattr(CT, "TR_ALIGN_WINDOWS_RIGHT", CT.TR_ALIGN_WINDOWS))
        self.VariablesList.SetIndent(0)
        self.VariablesList.SetSpacing(5)
        self.VariablesList.DoSelectItem = lambda *x,**y:True
        self.VariablesList.Bind(CT.EVT_TREE_ITEM_ACTIVATED,
                self.OnVariablesListItemActivated)
        self.VariablesList.Bind(wx.EVT_LEFT_DOWN, self.OnVariablesListLeftDown)
        self.VariablesList.Bind(wx.EVT_KEY_DOWN, self.OnVariablesListKeyDown)
        
        buttons_sizer = wx.FlexGridSizer(cols=3, hgap=0, rows=1, vgap=0)
        buttons_sizer.AddWindow(self.ParentButton)
        buttons_sizer.AddWindow(self.InstanceChoice, flag=wx.GROW)
        buttons_sizer.AddWindow(self.DebugButton)
        buttons_sizer.AddGrowableCol(1)
        buttons_sizer.AddGrowableRow(0)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        main_sizer.AddSizer(buttons_sizer, flag=wx.GROW)
        main_sizer.AddWindow(self.VariablesList, flag=wx.GROW)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        self.SetSizer(main_sizer)
        
        self.ParentWindow = window
        self.Controller = controller
        self.Debug = debug
        if not self.Debug:
            self.DebugButton.Hide()
        
        self.PouTagName = None
        self.PouInfos = None
        self.PouInstance = None
        
    def __del__(self):
        self.Controller = None
    
    def SetTreeImageList(self, tree_image_list):
        self.VariablesList.SetImageList(tree_image_list)
    
    def SetController(self, controller):
        self.Controller = controller
    
        self.RefreshView()
    
    def SetPouType(self, tagname, pou_instance=None):
        if  self.Controller is not None:
            self.PouTagName = tagname
            if self.PouTagName == "Project":
                config_name = self.Controller.GetProjectMainConfigurationName()
                if config_name is not None:
                    self.PouTagName = self.Controller.ComputeConfigurationName(config_name)
            if pou_instance is not None:
                self.PouInstance = pou_instance
        
        self.RefreshView()
    
    def ResetView(self):
        self.Controller = None
        
        self.PouTagName = None
        self.PouInfos = None
        self.PouInstance = None
        
        self.RefreshView()
    
    def RefreshView(self):
        self.VariablesList.DeleteAllItems()
        self.InstanceChoice.Clear()
        self.InstanceChoice.SetValue("")
        
        if self.Controller is not None and self.PouTagName is not None:
            self.PouInfos = self.Controller.GetPouVariables(self.PouTagName, self.Debug)
        else:
            self.PouInfos = None
        if self.PouInfos is not None:
            root = self.VariablesList.AddRoot("")
            for var_infos in self.PouInfos["variables"]:
                if var_infos.get("type", None) is not None:
                    text = "%(name)s (%(type)s)" % var_infos
                else:
                    text = var_infos["name"]
                
                panel = wx.Panel(self.VariablesList)
                    
                buttons = []
                if var_infos["class"] in ITEMS_VARIABLE:
                    if (not USE_MPL and var_infos["debug"] and self.Debug and
                        (self.Controller.IsOfType(var_infos["type"], "ANY_NUM", True) or
                         self.Controller.IsOfType(var_infos["type"], "ANY_BIT", True))):
                        graph_button = wx.lib.buttons.GenBitmapButton(panel, 
                              bitmap=GetBitmap("instance_graph"), 
                              size=wx.Size(28, 28), style=wx.NO_BORDER)
                        self.Bind(wx.EVT_BUTTON, self.GenGraphButtonCallback(var_infos), graph_button)
                        buttons.append(graph_button)
                elif var_infos["edit"]:
                    edit_button = wx.lib.buttons.GenBitmapButton(panel, 
                          bitmap=GetBitmap("edit"), 
                          size=wx.Size(28, 28), style=wx.NO_BORDER)
                    self.Bind(wx.EVT_BUTTON, self.GenEditButtonCallback(var_infos), edit_button)
                    buttons.append(edit_button)
                
                if var_infos["debug"] and self.Debug:
                    debug_button = wx.lib.buttons.GenBitmapButton(panel, 
                          bitmap=GetBitmap("debug_instance"), 
                          size=wx.Size(28, 28), style=wx.NO_BORDER)
                    self.Bind(wx.EVT_BUTTON, self.GenDebugButtonCallback(var_infos), debug_button)
                    buttons.append(debug_button)
                
                button_num = len(buttons)
                if button_num > 0:
                    panel.SetSize(wx.Size(button_num * 32, 28))
                    panel.SetBackgroundColour(self.VariablesList.GetBackgroundColour())
                    panel_sizer = wx.BoxSizer(wx.HORIZONTAL)
                    panel.SetSizer(panel_sizer)
                    
                    for button in buttons:
                        panel_sizer.AddWindow(button, 0, border=4, flag=wx.LEFT)
                    panel_sizer.Layout()
                    
                else:
                    panel.Destroy()
                    panel = None
                
                item = self.VariablesList.AppendItem(root, text, wnd=panel)
                self.VariablesList.SetItemImage(item, self.ParentWindow.GetTreeImage(var_infos["class"]))
                self.VariablesList.SetPyData(item, var_infos)
            
            instances = self.Controller.SearchPouInstances(self.PouTagName, self.Debug)
            for instance in instances:
                self.InstanceChoice.Append(instance)
            if len(instances) == 1:
                self.PouInstance = instances[0]
            if self.PouInfos["class"] in [ITEM_CONFIGURATION, ITEM_RESOURCE]:
                self.PouInstance = None
                self.InstanceChoice.SetSelection(0)
            elif self.PouInstance in instances:
                self.InstanceChoice.SetStringSelection(self.PouInstance)
            else:
                self.PouInstance = None
                self.InstanceChoice.SetValue(_("Select an instance"))
        
        self.RefreshButtons()
        
    def RefreshButtons(self):
        enabled = self.InstanceChoice.GetSelection() != -1
        self.ParentButton.Enable(enabled and self.PouInfos["class"] != ITEM_CONFIGURATION)
        self.DebugButton.Enable(enabled and self.PouInfos["debug"] and self.Debug)
        
        root = self.VariablesList.GetRootItem()
        if root is not None and root.IsOk():
            item, item_cookie = self.VariablesList.GetFirstChild(root)
            while item is not None and item.IsOk():
                panel = self.VariablesList.GetItemWindow(item)
                if panel is not None:
                    for child in panel.GetChildren():
                        if child.GetName() != "edit":
                            child.Enable(enabled)
                item, item_cookie = self.VariablesList.GetNextChild(root, item_cookie)
    
    def GenEditButtonCallback(self, infos):
        def EditButtonCallback(event):
            var_class = infos["class"]
            if var_class == ITEM_RESOURCE:
                tagname = self.Controller.ComputeConfigurationResourceName(
                    self.InstanceChoice.GetStringSelection(), 
                    infos["name"])
            elif var_class == ITEM_TRANSITION:
                tagname = self.Controller.ComputePouTransitionName(
                    self.PouTagName.split("::")[1],
                    infos["name"])
            elif var_class == ITEM_ACTION:
                tagname = self.Controller.ComputePouActionName(
                    self.PouTagName.split("::")[1],
                    infos["name"])
            else:
                var_class = ITEM_POU
                tagname = self.Controller.ComputePouName(infos["type"])
            self.ParentWindow.EditProjectElement(var_class, tagname)
            event.Skip()
        return EditButtonCallback
    
    def GenDebugButtonCallback(self, infos):
        def DebugButtonCallback(event):
            if self.InstanceChoice.GetSelection() != -1:
                var_class = infos["class"]
                var_path = "%s.%s" % (self.InstanceChoice.GetStringSelection(), 
                                      infos["name"])
                if var_class in ITEMS_VARIABLE:
                    self.ParentWindow.AddDebugVariable(var_path, force=True)
                elif var_class == ITEM_TRANSITION:
                    self.ParentWindow.OpenDebugViewer(
                        var_class,
                        var_path,
                        self.Controller.ComputePouTransitionName(
                            self.PouTagName.split("::")[1],
                            infos["name"]))
                elif var_class == ITEM_ACTION:
                    self.ParentWindow.OpenDebugViewer(
                        var_class,
                        var_path,
                        self.Controller.ComputePouActionName(
                            self.PouTagName.split("::")[1],
                            infos["name"]))
                else:
                    self.ParentWindow.OpenDebugViewer(
                        var_class,
                        var_path,
                        self.Controller.ComputePouName(infos["type"]))
            event.Skip()
        return DebugButtonCallback
    
    def GenGraphButtonCallback(self, infos):
        def GraphButtonCallback(event):
            if self.InstanceChoice.GetSelection() != -1:
                if infos["class"] in ITEMS_VARIABLE:
                    var_path = "%s.%s" % (self.InstanceChoice.GetStringSelection(), 
                                          infos["name"])
                    self.ParentWindow.OpenDebugViewer(infos["class"], var_path, infos["type"])
            event.Skip()
        return GraphButtonCallback
    
    def ShowInstanceChoicePopup(self):
        self.InstanceChoice.SetFocusFromKbd()
        size = self.InstanceChoice.GetSize()
        event = wx.MouseEvent(wx.EVT_LEFT_DOWN._getEvtType())
        event.m_x = size.width / 2
        event.m_y = size.height / 2
        event.SetEventObject(self.InstanceChoice)
        #event = wx.KeyEvent(wx.EVT_KEY_DOWN._getEvtType())
        #event.m_keyCode = wx.WXK_SPACE
        self.InstanceChoice.GetEventHandler().ProcessEvent(event)
    
    def OnParentButtonClick(self, event):
        if self.InstanceChoice.GetSelection() != -1:
            parent_path = self.InstanceChoice.GetStringSelection().rsplit(".", 1)[0]
            tagname = self.Controller.GetPouInstanceTagName(parent_path, self.Debug)
            if tagname is not None:
                wx.CallAfter(self.SetPouType, tagname, parent_path)
                wx.CallAfter(self.ParentWindow.SelectProjectTreeItem, tagname)
        event.Skip()
        
    def OnInstanceChoiceChanged(self, event):
        self.RefreshButtons()
        event.Skip()
        
    def OnDebugButtonClick(self, event):
        if self.InstanceChoice.GetSelection() != -1:
            self.ParentWindow.OpenDebugViewer(
                self.PouInfos["class"],
                self.InstanceChoice.GetStringSelection(),
                self.PouTagName)
        event.Skip()
        
    def OnVariablesListItemActivated(self, event):
        if self.InstanceChoice.GetSelection() != -1:
            instance_path = self.InstanceChoice.GetStringSelection()
            selected_item = event.GetItem()
            if selected_item is not None and selected_item.IsOk():
                item_infos = self.VariablesList.GetPyData(selected_item)
                if item_infos is not None and item_infos["class"] not in ITEMS_VARIABLE:
                    if item_infos["class"] == ITEM_RESOURCE:
                        tagname = self.Controller.ComputeConfigurationResourceName(
                                       instance_path, 
                                       item_infos["name"])
                    else:
                        tagname = self.Controller.ComputePouName(item_infos["type"])
                    item_path = "%s.%s" % (instance_path, item_infos["name"])
                    wx.CallAfter(self.SetPouType, tagname, item_path)
                    wx.CallAfter(self.ParentWindow.SelectProjectTreeItem, tagname)
        event.Skip()
    
    def OnVariablesListLeftDown(self, event):
        if self.InstanceChoice.GetSelection() == -1:
            wx.CallAfter(self.ShowInstanceChoicePopup)
        else:
            instance_path = self.InstanceChoice.GetStringSelection()
            item, flags = self.VariablesList.HitTest(event.GetPosition())
            if item is not None and flags & CT.TREE_HITTEST_ONITEMLABEL:
                item_infos = self.VariablesList.GetPyData(item)
                if item_infos is not None and item_infos["class"] in ITEMS_VARIABLE:
                    item_path = "%s.%s" % (instance_path, item_infos["name"])
                    data = wx.TextDataObject(str((item_path, "debug")))
                    dragSource = wx.DropSource(self.VariablesList)
                    dragSource.SetData(data)
                    dragSource.DoDragDrop()
        event.Skip()

    def OnVariablesListKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode != wx.WXK_LEFT:
            event.Skip()
        
    def OnInstanceChoiceLeftDown(self, event):
        event.Skip()
