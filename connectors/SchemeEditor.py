#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from __future__ import absolute_import

from itertools import repeat, izip_longest
import wx

class SchemeEditor(wx.Panel):
    def __init__(self, scheme, parent, *args, **kwargs):
        self.txtctrls = {} 
        wx.Panel.__init__(self, parent, *args, **kwargs)

        self.mainSizer = wx.FlexGridSizer(cols=2, hgap=10, rows=5, vgap=10)

        for tag, label in self.model:
            txtctrl = wx.TextCtrl(parent=self, size=wx.Size(200, -1))
            self.txtctrls[tag] = txtctrl
            for win, flag in [
                (wx.StaticText(self, label=label), wx.ALIGN_CENTER_VERTICAL),
                (txtctrl, wx.GROW)]:
                self.mainSizer.AddWindow(win, flag=flag)

        self.mainSizer.AddSpacer(20)

        self.SetSizer(self.mainSizer)

    def SetFields(self, fields):
        for tag, label in self.model:
            self.txtctrls[tag].SetValue(fields[tag])

    def GetFields(self):
        return {tag: self.txtctrls[tag].GetValue() for tag,label in self.model}

