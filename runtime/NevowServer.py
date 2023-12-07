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




import os
import collections
import shutil
from zope.interface import implementer
from nevow import appserver, inevow, tags, loaders, athena, url, rend
from nevow.page import renderer
from nevow.static import File
from formless import annotate
from formless import webform
from formless import configurable
from twisted.internet import reactor

import util.paths as paths
from runtime.loglevels import LogLevels, LogLevelsDict
from runtime import MainWorker, GetPLCObjectSingleton

PAGE_TITLE = 'Beremiz Runtime Web Interface'

xhtml_header = b'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
'''

WorkingDir = None

class ConfigurableBindings(configurable.Configurable):

    def __init__(self):
        configurable.Configurable.__init__(self, None)
        self.bindingsNames = []
        self.infostringcount = 0

    def getBindingNames(self, ctx):
        return self.bindingsNames

    def addInfoString(self, label, value, name=None):
        if isinstance(value, str):
            def default(*k):
                return value
        else:
            def default(*k):
                return value()

        if name is None:
            name = "_infostring_" + str(self.infostringcount)
            self.infostringcount = self.infostringcount + 1

        def _bind(ctx):
            return annotate.Property(
                name,
                annotate.String(
                    label=label,
                    default=default,
                    immutable=True))
        setattr(self, 'bind_' + name, _bind)
        self.bindingsNames.append(name)

    def addSettings(self, name, desc, fields, btnlabel, callback):
        def _bind(ctx):
            return annotate.MethodBinding(
                'action_' + name,
                annotate.Method(
                    arguments=[
                        annotate.Argument(*field)
                        for field in fields],
                    label=desc),
                action=btnlabel)
        setattr(self, 'bind_' + name, _bind)

        setattr(self, 'action_' + name, callback)

        self.bindingsNames.append(name)
            
    customSettingsURLs = {}
    def addCustomURL(self, segment, func):
        self.customSettingsURLs[segment] = func

    def removeCustomURL(self, segment):
        del self.customSettingsURLs[segment]

    def customLocateChild(self, ctx, segments):
        segment = segments[0]
        if segment in self.customSettingsURLs:
            return self.customSettingsURLs[segment](ctx, segments)

ConfigurableSettings = ConfigurableBindings()

def newExtensionSetting(display, token):
    global extensions_settings_od
    settings = ConfigurableBindings()
    extensions_settings_od[token] = (settings, display)
    return settings

def removeExtensionSetting(token):
    global extensions_settings_od
    extensions_settings_od.pop(token)


class ISettings(annotate.TypedInterface):
    platform = annotate.String(label=_("Platform"),
                               default=lambda *a,**k:GetPLCObjectSingleton().GetVersions(),
                               immutable=True)


    # pylint: disable=no-self-argument
    def sendLogMessage(
            ctx=annotate.Context(),
            level=annotate.Choice(LogLevels,
                                  required=True,
                                  label=_("Log message level")),
            message=annotate.String(label=_("Message text"))):
        pass

    sendLogMessage = annotate.autocallable(sendLogMessage,
                                           label=_(
                                               "Send a message to the log"),
                                           action=_("Send"))

    # pylint: disable=no-self-argument
    def restartOrRepairPLC(
            ctx=annotate.Context(),
            action=annotate.Choice(["Restart", "Repair"],
                                  required=True,
                                  label=_("Action"))):
        pass

    restartOrRepairPLC = annotate.autocallable(restartOrRepairPLC,
                                           label=_(
                                               "Restart or Repair"),
                                           action=_("Do"))

    # pylint: disable=no-self-argument
    def uploadFile(
            ctx=annotate.Context(),
            uploadedfile=annotate.FileUpload(required=True,
                                  label=_("File to upload"))):
        pass

    uploadFile = annotate.autocallable(uploadFile,
                                           label=_(
                                               "Upload a file to PLC working directory"),
                                           action=_("Upload"))

extensions_settings_od = collections.OrderedDict()


CSS_tags = [tags.link(rel='stylesheet',
                      type='text/css',
                      href=url.here.child("webform_css")),
           tags.link(rel='stylesheet',
                      type='text/css',
                      href=url.here.child("webinterface_css"))]

@implementer(ISettings)
class StyledSettingsPage(rend.Page):
    addSlash = True

    # This makes webform_css url answer some default CSS
    child_webform_css = webform.defaultCSS
    child_webinterface_css = File(paths.AbsNeighbourFile(__file__, 'webinterface.css'), 'text/css')

class SettingsPage(StyledSettingsPage):
   
    def extensions_settings(self, context, data):
        """ Project extensions settings
        Extensions added to Configuration Tree in IDE have their setting rendered here
        """
        global extensions_settings_od
        res = []
        for token in extensions_settings_od:
            _settings, display = extensions_settings_od[token]
            res += [tags.p[tags.a(href=token)[display]]]
        return res

    docFactory = loaders.stan([tags.html[
        tags.head[
            tags.title[_("Beremiz Runtime Settings")],
            CSS_tags
        ],
        tags.body[
            tags.h1["Settings"],
            tags.a(href='/')['Back'],
            tags.h2["Runtime service"],
            webform.renderForms('staticSettings'),
            tags.h2["Target specific"],
            webform.renderForms('dynamicSettings'),
            tags.h2["Extensions"],
            extensions_settings
        ]]])

    def configurable_staticSettings(self, ctx):
        return configurable.TypedInterfaceConfigurable(self)

    def configurable_dynamicSettings(self, ctx):
        """ Runtime Extensions settings
        Extensions loaded through Beremiz_service -e or optional runtime features render setting forms here
        """
        return ConfigurableSettings

    def sendLogMessage(self, level, message, **kwargs):
        level = LogLevelsDict[level]
        GetPLCObjectSingleton().LogMessage(
            level, "Web form log message: " + message)

    def restartOrRepairPLC(self, action, **kwargs):
        if(action == "Repair"):
            GetPLCObjectSingleton().RepairPLC()
        else:
            MainWorker.quit()

    def uploadFile(self, uploadedfile, **kwargs):
        if uploadedfile is not None:
            fobj = getattr(uploadedfile, "file", None)
        if fobj is not None:
            with open(uploadedfile.filename, 'wb') as destfd:
                fobj.seek(0)
                shutil.copyfileobj(fobj,destfd)

    def locateChild(self, ctx, segments):
        segment = segments[0]
        if segment in extensions_settings_od:
            settings, display = extensions_settings_od[segment]
            return ExtensionSettingsPage(settings, display), segments[1:]
        else:
            res = ConfigurableSettings.customLocateChild(ctx, segments)
            if res:
                return res 
        return super(SettingsPage, self).locateChild(ctx, segments)

class ExtensionSettingsPage(StyledSettingsPage):

    docFactory = loaders.stan([
        tags.html[
            tags.head()[
                tags.title[tags.directive("title")],
                CSS_tags
            ],
            tags.body[
                tags.h1[tags.directive("title")],
                tags.a(href='/settings')['Back'],
                webform.renderForms('settings')
            ]]])

    def render_title(self, ctx, data):
        return self._display_name

    def configurable_settings(self, ctx):
        return self._settings

    def __init__(self, settings, display):
        self._settings = settings
        self._display_name = display

    def locateChild(self, ctx, segments):
        res = self._settings.customLocateChild(ctx, segments)
        if res:
            return res 
        return super(ExtensionSettingsPage, self).locateChild(ctx, segments)


def RegisterWebsite(iface, port):
    website = SettingsPage()
    site = appserver.NevowSite(website)

    reactor.listenTCP(port, site, interface=iface)
    print(_('HTTP interface port :'), port)
    return website
