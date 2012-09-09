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
import wx.gizmos

class CustomEditableListBox(wx.gizmos.EditableListBox):
    
    def __init__(self, *args, **kwargs):
        wx.gizmos.EditableListBox.__init__(self, *args, **kwargs)
        
        listbox = self.GetListCtrl()
        listbox.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        listbox.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.OnLabelBeginEdit)
        listbox.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.OnLabelEndEdit)
        
        for button, tooltip, call_function in [
                (self.GetEditButton(), _("Edit item"), "_OnEditButton"),
                (self.GetNewButton(), _("New item"), "_OnNewButton"),
                (self.GetDelButton(), _("Delete item"), "_OnDelButton"),
                (self.GetUpButton(), _("Move up"), "_OnUpButton"),
                (self.GetDownButton(), _("Move down"), "_OnDownButton")]:
            button.SetToolTipString(tooltip)
            button.Bind(wx.EVT_BUTTON, self.GetButtonPressedFunction(call_function))
    
        self.Editing = False
    
    def EnsureCurrentItemVisible(self):
        listctrl = self.GetListCtrl()
        listctrl.EnsureVisible(listctrl.GetFocusedItem())
    
    def OnLabelBeginEdit(self, event):
        self.Editing = True
        func = getattr(self, "_OnLabelBeginEdit", None)
        if func is not None:
            func(event)
        else:
            event.Skip()
        
    def OnLabelEndEdit(self, event):
        self.Editing = False
        func = getattr(self, "_OnLabelEndEdit", None)
        if func is not None:
            func(event)
        else:
            event.Skip()
    
    def GetButtonPressedFunction(self, call_function):
        def OnButtonPressed(event):
            if wx.Platform != '__WXMSW__' or not self.Editing:
                func = getattr(self, call_function, None)
                if func is not None:
                    func(event)
                    wx.CallAfter(self.EnsureCurrentItemVisible)
                else:
                    wx.CallAfter(self.EnsureCurrentItemVisible)
                    event.Skip()
        return OnButtonPressed
    
    def OnKeyDown(self, event):
        button = None
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_ADD, wx.WXK_NUMPAD_ADD):
            button = self.GetNewButton()
        elif keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            button = self.GetDelButton()
        elif keycode == wx.WXK_UP and event.ShiftDown():
            button = self.GetUpButton()
        elif keycode == wx.WXK_DOWN and event.ShiftDown():
            button = self.GetDownButton()
        elif keycode == wx.WXK_SPACE:
            button = self.GetEditButton()
        if button is not None and button.IsEnabled():
            button.ProcessEvent(wx.CommandEvent(wx.EVT_BUTTON.typeId, button.GetId()))
        else:
            event.Skip()
