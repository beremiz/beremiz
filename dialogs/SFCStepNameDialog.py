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

#-------------------------------------------------------------------------------
#                          Edit Step Name Dialog
#-------------------------------------------------------------------------------

class SFCStepNameDialog(wx.TextEntryDialog):

    def __init__(self, parent, message, caption = "Please enter text", defaultValue = "", 
                       style = wx.OK|wx.CANCEL|wx.CENTRE, pos = wx.DefaultPosition):
        wx.TextEntryDialog.__init__(self, parent, message, caption, defaultValue, style, pos)
        
        self.PouNames = []
        self.Variables = []
        self.StepNames = []
        
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
              self.GetSizer().GetItem(2).GetSizer().GetItem(1).GetSizer().GetAffirmativeButton())
        
    def OnOK(self, event):
        message = None
        step_name = self.GetSizer().GetItem(1).GetWindow().GetValue()
        if step_name == "":
            message = _("You must type a name!")
        elif not TestIdentifier(step_name):
            message = _("\"%s\" is not a valid identifier!") % step_name
        elif step_name.upper() in IEC_KEYWORDS:
            message = _("\"%s\" is a keyword. It can't be used!") % step_name
        elif step_name.upper() in self.PouNames:
            message = _("A POU named \"%s\" already exists!") % step_name
        elif step_name.upper() in self.Variables:
            message = _("A variable with \"%s\" as name already exists in this pou!") % step_name
        elif step_name.upper() in self.StepNames:
            message = _("\"%s\" step already exists!") % step_name
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)
        event.Skip()

    def SetPouNames(self, pou_names):
        self.PouNames = [pou_name.upper() for pou_name in pou_names]

    def SetVariables(self, variables):
        self.Variables = [var.Name.upper() for var in variables]

    def SetStepNames(self, step_names):
        self.StepNames = [step_name.upper() for step_name in step_names]
