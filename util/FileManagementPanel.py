#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
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

import os
import shutil

import wx

from controls import EditorPanel
from utils.BitmapLibrary import GetBitmap

DRIVE, FOLDER, FILE = range(3)

FILTER = _("All files (*.*)|*.*|CSV files (*.csv)|*.csv")

def sort_folder(x, y):
    if x[1] == y[1]:
        return cmp(x[0], y[0])
    elif x[1] != FILE:
        return -1
    else:
        return 1

def splitpath(path):
    head, tail = os.path.split(path)
    if head == "":
        return [tail]
    elif tail == "":
        return splitpath(head)
    return splitpath(head) + [tail]
    
class FolderTree(wx.Panel):
    
    def __init__(self, parent, folder, filter, editable=True):
        wx.Panel.__init__(self, parent, style=wx.TAB_TRAVERSAL)
        
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        
        self.Tree = wx.TreeCtrl(self, 
              style=wx.TR_HAS_BUTTONS|
                    wx.TR_SINGLE|
                    wx.SUNKEN_BORDER|
                    wx.TR_HIDE_ROOT|
                    wx.TR_LINES_AT_ROOT|
                    wx.TR_EDIT_LABELS)
        if wx.Platform == '__WXMSW__':
            self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemExpanded, self.Tree)
            self.Tree.Bind(wx.EVT_LEFT_DOWN, self.OnTreeLeftDown)
        else:
            self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnTreeItemExpanded, self.Tree)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnTreeItemCollapsed, self.Tree)
        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnTreeBeginLabelEdit, self.Tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnTreeEndLabelEdit, self.Tree)
        main_sizer.AddWindow(self.Tree, 1, flag=wx.GROW)
        
        self.Filter = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnFilterChanged, self.Filter)
        main_sizer.AddWindow(self.Filter, flag=wx.GROW)
        
        self.SetSizer(main_sizer)
        
        self.Folder = folder
        self.Editable = editable
        
        self.TreeImageList = wx.ImageList(16, 16)
        self.TreeImageDict = {}
        for item_type, bitmap in [(DRIVE, "tree_drive"),
                                  (FOLDER, "tree_folder"),
                                  (FILE, "tree_file")]:
            self.TreeImageDict[item_type] = self.TreeImageList.Add(GetBitmap(bitmap))
        self.Tree.SetImageList(self.TreeImageList)
        
        self.Filters = {}
        filter_parts = filter.split("|")
        for idx in xrange(0, len(filter_parts), 2):
            if filter_parts[idx + 1] == "*.*":
                self.Filters[filter_parts[idx]] = ""
            else:
                self.Filters[filter_parts[idx]] = filter_parts[idx + 1].replace("*", "")
            self.Filter.Append(filter_parts[idx])
            if idx == 0:
                self.Filter.SetStringSelection(filter_parts[idx])
            
        self.CurrentFilter = self.Filters[self.Filter.GetStringSelection()]
    
    def _GetFolderChildren(self, folderpath, recursive=True):
        items = []
        if wx.Platform == '__WXMSW__' and folderpath == "/":
            for c in xrange(ord('a'), ord('z')):
                drive = os.path.join("%s:\\" % chr(c))
                if os.path.exists(drive):
                    items.append((drive, DRIVE, self._GetFolderChildren(drive, False)))
        else:
            try:
                files = os.listdir(folderpath)
            except:
                return []
            for filename in files:
                if not filename.startswith("."):
                    filepath = os.path.join(folderpath, filename)
                    if os.path.isdir(filepath):
                        if recursive:
                            children = len(self._GetFolderChildren(filepath, False))
                        else:
                            children = 0
                        items.append((filename, FOLDER, children))
                    elif (self.CurrentFilter == "" or 
                          os.path.splitext(filename)[1] == self.CurrentFilter):
                        items.append((filename, FILE, None))
        if recursive:
            items.sort(sort_folder)
        return items
    
    def GetTreeCtrl(self):
        return self.Tree
    
    def RefreshTree(self):
        root = self.Tree.GetRootItem()
        if not root.IsOk():
            root = self.Tree.AddRoot("")
        self.GenerateTreeBranch(root, self.Folder)
        
    def GenerateTreeBranch(self, root, folderpath):
        item, item_cookie = self.Tree.GetFirstChild(root)
        for idx, (filename, item_type, children) in enumerate(self._GetFolderChildren(folderpath)):
            if not item.IsOk():
                item = self.Tree.AppendItem(root, filename, self.TreeImageDict[item_type])
                if wx.Platform != '__WXMSW__':
                    item, item_cookie = self.Tree.GetNextChild(root, item_cookie)
            elif self.Tree.GetItemText(item) != filename:
                item = self.Tree.InsertItemBefore(root, idx, filename, self.TreeImageDict[item_type])
            filepath = os.path.join(folderpath, filename)
            if item_type != FILE:
                if self.Tree.IsExpanded(item):
                    self.GenerateTreeBranch(item, filepath)
                elif children > 0:
                    self.Tree.SetItemHasChildren(item)
            item, item_cookie = self.Tree.GetNextChild(root, item_cookie)
        to_delete = []
        while item.IsOk():
            to_delete.append(item)
            item, item_cookie = self.Tree.GetNextChild(root, item_cookie)
        for item in to_delete:
            self.Tree.Delete(item)

    def ExpandItem(self, item):
        self.GenerateTreeBranch(item, self.GetPath(item))
        self.Tree.Expand(item)
    
    def OnTreeItemActivated(self, event):
        self.ExpandItem(event.GetItem())
        event.Skip()
    
    def OnTreeLeftDown(self, event):
        item, flags = self.Tree.HitTest(event.GetPosition())
        if flags & wx.TREE_HITTEST_ONITEMBUTTON and not self.Tree.IsExpanded(item):
            self.ExpandItem(item)
        else:
            event.Skip()
    
    def OnTreeItemExpanded(self, event):
        item = event.GetItem()
        self.GenerateTreeBranch(item, self.GetPath(item))
        event.Skip()

    def OnTreeItemCollapsed(self, event):
        item = event.GetItem()
        self.Tree.DeleteChildren(item)
        self.Tree.SetItemHasChildren(item)
        event.Skip()

    def OnTreeBeginLabelEdit(self, event):
        item = event.GetItem()
        if self.Editable and not self.Tree.ItemHasChildren(item):
            event.Skip()
        else:
            event.Veto()
    
    def OnTreeEndLabelEdit(self, event):
        old_filepath = self.GetPath(event.GetItem())
        new_filepath = os.path.join(os.path.split(old_filepath)[0], event.GetLabel())
        if new_filepath != old_filepath:
            if not os.path.exists(new_filepath):
                os.rename(old_filepath, new_filepath)
                event.Skip()
            else:
                message =  wx.MessageDialog(self, 
                    _("File '%s' already exists!") % event.GetLabel(), 
                    _("Error"), wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
                event.Veto()
    
    def OnFilterChanged(self, event):
        self.CurrentFilter = self.Filters[self.Filter.GetStringSelection()]
        self.RefreshTree()
        event.Skip()
    
    def _SelectItem(self, root, parts):
        if len(parts) == 0:
            self.Tree.SelectItem(root)
        else:
            item, item_cookie = self.Tree.GetFirstChild(root)
            while item.IsOk():
                if self.Tree.GetItemText(item) == parts[0]:
                    if (self.Tree.ItemHasChildren(item) and 
                        not self.Tree.IsExpanded(item)):
                        self.Tree.Expand(item)
                        wx.CallAfter(self._SelectItem, item, parts[1:])
                    else:
                        self._SelectItem(item, parts[1:])
                    return
                item, item_cookie = self.Tree.GetNextChild(root, item_cookie)
    
    def SetPath(self, path):
        if path.startswith(self.Folder):
            root = self.Tree.GetRootItem()
            if root.IsOk():
                relative_path = path.replace(os.path.join(self.Folder, ""), "")
                self._SelectItem(root, splitpath(relative_path))
    
    def GetPath(self, item=None):
        if item is None:
            item = self.Tree.GetSelection()
        if item.IsOk():
            filepath = self.Tree.GetItemText(item)
            parent = self.Tree.GetItemParent(item)
            while parent.IsOk() and parent != self.Tree.GetRootItem():
                filepath = os.path.join(self.Tree.GetItemText(parent), filepath)
                parent = self.Tree.GetItemParent(parent)
            return os.path.join(self.Folder, filepath)
        return self.Folder

class FileManagementPanel(EditorPanel):
    
    def _init_Editor(self, parent):
        self.Editor = wx.Panel(parent)
        
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSizer(left_sizer, 1, border=5, flag=wx.GROW|wx.ALL)
        
        managed_dir_label = wx.StaticText(self.Editor, label=self.TagName + ":")
        left_sizer.AddWindow(managed_dir_label, border=5, flag=wx.GROW|wx.BOTTOM)
        
        self.ManagedDir = FolderTree(self.Editor, self.Folder, FILTER)
        left_sizer.AddWindow(self.ManagedDir, 1, flag=wx.GROW)
        
        managed_treectrl = self.ManagedDir.GetTreeCtrl()
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemChanged, managed_treectrl)
        if self.EnableDragNDrop:
            self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag, managed_treectrl)
        
        button_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSizer(button_sizer, border=5, 
              flag=wx.ALL|wx.ALIGN_CENTER_VERTICAL)
        
        for idx, (name, bitmap, help) in enumerate([
                ("DeleteButton", "remove_element", _("Remove file from left folder")),
                ("LeftCopyButton", "LeftCopy", _("Copy file from right folder to left")),
                ("RightCopyButton", "RightCopy", _("Copy file from left folder to right")),
                ("EditButton", "edit", _("Edit file"))]):
            button = wx.lib.buttons.GenBitmapButton(self.Editor, 
                  bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            if idx > 0:
                flag = wx.TOP
            else:
                flag = 0
            self.Bind(wx.EVT_BUTTON, getattr(self, "On" + name), button)
            button_sizer.AddWindow(button, border=20, flag=flag)
        
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.AddSizer(right_sizer, 1, border=5, flag=wx.GROW|wx.ALL)
        
        if wx.Platform == '__WXMSW__':
            system_dir_label = wx.StaticText(self.Editor, label=_("My Computer:"))
        else:
            system_dir_label = wx.StaticText(self.Editor, label=_("Home Directory:"))
        right_sizer.AddWindow(system_dir_label, border=5, flag=wx.GROW|wx.BOTTOM)
        
        self.SystemDir = FolderTree(self.Editor, self.HomeDirectory, FILTER, False)
        right_sizer.AddWindow(self.SystemDir, 1, flag=wx.GROW)
        
        system_treectrl = self.SystemDir.GetTreeCtrl()
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeItemChanged, system_treectrl)
        
        self.Editor.SetSizer(main_sizer)
        
    def __init__(self, parent, controler, name, folder, enable_dragndrop=False):
        self.Folder = os.path.realpath(folder)
        self.EnableDragNDrop = enable_dragndrop
        
        if wx.Platform == '__WXMSW__':
            self.HomeDirectory = "/"
        else:
            self.HomeDirectory = os.path.expanduser("~")
        
        EditorPanel.__init__(self, parent, name, None, None)
        
        self.Controler = controler
        
        self.EditableFileExtensions = []
        self.EditButton.Hide()
        
        self.SetIcon(GetBitmap("FOLDER"))
    
    def __del__(self):
        self.Controler.OnCloseEditor(self)
    
    def GetTitle(self):
        return self.TagName
    
    def SetEditableFileExtensions(self, extensions):
        self.EditableFileExtensions = extensions
        if len(self.EditableFileExtensions) > 0:
            self.EditButton.Show()
    
    def RefreshView(self):
        self.ManagedDir.RefreshTree()
        self.SystemDir.RefreshTree()
        self.RefreshButtonsState()
    
    def RefreshButtonsState(self):
        managed_filepath = self.ManagedDir.GetPath()
        system_filepath = self.SystemDir.GetPath()
        
        self.DeleteButton.Enable(os.path.isfile(managed_filepath))
        self.LeftCopyButton.Enable(os.path.isfile(system_filepath))
        self.RightCopyButton.Enable(os.path.isfile(managed_filepath))
        if len(self.EditableFileExtensions) > 0:
            self.EditButton.Enable(
                os.path.isfile(managed_filepath) and
                os.path.splitext(managed_filepath)[1] in self.EditableFileExtensions)
    
    def OnTreeItemChanged(self, event):
        self.RefreshButtonsState()
        event.Skip()
        
    def OnDeleteButton(self, event):
        filepath = self.ManagedDir.GetPath()
        if os.path.isfile(filepath):
            folder, filename = os.path.split(filepath)
            
            dialog = wx.MessageDialog(self, 
                  _("Do you really want to delete the file '%s'?") % filename, 
                  _("Delete File"), wx.YES_NO|wx.ICON_QUESTION)
            remove = dialog.ShowModal() == wx.ID_YES
            dialog.Destroy()
            
            if remove:
                os.remove(filepath)
                self.ManagedDir.RefreshTree()
        event.Skip()

    def OnEditButton(self, event):
        filepath = self.ManagedDir.GetPath()
        if (os.path.isfile(filepath) and 
            os.path.splitext(filepath)[1] in self.EditableFileExtensions):
            self.Controler._OpenView(filepath + "::")
        event.Skip()
        
    def CopyFile(self, src, dst):
        if os.path.isfile(src):
            src_folder, src_filename = os.path.split(src)
            if os.path.isfile(dst):
                dst_folder, dst_filename = os.path.split(dst)
            else:
                dst_folder = dst
            
            dst_filepath = os.path.join(dst_folder, src_filename)
            if os.path.isfile(dst_filepath):
                dialog = wx.MessageDialog(self, 
                      _("The file '%s' already exist.\nDo you want to replace it?") % src_filename, 
                      _("Replace File"), wx.YES_NO|wx.ICON_QUESTION)
                copy = dialog.ShowModal() == wx.ID_YES
                dialog.Destroy()
            else:
                copy = True
                
            if copy:
                shutil.copyfile(src, dst_filepath)
                return dst_filepath
        return None

    def OnLeftCopyButton(self, event):
        filepath = self.CopyFile(self.SystemDir.GetPath(), self.ManagedDir.GetPath())
        if filepath is not None:
            self.ManagedDir.RefreshTree()
            self.ManagedDir.SetPath(filepath)
        event.Skip()

    def OnRightCopyButton(self, event):
        filepath = self.CopyFile(self.ManagedDir.GetPath(), self.SystemDir.GetPath())
        if filepath is not None:
            self.SystemDir.RefreshTree()
            self.SystemDir.SetPath(filepath)
        event.Skip()
    
    def OnTreeBeginDrag(self, event):
        filepath = self.ManagedDir.GetPath()
        if os.path.isfile(filepath):
            relative_filepath = filepath.replace(os.path.join(self.Folder, ""), "")
            data = wx.TextDataObject(str(("'%s'" % relative_filepath, "Constant")))
            dragSource = wx.DropSource(self)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        