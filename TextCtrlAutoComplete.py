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
ITEM_HEIGHT = 25

class TextCtrlAutoComplete(wx.TextCtrl):

    def __init__ (self, parent, choices=None, dropDownClick=True,
                  element_path=None, **therest):
        """
        Constructor works just like wx.TextCtrl except you can pass in a
        list of choices.  You can also change the choice list at any time
        by calling setChoices.
        """

        therest['style'] = wx.TE_PROCESS_ENTER | therest.get('style', 0)

        wx.TextCtrl.__init__(self, parent, **therest)

        #Some variables
        self._dropDownClick = dropDownClick
        self._lastinsertionpoint = None
        
        self._screenheight = wx.SystemSettings.GetMetric(wx.SYS_SCREEN_Y)
        self.element_path = element_path
        
        #widgets
        self.dropdown = wx.PopupWindow(self)

        #Control the style
        flags = wx.LB_HSCROLL | wx.LB_SINGLE | wx.LB_SORT
        
        #Create the list and bind the events
        self.dropdownlistbox = wx.ListBox(self.dropdown, style=flags,
                                 pos=wx.Point(0, 0))
        
        self.SetChoices(choices)

        #gp = self
        #while ( gp != None ) :
        #    gp.Bind ( wx.EVT_MOVE , self.onControlChanged, gp )
        #    gp.Bind ( wx.EVT_SIZE , self.onControlChanged, gp )
        #    gp = gp.GetParent()

        self.Bind(wx.EVT_KILL_FOCUS, self.onControlChanged, self)
        self.Bind(wx.EVT_TEXT_ENTER, self.onControlChanged, self)
        self.Bind(wx.EVT_TEXT, self.onEnteredText, self)
        self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown, self)

        #If need drop down on left click
        if dropDownClick:
            self.Bind(wx.EVT_LEFT_DOWN , self.onClickToggleDown, self)
            self.Bind(wx.EVT_LEFT_UP , self.onClickToggleUp, self)

        self.dropdownlistbox.Bind(wx.EVT_LISTBOX, self.onListItemSelected)
        self.dropdownlistbox.Bind(wx.EVT_LISTBOX_DCLICK, self.onListItemSelected)

    def ChangeValue(self, value):
        wx.TextCtrl.ChangeValue(self, value)
        self._refreshListBoxChoices()

    def onEnteredText(self, event):
        wx.CallAfter(self._refreshListBoxChoices)
        event.Skip()

    def onKeyDown(self, event) :
        """ Do some work when the user press on the keys:
            up and down: move the cursor
        """
        visible = self.dropdown.IsShown()
        keycode = event.GetKeyCode()
        if keycode in [wx.WXK_DOWN, wx.WXK_UP]:
            if not visible:
                self._showDropDown()
            elif keycode == wx.WXK_DOWN:
                self._moveSelection(1)
            else:
                self._moveSelection(-1)
        elif keycode in [wx.WXK_LEFT, wx.WXK_RIGHT, wx.WXK_RETURN] and visible:
            if self.dropdownlistbox.GetSelection() != wx.NOT_FOUND:
                self._setValueFromSelected()
            else:
                self._showDropDown(False)
                event.Skip()
        elif event.GetKeyCode() == wx.WXK_ESCAPE:
            self._showDropDown(False)
        else:
            event.Skip()

    def onListItemSelected(self, event):
        self._setValueFromSelected()
        event.Skip()

    def onClickToggleDown(self, event):
        self._lastinsertionpoint = self.GetInsertionPoint()
        event.Skip()

    def onClickToggleUp(self, event):
        if self.GetInsertionPoint() == self._lastinsertionpoint:
            self._showDropDown(not self.dropdown.IsShown())
        self._lastinsertionpoint = None
        event.Skip()

    def onControlChanged(self, event):
        res = self.GetValue()
        config = wx.ConfigBase.Get()
        listentries = cPickle.loads(str(config.Read(self.element_path, cPickle.dumps([]))))
        if res and res not in listentries:
            listentries = (listentries + [res])[-MAX_ITEM_COUNT:]
            config.Write(self.element_path, cPickle.dumps(listentries))
            config.Flush()
            self.SetChoices(listentries)
        self._showDropDown(False)
        event.Skip()
    
    def SetChoices(self, choices):
        self._choices = choices
        self._refreshListBoxChoices()
        
    def GetChoices(self):
        return self._choices
    
#-------------------------------------------------------------------------------
#                           Internal methods
#-------------------------------------------------------------------------------

    def _refreshListBoxChoices(self):
        text = self.GetValue()

        self.dropdownlistbox.Clear()
        for choice in self._choices:
            if choice.startswith(text):
                self.dropdownlistbox.Append(choice)
        
        itemcount = min(len(self.dropdownlistbox.GetStrings()), MAX_ITEM_SHOWN)
        self.popupsize = wx.Size(self.GetSize()[0], ITEM_HEIGHT * itemcount + 4)
        self.dropdownlistbox.SetSize(self.popupsize)
        self.dropdown.SetClientSize(self.popupsize)
    
    def _moveSelection(self, direction):
        selected = self.dropdownlistbox.GetSelection()
        if selected == wx.NOT_FOUND:
            if direction >= 0:
                selected = 0
            else:
                selected = self.dropdownlistbox.GetCount() - 1
        else:
            selected = (selected + direction) % (self.dropdownlistbox.GetCount() + 1)
        if selected == self.dropdownlistbox.GetCount():
            selected = wx.NOT_FOUND
        self.dropdownlistbox.SetSelection(selected)
    
    def _setValueFromSelected(self):
         """
         Sets the wx.TextCtrl value from the selected wx.ListCtrl item.
         Will do nothing if no item is selected in the wx.ListCtrl.
         """
         selected = self.dropdownlistbox.GetStringSelection()
         if selected:
            self.SetValue(selected)
            self._showDropDown(False)


    def _showDropDown(self, show=True) :
        """
        Either display the drop down list (show = True) or hide it (show = False).
        """
        if show :
            size = self.dropdown.GetSize()
            width, height = self.GetSizeTuple()
            x, y = self.ClientToScreenXY(0, height)
            if size.GetWidth() != width :
                size.SetWidth(width)
                self.dropdown.SetSize(size)
                self.dropdownlistbox.SetSize(self.dropdown.GetClientSize())
            if (y + size.GetHeight()) < self._screenheight :
                self.dropdown.SetPosition(wx.Point(x, y))
            else:
                self.dropdown.SetPosition(wx.Point(x, y - height - size.GetHeight()))
        self.dropdown.Show(show) 

