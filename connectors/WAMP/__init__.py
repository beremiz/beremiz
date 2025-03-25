#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


import sys
import os
import traceback
from functools import partial
from threading import Thread, Event

from twisted.internet import reactor, threads
from twisted.internet._sslverify import OpenSSLCertificateAuthorities
from twisted.internet.ssl import PrivateCertificate, optionsForClientTLS, VerificationError
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types, auth
from autobahn.wamp.exception import TransportLost
from autobahn.wamp.serializer import MsgPackSerializer
from OpenSSL import crypto

from ProjectController import ToDoBeforeQuit
from connectors.ConnectorBase import ConnectorBase
import PSKManagement as PSK
import CertManagement as Cert

_WampSession = None
_WampConnection = None
_WampConnectEvent = Event()
_WampError = ""


AUTH_NONE = "None"
AUTH_PSK =  "PSK"
AUTH_CLIENTCERT = "ClientCertificate"
AUTHENTICATION_TYPES = [AUTH_NONE, AUTH_PSK, AUTH_CLIENTCERT]
SSL_AUTHENTICATION_TYPES = [AUTH_CLIENTCERT]

class WampSession(wamp.ApplicationSession):
    def onConnect(self):
        auth = self.config.extra["authentication"]
        if auth == AUTH_NONE:
            accepted_method = "anonymous"
            authID = None
        else:
            authID = self.config.extra["IDE_ID"]
            if auth == AUTH_PSK:
                accepted_method = "wampcra"
            elif auth in SSL_AUTHENTICATION_TYPES:
                accepted_method = "tls"
            else:
                log = self.config.extra["log"]
                log.write_error("WAMP Invalid authentication: %s\n"%auth)
                return

        self.join(self.config.realm,
                  authmethods=[accepted_method],
                  authid=authID)

    def onChallenge(self, challenge):
        if challenge.method == "wampcra":
            secret = self.config.extra["secret"]
            if 'salt' in challenge.extra:
                # salted secret
                key = auth.derive_key(secret,
                                      challenge.extra['salt'],
                                      challenge.extra['iterations'],
                                      challenge.extra['keylen'])
            else:
                # plain, unsalted secret
                key = secret

            signature = auth.compute_wcs(key, challenge.extra['challenge'])
            return signature
        else:
            log = self.config.extra["log"]
            log.write_error("Invalid authmethod {}\n".format(challenge.method))

    def onJoin(self, details):
        global _WampSession, _WampConnectEvent
        _WampSession = self
        _WampConnectEvent.set()
        log = self.config.extra["log"]
        log.write('WAMP session joined for: %s\n'%self.config.extra["IDE_ID"])

    def onLeave(self, details):
        global _WampSession, _WampError, _WampConnectEvent
        _WampSession = None
        if details.reason == "wamp.close.normal":
            _WampError = "Closed normally"
        elif details.reason == "wamp.error.not_authorized":
            _WampError = "WAMP authentication failed. Check IDE identity in security manager."
        else:
            _WampError = "WAMP closed with error {}: {}".format(details.reason, details.message)
            # this case can go silent if connection was already established, so log it additionally.
            log = self.config.extra["log"]
            log.write_error(_WampError+"\n")
        _WampConnectEvent.set()


class ComplainingWampWebSocketClientFactory(WampWebSocketClientFactory):

    def clientConnectionLost(self, connector, reason):
        global _WampError, _WampConnectEvent, _WampSession

        if not reason.check(VerificationError):
            # Verification failed
            _WampError = "WAMP TLS certificate verification failed. "+\
                         "Provide valid certicate in identity manager."
        else:
            _WampError = "WAMP connection lost: "+reason.getErrorMessage()
        
        _WampSession = None
        _WampConnectEvent.set()

    clientConnectionFailed = clientConnectionLost

