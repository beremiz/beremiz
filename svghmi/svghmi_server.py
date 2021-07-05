#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2019: Edouard TISSERANT
# See COPYING file for copyrights details.

from __future__ import absolute_import
import errno
from threading import RLock, Timer

try:
    from runtime.spawn_subprocess import Popen
except ImportError:
    from subprocess import Popen

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
# svghmi_watchdogs = []

svghmi_session = None
svghmi_watchdog = None

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
        return svghmi_recv_dispatch(len(msg), msg)

        # TODO multiclient : pass client index as well

    def sendMessage(self, msg):
        self.protocol_instance.sendMessage(msg, True)
        return 0

class Watchdog(object):
    def __init__(self, initial_timeout, interval, callback):
        self._callback = callback
        self.lock = RLock()
        self.initial_timeout = initial_timeout
        self.interval = interval
        self.callback = callback
        with self.lock:
            self._start()

    def _start(self, rearm=False):
        duration = self.interval if rearm else self.initial_timeout
        if duration:
            self.timer = Timer(duration, self.trigger)
            self.timer.start()
        else:
            self.timer = None

    def _stop(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def cancel(self):
        with self.lock:
            self._stop()

    def feed(self, rearm=True):
        with self.lock:
            self._stop()
            self._start(rearm)

    def trigger(self):
        self._callback()
        # wait for initial timeout on re-start
        self.feed(rearm=False)

class HMIProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        self._hmi_session = None
        WebSocketServerProtocol.__init__(self, *args, **kwargs)

    def onConnect(self, request):
        self.has_watchdog = request.params.get("mode", [None])[0] == "watchdog"
        return WebSocketServerProtocol.onConnect(self, request)

    def onOpen(self):
        assert(self._hmi_session is None)
        self._hmi_session = HMISession(self)

    def onClose(self, wasClean, code, reason):
        self._hmi_session = None

    def onMessage(self, msg, isBinary):
        assert(self._hmi_session is not None)

        result = self._hmi_session.onMessage(msg)
        if result == 1 :  # was heartbeat
            if svghmi_watchdog is not None:
                svghmi_watchdog.feed()

class HMIWebSocketServerFactory(WebSocketServerFactory):
    protocol = HMIProtocol

svghmi_servers = {}
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
        elif res == errno.ENODATA:
            # this happens when there is no data after wakeup
            # because of hmi data refresh period longer than PLC common ticktime
            pass 
        else:
            # this happens when finishing
            break

def AddPathToSVGHMIServers(path, factory):
    for k,v in svghmi_servers.iteritems():
        svghmi_root, svghmi_listener, path_list = v
        svghmi_root.putChild(path, factory())

# Called by PLCObject at start
def _runtime_00_svghmi_start():
    global svghmi_send_thread

    # start a thread that call the C part of SVGHMI
    svghmi_send_thread = Thread(target=SendThreadProc, name="SVGHMI Send")
    svghmi_send_thread.start()


# Called by PLCObject at stop
def _runtime_00_svghmi_stop():
    global svghmi_send_thread, svghmi_session

    if svghmi_session is not None:
        svghmi_session.close()
    # plc cleanup calls svghmi_(locstring)_cleanup and unlocks send thread
    svghmi_send_thread.join()
    svghmi_send_thread = None


class NoCacheFile(File):
    def render_GET(self, request):
        request.setHeader(b"Cache-Control", b"no-cache, no-store")
        return File.render_GET(self, request)
    render_HEAD = render_GET


