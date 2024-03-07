#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, 2010 by Steven Sproat
# Copyright (c) 2016 by Andrey Skvortsov <andrej.skvortzov@gmail.com>
# Copyright (c) 2024 by Edouard Tisserant

# See COPYING file for copyrights details.

import os
import wx
import wx.adv
from wx.lib.agw.hyperlink import HyperLinkCtrl


class AboutDialog(wx.Dialog):
    """
    Simpler replacement of About Dialog that shows LongVersion
    """
    def __init__(self, parent, info):
        title = _("About") + " " + info.Name
        wx.Dialog.__init__(self, parent, title=title)
        self.info = info

        if parent and parent.GetIcon():
            self.SetIcon(parent.GetIcon())

        image = None
        if self.info.Icon:
            bitmap = wx.Bitmap()
            bitmap.CopyFromIcon(self.info.Icon)
            image = wx.StaticBitmap(self, bitmap=bitmap)

        name = wx.StaticText(self, label="%s %s" % (info.Name, info.Version))
        description = wx.StaticText(self, label=info.Description)
        description.Wrap(400)
        copyright = wx.StaticText(self, label=info.Copyright)
        url = HyperLinkCtrl(self, label=info.WebSite[0], URL=info.WebSite[1])
        long_version = wx.StaticText(self, label=info.GetLongVersion())

        font = name.GetClassDefaultAttributes().font
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        font.SetPointSize(18)
        name.SetFont(font)

        credits = wx.Button(self, id=wx.ID_ABOUT, label=_("C&redits"))
        license = wx.Button(self, label=_("&License"))
        close = wx.Button(self, id=wx.ID_CANCEL, label=_("&Close"))

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(credits, flag=wx.CENTER | wx.LEFT | wx.RIGHT, border=5)
        btnSizer.Add(license, flag=wx.CENTER | wx.RIGHT, border=5)
        btnSizer.Add(close, flag=wx.CENTER | wx.RIGHT, border=5)

        sizer = wx.BoxSizer(wx.VERTICAL)
        if image:
            sizer.Add(image, flag=wx.CENTER | wx.TOP | wx.BOTTOM, border=5)
        sizer.Add(name, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(description, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(copyright, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(url, flag=wx.CENTER | wx.BOTTOM, border=15)
        sizer.Add(long_version, flag=wx.CENTER | wx.BOTTOM, border=10)
        sizer.Add(btnSizer, flag=wx.CENTER | wx.BOTTOM, border=5)

        container = wx.BoxSizer(wx.VERTICAL)
        container.Add(sizer, flag=wx.ALL, border=10)
        self.SetSizer(container)
        self.Layout()
        self.Fit()
        self.Centre()
        self.Show(True)
        self.SetEscapeId(close.GetId())

        credits.Bind(wx.EVT_BUTTON, self.on_credits)
        license.Bind(wx.EVT_BUTTON, self.on_license)
        close.Bind(wx.EVT_BUTTON, lambda evt: self.Destroy())

    def on_license(self, event):
        LicenseDialog(self, self.info)

    def on_credits(self, event):
        CreditsDialog(self, self.info)


class CreditsDialog(wx.Dialog):
    def __init__(self, parent, info):
        wx.Dialog.__init__(self, parent, title=_("Credits"), size=(475, 320),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if parent and parent.GetIcon():
            self.SetIcon(parent.GetIcon())

        self.SetMinSize((300, 200))
        notebook = wx.Notebook(self)
        close = wx.Button(self, id=wx.ID_CLOSE, label=_("&Close"))
        close.SetDefault()

        developer = wx.TextCtrl(notebook, style=wx.TE_READONLY | wx.TE_MULTILINE)
        translators = wx.TextCtrl(notebook, style=wx.TE_READONLY | wx.TE_MULTILINE)

        developer.SetValue('\n'.join(info.Developers))
        translators.SetValue('\n'.join(info.Translators))

        notebook.AddPage(developer, text=_("Written by"))
        notebook.AddPage(translators, text=_("Translated by"))

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(close)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(notebook, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(btnSizer, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.Layout()
        self.Show()
        self.SetEscapeId(close.GetId())

        close.Bind(wx.EVT_BUTTON, lambda evt: self.Destroy())


class LicenseDialog(wx.Dialog):
    def __init__(self, parent, info):
        wx.Dialog.__init__(self, parent, title=_("License"), size=(500, 400),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if parent and parent.GetIcon():
            self.SetIcon(parent.GetIcon())

        self.SetMinSize((400, 300))
        close = wx.Button(self, id=wx.ID_CLOSE, label=_("&Close"))

        ctrl = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE)
        ctrl.SetValue(info.License)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)
        btnSizer.Add(close)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, 10)
        sizer.Add(btnSizer, flag=wx.ALIGN_RIGHT | wx.RIGHT | wx.BOTTOM, border=10)
        self.SetSizer(sizer)
        self.Layout()
        self.Show()
        self.SetEscapeId(close.GetId())

        close.Bind(wx.EVT_BUTTON, lambda evt: self.Destroy())


def ShowAboutDialog(parent, info):
    AboutDialog(parent, info)
