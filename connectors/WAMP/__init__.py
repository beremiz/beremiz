#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


from __future__ import absolute_import
from __future__ import print_function
try:
    import wx
    isWx = True
except ImportError:
    isWx = False
else:
    from controls.UriLocationEditor import IConnectorPanel
    from zope.interface import implementer

import traceback
from threading import Thread, Event

from twisted.internet import reactor, threads
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types
from autobahn.wamp.exception import TransportLost
from autobahn.wamp.serializer import MsgPackSerializer


_WampSession = None
_WampConnection = None
_WampSessionEvent = Event()
URITypes = ["WAMP", "WAMPS"]


class WampSession(wamp.ApplicationSession):
    def onJoin(self, details):
        global _WampSession
        _WampSession = self
        _WampSessionEvent.set()
        print('WAMP session joined for :', self.config.extra["ID"])

    def onLeave(self, details):
        global _WampSession
        _WampSessionEvent.clear()
        _WampSession = None
        print('WAMP session left')


PLCObjDefaults = {
    "StartPLC":          False,
    "GetTraceVariables": ("Broken", None),
    "GetPLCstatus":      ("Broken", None),
    "RemoteExec":        (-1, "RemoteExec script failed!")
}


def WAMP_connector_factory(uri, confnodesroot):
    """
    WAMP://127.0.0.1:12345/path#realm#ID
    WAMPS://127.0.0.1:12345/path#realm#ID
    """
    servicetype, location = uri.split("://")
    urlpath, realm, ID = location.split('#')
    urlprefix = {"WAMP":  "ws",
                 "WAMPS": "wss"}[servicetype]
    url = urlprefix+"://"+urlpath

    def RegisterWampClient():

        # start logging to console
        # log.startLogging(sys.stdout)

        # create a WAMP application session factory
        component_config = types.ComponentConfig(
            realm=unicode(realm),
            extra={"ID": ID})
        session_factory = wamp.ApplicationSessionFactory(
            config=component_config)
        session_factory.session = WampSession

        # create a WAMP-over-WebSocket transport client factory
        transport_factory = WampWebSocketClientFactory(
            session_factory,
            url=url,
            serializers=[MsgPackSerializer()])

        # start the client from a Twisted endpoint
        conn = connectWS(transport_factory)
        confnodesroot.logger.write(_("WAMP connecting to URL : %s\n") % url)
        return conn

    AddToDoBeforeQuit = confnodesroot.AppFrame.AddToDoBeforeQuit

    def ThreadProc():
        global _WampConnection
        _WampConnection = RegisterWampClient()
        AddToDoBeforeQuit(reactor.stop)
        reactor.run(installSignalHandlers=False)

    def WampSessionProcMapper(funcname):
        wampfuncname = unicode('.'.join((ID, funcname)))

        def catcher_func(*args, **kwargs):
            if _WampSession is not None:
                try:
                    return threads.blockingCallFromThread(
                        reactor, _WampSession.call, wampfuncname,
                        *args, **kwargs)
                except TransportLost:
                    confnodesroot.logger.write_error(_("Connection lost!\n"))
                    confnodesroot._SetConnector(None)
                except Exception:
                    errmess = traceback.format_exc()
                    confnodesroot.logger.write_error(errmess+"\n")
                    print(errmess)
                    # confnodesroot._SetConnector(None)
            return PLCObjDefaults.get(funcname)
        return catcher_func

    class WampPLCObjectProxy(object):
        def __init__(self):
            global _WampConnection
            if not reactor.running:
                Thread(target=ThreadProc).start()
            else:
                _WampConnection = threads.blockingCallFromThread(
                    reactor, RegisterWampClient)
            if not _WampSessionEvent.wait(5):
                _WampConnection.stopConnecting()
                raise Exception(_("WAMP connection timeout"))

        def __del__(self):
            _WampConnection.disconnect()
            #
            # reactor.stop()

        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                member = WampSessionProcMapper(attrName)
                self.__dict__[attrName] = member
            return member

    # Try to get the proxy object
    try:
        return WampPLCObjectProxy()
    except Exception:
        confnodesroot.logger.write_error(_("WAMP connection to '%s' failed.\n") % location)
        confnodesroot.logger.write_error(traceback.format_exc())
        return None

if isWx:
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
                self.IpText = wx.TextCtrl(parent=self, id=ID_IPTEXT, size = wx.Size(200, -1))
                self.PortText = wx.TextCtrl(parent=self, id=ID_PORTTEXT, size = wx.Size(200, -1))
                self.RealmText = wx.TextCtrl(parent=self, id=ID_REALMTEXT, size = wx.Size(200, -1))
                self.WAMPIDText = wx.TextCtrl(parent=self, id=ID_WAMPIDTEXT, size = wx.Size(200, -1))
                self.SecureCheckbox = wx.CheckBox(self, ID_SECURECHECKBOX, _("Is connection secure?"))

            def _init_sizers(self):
                self.mainSizer = wx.BoxSizer(wx.VERTICAL)
                self.uriSizer = wx.BoxSizer(wx.HORIZONTAL)
                self.portSizer = wx.BoxSizer(wx.HORIZONTAL)
                self.realmSizer = wx.BoxSizer(wx.HORIZONTAL)
                self.wampIDSizer = wx.BoxSizer(wx.HORIZONTAL)

                self.uriSizer.Add(wx.StaticText(self, wx.ID_ANY, _("URI host:"), size = wx.Size(70, -1)), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)
                self.uriSizer.AddSpacer((0,0))
                self.uriSizer.Add(self.IpText, proportion=1, flag=wx.ALIGN_RIGHT)
                self.mainSizer.Add(self.uriSizer, border=2, flag=wx.ALL)

                self.portSizer.Add(wx.StaticText(self, wx.ID_ANY, _("URI port:"), size = wx.Size(70, -1)), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)
                self.portSizer.AddSpacer((0,0))
                self.portSizer.Add(self.PortText, proportion=1, flag=wx.ALIGN_RIGHT)
                self.mainSizer.Add(self.portSizer, border=2, flag=wx.ALL)

                self.realmSizer.Add(wx.StaticText(self, wx.ID_ANY, _("Realm:"), size = wx.Size(70, -1)), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)
                self.realmSizer.AddSpacer((0, 0))
                self.realmSizer.Add(self.RealmText, proportion=1, flag=wx.ALIGN_RIGHT)
                self.mainSizer.Add(self.realmSizer, border=2, flag=wx.ALL)

                self.wampIDSizer.Add(wx.StaticText(self, wx.ID_ANY, _("WAMP ID:"), size = wx.Size(70, -1)), proportion=0, flag=wx.ALIGN_CENTER_VERTICAL)
                self.wampIDSizer.AddSpacer((0, 0))
                self.wampIDSizer.Add(self.WAMPIDText, proportion=1, flag=wx.ALIGN_RIGHT)
                self.mainSizer.Add(self.wampIDSizer, border=2, flag=wx.ALL)

                self.mainSizer.Add(self.SecureCheckbox, proportion=1, flag=wx.ALIGN_LEFT)

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
