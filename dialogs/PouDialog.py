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

from plcopen.structures import TestIdentifier, IEC_KEYWORDS

def GetPouTypes():
    _ = lambda x : x
    return [_("function"), _("functionBlock"), _("program")]
POU_TYPES_DICT = dict([(_(pou_type), pou_type) for pou_type in GetPouTypes()])

def GetPouLanguages():
    _ = lambda x : x
    return [_("IL"), _("ST"), _("LD"), _("FBD"), _("SFC")]
POU_LANGUAGES_DICT = dict([(_(language), language) for language in GetPouLanguages()])

class PouDialog(wx.Dialog):
    
    def __init__(self, parent, pou_type = None):
        wx.Dialog.__init__(self, id=-1, parent=parent,
              name='PouDialog', title=_('Create a new POU'), 
              size=wx.Size(300, 200), style=wx.DEFAULT_DIALOG_STYLE)
        self.SetClientSize(wx.Size(300, 200))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        infos_sizer = wx.FlexGridSizer(cols=2, hgap=5, rows=3, vgap=15)
        infos_sizer.AddGrowableCol(1)
        main_sizer.AddSizer(infos_sizer, border=20, 
              flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        pouname_label = wx.StaticText(self, label=_('POU Name:'))
        infos_sizer.AddWindow(pouname_label, border=4, 
              flag=wx.ALIGN_CENTER_VERTICAL|wx.TOP)
        
        self.PouName = wx.TextCtrl(self)
        infos_sizer.AddWindow(self.PouName, flag=wx.GROW)
        
        poutype_label = wx.StaticText(self, label=_('POU Type:'))
        infos_sizer.AddWindow(poutype_label, border=4, 
              flag=wx.ALIGN_CENTER_VERTICAL|wx.TOP)
        
        self.PouType = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnTypeChanged, self.PouType)
        infos_sizer.AddWindow(self.PouType, flag=wx.GROW)
        
        language_label = wx.StaticText(self, label=_('Language:'))
        infos_sizer.AddWindow(language_label, border=4, 
              flag=wx.ALIGN_CENTER_VERTICAL|wx.TOP)
        
        self.Language = wx.ComboBox(self, style=wx.CB_READONLY)
        infos_sizer.AddWindow(self.Language, flag=wx.GROW)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, button_sizer.GetAffirmativeButton())
        main_sizer.AddSizer(button_sizer, border=20, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
            
        self.SetSizer(main_sizer)
        
        for option in GetPouTypes():
            self.PouType.Append(_(option))
        if pou_type is not None:
            self.PouType.SetStringSelection(_(pou_type))
        self.RefreshLanguage()

        self.PouNames = []
        self.PouElementNames = []

    def OnOK(self, event):
        error = []
        pou_name = self.PouName.GetValue()
        if pou_name == "":
            error.append(_("POU Name"))
        if self.PouType.GetSelection() == -1:
            error.append(_("POU Type"))
        if self.Language.GetSelection() == -1:
            error.append(_("Language"))
        message = None
        question = False
        if len(error) > 0:
            text = ""
            for i, item in enumerate(error):
                if i == 0:
                    text += item
                elif i == len(error) - 1:
                    text += _(" and %s")%item
                else:
                    text += _(", %s")%item 
            message = _("Form isn't complete. %s must be filled!") % text
        elif not TestIdentifier(pou_name):
            message = _("\"%s\" is not a valid identifier!") % pou_name
        elif pou_name.upper() in IEC_KEYWORDS:
            message = _("\"%s\" is a keyword. It can't be used!") % pou_name
        elif pou_name.upper() in self.PouNames:
            message = _("\"%s\" pou already exists!") % pou_name
        elif pou_name.upper() in self.PouElementNames:
            message = _("A POU has an element named \"%s\". This could cause a conflict. Do you wish to continue?") % pou_name
            question = True
        if message is not None:
            if question:
                dialog = wx.MessageDialog(self, message, _("Warning"), wx.YES_NO|wx.ICON_EXCLAMATION)
                result = dialog.ShowModal()
                dialog.Destroy()
                if result == wx.ID_YES:
                    self.EndModal(wx.ID_OK)
            else:
                dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
                dialog.ShowModal()
                dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)

    def RefreshLanguage(self):
        selection = POU_LANGUAGES_DICT.get(self.Language.GetStringSelection(), "")
        self.Language.Clear()
        for language in GetPouLanguages():
            if language != "SFC" or POU_TYPES_DICT[self.PouType.GetStringSelection()] != "function":
                self.Language.Append(_(language))
        if self.Language.FindString(_(selection)) != wx.NOT_FOUND:
            self.Language.SetStringSelection(_(selection))

    def OnTypeChanged(self, event):
        self.RefreshLanguage()
        event.Skip()

    def SetPouNames(self, pou_names):
        self.PouNames = [pou_name.upper() for pou_name in pou_names]

    def SetPouElementNames(self, element_names):
        self.PouElementNames = [element_name.upper() for element_name in element_names]

    def SetValues(self, values):
        for item, value in values.items():
            if item == "pouName":
                self.PouName.SetValue(value)
            elif item == "pouType":
                self.PouType.SetStringSelection(_(value))
            elif item == "language":
                self.Language.SetStringSelection(_(value))
                
    def GetValues(self):
        values = {}
        values["pouName"] = self.PouName.GetValue()
        values["pouType"] = POU_TYPES_DICT[self.PouType.GetStringSelection()]
        values["language"] = POU_LANGUAGES_DICT[self.Language.GetStringSelection()]
        return values
