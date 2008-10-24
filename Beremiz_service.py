#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os, sys, getopt

try:
    import wx, re
    from wx.lib.embeddedimage import PyEmbeddedImage
    from threading import Thread
    from types import *
    havewx = True
except:
    havewx = False

BeremizIcon = PyEmbeddedImage(
"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"
"ycvmAAAAAElFTkSuQmCC")

def usage():
    print """
Usage of Beremiz PLC execution service :\n
%s {[-n name] [-i ip] [-p port]|-h|--help} working_dir
           -n        - zeroconf service name
           -i        - ip of interface to bind to (x.x.x.x)
           -p        - port number
           -h        - print this help text and quit
           
           working_dir - directory where are stored PLC files
"""%sys.argv[0]

try:
    opts, args = getopt.getopt(sys.argv[1:], "i:p:n:h")
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
ip = ""
port = 3000
name = os.environ[{
     "linux2":"USER",
     "win32":"USERNAME",
     }.get(sys.platform, "USER")]

for o, a in opts:
    if o == "-h":
        usage()
        sys.exit()
    elif o == "-i":
        if len(a.split(".")) == 4 or a == "localhost":
            ip = a
    elif o == "-p":
        # port: port that the service runs on
        port = int(a)
    elif o == "-n":
        name = a
    else:
        usage()
        sys.exit()

if len(args) > 1:
    usage()
    sys.exit()
elif len(args) == 1:
    WorkingDir = args[0]
elif len(args) == 0:
    WorkingDir = os.getcwd()
    args=[WorkingDir]

from runtime import PLCObject, ServicePublisher
import Pyro.core as pyro

if not os.path.isdir(WorkingDir):
    os.mkdir(WorkingDir)



class Server():
    def __init__(self, name, ip, port, workdir, args):
        self.continueloop = True
        self.daemon = None
        self.name = name
        self.ip = ip
        self.port = port
        self.workdir = workdir
        self.args = args
        self.plcobj = None
        self.servicepublisher = ServicePublisher.ServicePublisher()

    def Loop(self):
        while self.continueloop:
            self.Start()
        
    def Restart(self):
        self.Stop()

    def Quit(self):
        self.continueloop = False
        self.Stop()

    def Start(self):
        pyro.initServer()
        self.daemon=pyro.Daemon(host=self.ip, port=self.port)
        self.plcobj = PLCObject(self.workdir, self.daemon, self.args)
        uri = self.daemon.connect(self.plcobj,"PLCObject")
    
        print "The daemon runs on port :",self.port
        print "The object's uri is :",uri
        print "The working directory :",self.workdir
        
        # Configure and publish service
        # Not publish service if localhost in address params
        if self.ip != "localhost" and self.ip != "127.0.0.1":    
            print "Publish service on local network"            
            self.servicepublisher.RegisterService(self.name, self.ip, self.port)
        
        sys.stdout.flush()
        
        self.daemon.requestLoop()
    
    def Stop(self):
        self.servicepublisher.UnRegisterService()
        self.daemon.shutdown(True)

