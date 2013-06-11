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

from graphics.GraphicCommons import CONTACT_NORMAL, CONTACT_REVERSE, \
    CONTACT_RISING, CONTACT_FALLING, COIL_NORMAL, COIL_REVERSE, COIL_SET, \
    COIL_RESET, COIL_RISING, COIL_FALLING
from graphics.LD_Objects import LD_Contact, LD_Coil
from BlockPreviewDialog import BlockPreviewDialog

#-------------------------------------------------------------------------------
#                       Set Ladder Element Parmeters Dialog
#-------------------------------------------------------------------------------

"""
Class that implements a dialog for defining parameters of a LD contact or coil
graphic element
"""

class LDElementDialog(BlockPreviewDialog):
    
    def __init__(self, parent, controller, tagname, type):
        """
        Constructor
        @param parent: Parent wx.Window of dialog for modal
        @param controller: Reference to project controller
        @param tagname: Tagname of project POU edited
        @param type: Type of LD element ('contact or 'coil')
        """
        BlockPreviewDialog.__init__(self, parent, controller, tagname, 
              size=wx.Size(350, 260 if type == "contact" else 310),
              title=(_("Edit Contact Values")
                     if type == "contact"
                     else _("Edit Coil Values")))
        
        # Create dialog main sizer
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        # Create a sizer for dividing LD element parameters in two columns
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        # Create a sizer for left column
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, 
              rows=(7 if type == "contact" else 9), vgap=0)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        # Create label for LD element modifier
        modifier_label = wx.StaticText(self, label=_('Modifier:'))
        left_gridsizer.AddWindow(modifier_label, border=5, 
              flag=wx.GROW|wx.BOTTOM)
        
        # Create radio buttons for selecting LD element modifier
        self.ModifierRadioButtons = {}
        first = True
        element_modifiers = ([CONTACT_NORMAL, CONTACT_REVERSE, 
                              CONTACT_RISING, CONTACT_FALLING]
                             if type == "contact"
                             else [COIL_NORMAL, COIL_REVERSE, COIL_SET,
                                   COIL_RESET, COIL_RISING, COIL_FALLING])
        modifiers_label = [_("Normal"), _("Negated")] + \
                          ([_("Set"), _("Reset")] if type == "coil" else []) + \
                          [_("Rising Edge"), _("Falling Edge")]
        
        for modifier, label in zip(element_modifiers, modifiers_label):
            radio_button = wx.RadioButton(self, label=label, 
                  style=(wx.RB_GROUP if first else 0))
            radio_button.SetValue(first)
            self.Bind(wx.EVT_RADIOBUTTON, self.OnModifierChanged, radio_button)
            left_gridsizer.AddWindow(radio_button, 
                  border=(5 if not first and wx.Platform == '__WXMSW__' else 0),
                  flag=wx.GROW|wx.TOP)
            self.ModifierRadioButtons[modifier] = radio_button
            first = False
        
        # Create label for LD element variable
        element_variable_label = wx.StaticText(self, label=_('Variable:'))
        left_gridsizer.AddWindow(element_variable_label, border=5,
              flag=wx.GROW|wx.TOP)
        
        # Create a combo box for defining LD element variable
        self.ElementVariable = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnVariableChanged, 
                  self.ElementVariable)
        left_gridsizer.AddWindow(self.ElementVariable, border=5,
             flag=wx.GROW|wx.TOP)
        
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
        
        # Save LD element class
        self.ElementClass = (LD_Contact if type == "contact" else LD_Coil)
        
        # Extract list of variables defined in POU
        self.RefreshVariableList()
        
        # Set values in ElementVariable
        for name, (var_type, value_type) in self.VariableList.iteritems():
            # Only select BOOL variable and avoid input for coil
            if (type == "contact" or var_type != "Input") and \
               value_type == "BOOL":
                self.ElementVariable.Append(name)
        self.ElementVariable.Enable(self.ElementVariable.GetCount() > 0)
        
        # Normal radio button is default control having keyboard focus
        self.ModifierRadioButtons[element_modifiers[0]].SetFocus()
    
    def GetElementModifier(self):
        """
        Return modifier selected for LD element
        @return: Modifier selected (None if not found)
        """
        # Go through radio buttons and return modifier associated to the one
        # that is selected
        for modifier, control in self.ModifierRadioButtons.iteritems():
            if control.GetValue():
                return modifier
        return None

    def SetValues(self, values):
        """
        Set default LD element parameters
        @param values: Block parameters values
        """
        # For each parameters defined, set corresponding control value
        for name, value in values.items():
            
            # Parameter is LD element variable
            if name == "variable":
                self.ElementVariable.SetStringSelection(value)
            
            # Set value of other controls
            elif name == "modifier":
                self.ModifierRadioButtons[value].SetValue(True)
        
        # Refresh preview panel
        self.RefreshPreview()

    def GetValues(self):
        """
        Return LD element parameters defined in dialog
        @return: {parameter_name: parameter_value,...}
        """
        values = {
            "variable": self.ElementVariable.GetValue(),
            "modifier": self.GetElementModifier()}
        values["width"], values["height"] = self.Element.GetSize()
        return values

    def OnModifierChanged(self, event):
        """
        Called when LD element modifier changed
        @param event: wx.RadioButtonEvent
        """
        self.RefreshPreview()
        event.Skip()

    def OnVariableChanged(self, event):
        """
        Called when LD element associated variable changed
        @param event: wx.ComboBoxEvent
        """
        self.RefreshPreview()
        event.Skip()

    def RefreshPreview(self):
        """
        Refresh preview panel of graphic element
        Override BlockPreviewDialog function
        """
        # Set graphic element displayed, creating a LD element
        self.Element = self.ElementClass(
                self.Preview, 
                self.GetElementModifier(),
                self.ElementVariable.GetStringSelection())
        
        # Call BlockPreviewDialog function
        BlockPreviewDialog.RefreshPreview(self)
