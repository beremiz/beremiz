#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
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
import os
from zope.interface import implements
from nevow import appserver, inevow, tags, loaders, athena, url, rend
from nevow.page import renderer
from formless import annotate
from formless import webform
from formless import configurable
from twisted.internet import reactor

import util.paths as paths
from runtime.loglevels import LogLevels, LogLevelsDict

PAGE_TITLE = 'Beremiz Runtime Web Interface'

xhtml_header = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
'''

WorkingDir = None
_PySrv = None


class PLCHMI(athena.LiveElement):

    initialised = False

    def HMIinitialised(self, result):
        self.initialised = True

    def HMIinitialisation(self):
        self.HMIinitialised(None)

class DefaultPLCStartedHMI(PLCHMI):
    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveElement'))[
            tags.h1["PLC IS NOW STARTED"],
        ])


class PLCStoppedHMI(PLCHMI):
    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveElement'))[
            tags.h1["PLC IS STOPPED"],
        ])


class MainPage(athena.LiveElement):
    jsClass = u"WebInterface.PLC"
    docFactory = loaders.stan(
        tags.div(render=tags.directive('liveElement'))[
            tags.div(id='content')[
                tags.div(render=tags.directive('PLCElement'))]
        ])

    def __init__(self, *a, **kw):
        athena.LiveElement.__init__(self, *a, **kw)
        self.pcl_state = False
        self.HMI = None
        self.resetPLCStartedHMI()

    def setPLCState(self, state):
        self.pcl_state = state
        if self.HMI is not None:
            self.callRemote('updateHMI')

    def setPLCStartedHMI(self, hmi):
        self.PLCStartedHMIClass = hmi

    def resetPLCStartedHMI(self):
        self.PLCStartedHMIClass = DefaultPLCStartedHMI

    def getHMI(self):
        return self.HMI

    def HMIexec(self, function, *args, **kwargs):
        if self.HMI is not None:
            getattr(self.HMI, function, lambda: None)(*args, **kwargs)
    athena.expose(HMIexec)

    def resetHMI(self):
        self.HMI = None

    def PLCElement(self, ctx, data):
        return self.getPLCElement()
    renderer(PLCElement)

    def getPLCElement(self):
        self.detachFragmentChildren()
        if self.pcl_state:
            f = self.PLCStartedHMIClass()
        else:
            f = PLCStoppedHMI()
        f.setFragmentParent(self)
        self.HMI = f
        return f
    athena.expose(getPLCElement)

    def detachFragmentChildren(self):
        for child in self.liveFragmentChildren[:]:
            child.detach()

class ConfigurableBindings(configurable.Configurable):

    def __init__(self):
        configurable.Configurable.__init__(self, None)
        self.bindingsNames = []

    def getBindingNames(self, ctx):
        return self.bindingsNames

    def addExtension(self, name, desc, fields, btnlabel, callback):
        def _bind(ctx):
            return annotate.MethodBinding(
                'action_'+name,
                annotate.Method(arguments=[
                    annotate.Argument(name, fieldtype)
                    for fieldname,fieldtype in fields],
                    label = desc),
                action = btnlabel)
        setattr(self, 'bind_'+name, _bind)
            
        setattr(self, 'action_'+name, callback)

        self.bindingsNames.append(name)

ConfigurableSettings = ConfigurableBindings()

class ISettings(annotate.TypedInterface):
    def sendLogMessage(
        ctx = annotate.Context(),
        level = annotate.Choice(LogLevels,
                                required=True, 
                                label=_("Log message level")),
        message = annotate.String(label=_("Message text"))):
            pass
    sendLogMessage = annotate.autocallable(sendLogMessage, 
                                           label=_("Send a message to the log"),
                                           action=_("Send"))


class SettingsPage(rend.Page):
    # We deserve a slash
    addSlash = True
    
    # This makes webform_css url answer some default CSS
    child_webform_css = webform.defaultCSS

    implements(ISettings)


    docFactory = loaders.stan([tags.html[
                                   tags.head[
                                       tags.title[_("Beremiz Runtime Settings")],
                                       tags.link(rel='stylesheet',
                                                 type='text/css', 
                                                 href=url.here.child("webform_css"))
                                   ],
                                   tags.body[ 
                                       tags.h1["Runtime settings:"],
                                       webform.renderForms('staticSettings'),
                                       tags.h2["Extensions settings:"],
                                       webform.renderForms('dynamicSettings'),
                                   ]]])

    def __init__(self):
        rend.Page.__init__(self)

    def configurable_staticSettings(self, ctx):
        return configurable.TypedInterfaceConfigurable(self)

    def configurable_dynamicSettings(self, ctx):
        return ConfigurableSettings
    
    def sendLogMessage(self, level, message, **kwargs):
        level = LogLevelsDict[level]
        if _PySrv.plcobj is not None:
            _PySrv.plcobj.LogMessage(level, "Web form log message: " + message )


class WebInterface(athena.LivePage):

    docFactory = loaders.stan([tags.raw(xhtml_header),
                               tags.html(xmlns="http://www.w3.org/1999/xhtml")[
                                   tags.head(render=tags.directive('liveglue'))[
                                       tags.title[PAGE_TITLE],
                                       tags.link(rel='stylesheet',
                                                 type='text/css', 
                                                 href=url.here.child("webform_css"))
                                   ],
                                   tags.body[
                                       tags.div[
                                           tags.div(render=tags.directive("MainPage")),
                                       ]]]])
    MainPage = MainPage()
    PLCHMI = PLCHMI

    def child_settings(self, context):
        return SettingsPage()

    def __init__(self, plcState=False, *a, **kw):
        super(WebInterface, self).__init__(*a, **kw)
        self.jsModules.mapping[u'WebInterface'] = paths.AbsNeighbourFile(__file__, 'webinterface.js')
        self.plcState = plcState
        self.MainPage.setPLCState(plcState)

    def getHMI(self):
        return self.MainPage.getHMI()

    def LoadHMI(self, hmi, jsmodules):
        for name, path in jsmodules.iteritems():
            self.jsModules.mapping[name] = os.path.join(WorkingDir, path)
        self.MainPage.setPLCStartedHMI(hmi)

    def UnLoadHMI(self):
        self.MainPage.resetPLCStartedHMI()

    def PLCStarted(self):
        self.plcState = True
        self.MainPage.setPLCState(True)

    def PLCStopped(self):
        self.plcState = False
        self.MainPage.setPLCState(False)

    def renderHTTP(self, ctx):
        """
        Force content type to fit with SVG
        """
        req = ctx.locate(inevow.IRequest)
        req.setHeader('Content-type', 'application/xhtml+xml')
        return super(WebInterface, self).renderHTTP(ctx)

    def render_MainPage(self, ctx, data):
        f = self.MainPage
        f.setFragmentParent(self)
        return ctx.tag[f]

    def child_(self, ctx):
        self.MainPage.detachFragmentChildren()
        return WebInterface(plcState=self.plcState)

    def beforeRender(self, ctx):
        d = self.notifyOnDisconnect()
        d.addErrback(self.disconnected)

    def disconnected(self, reason):
        self.MainPage.resetHMI()
        # print reason
        # print "We will be called back when the client disconnects"



def RegisterWebsite(port):
    website = WebInterface()
    site = appserver.NevowSite(website)

    reactor.listenTCP(port, site)
    print(_('HTTP interface port :'), port)
    return website


class statuslistener(object):
    def __init__(self, site):
        self.oldstate = None
        self.site = site

    def listen(self, state):
        if state != self.oldstate:
            action = {'Started': self.site.PLCStarted,
                      'Stopped': self.site.PLCStopped}.get(state, None)
            if action is not None:
                action()
            self.oldstate = state


def website_statuslistener_factory(site):
    return statuslistener(site).listen


def SetServer(pysrv):
    global _PySrv
    _PySrv = pysrv

