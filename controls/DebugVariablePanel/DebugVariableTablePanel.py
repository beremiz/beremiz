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

from types import TupleType

import wx
import wx.lib.buttons

from editors.DebugViewer import DebugViewer
from controls import CustomGrid, CustomTable
from dialogs.ForceVariableDialog import ForceVariableDialog
from util.BitmapLibrary import GetBitmap

from DebugVariableItem import DebugVariableItem

def GetDebugVariablesTableColnames():
    """
    Function returning table column header labels
    @return: List of labels [col_label,...]
    """
    _ = lambda x : x
    return [_("Variable"), _("Value")]

#-------------------------------------------------------------------------------
#                        Debug Variable Table Panel
#-------------------------------------------------------------------------------

"""
Class that implements a custom table storing value to display in Debug Variable
Table Panel grid
"""

class DebugVariableTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            return self.GetValueByName(row, self.GetColLabelValue(col, False))
        return ""
    
    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            self.SetValueByName(row, self.GetColLabelValue(col, False), value)
            
    def GetValueByName(self, row, colname):
        if row < self.GetNumberRows():
            if colname == "Variable":
                return self.data[row].GetVariable()
            elif colname == "Value":
                return self.data[row].GetValue()
        return ""

    def SetValueByName(self, row, colname, value):
        if row < self.GetNumberRows():
            if colname == "Variable":
                self.data[row].SetVariable(value)
            elif colname == "Value":
                self.data[row].SetValue(value)
    
    def IsForced(self, row):
        if row < self.GetNumberRows():
            return self.data[row].IsForced()
        return False
    
    def _updateColAttrs(self, grid):
        """
        wx.grid.Grid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                colname = self.GetColLabelValue(col, False)
                if colname == "Value":
                    if self.IsForced(row):
                        grid.SetCellTextColour(row, col, wx.BLUE)
                    else:
                        grid.SetCellTextColour(row, col, wx.BLACK)
                grid.SetReadOnly(row, col, True)
            self.ResizeRow(grid, row)
    
    def RefreshValues(self, grid):
        for col in xrange(self.GetNumberCols()):
            colname = self.GetColLabelValue(col, False)
            if colname == "Value":
                for row in xrange(self.GetNumberRows()):
                    grid.SetCellValue(row, col, str(self.data[row].GetValue()))
                    if self.IsForced(row):
                        grid.SetCellTextColour(row, col, wx.BLUE)
                    else:
                        grid.SetCellTextColour(row, col, wx.BLACK)
      
    def AppendItem(self, item):
        self.data.append(item)
    
    def InsertItem(self, idx, item):
        self.data.insert(idx, item)
    
    def RemoveItem(self, item):
        self.data.remove(item)
    
    def MoveItem(self, idx, new_idx):
        self.data.insert(new_idx, self.data.pop(idx))
        
    def GetItem(self, idx):
        return self.data[idx]


#-------------------------------------------------------------------------------
#                  Debug Variable Table Panel Drop Target
#-------------------------------------------------------------------------------

"""
Class that implements a custom drop target class for Debug Variable Table Panel
"""

class DebugVariableTableDropTarget(wx.TextDropTarget):
    
    def __init__(self, parent):
        """
        Constructor
        @param window: Reference to the Debug Variable Panel
        """
        wx.TextDropTarget.__init__(self)
        self.ParentWindow = parent
        
    def __del__(self):
        """
        Destructor
        """
        # Remove reference to Debug Variable Panel
        self.ParentWindow = None
        
    def OnDropText(self, x, y, data):
        """
        Function called when mouse is dragged over Drop Target
        @param x: X coordinate of mouse pointer
        @param y: Y coordinate of mouse pointer
        @param data: Text associated to drag'n drop
        """
        message = None
        try:
            values = eval(data)
            if not isinstance(values, TupleType):
                raise ValueError
        except:
            message = _("Invalid value \"%s\" for debug variable") % data
            values = None
        
        if message is not None:
            wx.CallAfter(self.ShowMessage, message)
        
        elif values[1] == "debug":
            grid = self.ParentWindow.VariablesGrid
            
            # Get row where variable was dropped
            x, y = grid.CalcUnscrolledPosition(x, y)
            row = grid.YToRow(y - grid.GetColLabelSize())
            
            # If no row found add variable at table end
            if row == wx.NOT_FOUND:
                row = self.ParentWindow.Table.GetNumberRows()
            
            # Add variable to table
            self.ParentWindow.InsertValue(values[0], row, force=True)
            
    def ShowMessage(self, message):
        """
        Show error message in Error Dialog
        @param message: Error message to display
        """
        dialog = wx.MessageDialog(self.ParentWindow, 
                                  message, 
                                  _("Error"), 
                                  wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()


#-------------------------------------------------------------------------------
#                       Debug Variable Table Panel
#-------------------------------------------------------------------------------

"""
Class that implements a panel displaying debug variable values in a table
"""

class DebugVariableTablePanel(wx.Panel, DebugViewer):
    
    def __init__(self, parent, producer, window):
        """
        Constructor
        @param parent: Reference to the parent wx.Window
        @param producer: Object receiving debug value and dispatching them to
        consumers
        @param window: Reference to Beremiz frame
        """
        wx.Panel.__init__(self, parent, style=wx.SP_3D|wx.TAB_TRAVERSAL)
        
        # Save Reference to Beremiz frame
        self.ParentWindow = window
        
        # Variable storing flag indicating that variable displayed in table
        # received new value and then table need to be refreshed
        self.HasNewData = False
        
        DebugViewer.__init__(self, producer, True)
        
        # Construction of window layout by creating controls and sizers
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(button_sizer, border=5, 
              flag=wx.ALIGN_RIGHT|wx.ALL)
        
        # Creation of buttons for navigating in table
        
        for name, bitmap, help in [
                ("DeleteButton", "remove_element", _("Remove debug variable")),
                ("UpButton", "up", _("Move debug variable up")),
                ("DownButton", "down", _("Move debug variable down"))]:
            button = wx.lib.buttons.GenBitmapButton(self, 
                  bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            button_sizer.AddWindow(button, border=5, flag=wx.LEFT)
        
        # Creation of grid and associated table
        
        self.VariablesGrid = CustomGrid(self, 
                size=wx.Size(-1, 150), style=wx.VSCROLL)
        # Define grid drop target
        self.VariablesGrid.SetDropTarget(DebugVariableTableDropTarget(self))
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, 
              self.OnVariablesGridCellRightClick)
        self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, 
              self.OnVariablesGridCellLeftClick)
        main_sizer.AddWindow(self.VariablesGrid, flag=wx.GROW)
    
        self.Table = DebugVariableTable(self, [], 
                GetDebugVariablesTableColnames())
        self.VariablesGrid.SetTable(self.Table)
        self.VariablesGrid.SetButtons({"Delete": self.DeleteButton,
                                       "Up": self.UpButton,
                                       "Down": self.DownButton})
        
        # Definition of function associated to navigation buttons
        
        def _AddVariable(new_row):
            return self.VariablesGrid.GetGridCursorRow()
        setattr(self.VariablesGrid, "_AddRow", _AddVariable)
    
        def _DeleteVariable(row):
            item = self.Table.GetItem(row)
            self.RemoveDataConsumer(item)
            self.Table.RemoveItem(item)
            self.RefreshView()
        setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
        
        def _MoveVariable(row, move):
            new_row = max(0, min(row + move, self.Table.GetNumberRows() - 1))
            if new_row != row:
                self.Table.MoveItem(row, new_row)
                self.RefreshView()
            return new_row
        setattr(self.VariablesGrid, "_MoveRow", _MoveVariable)
        
        # Initialization of grid layout
        
        self.VariablesGrid.SetRowLabelSize(0)
        
        self.GridColSizes = [200, 100]
        
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(wx.ALIGN_RIGHT, wx.ALIGN_CENTER)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColSize(col, self.GridColSizes[col])
        
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        
        self.SetSizer(main_sizer)
    
    def RefreshNewData(self, *args, **kwargs):
        """
        Called to refresh Table according to values received by variables
        Can receive any parameters (not used here)
        """
        # Refresh 'Value' column of table if new data have been received since
        # last refresh
        if self.HasNewData:
            self.HasNewData = False
            self.RefreshView(only_values=True)
        DebugViewer.RefreshNewData(self, *args, **kwargs)
    
    def RefreshView(self, only_values=False):
        """
        Function refreshing table layout and values
        @param only_values: True if only 'Value' column need to be updated
        """
        # Block refresh until table layout and values are completely updated
        self.Freeze()
        
        # Update only 'value' column from table 
        if only_values:
            self.Table.RefreshValues(self.VariablesGrid)
        
        # Update complete table layout refreshing table navigation buttons
        # state according to 
        else:
            self.Table.ResetView(self.VariablesGrid)
            self.VariablesGrid.RefreshButtons()
        
        self.Thaw()
        
    def ResetView(self):
        """
        Function removing all variables denugged from table
        @param only_values: True if only 'Value' column need to be updated
        """
        # Unsubscribe all variables debugged
        self.UnsubscribeAllDataConsumers()
        
        # Clear table content
        self.Table.Empty()
        
        # Update table layout
        self.Freeze()
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        self.Thaw()
    
    def SubscribeAllDataConsumers(self):
        """
        Function refreshing table layout and values
        @param only_values: True if only 'Value' column need to be updated
        """
        DebugViewer.SubscribeAllDataConsumers(self)
        
        # Navigate through variable displayed in table, removing those that
        # doesn't exist anymore in PLC
        for item in self.Table.GetData()[:]:
            iec_path = item.GetVariable()
            if self.GetDataType(iec_path) is None:
                self.RemoveDataConsumer(item)
                self.Table.RemoveItem(idx)
            else:
                self.AddDataConsumer(iec_path.upper(), item)
                item.RefreshVariableType()
        
        # Update table layout
        self.Freeze()
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
        self.Thaw()
    
    def GetForceVariableMenuFunction(self, item):
        """
        Function returning callback function for contextual menu 'Force' item
        @param item: Debug Variable item where contextual menu was opened 
        @return: Callback function
        """
        def ForceVariableFunction(event):
            # Get variable path and data type
            iec_path = item.GetVariable()
            iec_type = self.GetDataType(iec_path)
            
            # Return immediately if not data type found
            if iec_type is None:
                return
            
            # Open dialog for entering value to force variable
            dialog = ForceVariableDialog(self, iec_type, str(item.GetValue()))
            
            # If valid value entered, force variable
            if dialog.ShowModal() == wx.ID_OK:
                self.ForceDataValue(iec_path.upper(), dialog.GetValue())
        
        return ForceVariableFunction

    def GetReleaseVariableMenuFunction(self, iec_path):
        """
        Function returning callback function for contextual menu 'Release' item
        @param iec_path: Debug Variable path where contextual menu was opened
        @return: Callback function
        """
        def ReleaseVariableFunction(event):
            # Release variable
            self.ReleaseDataValue(iec_path)
        return ReleaseVariableFunction
    
    def OnVariablesGridCellLeftClick(self, event):
        """
        Called when left mouse button is pressed on a table cell
        @param event: wx.grid.GridEvent
        """
        # Initiate a drag and drop if the cell clicked was in 'Variable' column
        if self.Table.GetColLabelValue(event.GetCol(), False) == "Variable":
            item = self.Table.GetItem(event.GetRow())
            data = wx.TextDataObject(str((item.GetVariable(), "debug")))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        
        event.Skip()
    
    def OnVariablesGridCellRightClick(self, event):
        """
        Called when right mouse button is pressed on a table cell
        @param event: wx.grid.GridEvent
        """
        # Open a contextual menu if the cell clicked was in 'Value' column
        if self.Table.GetColLabelValue(event.GetCol(), False) == "Value":
            row = event.GetRow()
            
            # Get variable path
            item = self.Table.GetItem(row)
            iec_path = item.GetVariable().upper()
            
            # Create contextual menu
            menu = wx.Menu(title='')
            
            # Add menu items
            for text, enable, callback in [
                (_("Force value"), True,
                 self.GetForceVariableMenuFunction(item)),
                # Release menu item is enabled only if variable is forced 
                (_("Release value"), self.Table.IsForced(row),
                 self.GetReleaseVariableMenuFunction(iec_path))]:
                
                new_id = wx.NewId()
                menu.Append(help='', id=new_id, kind=wx.ITEM_NORMAL, text=text)
                menu.Enable(new_id, enable)
                self.Bind(wx.EVT_MENU, callback, id=new_id)
            
            # Popup contextual menu
            self.PopupMenu(menu)
            
            menu.Destroy()
        event.Skip()
    
    def InsertValue(self, iec_path, index=None, force=False):
        """
        Insert a new variable to debug in table
        @param iec_path: Variable path to debug
        @param index: Row where insert the variable in table (default None,
        insert at last position)
        @param force: Force insertion of variable even if not defined in
        producer side
        """
        # Return immediately if variable is already debugged
        for item in self.Table.GetData():
            if iec_path == item.GetVariable():
                return
            
        # Insert at last position if index not defined
        if index is None:
            index = self.Table.GetNumberRows()
        
        # Subscribe variable to producer
        item = DebugVariableItem(self, iec_path)
        result = self.AddDataConsumer(iec_path.upper(), item)
        
        # Insert variable in table if subscription done or insertion forced
        if result is not None or force:
            self.Table.InsertItem(index, item)
            self.RefreshView()
    
    def ResetGraphicsValues(self):
        """
        Called to reset graphics values when PLC is started
        (Nothing to do because no graphic values here. Defined for
        compatibility with Debug Variable Graphic Panel)
        """
        pass
    