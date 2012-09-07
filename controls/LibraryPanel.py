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

#-------------------------------------------------------------------------------
#                                 Helpers
#-------------------------------------------------------------------------------

[CATEGORY, BLOCK] = range(2)

#-------------------------------------------------------------------------------
#                              Library Panel
#-------------------------------------------------------------------------------

class LibraryPanel(wx.Panel):
    
    def __init__(self, parent, enable_drag=False):
        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        self.SearchCtrl = wx.SearchCtrl(self)
        self.SearchCtrl.ShowSearchButton(True)
        self.Bind(wx.EVT_TEXT, self.OnSearchCtrlChanged, self.SearchCtrl)
        self.Bind(wx.EVT_SEARCHCTRL_SEARCH_BTN, 
              self.OnSearchButtonClick, self.SearchCtrl)
        search_textctrl = self.SearchCtrl.GetChildren()[0]
        search_textctrl.Bind(wx.EVT_CHAR, self.OnKeyDown)
        main_sizer.AddWindow(self.SearchCtrl, flag=wx.GROW)
        
        splitter_window = wx.SplitterWindow(self)
        splitter_window.SetSashGravity(1.0)
        main_sizer.AddWindow(splitter_window, flag=wx.GROW)
        
        self.Tree = wx.TreeCtrl(splitter_window,
              size=wx.Size(0, 0),  
              style=wx.TR_HAS_BUTTONS|
                    wx.TR_SINGLE|
                    wx.SUNKEN_BORDER|
                    wx.TR_HIDE_ROOT|
                    wx.TR_LINES_AT_ROOT)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemSelected, self.Tree)
        self.Tree.Bind(wx.EVT_CHAR, self.OnKeyDown)
        if enable_drag:
            self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag, self.Tree)
        
        self.Comment = wx.TextCtrl(splitter_window, size=wx.Size(0, 80), 
              style=wx.TE_READONLY|wx.TE_MULTILINE)
        
        splitter_window.SplitHorizontally(self.Tree, self.Comment, -80)
        
        self.SetSizer(main_sizer)
            
        self.Controller = None
    
        self.BlockList = None
    
    def __del__(self):
        self.Controller = None
    
    def SetController(self, controller):
        self.Controller = controller
    
    def SetBlockList(self, blocklist):
        self.BlockList = blocklist
        self.RefreshTree()
    
    def SetFocus(self):
        self.SearchCtrl.SetFocus()
    
    def ResetTree(self):
        self.SearchCtrl.SetValue("")
        self.Tree.DeleteAllItems()
        self.Comment.SetValue("")
    
    def RefreshTree(self):
        if self.Controller is not None:
            to_delete = []
            selected_name = None
            selected = self.Tree.GetSelection()
            if selected.IsOk():
                selected_pydata = self.Tree.GetPyData(selected)
                if selected_pydata is not None and selected_pydata["type"] != CATEGORY:
                    selected_name = self.Tree.GetItemText(selected)
            if self.BlockList is not None:
                blocktypes = self.BlockList
            else:
                blocktypes = self.Controller.GetBlockTypes()
            root = self.Tree.GetRootItem()
            if not root.IsOk():
                root = self.Tree.AddRoot("")
            category_item, root_cookie = self.Tree.GetFirstChild(root)
            for category in blocktypes:
                category_name = category["name"]
                if not category_item.IsOk():
                    category_item = self.Tree.AppendItem(root, _(category_name))
                    if wx.Platform != '__WXMSW__':
                        category_item, root_cookie = self.Tree.GetNextChild(root, root_cookie)
                else:
                    self.Tree.SetItemText(category_item, _(category_name))
                self.Tree.SetPyData(category_item, {"type" : CATEGORY})
                blocktype_item, category_cookie = self.Tree.GetFirstChild(category_item)
                for blocktype in category["list"]:
                    if not blocktype_item.IsOk():
                        blocktype_item = self.Tree.AppendItem(category_item, blocktype["name"])
                        if wx.Platform != '__WXMSW__':
                            blocktype_item, category_cookie = self.Tree.GetNextChild(category_item, category_cookie)
                    else:
                        self.Tree.SetItemText(blocktype_item, blocktype["name"])
                    block_data = {"type" : BLOCK, 
                                  "block_type" : blocktype["type"], 
                                  "inputs" : tuple([type for name, type, modifier in blocktype["inputs"]]), 
                                  "extension" : None}
                    if blocktype["extensible"]:
                        block_data["extension"] = len(blocktype["inputs"])
                    self.Tree.SetPyData(blocktype_item, block_data)
                    if selected_name == blocktype["name"]:
                        self.Tree.SelectItem(blocktype_item)
                        comment = blocktype["comment"]
                        self.Comment.SetValue(_(comment) + blocktype.get("usage", ""))
                    blocktype_item, category_cookie = self.Tree.GetNextChild(category_item, category_cookie)
                while blocktype_item.IsOk():
                    to_delete.append(blocktype_item)
                    blocktype_item, category_cookie = self.Tree.GetNextChild(category_item, category_cookie)
                category_item, root_cookie = self.Tree.GetNextChild(root, root_cookie)
            while category_item.IsOk():
                to_delete.append(category_item)
                category_item, root_cookie = self.Tree.GetNextChild(root, root_cookie)
            for item in to_delete:
                self.Tree.Delete(item)
    
    def GetSelectedBlock(self):
        selected = self.Tree.GetSelection()
        if (selected.IsOk() and 
            self.Tree.GetItemParent(selected) != self.Tree.GetRootItem() and 
            selected != self.Tree.GetRootItem()):
            selected_data = self.Tree.GetPyData(selected)
            return {"type": self.Tree.GetItemText(selected), 
                    "inputs": selected_data["inputs"]}
        return None
    
    def SelectTreeItem(self, name, inputs):
        item = self.FindTreeItem(self.Tree.GetRootItem(), name, inputs)
        if item is not None and item.IsOk():
            self.Tree.SelectItem(item)
            self.Tree.EnsureVisible(item)
    
    def FindTreeItem(self, root, name, inputs = None):
        if root.IsOk():
            pydata = self.Tree.GetPyData(root)
            if pydata is not None:
                type_inputs = pydata.get("inputs", None)
                type_extension = pydata.get("extension", None)
                if inputs is not None and type_inputs is not None:
                    if type_extension is not None:
                        same_inputs = type_inputs == inputs[:type_extension]
                    else:
                        same_inputs = type_inputs == inputs
                else:
                    same_inputs = True
            if pydata is not None and self.Tree.GetItemText(root) == name and same_inputs:
                return root
            else:
                if wx.VERSION < (2, 6, 0):
                    item, root_cookie = self.Tree.GetFirstChild(root, 0)
                else:
                    item, root_cookie = self.Tree.GetFirstChild(root)
                while item.IsOk():
                    result = self.FindTreeItem(item, name, inputs)
                    if result:
                        return result
                    item, root_cookie = self.Tree.GetNextChild(root, root_cookie)
        return None
    
    def SearchInTree(self, value, mode="first"):
        root = self.Tree.GetRootItem()
        if not root.IsOk():
            return False
        
        if mode == "first":
            item, item_cookie = self.Tree.GetFirstChild(root)
            selected = None
        else:
            item = self.Tree.GetSelection()
            selected = item
            if not item.IsOk():
                item, item_cookie = self.Tree.GetFirstChild(root)
        while item.IsOk():
            item_pydata = self.Tree.GetPyData(item)
            if item_pydata["type"] == CATEGORY:
                if mode == "previous":
                    child = self.Tree.GetLastChild(item)
                else:
                    child, child_cookie = self.Tree.GetFirstChild(item)
                if child.IsOk():
                    item = child
                elif mode == "previous":
                    item = self.Tree.GetPrevSibling(item)
                else:
                    item = self.Tree.GetNextSibling(item)
            else:
                name = self.Tree.GetItemText(item)
                if name.upper().startswith(value.upper()) and item != selected:
                    child, child_cookie = self.Tree.GetFirstChild(root)
                    while child.IsOk():
                        self.Tree.CollapseAllChildren(child)
                        child, child_cookie = self.Tree.GetNextChild(root, child_cookie)
                    self.Tree.SelectItem(item)
                    self.Tree.EnsureVisible(item)
                    return True
                
                elif mode == "previous":
                    previous = self.Tree.GetPrevSibling(item)
                    if previous.IsOk():
                        item = previous
                    else:
                        parent = self.Tree.GetItemParent(item)
                        item = self.Tree.GetPrevSibling(parent)
                
                else:
                    next = self.Tree.GetNextSibling(item)
                    if next.IsOk():
                        item = next
                    else:
                        parent = self.Tree.GetItemParent(item)
                        item = self.Tree.GetNextSibling(parent)
        return False
    
    def OnSearchCtrlChanged(self, event):
        self.SearchInTree(self.SearchCtrl.GetValue())
        event.Skip()
    
    def OnSearchButtonClick(self, event):
        self.SearchInTree(self.SearchCtrl.GetValue(), "next")
        event.Skip()
    
    def OnTreeItemSelected(self, event):
        selected = event.GetItem()
        pydata = self.Tree.GetPyData(selected)
        if pydata is not None and pydata["type"] != CATEGORY:
            blocktype = self.Controller.GetBlockType(self.Tree.GetItemText(selected), pydata["inputs"])
            if blocktype:
                comment = blocktype["comment"]
                self.Comment.SetValue(_(comment) + blocktype.get("usage", ""))
            else:
                self.Comment.SetValue("")
        else:
            self.Comment.SetValue("")
        if getattr(self, "_OnTreeItemSelected", None) is not None:
            self._OnTreeItemSelected(event)
        event.Skip()
    
    def OnTreeBeginDrag(self, event):
        selected = event.GetItem()
        pydata = self.Tree.GetPyData(selected)
        if pydata is not None and pydata["type"] == BLOCK:
            data = wx.TextDataObject(str((self.Tree.GetItemText(selected), 
                pydata["block_type"], "", pydata["inputs"])))
            dragSource = wx.DropSource(self.Tree)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
    
    def OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        search_value = self.SearchCtrl.GetValue()
        if keycode == wx.WXK_UP and search_value != "":
            self.SearchInTree(search_value, "previous")
        elif keycode == wx.WXK_DOWN and search_value != "":
            self.SearchInTree(search_value, "next")
        else:
            event.Skip()
