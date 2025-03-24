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


import time
import json
import os
import re
import shutil
from autobahn.twisted import wamp
from autobahn.twisted.websocket import WampWebSocketClientFactory, connectWS
from autobahn.wamp import types, auth
from autobahn.wamp.serializer import MsgPackSerializer
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.python.components import registerAdapter
from twisted.internet.ssl import PrivateCertificate, optionsForClientTLS, VerificationError
from twisted.internet._sslverify import OpenSSLCertificateAuthorities
from OpenSSL import crypto

from formless import annotate, webform
import formless
from nevow import tags, url, static
from runtime import GetPLCObjectSingleton
from runtime.Stunnel import getPSKID
from runtime.loglevels import LogLevelsDict

mandatoryConfigItems = ["ID", "active", "realm", "url"]


AUTH_NONE = "None"
AUTH_PSK =  "PSK"
AUTH_CLIENTCERT = "ClientCertificate"
AUTHENTICATION_TYPES = [AUTH_NONE, AUTH_PSK, AUTH_CLIENTCERT]
SSL_AUTHENTICATION_TYPES = [AUTH_CLIENTCERT]

_transportFactory = None
_WampSession = None
WorkingDir = None

# Find pre-existing project WAMP config file
_WampConf = None
_WampSercretFile = None
_WampSecret = None
_WampTrust = None
_WampClientCert = None

ExposedCalls = [
    ("StartPLC", {}),
    ("StopPLC", {}),
    ("GetPLCstatus", {}),
    ("GetPLCID", {}),
    ("SeedBlob", {}),
    ("AppendChunkToBlob", {}),
    ("PurgeBlobs", {}),
    ("NewPLC", {}),
    ("RepairPLC", {}),
    ("MatchMD5", {}),
    ("SetTraceVariablesList", {}),
    ("GetTraceVariables", {}),
    ("GetLogMessage", {}),
    ("ResetLogCount", {}),
    ("ExtendedCall", {})
]

# de-activated dumb wamp config
defaultWampConfig = {
    "ID": "wamptest", # replaced by service name (-n in CLI)
    "active": False,
    "realm": "Automation",
    "url": "ws://127.0.0.1:8888",
    "clientFactoryOptions": {
        "maxDelay": 300
    },
    "protocolOptions": {
        "autoPingInterval": 10,
        "autoPingTimeout": 5
    },
    "authentication": "None",
    "verifyHostname": True
}

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
    obj = GetPLCObjectSingleton()
    while names:
        obj = getattr(obj, names.pop(0))
    return obj


class WampSession(wamp.ApplicationSession):

    def onConnect(self):
        auth = self.config.extra["authentication"]
        if auth == AUTH_NONE:
            accepted_method = "anonymous"
            authID = None
        else:
            authID = self.config.extra["ID"]
            if auth == AUTH_PSK:
                accepted_method = "wampcra"
            elif auth in SSL_AUTHENTICATION_TYPES:
                accepted_method = "tls"
            else:
                raise Exception("Invalid authentication: "+auth)

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
            raise Exception("Invalid authmethod {}".format(challenge.method))

    def onJoin(self, details):
        global _WampSession
        GetPLCObjectSingleton().LogMessage(LogLevelsDict["INFO"], 
            'WAMP session joined for: '+self.config.extra["ID"])
        _WampSession = self
        ID = self.config.extra["ID"]

        for name, kwargs in ExposedCalls:
            try:
                registerOptions = types.RegisterOptions(**kwargs)
            except TypeError as e:
                registerOptions = None
                print("TypeError register option: {}".format(e))

            self.register(GetCallee(name), '.'.join((ID, name)), registerOptions)

        for name in SubscribedEvents:
            self.subscribe(GetCallee(name), str(name))

        for func in DoOnJoin:
            func(self)

    def onLeave(self, details):
        global _WampSession, _transportFactory
        GetPLCObjectSingleton().LogMessage(LogLevelsDict["INFO"], 
            'WAMP session left for: {} reason: "{}" message: "{}"'.format(self.config.extra["ID"], details.reason, details.message))
        _WampSession = None
        _transportFactory = None

    def publishWithOwnID(self, eventID, value):
        ID = self.config.extra["ID"]
        self.publish(str(ID+'.'+eventID), value)


