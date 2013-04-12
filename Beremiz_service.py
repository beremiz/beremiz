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
from threading import Thread,Timer

def usage():
    print """
Usage of Beremiz PLC execution service :\n
%s {[-n servicename] [-i IP] [-p port] [-x enabletaskbar] [-a autostart]|-h|--help} working_dir
           -n        - zeroconf service name (default:disabled)
           -i        - IP address of interface to bind to (default:localhost)
           -p        - port number default:3000
           -h        - print this help text and quit
           -a        - autostart PLC (0:disable 1:enable) (default:0)
           -x        - enable/disable wxTaskbarIcon (0:disable 1:enable) (default:1)
           -t        - enable/disable Twisted web interface (0:disable 1:enable) (default:1)
           
           working_dir - directory where are stored PLC files
"""%sys.argv[0]

try:
    opts, argv = getopt.getopt(sys.argv[1:], "i:p:n:x:t:a:h")
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
given_ip = None
port = 3000
servicename = None
autostart = False
enablewx = True
havewx = False
enabletwisted = True
havetwisted = False

for o, a in opts:
    if o == "-h":
        usage()
        sys.exit()
    elif o == "-i":
        if len(a.split(".")) == 4 or a == "localhost":
            given_ip = a
        else:
            usage()
            sys.exit()
    elif o == "-p":
        # port: port that the service runs on
        port = int(a)
    elif o == "-n":
        servicename = a
    elif o == "-x":
        enablewx = int(a)
    elif o == "-t":
        enabletwisted = int(a)
    elif o == "-a":
        autostart = int(a)
    else:
        usage()
        sys.exit()

if len(argv) > 1:
    usage()
    sys.exit()
elif len(argv) == 1:
    WorkingDir = argv[0]
    os.chdir(WorkingDir)
elif len(argv) == 0:
    WorkingDir = os.getcwd()
    argv=[WorkingDir]

import __builtin__
if __name__ == '__main__':
    __builtin__.__dict__['_'] = lambda x: x

