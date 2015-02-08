#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

def MakeCallee(name):
    global _PySrv
    def Callee(*args,**kwargs):
        return getattr(_PySrv.plcobj, name)(*args,**kwargs)
    return Callee


class WampSession(wamp.ApplicationSession):

    @inlineCallbacks
    def onJoin(self, details):
        global _WampSession
        _WampSession = self
        print 'WAMP session joined by :', self.config.extra["ID"]
        for name in ExposedCalls:
            reg = yield self.register(MakeCallee(name), name)

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

def RegisterWampClient(wampconf):

    WSClientConf = json.load(open(wampconf))

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

