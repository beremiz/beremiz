#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Written by Edouard TISSERANT (C) 2024
# This file is part of Beremiz runtime
# See COPYING.Runtime file for copyrights details.

import sys
import traceback
from inspect import getmembers, isfunction

import erpc

# eRPC service code
from erpc_interface.erpc_PLCObject.common import PSKID, PLCstatus, TraceVariables, trace_sample, PLCstatus_enum, log_message
from erpc_interface.erpc_PLCObject.interface import IBeremizPLCObjectService
from erpc_interface.erpc_PLCObject.server import BeremizPLCObjectServiceService

from runtime import GetPLCObjectSingleton as PLC
from runtime.loglevels import LogLevelsDict
from runtime.ServicePublisher import ServicePublisher


CRITICAL_LOG_LEVEL = LogLevelsDict["CRITICAL"]

def ReturnAsLastOutput(method, args_wrapper, *args):
    args[-1].value = method(*args_wrapper(*args[:-1]))
    return 0

def TranslatedReturnAsLastOutput(translator):
    def wrapper(method, args_wrapper, *args):
        args[-1].value = translator(method(*args_wrapper(*args[:-1])))
        return 0
    return wrapper
    
    
ReturnWrappers = {
    "AppendChunkToBlob":ReturnAsLastOutput,
    "GetLogMessage":TranslatedReturnAsLastOutput(
        lambda res:log_message(*res)),
    "GetPLCID":TranslatedReturnAsLastOutput(
        lambda res:PSKID(*res)),
    "GetPLCstatus":TranslatedReturnAsLastOutput(
        lambda res:PLCstatus(getattr(PLCstatus_enum, res[0]),res[1])),
    "GetTraceVariables":TranslatedReturnAsLastOutput(
        lambda res:TraceVariables(getattr(PLCstatus_enum, res[0]),[trace_sample(*sample) for sample in res[1]])),
    "MatchMD5":ReturnAsLastOutput,
    "NewPLC":ReturnAsLastOutput,
    "SeedBlob":ReturnAsLastOutput,
    "SetTraceVariablesList": ReturnAsLastOutput,
    "StopPLC":ReturnAsLastOutput,
}

ArgsWrappers = {
    "AppendChunkToBlob":
        lambda data, blobID:(data, bytes(blobID)),
    "NewPLC":
        lambda md5sum, plcObjectBlobID, extrafiles: (
            md5sum, bytes(plcObjectBlobID), [(f.fname, bytes(f.blobID)) for f in extrafiles]),
    "SetTraceVariablesList": 
        lambda orders : ([(order.idx, None if len(order.force)==0 else bytes(order.force)) for order in orders],)
}

def rpc_wrapper(method_name):
    PLCobj = PLC()
    method=getattr(PLCobj, method_name)
    args_wrapper = ArgsWrappers.get(method_name, lambda *x:x)
    return_wrapper = ReturnWrappers.get(method_name,
        lambda method, args_wrapper, *args: method(*args_wrapper(*args)))

    def exception_wrapper(self, *args):
        try:
            print("Srv "+method_name)
            return_wrapper(method, args_wrapper, *args)
            return 0
        except Exception as e:
            print(traceback.format_exc())
            PLCobj.LogMessage(CRITICAL_LOG_LEVEL, f'eRPC call {method_name} Exception "{str(e)}"')
            raise
        
    return exception_wrapper


class eRPCServer(object):
    def __init__(self, servicename, ip_addr, port):
        self.continueloop = True
        self.server = None
        self.transport = None
        self.servicename = servicename
        self.ip_addr = ip_addr
        self.port = port
        self.servicepublisher = None

    def _to_be_published(self):
        return self.servicename is not None and \
               self.ip_addr not in ["", "localhost", "127.0.0.1"]

    def PrintServerInfo(self):
        print(_("eRPC port :"), self.port)

        if self._to_be_published():
            print(_("Publishing service on local network"))

        if sys.stdout:
            sys.stdout.flush()

    def Loop(self, when_ready):
        if self._to_be_published():
            self.Publish()

        while self.continueloop:

            # service handler calls PLC object though erpc_stubs's wrappers
            handler = type(
                "PLCObjectServiceHandlder", 
                (IBeremizPLCObjectService,),
                {name: rpc_wrapper(name)              
                        for name,_func in getmembers(IBeremizPLCObjectService, isfunction)})()
            
            service = BeremizPLCObjectServiceService(handler)

            # TODO initialize Serial transport layer if selected
            # transport = erpc.transport.SerialTransport(device, baudrate)

            # initialize TCP transport layer
            self.transport = erpc.transport.TCPTransport(self.ip_addr, int(self.port), True)

            self.server = erpc.simple_server.SimpleServer(self.transport, erpc.basic_codec.BasicCodec)
            self.server.add_service(service)

            when_ready()

            self.server.run()

        self.Unpublish()

    def Restart(self):
        self.server.stop()
        self.transport.stop()

    def Quit(self):
        self.continueloop = False
        self.server.stop()
        self.transport.stop()

    def Publish(self):
        self.servicepublisher = ServicePublisher("ERPC")
        self.servicepublisher.RegisterService(self.servicename,
                                              self.ip_addr, self.port)

    def Unpublish(self):
        if self.servicepublisher is not None:
            self.servicepublisher.UnRegisterService()
            self.servicepublisher = None