if enablewx:
    try:
        import wx, re
        from threading import Thread, currentThread
        from types import *
        havewx = True
    except:
        print "Wx unavailable !"
        havewx = False

    if havewx:
        app=wx.App(redirect=False)
        
        # Import module for internationalization
        import gettext
        
        CWD = os.path.split(os.path.realpath(__file__))[0]
        
        # Get folder containing translation files
        localedir = os.path.join(CWD,"locale")
        # Get the default language
        langid = wx.LANGUAGE_DEFAULT
        # Define translation domain (name of translation files)
        domain = "Beremiz"

        # Define locale for wx
        loc = __builtin__.__dict__.get('loc', None)
        if loc is None:
            loc = wx.Locale(langid)
            __builtin__.__dict__['loc'] = loc
        # Define location for searching translation files
        loc.AddCatalogLookupPathPrefix(localedir)
        # Define locale domain
        loc.AddCatalog(domain)

        def unicode_translation(message):
            return wx.GetTranslation(message).encode("utf-8")

        if __name__ == '__main__':
            __builtin__.__dict__['_'] = wx.GetTranslation#unicode_translation
        
        try:
            from wx.lib.embeddedimage import PyEmbeddedImage
        except:
            import cStringIO
            import base64
            
            class PyEmbeddedImage:
                def __init__(self, image_string):
                    stream = cStringIO.StringIO(base64.b64decode(image_string))
                    self.Image = wx.ImageFromStream(stream)
                def GetImage(self):
                    return self.Image
        
        defaulticon = PyEmbeddedImage(
        "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")
        
        #----------------------------------------------------------------------
        starticon = PyEmbeddedImage(
        "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"
        "Dw/HnwT4P6CDl+TMvD0JAAAAAElFTkSuQmCC")
        
        #----------------------------------------------------------------------
        stopicon = PyEmbeddedImage(
        "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")
        
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
                        message = wx.MessageDialog(self, message%texts, _("Error"), wx.OK|wx.ICON_ERROR)
                        message.ShowModal()
                        message.Destroy()
                        return
                self.EndModal(wx.ID_OK)
                event.Skip()
            
            def GetValue(self):
                return self.GetSizer().GetItem(1).GetWindow().GetValue()
            
            def SetTests(self, tests):
                self.Tests = tests
        
        class BeremizTaskBarIcon(wx.TaskBarIcon):
            TBMENU_START = wx.NewId()
            TBMENU_STOP = wx.NewId()
            TBMENU_CHANGE_NAME = wx.NewId()
            TBMENU_CHANGE_PORT = wx.NewId()
            TBMENU_CHANGE_INTERFACE = wx.NewId()
            TBMENU_LIVE_SHELL = wx.NewId()
            TBMENU_WXINSPECTOR = wx.NewId()
            TBMENU_CHANGE_WD = wx.NewId()
            TBMENU_QUIT = wx.NewId()
            
            def __init__(self, pyroserver, level):
                wx.TaskBarIcon.__init__(self)
                self.pyroserver = pyroserver
                # Set the image
                self.UpdateIcon(None)
                self.level = level
                
                # bind some events
                self.Bind(wx.EVT_MENU, self.OnTaskBarStartPLC, id=self.TBMENU_START)
                self.Bind(wx.EVT_MENU, self.OnTaskBarStopPLC, id=self.TBMENU_STOP)
                self.Bind(wx.EVT_MENU, self.OnTaskBarChangeName, id=self.TBMENU_CHANGE_NAME)
                self.Bind(wx.EVT_MENU, self.OnTaskBarChangeInterface, id=self.TBMENU_CHANGE_INTERFACE)
                self.Bind(wx.EVT_MENU, self.OnTaskBarLiveShell, id=self.TBMENU_LIVE_SHELL)
                self.Bind(wx.EVT_MENU, self.OnTaskBarWXInspector, id=self.TBMENU_WXINSPECTOR)
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
                menu.Append(self.TBMENU_START, _("Start PLC"))
                menu.Append(self.TBMENU_STOP, _("Stop PLC"))
                if self.level==1:
                    menu.AppendSeparator()
                    menu.Append(self.TBMENU_CHANGE_NAME, _("Change Name"))
                    menu.Append(self.TBMENU_CHANGE_INTERFACE, _("Change IP of interface to bind"))
                    menu.Append(self.TBMENU_CHANGE_PORT, _("Change Port Number"))
                    menu.Append(self.TBMENU_CHANGE_WD, _("Change working directory"))
                    menu.AppendSeparator()
                    menu.Append(self.TBMENU_LIVE_SHELL, _("Launch a live Python shell"))
                    menu.Append(self.TBMENU_WXINSPECTOR, _("Launch WX GUI inspector"))
                menu.AppendSeparator()
                menu.Append(self.TBMENU_QUIT, _("Quit"))
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
            
            def OnTaskBarStartPLC(self, evt):
                if self.pyroserver.plcobj is not None: 
                    self.pyroserver.plcobj.StartPLC()
                evt.Skip()
            
            def OnTaskBarStopPLC(self, evt):
                if self.pyroserver.plcobj is not None:
                    Thread(target=self.pyroserver.plcobj.StopPLC).start()
                evt.Skip()
            
            def OnTaskBarChangeInterface(self, evt):
                dlg = ParamsEntryDialog(None, _("Enter the IP of the interface to bind"), defaultValue=self.pyroserver.ip_addr)
                dlg.SetTests([(re.compile('\d{1,3}(?:\.\d{1,3}){3}$').match, _("IP is not valid!")),
                               ( lambda x :len([x for x in x.split(".") if 0 <= int(x) <= 255]) == 4, _("IP is not valid!"))
                               ])
                if dlg.ShowModal() == wx.ID_OK:
                    self.pyroserver.ip_addr = dlg.GetValue()
                    self.pyroserver.Stop()
                evt.Skip()
            
            def OnTaskBarChangePort(self, evt):
                dlg = ParamsEntryDialog(None, _("Enter a port number "), defaultValue=str(self.pyroserver.port))
                dlg.SetTests([(UnicodeType.isdigit, _("Port number must be an integer!")), (lambda port : 0 <= int(port) <= 65535 , _("Port number must be 0 <= port <= 65535!"))])
                if dlg.ShowModal() == wx.ID_OK:
                    self.pyroserver.port = int(dlg.GetValue())
                    self.pyroserver.Stop()
                evt.Skip()
            
            def OnTaskBarChangeWorkingDir(self, evt):
                dlg = wx.DirDialog(None, _("Choose a working directory "), self.pyroserver.workdir, wx.DD_NEW_DIR_BUTTON)
                if dlg.ShowModal() == wx.ID_OK:
                    self.pyroserver.workdir = dlg.GetPath()
                    self.pyroserver.Stop()
                evt.Skip()
            
            def OnTaskBarChangeName(self, evt):
                dlg = ParamsEntryDialog(None, _("Enter a name "), defaultValue=self.pyroserver.name)
                dlg.SetTests([(lambda name : len(name) is not 0 , _("Name must not be null!"))])
                if dlg.ShowModal() == wx.ID_OK:
                    self.pyroserver.name = dlg.GetValue()
                    self.pyroserver.Restart()
                evt.Skip()
            
            def _LiveShellLocals(self):
                if self.pyroserver.plcobj is not None:
                    return {"locals":self.pyroserver.plcobj.python_threads_vars}
                else:
                    return {}

            def OnTaskBarLiveShell(self, evt):
                from wx import py
                frame = py.crust.CrustFrame(**self._LiveShellLocals())
                frame.Show()
                evt.Skip()
            
            def OnTaskBarWXInspector(self, evt):
                # Activate the widget inspection tool
                from wx.lib.inspection import InspectionTool
                if not InspectionTool().initialized:
                    InspectionTool().Init(**self._LiveShellLocals())

                wnd = wx.GetApp()
                InspectionTool().Show(wnd, True)

                evt.Skip()
            
            def OnTaskBarQuit(self, evt):
                Thread(target=self.pyroserver.Quit).start()
                self.RemoveIcon()
                wx.CallAfter(wx.GetApp().Exit)
                evt.Skip()
            
            def UpdateIcon(self, plcstatus):
                if plcstatus is "Started" :
                    currenticon = self.MakeIcon(starticon.GetImage())
                elif plcstatus is "Stopped":
                    currenticon = self.MakeIcon(stopicon.GetImage())
                else:
                    currenticon = self.MakeIcon(defaulticon.GetImage())
                self.SetIcon(currenticon, "Beremiz Service")

