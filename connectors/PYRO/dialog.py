#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2018: Smarteh
#
# See COPYING file for copyrights details.


from __future__ import absolute_import
from __future__ import print_function

import wx
from controls.UriLocationEditor import IConnectorPanel
from zope.interface import implementer

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
            self.IpText = wx.TextCtrl(parent=self, id=ID_IPTEXT, size = wx.Size(200, -1))
            self.PortText = wx.TextCtrl(parent=self, id=ID_PORTTEXT, size = wx.Size(200, -1))

        def _init_sizers(self):
            self.mainSizer = wx.BoxSizer(wx.VERTICAL)
            self.uriSizer = wx.BoxSizer(wx.HORIZONTAL)
            self.portSizer = wx.BoxSizer(wx.HORIZONTAL)

            self.uriSizer.Add(wx.StaticText(self, wx.ID_ANY, _("URI host:"), size = wx.Size(70, -1)), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)
            self.uriSizer.AddSpacer((0,0))
            self.uriSizer.Add(self.IpText, proportion=1, flag=wx.ALIGN_RIGHT)
            self.mainSizer.Add(self.uriSizer, border=2, flag=wx.ALL)

            self.portSizer.Add(wx.StaticText(self, wx.ID_ANY, _("URI port:"), size = wx.Size(70, -1)), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)
            self.portSizer.AddSpacer((0,0))
            self.portSizer.Add(self.PortText, proportion=1, flag=wx.ALIGN_RIGHT)
            self.mainSizer.Add(self.portSizer, border=2, flag=wx.ALL)

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
