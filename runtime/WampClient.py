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
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types, auth
from autobahn.wamp.serializer import MsgPackSerializer
from twisted.internet.defer import inlineCallbacks
from twisted.internet.protocol import ReconnectingClientFactory


_WampSession = None
_PySrv = None

ExposedCalls = [
    "StartPLC",
    "StopPLC",
    "ForceReload",
    "GetPLCstatus",
    "NewPLC",
    "MatchMD5",
    "SetTraceVariablesList",
    "GetTraceVariables",
    "RemoteExec",
    "GetLogMessage",
    "ResetLogCount",
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
            user = self.config.extra["ID"].encode('utf8')
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
        print('WAMP session joined by :', ID)
        for name in ExposedCalls:
            regoption = types.RegisterOptions(u'exact', u'last')
            yield self.register(GetCallee(name), u'.'.join((ID, name)), regoption)

        for name in SubscribedEvents:
            yield self.subscribe(GetCallee(name), unicode(name))

        for func in DoOnJoin:
            yield func(self)

    def onLeave(self, details):
        global _WampSession
        _WampSession = None
        print(_('WAMP session left'))


class ReconnectingWampWebSocketClientFactory(WampWebSocketClientFactory, ReconnectingClientFactory):
    def clientConnectionFailed(self, connector, reason):
        print(_("WAMP Client connection failed (%s) .. retrying .." % time.ctime()))
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        print(_("WAMP Client connection lost (%s) .. retrying .." % time.ctime()))
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)


def LoadWampClientConf(wampconf):
    try:
        WSClientConf = json.load(open(wampconf))
        return WSClientConf
    except ValueError, ve:
        print(_("WAMP load error: "), ve)
        return None
    except Exception:
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


def RegisterWampClient(wampconf, secretfname):

    WSClientConf = LoadWampClientConf(wampconf)

    if not WSClientConf:
        print(_("WAMP client connection not established!"))
        return

    WampSecret = LoadWampSecret(secretfname)

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
        session_factory,
        url=WSClientConf["url"],
        serializers=[MsgPackSerializer()])

    # start the client from a Twisted endpoint
    conn = connectWS(transport_factory)
    print(_("WAMP client connecting to :"), WSClientConf["url"])
    return conn


def GetSession():
    return _WampSession


def SetServer(pysrv):
    global _PySrv
    _PySrv = pysrv
