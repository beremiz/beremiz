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

import re

import wx

RE_ESCAPED_CHARACTERS = ".*+()[]?:|{}^$<>=-,"

def EscapeText(text):
    text = text.replace('\\', '\\\\')
    for c in RE_ESCAPED_CHARACTERS:
        text = text.replace(c, '\\' + c)
    return text

#-------------------------------------------------------------------------------
#                          Search In Project Dialog
#-------------------------------------------------------------------------------

def GetElementsChoices():
    _ = lambda x: x
    return [("datatype", _("Data Type")), 
            ("function", _("Function")), 
            ("functionBlock", _("Function Block")), 
            ("program", _("Program")), 
            ("configuration", _("Configuration"))]

class SearchInProjectDialog(wx.Dialog):
    
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title=_('Search in Project'), 
              size=wx.Size(600, 350))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        pattern_sizer = wx.FlexGridSizer(cols=2, hgap=5, rows=2, vgap=5)
        pattern_sizer.AddGrowableCol(0)
        main_sizer.AddSizer(pattern_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        pattern_label = wx.StaticText(self, label=_('Pattern to search:'))
        pattern_sizer.AddWindow(pattern_label, flag=wx.ALIGN_BOTTOM)
        
        self.CaseSensitive = wx.CheckBox(self, label=_('Case sensitive'))
        pattern_sizer.AddWindow(self.CaseSensitive, flag=wx.GROW)
        
        self.Pattern = wx.TextCtrl(self)
        pattern_sizer.AddWindow(self.Pattern, flag=wx.GROW)
        
        self.RegularExpression = wx.CheckBox(self, label=_('Regular expression'))
        pattern_sizer.AddWindow(self.RegularExpression, flag=wx.GROW)
        
        scope_staticbox = wx.StaticBox(self, label=_('Scope'))
        scope_sizer = wx.StaticBoxSizer(scope_staticbox, wx.HORIZONTAL)
        main_sizer.AddSizer(scope_sizer, border=20, 
              flag=wx.GROW|wx.LEFT|wx.RIGHT)
        
        scope_selection_sizer = wx.BoxSizer(wx.VERTICAL)
        scope_sizer.AddSizer(scope_selection_sizer, 1, border=5, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.BOTTOM)
        
        self.WholeProject = wx.RadioButton(self, label=_('Whole Project'), 
              size=wx.Size(0, 24), style=wx.RB_GROUP)
        self.WholeProject.SetValue(True)
        self.Bind(wx.EVT_RADIOBUTTON, self.OnScopeChanged, self.WholeProject)
        scope_selection_sizer.AddWindow(self.WholeProject, border=5, 
              flag=wx.GROW|wx.BOTTOM)
        
        self.OnlyElements = wx.RadioButton(self, 
              label=_('Only Elements'), size=wx.Size(0, 24))
        self.Bind(wx.EVT_RADIOBUTTON, self.OnScopeChanged, self.OnlyElements)
        self.OnlyElements.SetValue(False)
        scope_selection_sizer.AddWindow(self.OnlyElements, flag=wx.GROW)
        
        self.ElementsList = wx.CheckListBox(self)
        self.ElementsList.Enable(False)
        scope_sizer.AddWindow(self.ElementsList, 1, border=5, 
              flag=wx.GROW|wx.TOP|wx.RIGHT|wx.BOTTOM)
        
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        ok_button = self.ButtonSizer.GetAffirmativeButton()
        ok_button.SetLabel(_('Search'))
        self.Bind(wx.EVT_BUTTON, self.OnOK, ok_button)
        main_sizer.AddSizer(self.ButtonSizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        for name, label in GetElementsChoices():
            self.ElementsList.Append(_(label))
        
        self.Pattern.SetFocus()

    def GetCriteria(self):
        raw_pattern = pattern = self.Pattern.GetValue()
        if not self.CaseSensitive.GetValue():
            pattern = pattern.upper()
        if not self.RegularExpression.GetValue():
            pattern = EscapeText(pattern)
        criteria = {
            "raw_pattern": raw_pattern, 
            "pattern": re.compile(pattern),
            "case_sensitive": self.CaseSensitive.GetValue(),
            "regular_expression": self.RegularExpression.GetValue(),
        }
        if self.WholeProject.GetValue():
            criteria["filter"] = "all"
        elif self.OnlyElements.GetValue():
            criteria["filter"] = []
            for index, (name, label) in enumerate(GetElementsChoices()):
                if self.ElementsList.IsChecked(index):
                    criteria["filter"].append(name)
        return criteria
    
    def OnScopeChanged(self, event):
        self.ElementsList.Enable(self.OnlyElements.GetValue())
        event.Skip()
    
    def OnOK(self, event):
        message = None
        if self.Pattern.GetValue() == "":
            message = _("Form isn't complete. Pattern to search must be filled!")
        else:
            wrong_pattern = False
            if self.RegularExpression.GetValue():
                try:
                    re.compile(self.Pattern.GetValue())
                except:
                    wrong_pattern = True
            if wrong_pattern:
                message = _("Syntax error in regular expression of pattern to search!")
        
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)
