#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING.Runtime file for copyrights details.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


from __future__ import absolute_import
from __future__ import print_function
import time
import json
import os
import inspect
import re
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types, auth
from autobahn.wamp.serializer import MsgPackSerializer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ReconnectingClientFactory


_transportFactory = None
_WampSession = None
_PySrv = None
_WampConf = None
_WampSecret = None

ExposedCalls = [
    ("StartPLC", {}),
    ("StopPLC", {}),
    ("ForceReload", {}),
    ("GetPLCstatus", {}),
    ("NewPLC", {}),
    ("MatchMD5", {}),
    ("SetTraceVariablesList", {}),
    ("GetTraceVariables", {}),
    ("RemoteExec", {}),
    ("GetLogMessage", {}),
    ("ResetLogCount", {})
]

# Those two lists are meant to be filled by customized runtime
# or User python code.

""" crossbar Events to register to """
SubscribedEvents = []

""" things to do on join (callables) """
DoOnJoin = []


def GetCallee(name):
    """ Get Callee or Subscriber corresponding to '.' spearated object path """
    names = name.split('.')
    obj = _PySrv.plcobj
    while names:
        obj = getattr(obj, names.pop(0))
    return obj

def getValidOptins(options, arguments):
    validOptions = {}
    for key in options:
        if key in arguments:
            validOptions[key] = options[key]
    if len(validOptions) > 0:
        return validOptions
    else:
        return None

class WampSession(wamp.ApplicationSession):
    def onConnect(self):
        if "secret" in self.config.extra:
            user = self.config.extra["ID"]
            self.join(u"Automation", [u"wampcra"], user)
        else:
            self.join(u"Automation")

    def onChallenge(self, challenge):
        if challenge.method == u"wampcra":
            secret = self.config.extra["secret"].encode('utf8')
            signature = auth.compute_wcs(secret, challenge.extra['challenge'].encode('utf8'))
            return signature.decode("ascii")
        else:
            raise Exception("don't know how to handle authmethod {}".format(challenge.method))

    @inlineCallbacks
    def onJoin(self, details):
        global _WampSession
        _WampSession = self
        ID = self.config.extra["ID"]

        for name, kwargs in ExposedCalls:
            try:
                registerOptions = types.RegisterOptions(**kwargs)
            except TypeError as e:
                registerOptions = None
                print(_("TypeError register option: {}".format(e)))

            yield self.register(GetCallee(name), u'.'.join((ID, name)), registerOptions)

        for name in SubscribedEvents:
            yield self.subscribe(GetCallee(name), unicode(name))

        for func in DoOnJoin:
            yield func(self)

        print(_('WAMP session joined (%s) by:' % time.ctime()), ID)

    def onLeave(self, details):
        global _WampSession, _transportFactory
        super(WampSession, self).onLeave(details)
        _WampSession = None
        _transportFactory = None
        print(_('WAMP session left'))


class ReconnectingWampWebSocketClientFactory(WampWebSocketClientFactory, ReconnectingClientFactory):
    def __init__(self, config, *args, **kwargs):
        global _transportFactory
        WampWebSocketClientFactory.__init__(self, *args, **kwargs)

        protocolOptions = config.extra.get('protocolOptions', None)
        if protocolOptions:
            arguments = inspect.getargspec(self.setProtocolOptions).args
            validProtocolOptions = getValidOptins(protocolOptions, arguments)
            if validProtocolOptions:
                self.setProtocolOptions(**validProtocolOptions)
                #print(_("Added custom protocol options"))
        _transportFactory = self

    def buildProtocol(self, addr):
        self.resetDelay()
        return ReconnectingClientFactory.buildProtocol(self, addr)

    def clientConnectionFailed(self, connector, reason):
        if self.continueTrying:
            print(_("WAMP Client connection failed (%s) .. retrying .." % time.ctime()))
            super(ReconnectingWampWebSocketClientFactory, self).clientConnectionFailed(connector, reason)
        else:
            del connector

    def clientConnectionLost(self, connector, reason):
        if self.continueTrying:
            print(_("WAMP Client connection lost (%s) .. retrying .." % time.ctime()))
            super(ReconnectingWampWebSocketClientFactory, self).clientConnectionFailed(connector, reason)
        else:
            del connector