def _WAMP_connector_factory(cls, uri, confnodesroot):
    """
    WAMP://127.0.0.1:12345/path#realm#PLC_ID
    WAMPS://127.0.0.1:12345/path#realm#PLC_ID
    WAMP-CRT://127.0.0.1:12345/path#realm#PLC_ID
    """
    scheme, location = uri.split("://")
    urlpath, realm, PLC_ID = location.split('#')
    urlprefix                  , ssl_auth, use_secret, use_ssl, verify, auth            = {
        "WAMP":          ("ws" , 0       , 1         , 0      , 0     , AUTH_PSK        ),
        "WAMP-ANNON":    ("ws" , 0       , 0         , 0      , 0     , AUTH_NONE       ),
        "WAMPS":         ("wss", 0       , 1         , 1      , 1     , AUTH_PSK        ),
        "WAMPS-ANNON":   ("wss", 0       , 0         , 1      , 1     , AUTH_NONE       ),
        "WAMPS-INSECURE":("wss", 0       , 0         , 1      , 0     , AUTH_NONE       ),
        "WAMPS-NOVERIFY":("wss", 0       , 1         , 1      , 0     , AUTH_PSK        ),
        "WAMPS-CRT":     ("wss", 1       , 0         , 1      , 1     , AUTH_CLIENTCERT ),
        }[scheme]
    url = urlprefix+"://"+urlpath
    CN = urlpath.split("/")[0].split(":")[0]
    try:
        IDE_ID, secret = PSK.GetIDEIdentity()
        if use_ssl:
            trust_store = Cert.GetCertPath(CN)
            if ssl_auth:
                client_cert_file = Cert.GetClientCert()

    except Exception as e:
        confnodesroot.logger.write_error(
            _("Connection to {loc} failed with exception {ex}\n").format(
                loc=uri, ex=str(e)))
        return None

    def RegisterWampClient():

        # start logging to console
        # log.startLogging(sys.stdout)

        extraconf={
            "IDE_ID": IDE_ID,
            "authentication": auth,
            "log": confnodesroot.logger
        }
        if use_secret:
            extraconf["secret"] = secret
        # create a WAMP application session factory
        session_factory = wamp.ApplicationSessionFactory(
            config=types.ComponentConfig(
                realm=str(realm),
                extra=extraconf))
        session_factory.session = cls

        # create a WAMP-over-WebSocket transport client factory
        transport_factory = ComplainingWampWebSocketClientFactory(
            session_factory,
            url=url,
            serializers=[MsgPackSerializer()])

        contextFactory=None
        if transport_factory.isSecure:

            client_cert=None
            trustRoot=None
            if ssl_auth:
                if os.path.exists(client_cert_file):
                    client_cert = PrivateCertificate.loadPEM(open(client_cert_file, 'rb').read())
                else:
                    confnodesroot.logger.write_error(
                        _("WAMP client certificate not provided for: {loc}\n").format(loc=uri))
                    return
            if verify:
                if os.path.exists(trust_store):
                    cert = crypto.load_certificate(crypto.FILETYPE_PEM,
                        open(trust_store, 'rb').read())
                    trustRoot = OpenSSLCertificateAuthorities([cert])
            if verify or ssl_auth:
                contextFactory=optionsForClientTLS(transport_factory.host,
                                                   trustRoot=trustRoot,
                                                   clientCertificate=client_cert)

        # start the client from a Twisted endpoint
        conn = connectWS(transport_factory, contextFactory)
        confnodesroot.logger.write(_("WAMP connecting to URL : %s\n") % url)
        return conn


    def ThreadProc():
        global _WampConnection
        _WampConnection = RegisterWampClient()
        ToDoBeforeQuit.append(reactor.stop)
        reactor.run(installSignalHandlers=False)

    global _WampConnection, _WampSession, _WampConnectEvent, _WampError
    _WampConnectEvent.clear()
    if not reactor.running:
        Thread(target=ThreadProc).start()
    else:
        _WampConnection = threads.blockingCallFromThread(
            reactor, RegisterWampClient)
    if not _WampConnectEvent.wait(4):
        confnodesroot.logger.write_error("WAMP connection timeout\n")
        try:
            threads.blockingCallFromThread(
                reactor, _WampConnection.stopConnecting)
        except:
            pass
        return None
    else:
        if _WampSession is None:
            confnodesroot.logger.write_error(f"WAMP connection failed: {_WampError}\n")
            return None


    class WampPLCObjectProxy(ConnectorBase):

        def __del__(self):
            _WampConnection.disconnect()
            #
            # reactor.stop()

        def WampSessionProcMapper(self, funcname):
            wampfuncname = '.'.join((PLC_ID, funcname))

            def catcher_func(*args, **kwargs):
                if _WampSession is not None:
                    try:
                        return threads.blockingCallFromThread(
                            reactor, _WampSession.call, wampfuncname,
                            *args, **kwargs)
                    except TransportLost:
                        confnodesroot.logger.write_error(_("Connection lost!\n"))
                        confnodesroot._SetConnector(None)
                    except Exception:
                        errmess = traceback.format_exc()
                        confnodesroot.logger.write_error(errmess+"\n")
                        print(errmess)
                        # confnodesroot._SetConnector(None)
                return self.PLCObjDefaults.get(funcname)
            return catcher_func

        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                member = self.WampSessionProcMapper(attrName)
                self.__dict__[attrName] = member
            return member

    # TODO : GetPLCID()
    # TODO : PSK.UpdateID()

    return WampPLCObjectProxy()


WAMP_connector_factory = partial(_WAMP_connector_factory, WampSession)