from runtime import PLCObject, PLCprint, ServicePublisher
import Pyro.core as pyro

if not os.path.isdir(WorkingDir):
    os.mkdir(WorkingDir)

def default_evaluator(tocall, *args, **kwargs):
    try:
        res=(tocall(*args,**kwargs), None)
    except Exception,exp:
        res=(None, exp)
    return res

class Server():
    def __init__(self, servicename, ip_addr, port, workdir, argv, autostart=False, statuschange=None, evaluator=default_evaluator, website=None):
        self.continueloop = True
        self.daemon = None
        self.servicename = servicename
        self.ip_addr = ip_addr
        self.port = port
        self.workdir = workdir
        self.argv = argv
        self.plcobj = None
        self.servicepublisher = None
        self.autostart = autostart
        self.statuschange = statuschange
        self.evaluator = evaluator
        self.website = website
    
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
        self.daemon=pyro.Daemon(host=self.ip_addr, port=self.port)
        self.plcobj = PLCObject(self.workdir, self.daemon, self.argv, self.statuschange, self.evaluator, self.website)
        uri = self.daemon.connect(self.plcobj,"PLCObject")
    
        print "Pyro port :",self.port
        print "Pyro object's uri :",uri
        print "Current working directory :",self.workdir
        
        # Configure and publish service
        # Not publish service if localhost in address params
        if (self.servicename is not None and 
            self.ip_addr is not None and 
            self.ip_addr != "localhost" and 
            self.ip_addr != "127.0.0.1"):
            print "Publishing service on local network"
            self.servicepublisher = ServicePublisher.ServicePublisher()
            self.servicepublisher.RegisterService(self.servicename, self.ip_addr, self.port)
        
        if self.autostart:
            self.plcobj.LoadPLC()
            self.plcobj.StartPLC()
        
        sys.stdout.flush()
        
        self.daemon.requestLoop()
    
    def Stop(self):
        self.plcobj.StopPLC()
        if self.servicepublisher is not None:
            self.servicepublisher.UnRegisterService()
            self.servicepublisher = None
        self.daemon.shutdown(True)

