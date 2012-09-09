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

from dialogs.DurationEditorDialog import DurationEditorDialog

class DurationCellControl(wx.PyControl):
    
    '''
    Custom cell editor control with a text box and a button that launches
    the DurationEditorDialog.
    '''
    def __init__(self, parent):
        wx.Control.__init__(self, parent)
        
        main_sizer = wx.FlexGridSizer(cols=2, hgap=0, rows=1, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        # create location text control
        self.Duration = wx.TextCtrl(self, size=wx.Size(0, -1), 
              style=wx.TE_PROCESS_ENTER)
        self.Duration.Bind(wx.EVT_KEY_DOWN, self.OnDurationChar)
        main_sizer.AddWindow(self.Duration, flag=wx.GROW)
        
        # create browse button
        self.EditButton = wx.Button(self, label='...', size=wx.Size(30, -1))
        self.Bind(wx.EVT_BUTTON, self.OnEditButtonClick, self.EditButton)
        main_sizer.AddWindow(self.EditButton, flag=wx.GROW)
        
        self.Bind(wx.EVT_SIZE, self.OnSize)
        
        self.SetSizer(main_sizer)
        
        self.Default = None
        
    def SetValue(self, value):
        self.Default = value
        self.Duration.SetValue(value)
    
    def GetValue(self):
        return self.Duration.GetValue()

    def OnSize(self, event):
        self.Layout()

    def OnEditButtonClick(self, event):
        # pop up the Duration Editor dialog
        dialog = DurationEditorDialog(self)
        dialog.SetDuration(self.Duration.GetValue())
        if dialog.ShowModal() == wx.ID_OK:
            # set the duration
            self.Duration.SetValue(dialog.GetDuration())

        dialog.Destroy()

        self.Duration.SetFocus()

    def OnDurationChar(self, event):
        keycode = event.GetKeyCode()
        if keycode in [wx.WXK_RETURN, wx.WXK_TAB]:
            self.Parent.Parent.ProcessEvent(event)
        elif keycode == wx.WXK_ESCAPE:
            self.Duration.SetValue(self.Default)
            self.Parent.Parent.CloseEditControl()
        else:
            event.Skip()

    def SetInsertionPoint(self, i):
        self.Duration.SetInsertionPoint(i)
    
    def SetFocus(self):
        self.Duration.SetFocus()

class DurationCellEditor(wx.grid.PyGridCellEditor):
    '''
    Grid cell editor that uses DurationCellControl to display an edit button.
    '''
    def __init__(self, table):
        wx.grid.PyGridCellEditor.__init__(self)
        
        self.Table = table
    
    def __del__(self):
        self.CellControl = None
    
    def Create(self, parent, id, evt_handler):
        self.CellControl = DurationCellControl(parent)
        self.SetControl(self.CellControl)
        if evt_handler:
            self.CellControl.PushEventHandler(evt_handler)

    def BeginEdit(self, row, col, grid):
        self.CellControl.Enable()
        self.CellControl.SetValue(self.Table.GetValueByName(row, 'Interval'))
        self.CellControl.SetFocus()

    def EndEdit(self, row, col, grid):
        duration = self.CellControl.GetValue()
        old_duration = self.Table.GetValueByName(row, 'Interval')
        changed = duration != old_duration
        if changed:
            self.Table.SetValueByName(row, 'Interval', duration)
        self.CellControl.Disable()
        return changed

    def SetSize(self, rect):
        self.CellControl.SetDimensions(rect.x + 1, rect.y,
                                        rect.width, rect.height,
                                        wx.SIZE_ALLOW_MINUS_ONE)

    def Clone(self):
        return DurationCellEditor(self.Table)