class ReconnectingWampWebSocketClientFactory(WampWebSocketClientFactory, ReconnectingClientFactory):

    def __init__(self, config, *args, **kwargs):
        global _transportFactory
        WampWebSocketClientFactory.__init__(self, *args, **kwargs)

        try:
            clientFactoryOptions = config.extra.get("clientFactoryOptions")
            if clientFactoryOptions:
                self.setClientFactoryOptions(clientFactoryOptions)
        except Exception as e:
            print(_("Custom client factory options failed : "), e)
            _transportFactory = None

        try:
            protocolOptions = config.extra.get('protocolOptions', None)
            if protocolOptions:
                self.setProtocolOptions(**protocolOptions)
            _transportFactory = self
        except Exception as e:
            print("Custom protocol options failed :", e)
            _transportFactory = None

    def setClientFactoryOptions(self, options):
        for key, value in list(options.items()):
            if key in ["maxDelay", "initialDelay", "maxRetries", "factor", "jitter"]:
                setattr(self, key, value)

    def buildProtocol(self, addr):
        self.resetDelay()
        return ReconnectingClientFactory.buildProtocol(self, addr)

    def _clientConnectionLostOrFailed(self, connector, reason):
        """ report connection lost """
        if not reason.check(VerificationError):
            # Verification failed
            GetPLCObjectSingleton().LogMessage(LogLevelsDict["WARNING"], 
                "WAMP TLS certificate verification failed: "+\
                reason.getErrorMessage()+
                "\nProvide a certicate on web interface or as wampTrustStore.crt in project files.")
        else:
            GetPLCObjectSingleton().LogMessage(LogLevelsDict["WARNING"], 
                "WAMP connection lost: "+reason.getErrorMessage())
        
    def clientConnectionFailed(self, connector, reason):
        print("WAMP Client connection failed (%s) .. retrying .." %
              time.ctime())
        super(ReconnectingWampWebSocketClientFactory,
              self).clientConnectionFailed(connector, reason)
        self._clientConnectionLostOrFailed(connector, reason)

    def clientConnectionLost(self, connector, reason):
        print("WAMP Client connection lost (%s) .. retrying .." %
              time.ctime())
        super(ReconnectingWampWebSocketClientFactory,
              self).clientConnectionFailed(connector, reason)
        self._clientConnectionLostOrFailed(connector, reason)


def CheckConfiguration(WampClientConf):
    url = WampClientConf["url"]
    if not IsCorrectUri(url):
        raise annotate.ValidateError(
            {"url": "Invalid URL: {}".format(url)},
            _("WAMP configuration error:"))

def UpdateWithDefault(d1, d2):
    for k, v in list(d2.items()):
        d1.setdefault(k, v)

def GetConfiguration():
    global lastKnownConfig

    WampClientConf = None

    if os.path.exists(_WampConf):
        try:
            WampClientConf = json.load(open(_WampConf))
            UpdateWithDefault(WampClientConf, defaultWampConfig)
        except ValueError:
            pass

    if WampClientConf is None:
        WampClientConf = defaultWampConfig.copy()

    for itemName in mandatoryConfigItems:
        if WampClientConf.get(itemName, None) is None:
            raise Exception(
                _("WAMP configuration error : missing '{}' parameter.").format(itemName))

    CheckConfiguration(WampClientConf)

    lastKnownConfig = WampClientConf.copy()
    return WampClientConf


def SetConfiguration(WampClientConf):
    global lastKnownConfig

    CheckConfiguration(WampClientConf)

    lastKnownConfig = WampClientConf.copy()

    with open(os.path.realpath(_WampConf), 'w') as f:
        json.dump(WampClientConf, f, sort_keys=True, indent=4)
    StopReconnectWampClient()
    if 'active' in WampClientConf and WampClientConf['active']:
        StartReconnectWampClient()

    return WampClientConf


def LoadWampSecret(secretfname):
    WSClientWampSecret = open(secretfname, 'rb').read()
    if len(WSClientWampSecret) == 0:
        raise Exception(_("WAMP secret is empty"))
    return WSClientWampSecret


def IsCorrectUri(uri):
    return re.match(r'wss?://[^\s?:#-]+(:[0-9]+)?(/[^\s]*)?$', uri) is not None