if enabletwisted:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            from threading import Thread, currentThread
            if havewx:
                from twisted.internet import wxreactor
                wxreactor.install()
            from twisted.internet import reactor, task
            from twisted.python import log, util
            from nevow import rend, appserver, inevow, tags, loaders, athena
            from nevow.page import renderer
            
            havetwisted = True
        except:
            print "Twisted unavailable !"
            havetwisted = False

if havetwisted:
    
    xhtml_header = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN"
"http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
'''

    class PLCHMI(athena.LiveElement):
    
        initialised = False
    
        def HMIinitialised(self, result):
            self.initialised = True
        
        def HMIinitialisation(self):
            self.HMIinitialised(None)
    
    class DefaultPLCStartedHMI(PLCHMI):
        docFactory = loaders.stan(tags.div(render=tags.directive('liveElement'))[                                    
                                             tags.h1["PLC IS NOW STARTED"],
                                             ])
        
    class PLCStoppedHMI(PLCHMI):
        docFactory = loaders.stan(tags.div(render=tags.directive('liveElement'))[
                                             tags.h1["PLC IS STOPPED"],
                                             ])
    
    class MainPage(athena.LiveElement):
        jsClass = u"WebInterface.PLC"
        docFactory = loaders.stan(tags.div(render=tags.directive('liveElement'))[
                                                        tags.div(id='content')[                         
                                                        tags.div(render = tags.directive('PLCElement')),
                                                        ]])
        
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
                getattr(self.HMI, function, lambda:None)(*args, **kwargs)
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
    
    class WebInterface(athena.LivePage):

        docFactory = loaders.stan([tags.raw(xhtml_header),
                                   tags.html(xmlns="http://www.w3.org/1999/xhtml")[
                                       tags.head(render=tags.directive('liveglue')),
                                       tags.body[
                                           tags.div[
                                                   tags.div( render = tags.directive( "MainPage" ))
                                                   ]]]])
        MainPage = MainPage()
        PLCHMI = PLCHMI
        
        def __init__(self, plcState=False, *a, **kw):
            super(WebInterface, self).__init__(*a, **kw)
            self.jsModules.mapping[u'WebInterface'] = util.sibpath(__file__, os.path.join('runtime', 'webinterface.js'))
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
            req = inevow.IRequest(ctx)
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
            #print reason
            #print "We will be called back when the client disconnects"
        
    if havewx:
        reactor.registerWxApp(app)
    website = WebInterface()
    site = appserver.NevowSite(website)
    
    website_port = 8009
    listening = False
    while not listening:
        try:
            reactor.listenTCP(website_port, site)
            listening = True
        except:
            website_port += 1
    print "Http interface port :",website_port
else:
    website = None

if havewx:
    from threading import Semaphore
    wx_eval_lock = Semaphore(0)
    main_thread = currentThread()

    def statuschange(status):
        wx.CallAfter(taskbar_instance.UpdateIcon,status)
        
    def wx_evaluator(obj, *args, **kwargs):
        tocall,args,kwargs = obj.call
        obj.res = default_evaluator(tocall, *args, **kwargs)
        wx_eval_lock.release()
        
    def evaluator(tocall, *args, **kwargs):
        global main_thread
        if(main_thread == currentThread()):
            # avoid dead lock if called from the wx mainloop 
            return default_evaluator(tocall, *args, **kwargs)
        else:
            o=type('',(object,),dict(call=(tocall, args, kwargs), res=None))
            wx.CallAfter(wx_evaluator,o)
            wx_eval_lock.acquire()
            return o.res
    
    pyroserver = Server(servicename, given_ip, port, WorkingDir, argv, autostart, statuschange, evaluator, website)
    taskbar_instance = BeremizTaskBarIcon(pyroserver, enablewx)
else:
    pyroserver = Server(servicename, given_ip, port, WorkingDir, argv, autostart, website=website)

if havetwisted or havewx:
    pyro_thread=Thread(target=pyroserver.Loop)
    pyro_thread.start()

    if havetwisted:
        reactor.run()
    elif havewx:
        app.MainLoop()
else:
    try :
        pyroserver.Loop()
    except KeyboardInterrupt,e:
        pass
pyroserver.Quit()
sys.exit(0)