def GetConfiguration(items=None):
    try:
        WSClientConf = json.load(open(_WampConf))
        if items and isinstance(items, list):
            WSClientConfItems = {}
            for item in items:
                wampconf_value = WSClientConf.get(item, None)
                if wampconf_value is not None:
                    WSClientConfItems[item] = wampconf_value
            if WSClientConfItems:
                return WSClientConfItems
        return WSClientConf
    except ValueError, ve:
        print(_("WAMP load error: "), ve)
        return None
    except Exception, e:
        print(_("WAMP load error: "), e)
        return None

def SetConfiguration(items):
    try:
        WSClientConf = json.load(open(_WampConf))
        saveChanges = False
        if items:
            for itemKey in items.keys():
                wampconf_value = WSClientConf.get(itemKey, None)
                if (wampconf_value is not None) and (items[itemKey] is not None) and (wampconf_value != items[itemKey]):
                    WSClientConf[itemKey] = items[itemKey]
                    saveChanges = True

        if saveChanges:
            with open(os.path.realpath(_WampConf), 'w') as f:
                json.dump(WSClientConf, f, sort_keys=True, indent=4)
            if 'active' in WSClientConf and WSClientConf['active']:
                StartReconnectWampClient()
            else:
                StopReconnectWampClient()

        return WSClientConf
    except ValueError, ve:
        print(_("WAMP save error: "), ve)
        return None
    except Exception, e:
        print(_("WAMP save error: "), e)
        return None

def LoadWampSecret(secretfname):
    try:
        WSClientWampSecret = open(secretfname, 'rb').read()
        return WSClientWampSecret
    except ValueError, ve:
        print(_("Wamp secret load error:"), ve)
        return None
    except Exception:
        return None


def IsCorrectUri(uri):
    if re.match(r'w{1}s{1,2}:{1}/{2}.+:{1}[0-9]+/{1}.+', uri):
        return True
    else:
        return False


def RegisterWampClient(wampconf=None, secretfname=None):
    global _WampConf
    if wampconf:
        _WampConf = wampconf
        WSClientConf = GetConfiguration()
    else:
        WSClientConf = GetConfiguration()

    if not WSClientConf:
        print(_("WAMP client connection not established!"))
        return False

    if not IsCorrectUri(WSClientConf["url"]):
        print(_("WAMP url {} is not correct!".format(WSClientConf["url"])))
        return False

    if secretfname:
        WampSecret = LoadWampSecret(secretfname)
    else:
        WampSecret = LoadWampSecret(_WampSecret)

    if WampSecret is not None:
        WSClientConf["secret"] = WampSecret

    # create a WAMP application session factory
    component_config = types.ComponentConfig(
        realm=WSClientConf["realm"],
        extra=WSClientConf)
    session_factory = wamp.ApplicationSessionFactory(
        config=component_config)
    session_factory.session = WampSession

    # create a WAMP-over-WebSocket transport client factory
    transport_factory = ReconnectingWampWebSocketClientFactory(
        component_config,
        session_factory,
        url=WSClientConf["url"],
        serializers=[MsgPackSerializer()])

    # start the client from a Twisted endpoint
    conn = connectWS(transport_factory)
    print(_("WAMP client connecting to :"), WSClientConf["url"])
    return True


def StopReconnectWampClient():
    _transportFactory.stopTrying()
    return _WampSession.leave()


def StartReconnectWampClient():
    if _WampSession:
        # do reconnect
        _WampSession.disconnect()
        return True
    else:
        # do connect
        RegisterWampClient()
        return True


def GetSession():
    return _WampSession


def StatusWampClient():
    return _WampSession and _WampSession.is_attached()


def SetServer(pysrv, wampconf=None, wampsecret=None):
    global _PySrv, _WampConf, _WampSecret
    _PySrv = pysrv
    _WampConf = wampconf
    _WampSecret = wampsecret
