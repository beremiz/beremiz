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