class ParamsEntryDialog(wx.TextEntryDialog):
    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    

    def __init__(self, parent, message, caption = "Please enter text", defaultValue = "", 
                       style = wx.OK|wx.CANCEL|wx.CENTRE, pos = wx.DefaultPosition):
        wx.TextEntryDialog.__init__(self, parent, message, caption, defaultValue, style, pos)
        
        self.Tests = []
        if wx.VERSION >= (2, 8, 0):
            self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.GetAffirmativeId())
        elif wx.VERSION >= (2, 6, 0):
            self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.GetSizer().GetItem(3).GetSizer().GetAffirmativeButton().GetId())
        else:
            self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.GetSizer().GetItem(3).GetSizer().GetChildren()[0].GetSizer().GetChildren()[0].GetWindow().GetId())
    
    def OnOK(self, event):
        value = self.GetValue()
        texts = {"value" : value}
        for function, message in self.Tests:
            if not function(value):
                message = wx.MessageDialog(self, message%texts, "Error", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
                return
        self.EndModal(wx.ID_OK)
    
    def GetValue(self):
        return self.GetSizer().GetItem(1).GetWindow().GetValue()
    
    def SetTests(self, tests):
        self.Tests = tests
        
class DemoTaskBarIcon(wx.TaskBarIcon):
    TBMENU_CHANGE_NAME = wx.NewId()
    TBMENU_CHANGE_PORT = wx.NewId()
    TBMENU_CHANGE_INTERFACE = wx.NewId()
    TBMENU_CHANGE_WD = wx.NewId()
    TBMENU_QUIT = wx.NewId()
    
    def __init__(self, pyroserver):
        wx.TaskBarIcon.__init__(self)
        # Set the image
        icon = self.MakeIcon(BeremizIcon.GetImage())
        self.SetIcon(icon, "Beremiz Service")        
        # bind some events
        #self.Bind(wx.EVT_TASKBAR_CLICK, self.OnClick)
        #self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        self.Bind(wx.EVT_MENU, self.OnTaskBarChangeName, id=self.TBMENU_CHANGE_NAME)
        self.Bind(wx.EVT_MENU, self.OnTaskBarChangeInterface, id=self.TBMENU_CHANGE_INTERFACE)
        self.Bind(wx.EVT_MENU, self.OnTaskBarChangePort, id=self.TBMENU_CHANGE_PORT)
        self.Bind(wx.EVT_MENU, self.OnTaskBarChangeWorkingDir, id=self.TBMENU_CHANGE_WD)
        self.Bind(wx.EVT_MENU, self.OnTaskBarQuit, id=self.TBMENU_QUIT)
    
    def CreatePopupMenu(self):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """
        menu = wx.Menu()
        menu.Append(self.TBMENU_CHANGE_NAME, "Change Name")
        menu.Append(self.TBMENU_CHANGE_INTERFACE, "Change IP of interface to bind")
        menu.Append(self.TBMENU_CHANGE_PORT, "Change Port Number")
        menu.AppendSeparator()
        menu.Append(self.TBMENU_CHANGE_WD, "Change working directory")
        menu.Append(self.TBMENU_QUIT, "Quit")
        return menu

    def MakeIcon(self, img):
        """
        The various platforms have different requirements for the
        icon size...
        """
        if "wxMSW" in wx.PlatformInfo:
            img = img.Scale(16, 16)
        elif "wxGTK" in wx.PlatformInfo:
            img = img.Scale(22, 22)
        # wxMac can be any size upto 128x128, so leave the source img alone....
        icon = wx.IconFromBitmap(img.ConvertToBitmap() )
        return icon
    
    def OnTaskBarChangeInterface(self,evt):
        dlg = ParamsEntryDialog(None, "Enter the ip of the interface to bind", defaultValue=pyroserver.ip)
        dlg.SetTests([(re.compile('\d{1,3}(?:\.\d{1,3}){3}$').match, "Ip is not valid!"),
                       ( lambda ip :len([x for x in ip.split(".") if 0 <= int(x) <= 255]) == 4, "Ip is not valid!")
                       ])
        if dlg.ShowModal() == wx.ID_OK:
            pyroserver.ip = dlg.GetValue()
            pyroserver.Stop()
            
    def OnTaskBarChangePort(self,evt):
        dlg = ParamsEntryDialog(None, "Enter a port number ", defaultValue=str(pyroserver.port))
        dlg.SetTests([(UnicodeType.isdigit, "Port number must be an integer!"), (lambda port : 0 <= int(port) <= 65535 , "Port number must be 0 <= port <= 65535!")])
        if dlg.ShowModal() == wx.ID_OK:
            pyroserver.port = int(dlg.GetValue())
            pyroserver.Stop()
            
    
    def OnTaskBarChangeWorkingDir(self,evt):
        dlg = wx.DirDialog(None, "Choose a working directory ", pyroserver.workdir, wx.DD_NEW_DIR_BUTTON)
        if dlg.ShowModal() == wx.ID_OK:
            pyroserver.workdir = dlg.GetPath()
            pyroserver.Stop()
            
    def OnTaskBarChangeName(self,evt):
        dlg = ParamsEntryDialog(None, "Enter a name ", defaultValue=pyroserver.name)
        dlg.SetTests([(lambda name : len(name) is not 0 , "Name must not be null!")])
        if dlg.ShowModal() == wx.ID_OK:
            pyroserver.name = dlg.GetValue()
            pyroserver.Restart()

    def OnTaskBarQuit(self,evt):
        pyroserver.Quit()
        self.RemoveIcon()
        
pyroserver = Server(name, ip, port, WorkingDir, args)

if havewx:
    app=wx.App(redirect=False)
    taskbar_instance = DemoTaskBarIcon(pyroserver)
    pyro_thread=Thread(target=pyroserver.Loop)
    pyro_thread.start()
    app.MainLoop()
else:
    pyroserver.Loop()
