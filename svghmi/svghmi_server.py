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

svghmi_send_collect = PLCBinary.svghmi_send_collect
svghmi_send_collect.restype = ctypes.c_int # error or 0
svghmi_send_collect.argtypes = [
    ctypes.POINTER(ctypes.c_uint32),  # size
    ctypes.POINTER(ctypes.c_void_p)]  # data ptr
# TODO multiclient : switch to arrays

svghmi_recv_dispatch = PLCBinary.svghmi_recv_dispatch
svghmi_recv_dispatch.restype = ctypes.c_int # error or 0
svghmi_recv_dispatch.argtypes = [
    ctypes.c_uint32,                  # size
    ctypes.POINTER(ctypes.c_void_p)]  # data ptr
# TODO multiclient : switch to arrays

def SendThreadProc():
   assert(svghmi_session)
   size = ctypes.c_uint32()
   ptr = ctypes.c_void_p()
   res = 0
   while svghmi_send_collect(ctypes.byref(size), ctypes.byref(ptr)) == 0 and \
         svghmi_session is not None and \
         svghmi_session.sendMessage(ctypes.string_at(ptr,size)) == 0:
         pass

       # TODO multiclient : dispatch to sessions

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

    def sendMessage(self, msg):
        self.sendMessage(msg, True)

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
svghmi_send_thread = None


# Called by PLCObject at start
def _runtime_svghmi0_start():
    global svghmi_listener, svghmi_root, svghmi_send_thread

    svghmi_root = Resource()

    wsfactory = WebSocketServerFactory()
    wsfactory.protocol = HMIProtocol

    svghmi_root.putChild("ws", WebSocketResource(wsfactory))

    sitefactory = Site(svghmi_root)

    svghmi_listener = reactor.listenTCP(8008, sitefactory)

    # start a thread that call the C part of SVGHMI
    svghmi_send_thread = Thread(target=SendThreadProc, name="SVGHMI Send")
    svghmi_send_thread.start()


# Called by PLCObject at stop
def _runtime_svghmi0_stop():
    global svghmi_listener, svghmi_root, svghmi_send_thread
    svghmi_root.delEntity("ws")
    svghmi_root = None
    svghmi_listener.stopListening()
    svghmi_listener = None
    # plc cleanup calls svghmi_(locstring)_cleanup and unlocks send thread
    svghmi_send_thread.join()
    svghmi_send_thread = None

