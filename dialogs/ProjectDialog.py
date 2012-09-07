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

import wx

from controls.ProjectPropertiesPanel import ProjectPropertiesPanel

class ProjectDialog(wx.Dialog):
    
    def __init__(self, parent, enable_required=True):
        wx.Dialog.__init__(self, parent, title=_('Project properties'), 
              size=wx.Size(500, 350), style=wx.DEFAULT_DIALOG_STYLE)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        self.ProjectProperties = ProjectPropertiesPanel(self, 
              enable_required=enable_required)
        main_sizer.AddWindow(self.ProjectProperties, flag=wx.GROW)
        
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
                  self.ButtonSizer.GetAffirmativeButton())
        main_sizer.AddSizer(self.ButtonSizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
    def OnOK(self, event):
        values = self.ProjectProperties.GetValues()
        error = []
        for param, name in [("projectName", "Project Name"),
                            ("productName", "Product Name"),
                            ("productVersion", "Product Version"),
                            ("companyName", "Company Name")]:
            if values[param] == "":
                error.append(name)
        if len(error) > 0:
            text = ""
            for i, item in enumerate(error):
                if i == 0:
                    text += item
                elif i == len(error) - 1:
                    text += " and %s"%item
                else:
                    text += ", %s"%item
            dialog = wx.MessageDialog(self, 
                _("Form isn't complete. %s must be filled!") % text, 
                _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)

    def SetValues(self, values):
        self.ProjectProperties.SetValues(values)
        
    def GetValues(self):
        return self.ProjectProperties.GetValues()
