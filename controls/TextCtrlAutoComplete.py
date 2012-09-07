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

import wx
import cPickle

MAX_ITEM_COUNT = 10
MAX_ITEM_SHOWN = 6
if wx.Platform == '__WXMSW__':
    ITEM_INTERVAL_HEIGHT = 3
else:
    ITEM_INTERVAL_HEIGHT = 6

if wx.Platform == '__WXMSW__':
    popupclass = wx.PopupTransientWindow
else:
    popupclass = wx.PopupWindow

class PopupWithListbox(popupclass):
    
    def __init__(self, parent, choices=[]):
        popupclass.__init__(self, parent, wx.SIMPLE_BORDER)
        
        self.ListBox = wx.ListBox(self, -1, style=wx.LB_HSCROLL|wx.LB_SINGLE|wx.LB_SORT)
        if not wx.Platform == '__WXMSW__':
            self.ListBox.Bind(wx.EVT_LISTBOX, self.OnListBoxClick)
            self.ListBox.Bind(wx.EVT_LISTBOX_DCLICK, self.OnListBoxClick)
            
        self.SetChoices(choices)
        
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
    
    def SetChoices(self, choices):
        max_text_width = 0
        max_text_height = 0
        
        self.ListBox.Clear()
        for choice in choices:
            self.ListBox.Append(choice)
            w, h = self.ListBox.GetTextExtent(choice)
            max_text_width = max(max_text_width, w)
            max_text_height = max(max_text_height, h)
        
        itemcount = min(len(choices), MAX_ITEM_SHOWN)
        width = self.Parent.GetSize()[0]
        height = max_text_height * itemcount + ITEM_INTERVAL_HEIGHT * (itemcount + 1)
        if max_text_width + 10 > width:
            height += 15
        size = wx.Size(width, height)
        self.ListBox.SetSize(size)
        self.SetClientSize(size)
    
    def MoveSelection(self, direction):
        selected = self.ListBox.GetSelection()
        if selected == wx.NOT_FOUND:
            if direction >= 0:
                selected = 0
            else:
                selected = self.ListBox.GetCount() - 1
        else:
            selected = (selected + direction) % (self.ListBox.GetCount() + 1)
        if selected == self.ListBox.GetCount():
            selected = wx.NOT_FOUND
        self.ListBox.SetSelection(selected)
    
    def GetSelection(self):
        return self.ListBox.GetStringSelection()
    
    def ProcessLeftDown(self, event):
        selected = self.ListBox.HitTest(wx.Point(event.m_x, event.m_y))
        if selected != wx.NOT_FOUND:
            wx.CallAfter(self.Parent.SetValueFromSelected, self.ListBox.GetString(selected))
        return False
    
    def OnListBoxClick(self, event):
        selected = event.GetSelection()
        if selected != wx.NOT_FOUND:
            wx.CallAfter(self.Parent.SetValueFromSelected, self.ListBox.GetString(selected))
        event.Skip()
    
    def OnKeyDown(self, event):
        self.Parent.ProcessEvent(event)

    def OnDismiss(self):
        self.Parent.listbox = None
        wx.CallAfter(self.Parent.DismissListBox)
    