def RegisterWampClient(wampconf=None, wampsecret=None, ConfDir=None, KeyStore=None, servicename=None):
    from twisted.internet import reactor
    global _WampConf, _WampSecret, _WampSercretFile, _WampClientCert, _WampTrust, defaultWampConfig

    if servicename:
        defaultWampConfig["ID"] = servicename

    ConfDir = ConfDir if ConfDir else WorkingDir
    KeyStore = KeyStore if KeyStore else WorkingDir

    _WampConfDefault = os.path.join(ConfDir, "wampconf.json")
    _WampSecretDefault = os.path.join(KeyStore, "wamp.secret")

    if _WampClientCert is None:
        _WampClientCert = os.path.join(KeyStore, "wampClientCert.pem")

    if _WampTrust is None:
        _WampTrust = os.path.join(KeyStore, "wampTrustStore.crt")

    # set config file path only if not already set
    if _WampConf is None:
        # default project's wampconf has precedance over commandline given
        if os.path.exists(_WampConfDefault) or wampconf is None:
            _WampConf = _WampConfDefault
        else:
            _WampConf = wampconf

    WampClientConf = GetConfiguration()

    if not WampClientConf["active"]:
        print("WAMP deactivated in configuration")
        return

    # set secret file path only if not already set
    if _WampSercretFile is None:
        # default project's wamp secret also
        # has precedance over commandline given
        if os.path.exists(_WampSecretDefault):
            _WampSercretFile = _WampSecretDefault
        else:
            _WampSercretFile = wampsecret

    if _WampSercretFile is not None:
        if _WampSercretFile == _WampSecretDefault:
            # secret from project dir is raw (no ID prefix)
            _WampSecret = LoadWampSecret(_WampSercretFile)
        else:
            # secret from command line is formated ID:PSK
            # fall back to PSK data (works because wampsecret is PSKpath)
            _ID, _WampSecret = getPSKID()
    else:
        raise Exception(_("WAMP no secret file given"))

    reactor.callInThread(_RegisterWampClient)

    return WampClientConf

def _RegisterWampClient():
    global _WampSecret, _transportFactory
    WampClientConf = GetConfiguration()

    WampClientConf["secret"] = _WampSecret

    # create a WAMP application session factory
    component_config = types.ComponentConfig(
        realm=WampClientConf["realm"],
        extra=WampClientConf)
    session_factory = wamp.ApplicationSessionFactory(
        config=component_config)
    session_factory.session = WampSession

    # create a WAMP-over-WebSocket transport client factory
    ReconnectingWampWebSocketClientFactory(
        component_config,
        session_factory,
        url=WampClientConf["url"],
        serializers=[MsgPackSerializer()])

    # start the client
    if _transportFactory:
        auth = WampClientConf["authentication"]
        verify = WampClientConf["verifyHostname"]

        contextFactory=None
        if _transportFactory.isSecure:
            client_cert=None
            trustRoot=None
            ssl_auth = auth in SSL_AUTHENTICATION_TYPES
            if ssl_auth:
                if os.path.exists(_WampClientCert):
                    client_cert = PrivateCertificate.loadPEM(open(_WampClientCert, 'rb').read())
                else:
                    GetPLCObjectSingleton().LogMessage(LogLevelsDict["ERROR"], 
                        "WAMP client certificate not provided for:", WampClientConf["url"])
                    return
            if verify:
                if os.path.exists(_WampTrust):
                    cert = crypto.load_certificate(crypto.FILETYPE_PEM,
                        open(_WampTrust, 'rb').read())
                    trustRoot = OpenSSLCertificateAuthorities([cert])
            if verify or ssl_auth:
                contextFactory=optionsForClientTLS(_transportFactory.host,
                                                   trustRoot=trustRoot,
                                                   clientCertificate=client_cert)
        else:
            # non encrypted connection is not accepted in case some security is requested
            if auth != AUTH_NONE or verify:
                GetPLCObjectSingleton().LogMessage(LogLevelsDict["ERROR"], 
                    "WAMP connection must be secure:", WampClientConf["url"])
                return

        connectWS(_transportFactory, contextFactory)
        print("WAMP client connecting to :", WampClientConf["url"])
    else:
        GetPLCObjectSingleton().LogMessage(LogLevelsDict["WARNING"], 
            "WAMP configuration invalid:", WampClientConf["url"])

def StopReconnectWampClient():
    if _transportFactory is not None:
        _transportFactory.stopTrying()
    if _WampSession is not None:
        _WampSession.leave()


