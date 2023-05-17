#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.

# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
# Copyright (C) 2018: Edouard TISSERANT

# See COPYING file for copyrights details.



import sys
import os

import Pyro5
import Pyro5.server

import runtime
from runtime.ServicePublisher import ServicePublisher

def make_pyro_exposed_stub(method_name):
    stub = lambda self, *args, **kwargs: \
        getattr(self.plc_object_instance, method_name)(*args, **kwargs)
    stub.__name__ = method_name
    Pyro5.server.expose(stub)
    return stub
    

class PLCObjectPyroAdapter(type("PLCObjectPyroStubs", (), {
    name: make_pyro_exposed_stub(name) for name in [
        "AppendChunkToBlob",
        "GetLogMessage",
        "GetPLCID",
        "GetPLCstatus",
        "GetTraceVariables",
        "MatchMD5", 
        "NewPLC",
        "PurgeBlobs",
        "RemoteExec",
        "RepairPLC",
        "ResetLogCount",
        "SeedBlob",
        "SetTraceVariablesList",
        "StartPLC",
        "StopPLC"
    ]
})):
    def __init__(self, plc_object_instance):
        self.plc_object_instance = plc_object_instance
    

class PyroServer(object):
    def __init__(self, servicename, ip_addr, port):
        self.continueloop = True
        self.daemon = None
        self.servicename = servicename
        self.ip_addr = ip_addr
        self.port = port
        self.servicepublisher = None
        self.piper, self.pipew = None, None

    def _to_be_published(self):
        return self.servicename is not None and \
               self.ip_addr not in ["", "localhost", "127.0.0.1"]

    def PrintServerInfo(self):
        print(_("Pyro port :"), self.port)

        if self._to_be_published():
            print(_("Publishing service on local network"))

        sys.stdout.flush()

    def PyroLoop(self, when_ready):
        if self._to_be_published():
            self.Publish()

        while self.continueloop:
            self.daemon = Pyro5.server.Daemon(host=self.ip_addr, port=self.port)

            self.daemon.register(PLCObjectPyroAdapter(runtime.GetPLCObjectSingleton()), "PLCObject")

            when_ready()

            self.daemon.requestLoop()

        self.Unpublish()

    def Restart(self):
        self.daemon.shutdown(True)

    def Quit(self):
        self.continueloop = False
        self.daemon.shutdown()
        if not sys.platform.startswith('win'):
            if self.pipew is not None:
                os.write(self.pipew, "goodbye")

    def Publish(self):
        self.servicepublisher = ServicePublisher("PYRO")
        self.servicepublisher.RegisterService(self.servicename,
                                              self.ip_addr, self.port)

    def Unpublish(self):
        if self.servicepublisher is not None:
            self.servicepublisher.UnRegisterService()
            self.servicepublisher = None
