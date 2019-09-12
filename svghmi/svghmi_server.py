#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2019: Edouard TISSERANT
# See COPYING file for copyrights details.

from __future__ import absolute_import

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from autobahn.twisted.resource import  WebSocketResource

# TODO multiclient :
# session list lock
# svghmi_sessions = []

svghmi_session = None

class HMISession(object):
    def __init__(self, protocol_instance):
        global svghmi_session
        
        # TODO: kill existing session for robustness
        assert(svghmi_session is None)

        svghmi_session = self
        self.protocol_instance = protocol_instance

        # TODO multiclient :
        # svghmi_sessions.append(self)
        # get a unique bit index amont other svghmi_sessions,
        # so that we can match flags passed by C->python callback
    
    def __del__(self):
        global svghmi_session
        assert(svghmi_session)
        svghmi_session = None

        # TODO multiclient :
        # svghmi_sessions.remove(self)

    def onMessage(self, msg):
        # TODO :  pass it to the C side recieve_message()
        #    update HMITree
        #        - values
        #        - refresh rates / subsriptions

        # TODO multiclient : pass client index as well
        pass
         

class HMIProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        self._hmi_session = None
        WebSocketServerProtocol.__init__(self, *args, **kwargs)

    def onOpen(self):
        self._hmi_session = HMISession(self)
        print "open"

    def onClose(self, wasClean, code, reason):
        del self._hmi_session
        self._hmi_session = None
        print "close"

    def onMessage(self, msg, isBinary):
        self._hmi_session.onMessage(msg)
        print msg
        #self.sendMessage(msg, binary)
     
svghmi_root = None
svghmi_listener = None

# Called by PLCObject at start
def _runtime_svghmi0_start():
    global svghmi_listener, svghmi_root

    svghmi_root = Resource()

    wsfactory = WebSocketServerFactory()
    wsfactory.protocol = HMIProtocol

    # svghmi_root.putChild("",File(".svg"))
    svghmi_root.putChild("ws",WebSocketResource(wsfactory))

    sitefactory = Site(svghmi_root)

    svghmi_listener = reactor.listenTCP(8008, sitefactory)

    # TODO
    # start a thread that call the C part of SVGHMI


# Called by PLCObject at stop
def _runtime_svghmi0_stop():
    global svghmi_listener
    svghmi_listener.stopListening()
