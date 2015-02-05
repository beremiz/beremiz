#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from twisted.python import log

from twisted.internet import reactor, ssl
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types
import json

_WampSession = None
_PySrv = None

class WampSession(wamp.ApplicationSession):
    def onJoin(self, details):
        global _WampSession
        _WampSession = self
        print 'WAMP session joined by :', self.config.extra["ID"]

    def onLeave(self, details):
        global _WampSession
        _WampSession = None
        print 'WAMP session left'


def RegisterWampClient(wampconf):

    WSClientConf = json.load(open(wampconf))

    ## TODO log to PLC console instead
    ## 0) start logging to console
    log.startLogging(sys.stdout)

    ## 1) create a WAMP application session factory
    component_config = types.ComponentConfig(
        realm = WSClientConf["realm"],
        extra = {"ID":WSClientConf["ID"]})
    session_factory = wamp.ApplicationSessionFactory(
        config = component_config)
    session_factory.session = WampSession

    ## TODO select optimum serializer for passing session lists
    ## optional: use specific set of serializers
    #from autobahn.wamp.serializer import *
    #serializers = []
    ##serializers.append(JsonSerializer(batched = True))
    ##serializers.append(MsgPackSerializer(batched = True))
    #serializers.append(JsonSerializer())
    ##serializers.append(MsgPackSerializer())
    serializers = None

    ## 2) create a WAMP-over-WebSocket transport client factory
    transport_factory = WampWebSocketClientFactory(
        session_factory,
        url = WSClientConf["url"],
        serializers = serializers,
        debug = False,
        debug_wamp = False)

    ## 3) start the client from a Twisted endpoint
    conn = connectWS(transport_factory)
    print "WAMP clien connecting to :",WSClientConf["url"]
    return conn

def GetSession():
    global _WampSession
    return _WampSession

def SetServer(pysrv):
    global _PySrv
    _PySrv = pysrv

