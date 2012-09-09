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

from dialogs.BrowseLocationsDialog import BrowseLocationsDialog

class LocationCellControl(wx.PyControl):
    
    '''
    Custom cell editor control with a text box and a button that launches
    the BrowseLocationsDialog.
    '''
    def __init__(self, parent):
        wx.Control.__init__(self, parent)
        
        main_sizer = wx.FlexGridSizer(cols=2, hgap=0, rows=1, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        # create location text control
        self.Location = wx.TextCtrl(self, size=wx.Size(0, -1), 
              style=wx.TE_PROCESS_ENTER)
        self.Location.Bind(wx.EVT_KEY_DOWN, self.OnLocationChar)
        main_sizer.AddWindow(self.Location, flag=wx.GROW)
        
        # create browse button
        self.BrowseButton = wx.Button(self, label='...', size=wx.Size(30, -1))
        self.BrowseButton.Bind(wx.EVT_BUTTON, self.OnBrowseButtonClick)
        main_sizer.AddWindow(self.BrowseButton, flag=wx.GROW)
        
        self.Bind(wx.EVT_SIZE, self.OnSize)
        
        self.SetSizer(main_sizer)

        self.Locations = None
        self.VarType = None
        self.Default = False

    def SetLocations(self, locations):
        self.Locations = locations

    def SetVarType(self, vartype):
        self.VarType = vartype

    def SetValue(self, value):
        self.Default = value
        self.Location.SetValue(value)
    
    def GetValue(self):
        return self.Location.GetValue()

    def OnSize(self, event):
        self.Layout()

    def OnBrowseButtonClick(self, event):
        # pop up the location browser dialog
        dialog = BrowseLocationsDialog(self, self.VarType, self.Locations)
        if dialog.ShowModal() == wx.ID_OK:
            infos = dialog.GetValues()

            # set the location
            self.Location.SetValue(infos["location"])

        dialog.Destroy()

        self.Location.SetFocus()

    def OnLocationChar(self, event):
        keycode = event.GetKeyCode()
        if keycode in [wx.WXK_RETURN, wx.WXK_TAB]:
            self.Parent.Parent.ProcessEvent(event)
        elif keycode == wx.WXK_ESCAPE:
            self.Location.SetValue(self.Default)
            self.Parent.Parent.CloseEditControl()
        else:
            event.Skip()

    def SetInsertionPoint(self, i):
        self.Location.SetInsertionPoint(i)
    
    def SetFocus(self):
        self.Location.SetFocus()

class LocationCellEditor(wx.grid.PyGridCellEditor):
    '''
    Grid cell editor that uses LocationCellControl to display a browse button.
    '''
    def __init__(self, table, controller):
        wx.grid.PyGridCellEditor.__init__(self)
        
        self.Table = table
        self.Controller = controller

    def __del__(self):
        self.CellControl = None
    
    def Create(self, parent, id, evt_handler):
        self.CellControl = LocationCellControl(parent)
        self.SetControl(self.CellControl)
        if evt_handler:
            self.CellControl.PushEventHandler(evt_handler)

    def BeginEdit(self, row, col, grid):
        self.CellControl.Enable()
        self.CellControl.SetLocations(self.Controller.GetVariableLocationTree())
        self.CellControl.SetValue(self.Table.GetValueByName(row, 'Location'))
        if isinstance(self.CellControl, LocationCellControl):
            self.CellControl.SetVarType(self.Controller.GetBaseType(self.Table.GetValueByName(row, 'Type')))
        self.CellControl.SetFocus()

    def EndEdit(self, row, col, grid):
        loc = self.CellControl.GetValue()
        old_loc = self.Table.GetValueByName(row, 'Location')
        changed = loc != old_loc
        if changed:
            self.Table.SetValueByName(row, 'Location', loc)
        self.CellControl.Disable()
        return changed
    
    def SetSize(self, rect):
        self.CellControl.SetDimensions(rect.x + 1, rect.y,
                                        rect.width, rect.height,
                                        wx.SIZE_ALLOW_MINUS_ONE)

    def Clone(self):
        return LocationCellEditor(self.Table, self.Controller)

