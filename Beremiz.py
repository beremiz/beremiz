#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2016 - 2017: Andrey Skvortsov <andrej.skvortzov@gmail.com>
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


import os
import sys
import getopt

from util import SuppressGTKDiagnostics, SetDeveloperMode, SetSDKPath
SuppressGTKDiagnostics()

import wx
from wx.lib.agw.advancedsplash import AdvancedSplash, AS_NOTIMEOUT, AS_CENTER_ON_SCREEN

import util.paths as paths
from dialogs.SDKManager import SDKManagerDialog

from util.ProcessLogger import SetDefaultEnv
# BEremiz console doesn't support colors yet.
SetDefaultEnv({"NO_COLOR":"1",
               "GCC_COLORS":""})

class BeremizIDELauncher(object):
    def __init__(self):
        self.app = None
        self.frame = None
        self.updateinfo_url = None
        self.extensions = []
        self.app_dir = paths.AbsDir(__file__)
        self.projectOpen = None
        self.buildpath = None
        self.splash = None
        self.splashPath = self.Bpath("images", "splash.png")
        self.modules = ["BeremizIDE"]
        self.handle_exception = None
        self.logf = None
        self.devmode = False
        self.sdk_selector = False

    def Bpath(self, *args):
        return os.path.join(self.app_dir, *args)

    def Usage(self):
        print("Usage:")
        print("%s [Options] [Projectpath] [Buildpath]" % sys.argv[0])
        print("")
        print("Supported options:")
        print("-h --help                    Print this help")
        print("-d --devmode                 Run in development mode")
        print("-p --plcsdkselector          Show SDK location selector dialog at startup")
        print("-s --sdkpath PATH            Use PATH as SDK location")
        print("-u --updatecheck URL         Retrieve update information by checking URL")
        print("-e --extend PathToExtension  Extend IDE functionality by loading at start additional extensions")
        print("-l --log path                write content of console tab to given file")
        print("")
        print("")

    def SetCmdOptions(self):
        self.shortCmdOpts = "hdpsu:e:l:"
        self.longCmdOpts = ["help", "devmode", "plcsdkselector", "sdkpath=", "updatecheck=", "extend=", "log="]

    def ProcessOption(self, o, a):
        if o in ("-h", "--help"):
            self.Usage()
            sys.exit()
        if o in ("-d", "--devmode"):
            self.devmode = True
            SetDeveloperMode()
        if o in ("-p", "--plcsdkselector"):
            self.sdk_selector = True            
        if o in ("-s", "--sdkpath"):
            if a is not None and os.path.isdir(a):
                SetSDKPath(a)
            else:
                print("Invalid SDK path: %s" % a)
                self.Usage()
                sys.exit(2)
        if o in ("-u", "--updatecheck"):
            self.updateinfo_url = a
        if o in ("-e", "--extend"):
            self.extensions.append(a)
        if o in ("-l", "--log"):
            self.logf = open(a, 'a')

    def ProcessCommandLineArgs(self):
        self.SetCmdOptions()
        try:
            opts, args = getopt.getopt(sys.argv[1:], self.shortCmdOpts, self.longCmdOpts)
        except getopt.GetoptError:
            # print help information and exit:
            self.Usage()
            sys.exit(2)

        for o, a in opts:
            self.ProcessOption(o, a)

        if len(args) > 2:
            self.Usage()
            sys.exit()

        elif len(args) == 1:
            self.projectOpen = args[0]
            self.buildpath = None
        elif len(args) == 2:
            self.projectOpen = args[0]
            self.buildpath = args[1]

    def CreateApplication(self):

        BeremizAppType = wx.App

        class BeremizApp(BeremizAppType):
            def OnInit(_self):  # pylint: disable=no-self-argument
                if self.sdk_selector:                
                    dlg = SDKManagerDialog(None, paths.AppDataPath("sdks"))
                    dlg_result = dlg.ShowModal() == wx.ID_OK
                    dlg.Destroy()
                    if dlg_result:
                        sdk_path = dlg.GetSelectedSDKPath()
                        if sdk_path:
                            SetSDKPath(sdk_path)
                    else:
                        return False
                self.ShowSplashScreen()
                return True

        self.app = BeremizApp(
            # on windows, this makes stdout and stderr visible in separate windows
            # on other platforms better to use the normal stdout and stderr
            redirect=self.devmode and sys.platform.startswith('win'))
        self.app.SetAppName('beremiz')

    def ShowSplashScreen(self):
        class Splash(AdvancedSplash):
            Painted = False

            def OnPaint(_self, event):  # pylint: disable=no-self-argument
                AdvancedSplash.OnPaint(_self, event)
                if not _self.Painted:  # trigger app start only once
                    _self.Painted = True
                    wx.CallAfter(self.AppStart)
        bmp = wx.Image(self.splashPath).ConvertToBitmap()
        self.splash = Splash(None,
                             bitmap=bmp,
                             agwStyle=AS_NOTIMEOUT | AS_CENTER_ON_SCREEN)

    def BackgroundInitialization(self):
        self.InitI18n()
        self.CheckUpdates()
        self.LoadExtensions()
        self.ImportModules()

    def InitI18n(self):
        from util.misc import InstallLocalRessources
        InstallLocalRessources(self.app_dir)

    def globals(self):
        """
        allows customizations to specify what globals
        are passed to extensions
        """
        return globals()

    def LoadExtensions(self):
        for extfilename in self.extensions:
            from util.TranslationCatalogs import AddCatalog
            from util.BitmapLibrary import AddBitmapFolder
            extension_folder = os.path.split(os.path.realpath(extfilename))[0]
            sys.path.append(extension_folder)
            AddCatalog(os.path.join(extension_folder, "locale"))
            AddBitmapFolder(os.path.join(extension_folder, "images"))
            exec(compile(open(extfilename, "rb").read(), extfilename, 'exec'), self.globals())

    def CheckUpdates(self):
        if self.updateinfo_url is not None:
            self.updateinfo = _("Fetching %s") % self.updateinfo_url

            def updateinfoproc():
                try:
                    import urllib.request, urllib.error, urllib.parse
                    self.updateinfo = urllib.request.urlopen(self.updateinfo_url, None).read()
                except Exception:
                    self.updateinfo = _("update info unavailable.")

            from threading import Thread
            self.splash.SetText(text=self.updateinfo)
            updateinfoThread = Thread(target=updateinfoproc)
            updateinfoThread.start()
            updateinfoThread.join(2)
            self.splash.SetText(text=self.updateinfo)

    def ImportModules(self):
        for modname in self.modules:
            mod = __import__(modname)
            setattr(self, modname, mod)

    def InstallExceptionHandler(self):
        import version
        import util.ExceptionHandler
        self.handle_exception = util.ExceptionHandler.AddExceptHook(version.app_version, logf=self.logf)

    def CreateUI(self):
        self.frame = self.BeremizIDE.Beremiz(None, self.projectOpen, self.buildpath, logf=self.logf, devmode=self.devmode)

    def CloseSplash(self):
        if self.splash:
            self.splash.Close()

    def ShowUI(self):
        self.frame.Show()

    def PreStart(self):
        self.ProcessCommandLineArgs()
        self.CreateApplication()

    def AppStart(self):
        try:
            self.BackgroundInitialization()
            self.CreateUI()
            self.CloseSplash()
            self.ShowUI()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            if self.handle_exception is not None:
                self.handle_exception(*sys.exc_info(), exit=True)
            else:
                raise

    def MainLoop(self):
        self.app.MainLoop()

    def Start(self):
        self.PreStart()
        if not self.devmode:
            # if in devmode mode, we don't want to install the exception handler
            # because we want to see the exception in the console
            # and not in a popup window
            self.InstallExceptionHandler()
        self.MainLoop()
        # Skip Python finalization to avoid SIP double-free crash
        # in sipOMFinalise: GTK destroys child C++ widgets during frame
        # destruction, but SIP's object map retains stale pointers.
        os._exit(0)


if __name__ == '__main__':
    beremiz = BeremizIDELauncher()
    beremiz.Start()
