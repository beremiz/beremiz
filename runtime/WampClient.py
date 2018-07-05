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
import re
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types, auth
from autobahn.wamp.serializer import MsgPackSerializer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ReconnectingClientFactory


mandatoryConfigItems = ["ID", "active", "realm", "url"]

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

        try:
            protocolOptions = config.extra.get('protocolOptions', None)
            if protocolOptions:
                self.setProtocolOptions(**protocolOptions)
            _transportFactory = self
        except Exception, e:
            print(_("Custom protocol options failed :"), e)
            _transportFactory = None

    def buildProtocol(self, addr):
        self.resetDelay()
        return ReconnectingClientFactory.buildProtocol(self, addr)

    def clientConnectionFailed(self, connector, reason):
        if self.continueTrying:
            print(_("WAMP Client connection failed (%s) .. retrying ..") % time.ctime())
            super(ReconnectingWampWebSocketClientFactory, self).clientConnectionFailed(connector, reason)
        else:
            del connector

    def clientConnectionLost(self, connector, reason):
        if self.continueTrying:
            print(_("WAMP Client connection lost (%s) .. retrying ..") % time.ctime())
            super(ReconnectingWampWebSocketClientFactory, self).clientConnectionFailed(connector, reason)
        else:
            del connector


def GetConfiguration():
    WSClientConf = json.load(open(_WampConf))
    for itemName in mandatoryConfigItems:
        if WSClientConf.get(itemName, None) is None :
            raise Exception(_("WAMP configuration error : missing '{}' parameter.").format(itemName))

    return WSClientConf


def SetConfiguration(WSClientConf):
    try:
        with open(os.path.realpath(_WampConf), 'w') as f:
            json.dump(WSClientConf, f, sort_keys=True, indent=4)
        if 'active' in WSClientConf and WSClientConf['active']:
            if _transportFactory and _WampSession:
                StopReconnectWampClient()
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


def RegisterWampClient(wampconf=None, wampsecret=None):
    global _WampConf, _WampSecret
    if wampsecret:
        _WampSecret = wampsecret
    if wampconf:
        _WampConf = wampconf

    WSClientConf = GetConfiguration()

    if not IsCorrectUri(WSClientConf["url"]):
        raise Exception(_("WAMP url {} is not correct!").format(WSClientConf["url"]))

    if not WSClientConf["active"]:
        print(_("WAMP deactivated in configuration"))
        return

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
    ReconnectingWampWebSocketClientFactory(
        component_config,
        session_factory,
        url=WSClientConf["url"],
        serializers=[MsgPackSerializer()])

    # start the client from a Twisted endpoint
    if _transportFactory:
        conn = connectWS(_transportFactory)
        print(_("WAMP client connecting to :"), WSClientConf["url"])
        return True
    else:
        print(_("WAMP client can not connect to :"), WSClientConf["url"])
        return False


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


def SetServer(pysrv):
    _PySrv = pysrv
