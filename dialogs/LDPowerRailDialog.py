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

from graphics.GraphicCommons import LEFTRAIL, RIGHTRAIL, LD_LINE_SIZE
from graphics.LD_Objects import LD_PowerRail
from BlockPreviewDialog import BlockPreviewDialog

#-------------------------------------------------------------------------------
#                    Set Ladder Power Rail Parameters Dialog
#-------------------------------------------------------------------------------

"""
Class that implements a dialog for defining parameters of a power rail graphic
element
"""

class LDPowerRailDialog(BlockPreviewDialog):
    
    def __init__(self, parent, controller, tagname):
        """
        Constructor
        @param parent: Parent wx.Window of dialog for modal
        @param controller: Reference to project controller
        @param tagname: Tagname of project POU edited
        """
        BlockPreviewDialog.__init__(self, parent, controller, tagname,
              size=wx.Size(350, 260), title=_('Power Rail Properties'))
        
        # Create dialog main sizer
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        # Create a sizer for dividing power rail parameters in two columns
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        # Create a sizer for left column
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=5, vgap=5)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        # Create label for connection type
        type_label = wx.StaticText(self, label=_('Type:'))
        left_gridsizer.AddWindow(type_label, flag=wx.GROW)
        
        # Create radio buttons for selecting power rail type
        self.TypeRadioButtons = {}
        first = True
        for type, label in [(LEFTRAIL, _('Left PowerRail')),
                            (RIGHTRAIL, _('Right PowerRail'))]:
            radio_button = wx.RadioButton(self, label=label, 
                  style=(wx.RB_GROUP if first else 0))
            radio_button.SetValue(first)
            self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, radio_button)
            left_gridsizer.AddWindow(radio_button, flag=wx.GROW)
            self.TypeRadioButtons[type] = radio_button
            first = False
        
        # Create label for power rail pin number
        pin_number_label = wx.StaticText(self, label=_('Pin number:'))
        left_gridsizer.AddWindow(pin_number_label, flag=wx.GROW)
        
        # Create spin control for defining power rail pin number
        self.PinNumber = wx.SpinCtrl(self, min=1, max=50,
              style=wx.SP_ARROW_KEYS)
        self.Bind(wx.EVT_SPINCTRL, self.OnPinNumberChanged, self.PinNumber)
        left_gridsizer.AddWindow(self.PinNumber, flag=wx.GROW)
        
        # Create a sizer for right column
        right_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        right_gridsizer.AddGrowableCol(0)
        right_gridsizer.AddGrowableRow(1)
        column_sizer.AddSizer(right_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.LEFT)
        
        # Add preview panel and associated label to sizers
        right_gridsizer.AddWindow(self.PreviewLabel, flag=wx.GROW)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        # Add buttons sizer to sizers
        main_sizer.AddSizer(self.ButtonSizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        # Left Power Rail radio button is default control having keyboard focus
        self.TypeRadioButtons[LEFTRAIL].SetFocus()
    
    def GetMinElementSize(self):
        """
        Get minimal graphic element size
        @return: Tuple containing minimal size (width, height) or None if no
        element defined
        May be overridden by inherited classes
        """
        return (2, LD_LINE_SIZE * self.PinNumber.GetValue())
    
    def GetPowerRailType(self):
        """
        Return type selected for power rail
        @return: Type selected (LEFTRAIL or RIGHTRAIL)
        """
        return (LEFTRAIL
                if self.TypeRadioButtons[LEFTRAIL].GetValue()
                else RIGHTRAIL)
    
    def SetValues(self, values):
        """
        Set default power rail parameters
        @param values: Power rail parameters values
        """
        # For each parameters defined, set corresponding control value
        for name, value in values.items():
            
            # Parameter is power rail type
            if name == "type":
                self.TypeRadioButtons[value].SetValue(True)
            
            # Parameter is power rail pin number
            elif name == "pin_number":
                self.PinNumber.SetValue(value)

    def GetValues(self):
        """
        Return power rail parameters defined in dialog
        @return: {parameter_name: parameter_value,...}
        """
        values = {
            "type": self.GetPowerRailType(),
            "pin_number": self.PinNumber.GetValue()}
        values["width"], values["height"] = self.Element.GetSize()
        return values

    def OnTypeChanged(self, event):
        """
        Called when power rail type changed
        @param event: wx.RadioButtonEvent
        """
        self.RefreshPreview()
        event.Skip()

    def OnPinNumberChanged(self, event):
        """
        Called when power rail pin number value changed
        @param event: wx.SpinEvent
        """
        self.RefreshPreview()
        event.Skip()

    def RefreshPreview(self):
        """
        Refresh preview panel of graphic element
        Override BlockPreviewDialog function
        """
        
        # Set graphic element displayed, creating a power rail element
        self.Element = LD_PowerRail(self.Preview, 
                self.GetPowerRailType(), 
                connectors = self.PinNumber.GetValue())
        
        # Call BlockPreviewDialog function
        BlockPreviewDialog.RefreshPreview(self)
