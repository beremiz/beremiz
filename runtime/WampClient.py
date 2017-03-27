#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING.Runtime file for copyrights details.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import sys
#from twisted.python import log
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from twisted.internet.defer import inlineCallbacks
from autobahn.wamp import types
from autobahn.wamp.serializer import MsgPackSerializer
from twisted.internet.protocol import ReconnectingClientFactory
import json

_WampSession = None
_PySrv = None

ExposedCalls = ["StartPLC",
                "StopPLC",
                "ForceReload",
                "GetPLCstatus",
                "NewPLC",
                "MatchMD5",
                "SetTraceVariablesList",
                "GetTraceVariables",
                "RemoteExec",
                "GetLogMessage",
                "ResetLogCount",
                ]

SubscribedEvents = []

DoOnJoin = []

def GetCallee(name):
    """ Get Callee or Subscriber corresponding to '.' spearated object path """
    global _PySrv
    names = name.split('.')
    obj = _PySrv.plcobj
    while names: obj = getattr(obj, names.pop(0))
    return obj

class WampSession(wamp.ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
        global _WampSession
        _WampSession = self
        ID = self.config.extra["ID"]
        print 'WAMP session joined by :', ID
        for name in ExposedCalls:
            reg = yield self.register(GetCallee(name), '.'.join((ID,name)))

        for name in SubscribedEvents:
            reg = yield self.subscribe(GetCallee(name), name)

        for func in DoOnJoin:
            yield func(self)

    def onLeave(self, details):
        global _WampSession
        _WampSession = None
        print 'WAMP session left'

class ReconnectingWampWebSocketClientFactory(WampWebSocketClientFactory, ReconnectingClientFactory):
    def clientConnectionFailed(self, connector, reason):
        print("WAMP Client connection failed .. retrying ..")
        self.retry(connector)
    def clientConnectionLost(self, connector, reason):
        print("WAMP Client connection lost .. retrying ..")
        self.retry(connector)

def LoadWampClientConf(wampconf):

    WSClientConf = json.load(open(wampconf))
    return WSClientConf

def RegisterWampClient(wampconf):

    WSClientConf = LoadWampClientConf(wampconf)

    ## start logging to console
    # log.startLogging(sys.stdout)

    # create a WAMP application session factory
    component_config = types.ComponentConfig(
        realm = WSClientConf["realm"],
        extra = {"ID":WSClientConf["ID"]})
    session_factory = wamp.ApplicationSessionFactory(
        config = component_config)
    session_factory.session = WampSession

    # create a WAMP-over-WebSocket transport client factory
    transport_factory = ReconnectingWampWebSocketClientFactory(
        session_factory,
        url = WSClientConf["url"],
        serializers = [MsgPackSerializer()],
        debug = False,
        debug_wamp = False)

    # start the client from a Twisted endpoint
    conn = connectWS(transport_factory)
    print "WAMP client connecting to :",WSClientConf["url"]
    return conn

def GetSession():
    global _WampSession
    return _WampSession

def SetServer(pysrv):
    global _PySrv
    _PySrv = pysrv