def StartReconnectWampClient():
    if _WampSession:
        # do reconnect and reset continueTrying and initialDelay parameter
        if _transportFactory is not None:
            _transportFactory.resetDelay()
        _WampSession.disconnect()
        return True
    else:
        # do connect
        _RegisterWampClient()
        return True


def GetSession():
    return _WampSession


def getWampStatus():
    if _transportFactory is not None:
        if _WampSession is not None:
            if _WampSession.is_attached():
                return "Attached"
            return "Established"
        return "Connecting"
    return "Disconnected"


def PublishEvent(eventID, value):
    if getWampStatus() == "Attached":
        _WampSession.publish(str(eventID), value)


def PublishEventWithOwnID(eventID, value):
    if getWampStatus() == "Attached":
        _WampSession.publishWithOwnID(str(eventID), value)


# WEB CONFIGURATION INTERFACE
WAMP_SECRET_URL = "secret"
WAMP_DELETE_CLIENTCERT_URL = "delete_clientcert"
WAMP_DELETE_TRUSTSTORE_URL = "delete_truststore"
webExposedConfigItems = [
    'active', 'url', 'ID',
    "clientFactoryOptions.maxDelay",
    "protocolOptions.autoPingInterval",
    "protocolOptions.autoPingTimeout",
    "authentication",
    "verifyHostname"
]


def wampConfigDefault(ctx, argument):
    if lastKnownConfig is not None:
        # Check if name is composed with an intermediate dot symbol and go deep in lastKnownConfig if it is
        argument_name_path = argument.name.split(".")
        searchValue = lastKnownConfig
        while argument_name_path:
            if searchValue:
                searchValue = searchValue.get(argument_name_path.pop(0), None)
            else:
                break
        return searchValue


def wampConfig(**kwargs):
    secretfile_field = kwargs["secretfile"]
    if secretfile_field is not None:
        secretfile = getattr(secretfile_field, "file", None)
        if secretfile is not None:
            with open(os.path.realpath(_WampSercretFile), 'w') as destfd:
                secretfile.seek(0)
                shutil.copyfileobj(secretfile,destfd)

    clientCert_field = kwargs["clientCert"]
    if clientCert_field is not None:
        clientCert_file = getattr(clientCert_field, "file", None)
        if clientCert_file is not None:
            with open(os.path.realpath(_WampClientCert), 'w') as destfd:
                clientCert_file.seek(0)
                shutil.copyfileobj(clientCert_file,destfd)

    trustStore_field = kwargs["trustStore"]
    if trustStore_field is not None:
        trustStore_file = getattr(trustStore_field, "file", None)
        if trustStore_file is not None:
            with open(os.path.realpath(_WampTrust), 'w') as destfd:
                trustStore_file.seek(0)
                shutil.copyfileobj(trustStore_file,destfd)

    newConfig = lastKnownConfig.copy()
    for argname in webExposedConfigItems:
        # Check if name is composed with an intermediate dot symbol and go deep in lastKnownConfig if it is
        #  and then set a new value.
        argname_path = argname.split(".")
        arg_last = argname_path.pop()
        arg = kwargs.get(argname, None)
        if arg is not None:
            tmpConf = newConfig
            while argname_path:
                tmpConf = tmpConf.setdefault(argname_path.pop(0), {})
            tmpConf[arg_last] = arg.decode() if type(arg)==bytes else arg

    SetConfiguration(newConfig)


class FileUploadDownload(annotate.FileUpload):
    pass


class FileUploadDownloadRenderer(webform.FileUploadRenderer):

    def input(self, context, slot, data, name, value):
        # pylint: disable=expression-not-assigned
        slot[_("Upload:")]
        slot = webform.FileUploadRenderer.input(
            self, context, slot, data, name, value)
        download_url = data.typedValue.getAttribute('download_url')
        return slot[tags.a(href=download_url)[_("Download")]]


registerAdapter(FileUploadDownloadRenderer, FileUploadDownload,
                formless.iformless.ITypedRenderer)


def getDownloadUrl(ctx, argument):
    if lastKnownConfig is not None:
        return url.URL.fromContext(ctx).\
            child(WAMP_SECRET_URL).\
            child(lastKnownConfig["ID"] + ".secret")


class FileUploadDelete(annotate.FileUpload):
    pass


