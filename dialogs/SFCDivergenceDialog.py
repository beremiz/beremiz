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

from graphics import *

#-------------------------------------------------------------------------------
#                         Create New Divergence Dialog
#-------------------------------------------------------------------------------

class SFCDivergenceDialog(wx.Dialog):
    
    def __init__(self, parent, controller):
        wx.Dialog.__init__(self, parent, size=wx.Size(500, 300), 
              title=_('Create a new divergence or convergence'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        column_sizer = wx.BoxSizer(wx.HORIZONTAL)
        main_sizer.AddSizer(column_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        left_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=7, vgap=5)
        left_gridsizer.AddGrowableCol(0)
        column_sizer.AddSizer(left_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.RIGHT)
        
        type_label = wx.StaticText(self, label=_('Type:'))
        left_gridsizer.AddWindow(type_label, flag=wx.GROW)

        self.SelectionDivergence = wx.RadioButton(self, 
              label=_('Selection Divergence'), style=wx.RB_GROUP)
        self.SelectionDivergence.SetValue(True)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, 
                  self.SelectionDivergence)
        left_gridsizer.AddWindow(self.SelectionDivergence, flag=wx.GROW)
        
        self.SelectionConvergence = wx.RadioButton(self,
              label=_('Selection Convergence'))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, 
                  self.SelectionConvergence)
        left_gridsizer.AddWindow(self.SelectionConvergence, flag=wx.GROW)
        
        self.SimultaneousDivergence = wx.RadioButton(self,
              label=_('Simultaneous Divergence'))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, 
                  self.SimultaneousDivergence)
        left_gridsizer.AddWindow(self.SimultaneousDivergence, flag=wx.GROW)
        
        self.SimultaneousConvergence = wx.RadioButton(self,
              label=_('Simultaneous Convergence'))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnTypeChanged, 
                  self.SimultaneousConvergence)
        left_gridsizer.AddWindow(self.SimultaneousConvergence, flag=wx.GROW)
        
        sequences_label = wx.StaticText(self, 
              label=_('Number of sequences:'))
        left_gridsizer.AddWindow(sequences_label, flag=wx.GROW)
        
        self.Sequences = wx.SpinCtrl(self, min=2, max=20)
        self.Bind(wx.EVT_SPINCTRL, self.OnSequencesChanged, self.Sequences)
        left_gridsizer.AddWindow(self.Sequences, flag=wx.GROW)
        
        right_gridsizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        right_gridsizer.AddGrowableCol(0)
        right_gridsizer.AddGrowableRow(1)
        column_sizer.AddSizer(right_gridsizer, 1, border=5, 
              flag=wx.GROW|wx.LEFT)
        
        preview_label = wx.StaticText(self, label=_('Preview:'))
        right_gridsizer.AddWindow(preview_label, flag=wx.GROW)
        
        self.Preview = wx.Panel(self, style=wx.TAB_TRAVERSAL|wx.SIMPLE_BORDER)
        self.Preview.SetBackgroundColour(wx.Colour(255,255,255))
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        setattr(self.Preview, "GetDrawingMode", lambda:FREEDRAWING_MODE)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        right_gridsizer.AddWindow(self.Preview, flag=wx.GROW)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        main_sizer.AddSizer(button_sizer, border=20, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.Divergence = None
        self.MinSize = (0, 0)
        
        self.SelectionDivergence.SetFocus()
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def GetValues(self):
        values = {}
        if self.SelectionDivergence.GetValue():
            values["type"] = SELECTION_DIVERGENCE
        elif self.SelectionConvergence.GetValue():
            values["type"] = SELECTION_CONVERGENCE
        elif self.SimultaneousDivergence.GetValue():
            values["type"] = SIMULTANEOUS_DIVERGENCE
        else:
            values["type"] = SIMULTANEOUS_CONVERGENCE
        values["number"] = self.Sequences.GetValue()
        return values

    def SetMinSize(self, size):
        self.MinSize = size

    def OnTypeChanged(self, event):
        self.RefreshPreview()
        event.Skip()

    def OnSequencesChanged(self, event):
        self.RefreshPreview()
        event.Skip()
        
    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        if self.SelectionDivergence.GetValue():
            self.Divergence = SFC_Divergence(self.Preview, SELECTION_DIVERGENCE, self.Sequences.GetValue())
        elif self.SelectionConvergence.GetValue():
            self.Divergence = SFC_Divergence(self.Preview, SELECTION_CONVERGENCE, self.Sequences.GetValue())
        elif self.SimultaneousDivergence.GetValue():
            self.Divergence = SFC_Divergence(self.Preview, SIMULTANEOUS_DIVERGENCE, self.Sequences.GetValue())
        else:
            self.Divergence = SFC_Divergence(self.Preview, SIMULTANEOUS_CONVERGENCE, self.Sequences.GetValue())
        width, height = self.Divergence.GetSize()
        min_width, min_height = max(width, self.MinSize[0]), max(height, self.MinSize[1])
        self.Divergence.SetSize(min_width, min_height)
        clientsize = self.Preview.GetClientSize()
        x = (clientsize.width - min_width) / 2
        y = (clientsize.height - min_height) / 2
        self.Divergence.SetPosition(x, y)
        self.Divergence.Draw(dc)

    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
