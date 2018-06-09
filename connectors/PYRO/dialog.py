#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2018: Smarteh
#
# See COPYING file for copyrights details.


from __future__ import absolute_import
from __future__ import print_function

import wx
from zope.interface import implementer

from controls.UriLocationEditor import IConnectorPanel

URITypes = ["LOCAL", "PYRO", "PYROS"]


def PYRO_connector_dialog(confnodesroot):
    [ID_IPTEXT, ID_PORTTEXT] = [wx.NewId() for _init_ctrls in range(2)]

    @implementer(IConnectorPanel)
    class PYROConnectorPanel(wx.Panel):
        def __init__(self, typeConnector, parrent, *args, **kwargs):
            self.type = typeConnector
            self.parrent = parrent
            wx.Panel.__init__(self, parrent, *args, **kwargs)
            self._init_ctrls()
            self._init_sizers()
            self.uri = None

        def _init_ctrls(self):
            self.IpText = wx.TextCtrl(parent=self, id=ID_IPTEXT, size=wx.Size(200, -1))
            self.PortText = wx.TextCtrl(parent=self, id=ID_PORTTEXT, size=wx.Size(200, -1))

        def _init_sizers(self):
            self.mainSizer = wx.FlexGridSizer(cols=2, hgap=10, rows=5, vgap=10)
            self.mainSizer.AddWindow(wx.StaticText(self, label=_("URI host:")),
                                     flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.IpText, flag=wx.GROW)

            self.mainSizer.AddWindow(wx.StaticText(self, label=_("URI port:")),
                                     flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.PortText, flag=wx.GROW)
            self.SetSizer(self.mainSizer)

        def SetURI(self, uri):
            self.uri = uri
            uri_list = uri.strip().split(":")
            length = len(uri_list)
            if length == 3:
                self.IpText.SetValue(uri_list[1].strip("/"))
                self.PortText.SetValue(uri_list[2])
            elif length == 2:
                self.IpText.SetValue(uri_list[1].strip("/"))

        def GetURI(self):
            self.uri = self.type+"://"+self.IpText.GetValue()+":"+self.PortText.GetValue()
            return self.uri

    return PYROConnectorPanel("PYRO", confnodesroot)
