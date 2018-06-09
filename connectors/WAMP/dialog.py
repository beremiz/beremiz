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

URITypes = ["WAMP", "WAMPS"]


def WAMP_connector_dialog(confnodesroot):
    [ID_IPTEXT, ID_PORTTEXT, ID_REALMTEXT, ID_WAMPIDTEXT, ID_SECURECHECKBOX] = [wx.NewId() for _init_ctrls in range(5)]

    @implementer(IConnectorPanel)
    class WAMPConnectorPanel(wx.Panel):
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
            self.RealmText = wx.TextCtrl(parent=self, id=ID_REALMTEXT, size=wx.Size(200, -1))
            self.WAMPIDText = wx.TextCtrl(parent=self, id=ID_WAMPIDTEXT, size=wx.Size(200, -1))
            self.SecureCheckbox = wx.CheckBox(self, ID_SECURECHECKBOX, _("Is connection secure?"))

        def _init_sizers(self):
            self.mainSizer = wx.FlexGridSizer(cols=2, hgap=10, rows=5, vgap=10)
            self.mainSizer.AddWindow(wx.StaticText(self, label=_("URI host:")),
                                     flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.IpText, flag=wx.GROW)

            self.mainSizer.AddWindow(wx.StaticText(self, label=_("URI port:")),
                                     flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.PortText, flag=wx.GROW)

            self.mainSizer.AddWindow(wx.StaticText(self, label=_("Realm:")),
                                     flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.RealmText, flag=wx.GROW)

            self.mainSizer.AddWindow(wx.StaticText(self, label=_("WAMP ID:")),
                                     flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.WAMPIDText, flag=wx.GROW)

            self.mainSizer.AddWindow(wx.StaticText(self, label=""), flag=wx.ALIGN_CENTER_VERTICAL)
            self.mainSizer.AddWindow(self.SecureCheckbox, flag=wx.GROW)

            self.SetSizer(self.mainSizer)

        def SetURI(self, uri):
            self.uri = uri
            uri_list = uri.strip().split(":")
            length = len(uri_list)

            if length > 0:
                if uri_list[0] == URITypes[1]:
                    self.SecureCheckbox.SetValue(True)

                if length > 2:
                    self.IpText.SetValue(uri_list[1].strip("/"))
                    wampSett = uri_list[2].split("#")
                    length2 = len(wampSett)
                    if length2 > 0:
                        self.PortText.SetValue(wampSett[0])
                        if length2 > 1:
                            self.RealmText.SetValue(wampSett[1])
                            if length2 > 2:
                                self.WAMPIDText.SetValue(wampSett[2])

        def GetURI(self):
            if self.IpText.Validate():
                typeForURI = self.type + "S" if self.SecureCheckbox.GetValue() else self.type
                self.uri = typeForURI + "://" + self.IpText.GetValue() + ":" + self.PortText.GetValue() + "#" + self.RealmText.GetValue() + "#" + self.WAMPIDText.GetValue()
                return self.uri
            else:
                return ""

    return WAMPConnectorPanel("WAMP", confnodesroot)
