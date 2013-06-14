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

from graphics.GraphicCommons import SELECTION_DIVERGENCE, \
    SELECTION_CONVERGENCE, SIMULTANEOUS_DIVERGENCE, SIMULTANEOUS_CONVERGENCE
from graphics.SFC_Objects import SFC_Divergence
from BlockPreviewDialog import BlockPreviewDialog

#-------------------------------------------------------------------------------
#                         Create New Divergence Dialog
#-------------------------------------------------------------------------------

"""
Class that implements a dialog for defining parameters for creating a new
divergence graphic element
"""

class SFCDivergenceDialog(BlockPreviewDialog):
    
    def __init__(self, parent, controller, tagname):
        """
        Constructor
        @param parent: Parent wx.Window of dialog for modal
        @param controller: Reference to project controller
        @param tagname: Tagname of project POU edited
        """
        BlockPreviewDialog.__init__(self, parent, controller, tagname, 
              size=wx.Size(500, 300), 
              title=_('Create a new divergence or convergence'))
        
        # Init common sizers
        self._init_sizers(2, 0, 7, None, 2, 1)
        
        # Create label for divergence type
        type_label = wx.StaticText(self, label=_('Type:'))
        self.LeftGridSizer.AddWindow(type_label, flag=wx.GROW)
        
        # Create radio buttons for selecting divergence type
        self.TypeRadioButtons = {}
        first = True
        for type, label in [
                (SELECTION_DIVERGENCE, _('Selection Divergence')),
                (SELECTION_CONVERGENCE, _('Selection Convergence')),
                (SIMULTANEOUS_DIVERGENCE, _('Simultaneous Divergence')),
                (SIMULTANEOUS_CONVERGENCE, _('Simultaneous Convergence'))]:
            radio_button = wx.RadioButton(self, label=label, 
                  style=(wx.RB_GROUP if first else 0))
            radio_button.SetValue(first)
            self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, radio_button)
            self.LeftGridSizer.AddWindow(radio_button, flag=wx.GROW)
            self.TypeRadioButtons[type] = radio_button
            first = False

        # Create label for number of divergence sequences
        sequences_label = wx.StaticText(self, 
              label=_('Number of sequences:'))
        self.LeftGridSizer.AddWindow(sequences_label, flag=wx.GROW)
        
        # Create spin control for defining number of divergence sequences
        self.Sequences = wx.SpinCtrl(self, min=2, max=20)
        self.Bind(wx.EVT_SPINCTRL, self.OnSequencesChanged, self.Sequences)
        self.LeftGridSizer.AddWindow(self.Sequences, flag=wx.GROW)
        
        # Add preview panel and associated label to sizers
        self.RightGridSizer.AddWindow(self.PreviewLabel, flag=wx.GROW)
        self.RightGridSizer.AddWindow(self.Preview, flag=wx.GROW)
        
        # Add buttons sizer to sizers
        self.MainSizer.AddSizer(self.ButtonSizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        # Selection divergence radio button is default control having keyboard
        # focus
        self.TypeRadioButtons[SELECTION_DIVERGENCE].SetFocus()
    
    def GetMinElementSize(self):
        """
        Get minimal graphic element size
        @return: Tuple containing minimal size (width, height) or None if no
        element defined
        """
        return self.Element.GetMinSize(True)
    
    def GetDivergenceType(self):
        """
        Return type selected for SFC divergence
        @return: Type selected (None if not found)
        """
        # Go through radio buttons and return type associated to the one that
        # is selected
        for type, control in self.TypeRadioButtons.iteritems():
            if control.GetValue():
                return type
        return None
    
    def GetValues(self):
        """
        Set default SFC divergence parameters
        @param values: Divergence parameters values
        """
        return {"type": self.GetDivergenceType(),
                "number": self.Sequences.GetValue()}

    def OnTypeChanged(self, event):
        """
        Called when SFC divergence type changed
        @param event: wx.RadioButtonEvent
        """
        self.RefreshPreview()
        event.Skip()

    def OnSequencesChanged(self, event):
        """
        Called when SFC divergence number of sequences changed
        @param event: wx.SpinEvent
        """
        self.RefreshPreview()
        event.Skip()
        
    def RefreshPreview(self):
        """
        Refresh preview panel of graphic element
        Override BlockPreviewDialog function
        """
        # Set graphic element displayed, creating a SFC divergence
        self.Element = SFC_Divergence(self.Preview, 
                                      self.GetDivergenceType(), 
                                      self.Sequences.GetValue())
        
        # Call BlockPreviewDialog function
        BlockPreviewDialog.RefreshPreview(self)
        