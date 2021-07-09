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

max_svghmi_sessions = None
svghmi_watchdog = None


svghmi_wait = PLCBinary.svghmi_wait
svghmi_wait.restype = ctypes.c_int # error or 0
svghmi_wait.argtypes = []

svghmi_send_collect = PLCBinary.svghmi_send_collect
svghmi_send_collect.restype = ctypes.c_int # error or 0
svghmi_send_collect.argtypes = [
    ctypes.c_uint32,  # index
    ctypes.POINTER(ctypes.c_uint32),  # size
    ctypes.POINTER(ctypes.c_void_p)]  # data ptr

svghmi_reset = PLCBinary.svghmi_reset
svghmi_reset.restype = ctypes.c_int # error or 0
svghmi_reset.argtypes = [
    ctypes.c_uint32]  # index

svghmi_recv_dispatch = PLCBinary.svghmi_recv_dispatch
svghmi_recv_dispatch.restype = ctypes.c_int # error or 0
svghmi_recv_dispatch.argtypes = [
    ctypes.c_uint32,  # index
    ctypes.c_uint32,  # size
    ctypes.c_char_p]  # data ptr

class HMISessionMgr(object):
    def __init__(self):
        self.multiclient_sessions = set()
        self.watchdog_session = None
        self.session_count = 0
        self.lock = RLock()
        self.indexes = set()

    def next_index(self):
        if self.indexes:
            greatest = max(self.indexes)
            holes = set(range(greatest)) - self.indexes
            index = min(holes) if holes else greatest+1
        else:
            index = 0
        self.indexes.add(index)
        return index

    def free_index(self, index):
        self.indexes.remove(index)

    def register(self, session):
        global max_svghmi_sessions
        with self.lock:
            if session.is_watchdog_session:
                # Creating a new watchdog session closes pre-existing one
                if self.watchdog_session is not None:
                    self.unregister(self.watchdog_session)
                else:
                    assert(self.session_count < max_svghmi_sessions)
                    self.session_count += 1

                self.watchdog_session = session
            else:
                assert(self.session_count < max_svghmi_sessions)
                self.multiclient_sessions.add(session)
                self.session_count += 1
            session.session_index = self.next_index()

    def unregister(self, session):
        with self.lock:
            if session.is_watchdog_session :
                if self.watchdog_session != session:
                    return
                self.watchdog_session = None
            else:
                try:
                    self.multiclient_sessions.remove(self)
                except KeyError:
                    return
            self.free_index(session.session_index)
            self.session_count -= 1
        session.kill()
        
    def close_all(self):
        with self.lock:
            close_list = list(self.multiclient_sessions)
            if self.watchdog_session:
                close_list.append(self.watchdog_session)
            for session in close_list:
                self.unregister(session)
        
    def iter_sessions(self):
        with self.lock:
            nxt_session = self.watchdog_session
        if nxt_session is not None:
            yield nxt_session
        idx = 0
        while True:
            with self.lock:
                if idx >= len(self.multiclient_sessions):
                    return
                nxt_session = self.multiclient_sessions[idx]
            yield nxt_session
            idx += 1


svghmi_session_manager = HMISessionMgr()


class HMISession(object):
    def __init__(self, protocol_instance):
        self.protocol_instance = protocol_instance
        self._session_index = None
        self.closed = False

    @property
    def is_watchdog_session(self):
        return self.protocol_instance.has_watchdog

    @property
    def session_index(self):
        return self._session_index

    @session_index.setter
    def session_index(self, value):
        self._session_index = value

    def reset(self):
        return svghmi_reset(self.session_index)

    def close(self):
        if self.closed: return
        self.protocol_instance.sendClose(WebSocketProtocol.CLOSE_STATUS_CODE_NORMAL)

    def notify_closed(self):
        self.closed = True

    def kill(self):
        self.close()
        self.reset()

    def onMessage(self, msg):
        # pass message to the C side recieve_message()
        if self.closed: return
        return svghmi_recv_dispatch(self.session_index, len(msg), msg)

    def sendMessage(self, msg):
        if self.closed: return
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
        # Don't repeat trigger periodically
        # # wait for initial timeout on re-start
        # self.feed(rearm=False)

class HMIProtocol(WebSocketServerProtocol):

    def __init__(self, *args, **kwargs):
        self._hmi_session = None
        self.has_watchdog = False
        WebSocketServerProtocol.__init__(self, *args, **kwargs)

    def onConnect(self, request):
        self.has_watchdog = request.params.get("mode", [None])[0] == "watchdog"
        return WebSocketServerProtocol.onConnect(self, request)

    def onOpen(self):
        global svghmi_session_manager
        assert(self._hmi_session is None)
        self._hmi_session = HMISession(self)
        registered = svghmi_session_manager.register(self._hmi_session)

    def onClose(self, wasClean, code, reason):
        global svghmi_session_manager
        self._hmi_session.notify_closed()
        svghmi_session_manager.unregister(self._hmi_session)
        self._hmi_session = None

    def onMessage(self, msg, isBinary):
        global svghmi_watchdog
        assert(self._hmi_session is not None)

        result = self._hmi_session.onMessage(msg)
        if result == 1 and self.has_watchdog:  # was heartbeat
            if svghmi_watchdog is not None:
                svghmi_watchdog.feed()

class HMIWebSocketServerFactory(WebSocketServerFactory):
    protocol = HMIProtocol

svghmi_servers = {}
svghmi_send_thread = None

def SendThreadProc():
    global svghmi_session_manager
    size = ctypes.c_uint32()
    ptr = ctypes.c_void_p()
    res = 0
    finished = False
    while not(finished):
        svghmi_wait()
        for svghmi_session in svghmi_session_manager.iter_sessions():
            # TODO make svghmi_send_collect waiting only once per
            # svghmi_session_manager.iter_sessions cycle
            res = svghmi_send_collect(
                svghmi_session.session_index,
                ctypes.byref(size), ctypes.byref(ptr))
            if res == 0:
                svghmi_session.sendMessage(
                    ctypes.string_at(ptr.value,size.value))
            elif res == errno.ENODATA:
                # this happens when there is no data after wakeup
                # because of hmi data refresh period longer than
                # PLC common ticktime
                pass
            else:
                # this happens when finishing
                finished = True
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

    svghmi_session_manager.close_all()

    # plc cleanup calls svghmi_(locstring)_cleanup and unlocks send thread
    svghmi_send_thread.join()
    svghmi_send_thread = None


class NoCacheFile(File):
    def render_GET(self, request):
        request.setHeader(b"Cache-Control", b"no-cache, no-store")
        return File.render_GET(self, request)
    render_HEAD = render_GET


