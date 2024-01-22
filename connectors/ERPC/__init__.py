#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Written by Edouard TISSERANT (C) 2024
# This file is part of Beremiz IDE
# See COPYING file for copyrights details.


import os.path
import re
import traceback
from inspect import getmembers, isfunction


import erpc

# eRPC service code
from erpc_interface.erpc_PLCObject.interface import IBeremizPLCObjectService
from erpc_interface.erpc_PLCObject.client import BeremizPLCObjectServiceClient
from erpc_interface.erpc_PLCObject.common import trace_order, extra_file, PLCstatus_enum

import PSKManagement as PSK
from connectors.ERPC.PSK_Adapter import SSLPSKClientTransport
from connectors.ConnectorBase import ConnectorBase

enum_to_PLCstatus = dict(map(lambda t:(t[1],t[0]),getmembers(PLCstatus_enum, lambda x:type(x)==int)))

class MissingCallException(Exception):
    pass

def ExceptionFromERPCReturn(ret):
    return {1:Exception,
            2:MissingCallException}.get(ret,ValueError)

def ReturnAsLastOutput(client_method, obj, args_wrapper, *args):
    retval = erpc.Reference()
    ret = client_method(obj, *args_wrapper(*args), retval)
    if ret != 0:
        raise ExceptionFromERPCReturn(ret)(client_method.__name__)
    return retval.value

def TranslatedReturnAsLastOutput(translator):
    def wrapper(client_method, obj, args_wrapper, *args):
        res = ReturnAsLastOutput(client_method, obj, args_wrapper, *args)
        return translator(res)
    return wrapper

ReturnWrappers = {
    "AppendChunkToBlob":ReturnAsLastOutput,
    "GetLogMessage":TranslatedReturnAsLastOutput(
        lambda res:(res.msg, res.tick, res.sec, res.nsec)),
    "GetPLCID":TranslatedReturnAsLastOutput(
        lambda res:(res.ID, res.PSK)),
    "GetPLCstatus":TranslatedReturnAsLastOutput(
        lambda res:(enum_to_PLCstatus[res.PLCstatus], res.logcounts)),
    "GetTraceVariables":TranslatedReturnAsLastOutput(
        lambda res:(enum_to_PLCstatus[res.PLCstatus],
                    [(sample.tick, bytes(sample.TraceBuffer)) for sample in res.traces])),
    "MatchMD5":ReturnAsLastOutput,
    "NewPLC":ReturnAsLastOutput,
    "SeedBlob":ReturnAsLastOutput,
    "SetTraceVariablesList": ReturnAsLastOutput,
    "StopPLC":ReturnAsLastOutput,
}

ArgsWrappers = {
    "NewPLC":
        lambda md5sum, plcObjectBlobID, extrafiles: (
            md5sum, plcObjectBlobID, [extra_file(*f) for f in extrafiles]),
    "SetTraceVariablesList":
        lambda orders : ([
            trace_order(idx, b"" if force is None else force) 
            for idx, force in orders],)
}

def ERPC_connector_factory(uri, confnodesroot):
    """
    returns the ERPC connector
    """
    confnodesroot.logger.write(_("ERPC connecting to URI : %s\n") % uri)

    # TODO add parsing for serial URI
    # ERPC:///dev/ttyXX:baudrate or ERPC://:COM4:baudrate

    try:
        _scheme, location = uri.split("://",1)
        locator, *IDhash = location.split('#',1)
        x = re.match(r'(?P<host>[^\s:]+):?(?P<port>\d+)?', locator)
        host = x.group('host')
        port = x.group('port')
        if port:
            port = int(port)
        else:
            port = 3000
    except Exception as e:
        confnodesroot.logger.write_error(
            'Malformed URI "%s": %s\n' % (uri, str(e)))
        return None

    def rpc_wrapper(method_name):
        client_method = getattr(BeremizPLCObjectServiceClient, method_name)
        return_wrapper = ReturnWrappers.get(
            method_name, 
            lambda client_method, obj, args_wrapper, *args: client_method(obj, *args_wrapper(*args)))
        args_wrapper = ArgsWrappers.get(method_name, lambda *x:x)

        def exception_wrapper(self, *args):
            try:
                print("Clt "+method_name)
                return return_wrapper(client_method, self, args_wrapper, *args)
            except erpc.transport.ConnectionClosed as e:
                confnodesroot._SetConnector(None)
                confnodesroot.logger.write_error(_("Connection lost!\n"))
            except erpc.codec.CodecError as e:
                confnodesroot.logger.write_warning(_("ERPC codec error: %s\n") % e)
            except erpc.client.RequestError as e:
                confnodesroot.logger.write_error(_("ERPC request error: %s\n") % e)                
            except MissingCallException as e:
                confnodesroot.logger.write_warning(_("Remote call not supported: %s\n") % e.message)
            except Exception as e:
                errmess = _("Exception calling remote PLC object fucntio %s:\n") % method_name \
                          + traceback.format_exc()
                confnodesroot.logger.write_error(errmess + "\n")
                print(errmess)
                confnodesroot._SetConnector(None)

            return self.PLCObjDefaults.get(method_name)
        return exception_wrapper


    PLCObjectERPCProxy = type(
        "PLCObjectERPCProxy",
        (ConnectorBase, BeremizPLCObjectServiceClient),
        {name: rpc_wrapper(name)
            for name,_func in getmembers(IBeremizPLCObjectService, isfunction)})

    try:
        if IDhash:
            ID = IDhash[0]
            # load PSK from project
            secpath = os.path.join(str(confnodesroot.ProjectPath), 'psk', ID + '.secret')
            if not os.path.exists(secpath):
                confnodesroot.logger.write_error(
                    'Error: Pre-Shared-Key Secret in %s is missing!\n' % secpath)
                return None
            secret = open(secpath).read().partition(':')[2].rstrip('\n\r')
            transport = SSLPSKClientTransport(host, port, (secret, ID))
        else:
            # TODO if serial URI then 
            # transport = erpc.transport.SerialTransport(device, baudrate)

            transport = erpc.transport.TCPTransport(host, port, False)

        clientManager = erpc.client.ClientManager(transport, erpc.basic_codec.BasicCodec)
        client = PLCObjectERPCProxy(clientManager)

    except Exception as e:
        confnodesroot.logger.write_error(
            _("Connection to {loc} failed with exception {ex}\n").format(
                loc=locator, ex=str(e)))
        return None

    # Check connection is effective.
    IDPSK = client.GetPLCID()
    if IDPSK:
        ID, secret = IDPSK
        PSK.UpdateID(confnodesroot.ProjectPath, ID, secret, uri)
    else:
        confnodesroot.logger.write_warning(_("PLC did not provide identity and security infomation.\n"))

    return client