class TextCtrlAutoComplete(wx.TextCtrl):

    def __init__ (self, parent, appframe, choices=None, dropDownClick=True,
                  element_path=None, **therest):
        """
        Constructor works just like wx.TextCtrl except you can pass in a
        list of choices.  You can also change the choice list at any time
        by calling setChoices.
        """

        therest['style'] = wx.TE_PROCESS_ENTER | therest.get('style', 0)

        wx.TextCtrl.__init__(self, parent, **therest)
        self.AppFrame = appframe
        
        #Some variables
        self._dropDownClick = dropDownClick
        self._lastinsertionpoint = None
        
        self._screenheight = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)
        self.element_path = element_path
        
        self.listbox = None
        
        self.SetChoices(choices)

        #gp = self
        #while ( gp != None ) :
        #    gp.Bind ( wx.EVT_MOVE , self.onControlChanged, gp )
        #    gp.Bind ( wx.EVT_SIZE , self.onControlChanged, gp )
        #    gp = gp.GetParent()

        self.Bind(wx.EVT_KILL_FOCUS, self.OnControlChanged)
        self.Bind(wx.EVT_TEXT_ENTER, self.OnControlChanged)
        self.Bind(wx.EVT_TEXT, self.OnEnteredText)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        #If need drop down on left click
        if dropDownClick:
            self.Bind(wx.EVT_LEFT_DOWN, self.OnClickToggleDown)
            self.Bind(wx.EVT_LEFT_UP, self.OnClickToggleUp)

    def __del__(self):
        self.AppFrame = None

    def ChangeValue(self, value):
        wx.TextCtrl.ChangeValue(self, value)
        self.RefreshListBoxChoices()

    def OnEnteredText(self, event):
        wx.CallAfter(self.RefreshListBoxChoices)
        event.Skip()

    def OnKeyDown(self, event):
        """ Do some work when the user press on the keys:
            up and down: move the cursor
        """
        keycode = event.GetKeyCode()
        if keycode in [wx.WXK_DOWN, wx.WXK_UP]:
            self.PopupListBox()
            if keycode == wx.WXK_DOWN:
                self.listbox.MoveSelection(1)
            else:
                self.listbox.MoveSelection(-1)
        elif keycode in [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_RETURN] and self.listbox is not None:
            self.SetValueFromSelected(self.listbox.GetSelection())
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self.DismissListBox()
        else:
            event.Skip()

    def OnClickToggleDown(self, event):
        self._lastinsertionpoint = self.GetInsertionPoint()
        event.Skip()

    def OnClickToggleUp(self, event):
        if self.GetInsertionPoint() == self._lastinsertionpoint:
            wx.CallAfter(self.PopupListBox)
        self._lastinsertionpoint = None
        event.Skip()

    def OnControlChanged(self, event):
        res = self.GetValue()
        config = wx.ConfigBase.Get()
        listentries = cPickle.loads(str(config.Read(self.element_path, cPickle.dumps([]))))
        if res and res not in listentries:
            listentries = (listentries + [res])[-MAX_ITEM_COUNT:]
            config.Write(self.element_path, cPickle.dumps(listentries))
            config.Flush()
            self.SetChoices(listentries)
        self.DismissListBox()
        event.Skip()
    
    def SetChoices(self, choices):
        self._choices = choices
        self.RefreshListBoxChoices()
        
    def GetChoices(self):
        return self._choices
    
    def SetValueFromSelected(self, selected):
         """
         Sets the wx.TextCtrl value from the selected wx.ListCtrl item.
         Will do nothing if no item is selected in the wx.ListCtrl.
         """
         if selected != "":
            self.SetValue(selected)
         self.DismissListBox()
    
    def RefreshListBoxChoices(self):
        if self.listbox is not None:
            text = self.GetValue()
            choices = [choice for choice in self._choices if choice.startswith(text)]
            self.listbox.SetChoices(choices)

    def PopupListBox(self):
        if self.listbox is None:
            self.listbox = PopupWithListbox(self)
            
            # Show the popup right below or above the button
            # depending on available screen space...
            pos = self.ClientToScreen((0, 0))
            sz = self.GetSize()
            self.listbox.Position(pos, (0, sz[1]))
            
            self.RefreshListBoxChoices()
            
            if wx.Platform == '__WXMSW__':
                self.listbox.Popup()
            else:
                self.listbox.Show()
            self.AppFrame.EnableScrolling(False)

    def DismissListBox(self):
        if self.listbox is not None:
            if wx.Platform == '__WXMSW__':
                self.listbox.Dismiss()
            else:
                self.listbox.Destroy()
            self.listbox = None
        self.AppFrame.EnableScrolling(True)

