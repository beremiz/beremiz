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

import runtime.NevowServer as NS

from formless import annotate

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

lastKnownConfig = None

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
            if "secret" in self.config.extra:
                secret = self.config.extra["secret"].encode('utf8')
                signature = auth.compute_wcs(secret, challenge.extra['challenge'].encode('utf8'))
                return signature.decode("ascii")
            else:
                raise Exception("no secret given for authentication")
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


def CheckConfiguration(WSClientConf):
    url = WSClientConf["url"]
    if not IsCorrectUri(url):
        raise annotate.ValidateError(
            {"url":"Invalid URL: {}".format(url)},
            _("WAMP confiuration error:"))

def GetConfiguration():
    global lastKnownConfig

    WSClientConf = json.load(open(_WampConf))
    for itemName in mandatoryConfigItems:
        if WSClientConf.get(itemName, None) is None :
            raise Exception(_("WAMP configuration error : missing '{}' parameter.").format(itemName))

    CheckConfiguration(WSClientConf)

    lastKnownConfig = WSClientConf.copy()
    return WSClientConf


def SetConfiguration(WSClientConf):
    global lastKnownConfig

    CheckConfiguration(WSClientConf)

    lastKnownConfig = WSClientConf.copy()
    
    with open(os.path.realpath(_WampConf), 'w') as f:
        json.dump(WSClientConf, f, sort_keys=True, indent=4)
    if 'active' in WSClientConf and WSClientConf['active']:
        if _transportFactory and _WampSession:
            StopReconnectWampClient()
        StartReconnectWampClient()
    else:
        StopReconnectWampClient()

    return WSClientConf


def LoadWampSecret(secretfname):
    WSClientWampSecret = open(secretfname, 'rb').read()
    if len(WSClientWampSecret) == 0 :
        raise Exception(_("WAMP secret empty"))
    return WSClientWampSecret


def IsCorrectUri(uri):
    return re.match(r'wss?://[^\s?:#-]+(:[0-9]+)?(/[^\s]*)?$', uri) is not None


def RegisterWampClient(wampconf=None, wampsecret=None):
    global _WampConf, _WampSecret
    if wampsecret:
        _WampSecret = wampsecret
    if wampconf:
        _WampConf = wampconf

    WSClientConf = GetConfiguration()

    if not WSClientConf["active"]:
        print(_("WAMP deactivated in configuration"))
        return

    if _WampSecret is not None:
        WSClientConf["secret"] = LoadWampSecret(_WampSecret)

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
    if _transportFactory is not None :
        _transportFactory.stopTrying()
    if _WampSession is not None :
        _WampSession.leave()


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

def getWampStatus():
    if _transportFactory is not None :
        if _WampSession is not None :
            if _WampSession.is_attached() :
                return "Attached"
            return "Established"
        return "Connecting"
    return "Disconnected"


def SetServer(pysrv):
    _PySrv = pysrv


#### WEB CONFIGURATION INTERFACE ####

webExposedConfigItems = ['active', 'url', 'ID']

def wampConfigDefault(ctx,argument):
    if lastKnownConfig is not None :
        return lastKnownConfig.get(argument.name, None)

def wampConfig(**kwargs):
    newConfig = lastKnownConfig.copy()
    for argname in webExposedConfigItems:
        newConfig[argname] = kwargs[argname]

    SetConfiguration(newConfig)

webFormInterface = [
    ("status",
       annotate.String(label=_("Current status"),
                       immutable = True,
                       default = lambda *k:getWampStatus())),
    ("ID",
       annotate.String(label=_("ID"),
                       default = wampConfigDefault)),
    ("active",
       annotate.Boolean(label=_("Enable WAMP connection"),
                        default=wampConfigDefault)),
    ("url",
       annotate.String(label=_("WAMP Server URL"),
                       default=wampConfigDefault))]


NS.ConfigurableSettings.addExtension(
    "wamp", 
    _("Wamp Settings"),
    webFormInterface,
    _("Set"),
    wampConfig)
