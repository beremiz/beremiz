#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2019: Edouard TISSERANT
# See COPYING file for copyrights details.

from __future__ import absolute_import
import errno

from twisted.web.server import Site
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, WebSocketServerProtocol
from autobahn.websocket.protocol import WebSocketProtocol
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
    ctypes.c_uint32,  # size
    ctypes.c_char_p]  # data ptr
# TODO multiclient : switch to arrays

class HMISession(object):
    def __init__(self, protocol_instance):
        global svghmi_session
        
        # Single client :
        # Creating a new HMISession closes pre-existing HMISession
        if svghmi_session is not None:
            svghmi_session.close()
        svghmi_session = self
        self.protocol_instance = protocol_instance

        # TODO multiclient :
        # svghmi_sessions.append(self)
        # get a unique bit index amont other svghmi_sessions,
        # so that we can match flags passed by C->python callback

    def close(self):
        global svghmi_session
        if svghmi_session == self:
            svghmi_session = None
        self.protocol_instance.sendClose(WebSocketProtocol.CLOSE_STATUS_CODE_NORMAL)

    def onMessage(self, msg):
        # pass message to the C side recieve_message()
        svghmi_recv_dispatch(len(msg), msg)

        # TODO multiclient : pass client index as well


    def sendMessage(self, msg):
        self.protocol_instance.sendMessage(msg, True)
        return 0

class HMIProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        self._hmi_session = None
        WebSocketServerProtocol.__init__(self, *args, **kwargs)

    def onOpen(self):
        assert(self._hmi_session is None)
        self._hmi_session = HMISession(self)

    def onClose(self, wasClean, code, reason):
        self._hmi_session = None

    def onMessage(self, msg, isBinary):
        assert(self._hmi_session is not None)
        self._hmi_session.onMessage(msg)

class HMIWebSocketServerFactory(WebSocketServerFactory):
    protocol = HMIProtocol

svghmi_root = None
svghmi_listener = None
svghmi_send_thread = None

def SendThreadProc():
   global svghmi_session
   size = ctypes.c_uint32()
   ptr = ctypes.c_void_p()
   res = 0
   while True:
       res=svghmi_send_collect(ctypes.byref(size), ctypes.byref(ptr))
       if res == 0:
           # TODO multiclient : dispatch to sessions
           if svghmi_session is not None:
               svghmi_session.sendMessage(ctypes.string_at(ptr.value,size.value))
       elif res not in [errno.EAGAIN, errno.ENODATA]:
           break




# Called by PLCObject at start
def _runtime_svghmi0_start():
    global svghmi_listener, svghmi_root, svghmi_send_thread

    svghmi_root = Resource()
    svghmi_root.putChild("ws", WebSocketResource(HMIWebSocketServerFactory()))

    svghmi_listener = reactor.listenTCP(8008, Site(svghmi_root))

    # start a thread that call the C part of SVGHMI
    svghmi_send_thread = Thread(target=SendThreadProc, name="SVGHMI Send")
    svghmi_send_thread.start()


# Called by PLCObject at stop
def _runtime_svghmi0_stop():
    global svghmi_listener, svghmi_root, svghmi_send_thread, svghmi_session
    if svghmi_session is not None:
        svghmi_session.close()
    svghmi_root.delEntity("ws")
    svghmi_root = None
    svghmi_listener.stopListening()
    svghmi_listener = None
    # plc cleanup calls svghmi_(locstring)_cleanup and unlocks send thread
    svghmi_send_thread.join()
    svghmi_send_thread = None