class FileUploadDeleteRenderer(webform.FileUploadRenderer):

    def input(self, context, slot, data, name, value):
        # pylint: disable=expression-not-assigned
        slot[_("Upload:")]
        slot = webform.FileUploadRenderer.input(
            self, context, slot, data, name, value)
        file_exists = data.typedValue.getAttribute('file_exists')
        if file_exists and file_exists():
            unique = str(id(self))
            file_delete = data.typedValue.getAttribute('file_delete')
            slot = slot[
                tags.a(href=file_delete, target=unique)[_("Delete")],
                tags.iframe(srcdoc="File exists", name=unique,
                            height="20", width="150",
                            marginheight="5", marginwidth="5",
                            scrolling="no", frameborder="0")
            ]
        return slot


registerAdapter(FileUploadDeleteRenderer, FileUploadDelete,
                formless.iformless.ITypedRenderer)


def getClientCertPresence():
    return os.path.exists(_WampClientCert)


def getClientCertDeleteUrl(ctx, argument):
    return url.URL.fromContext(ctx).child(WAMP_DELETE_CLIENTCERT_URL)


def getTrustStorePresence():
    return os.path.exists(_WampTrust)


def getTrustStoreDeleteUrl(ctx, argument):
    return url.URL.fromContext(ctx).child(WAMP_DELETE_TRUSTSTORE_URL)


webFormInterface = [
    ("status",
     annotate.String(label=_("Current status"),
                     immutable=True,
                     default=lambda *k:getWampStatus())),
    ("ID",
     annotate.String(label=_("ID"),
                     default=wampConfigDefault)),
    ("secretfile",
     FileUploadDownload(label=_("File containing secret for that ID"),
                        download_url=getDownloadUrl)),
    ("active",
     annotate.Boolean(label=_("Enable WAMP connection"),
                      default=wampConfigDefault)),
    ("url",
     annotate.String(label=_("WAMP Server URL"),
                     default=wampConfigDefault)),
    ("clientFactoryOptions.maxDelay",
     annotate.Integer(label=_("Max reconnection delay (s)"),
                      default=wampConfigDefault)),
    ("protocolOptions.autoPingInterval",
     annotate.Integer(label=_("Auto ping interval (s)"),
                      default=wampConfigDefault)),
    ("protocolOptions.autoPingTimeout",
     annotate.Integer(label=_("Auto ping timeout (s)"),
                      default=wampConfigDefault)),
    ("clientCert",
     FileUploadDelete(label=_("File containing client certificate"),
                      file_exists=getClientCertPresence,
                      file_delete=getClientCertDeleteUrl)),
    ("trustStore",
     FileUploadDelete(label=_("File containing server certificate"),
                      file_exists=getTrustStorePresence,
                      file_delete=getTrustStoreDeleteUrl)),
    ("authentication",
     annotate.Choice(AUTHENTICATION_TYPES,
                     required=True,
                     label=_("Authentication type"),
                     default=wampConfigDefault)),
    ("verifyHostname",
     annotate.Boolean(label=_("Verify hostname matches certificate hostname"),
                      default=wampConfigDefault)),
    ]

def deliverWampSecret(ctx, segments):
    # filename = segments[1].decode('utf-8')

    # FIXME: compare filename to ID+".secret"
    # for now all url under /secret returns the secret

    # TODO: make beautifull message in case of exception
    # while loading secret (if empty or dont exist)
    secret = LoadWampSecret(_WampSercretFile)
    return static.Data(secret, 'application/octet-stream'), ()

def deleteClientCert(ctx, segments):
    if os.path.exists(_WampClientCert):
        os.remove(_WampClientCert)
    return static.Data("ClientCert deleted", 'text/html'), ()

def deleteTrustStore(ctx, segments):
    if os.path.exists(_WampTrust):
        os.remove(_WampTrust)
    return static.Data("TrustStore deleted", 'text/html'), ()

def RegisterWebSettings(NS):

    WebSettings = NS.newExtensionSetting("Wamp Extension Settings", "wamp_settings")
    WebSettings.addSettings(
        "wamp",
        _("Wamp Settings"),
        webFormInterface,
        _("Set"),
        wampConfig)

    WebSettings.addCustomURL(WAMP_SECRET_URL, deliverWampSecret)
    WebSettings.addCustomURL(WAMP_DELETE_TRUSTSTORE_URL, deleteTrustStore)

