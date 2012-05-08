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


updateinfo_url = None

import os, sys, getopt, wx
import __builtin__
from wx.lib.agw.advancedsplash import AdvancedSplash
import tempfile
import shutil
import random
import time
from types import ListType

CWD = os.path.split(os.path.realpath(__file__))[0]

def Bpath(*args):
    return os.path.join(CWD,*args)

if __name__ == '__main__':
    def usage():
        print "\nUsage of Beremiz.py :"
        print "\n   %s [Projectpath] [Buildpath]\n"%sys.argv[0]
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hu:", ["help", "updatecheck="])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-u", "--updatecheck"):
            updateinfo_url = a
    
    if len(args) > 2:
        usage()
        sys.exit()
    elif len(args) == 1:
        projectOpen = args[0]
        buildpath = None
    elif len(args) == 2:
        projectOpen = args[0]
        buildpath = args[1]
    else:
        projectOpen = None
        buildpath = None
    
    if os.path.exists("BEREMIZ_DEBUG"):
        __builtin__.__dict__["BMZ_DBG"] = True
    else :
        __builtin__.__dict__["BMZ_DBG"] = False

    app = wx.PySimpleApp(redirect=BMZ_DBG)
    app.SetAppName('beremiz')
    wx.InitAllImageHandlers()
    
    # popup splash
    bmp = wx.Image(Bpath("images","splash.png")).ConvertToBitmap()
    #splash=AdvancedSplash(None, bitmap=bmp, style=wx.SPLASH_CENTRE_ON_SCREEN, timeout=4000)
    splash=AdvancedSplash(None, bitmap=bmp)
    wx.Yield()

    if updateinfo_url is not None:
        updateinfo = "Fetching %s" % updateinfo_url
        # warn for possible updates
        def updateinfoproc():
            global updateinfo
            try :
                import urllib2
                updateinfo = urllib2.urlopen(updateinfo_url,None).read()
            except :
                updateinfo = "update info unavailable." 
                
        from threading import Thread
        splash.SetText(text=updateinfo)
        wx.Yield()
        updateinfoThread = Thread(target=updateinfoproc)
        updateinfoThread.start()
        updateinfoThread.join(2)
        splash.SetText(text=updateinfo)
        wx.Yield()

# Import module for internationalization
import gettext

# Get folder containing translation files
localedir = os.path.join(CWD,"locale")
# Get the default language
langid = wx.LANGUAGE_DEFAULT
# Define translation domain (name of translation files)
domain = "Beremiz"

# Define locale for wx
loc = __builtin__.__dict__.get('loc', None)
if loc is None:
    test_loc = wx.Locale(langid)
    test_loc.AddCatalogLookupPathPrefix(localedir)
    if test_loc.AddCatalog(domain):
        loc = wx.Locale(langid)
    else:
        loc = wx.Locale(wx.LANGUAGE_ENGLISH)
    __builtin__.__dict__['loc'] = loc
# Define location for searching translation files
loc.AddCatalogLookupPathPrefix(localedir)
# Define locale domain
loc.AddCatalog(domain)

def unicode_translation(message):
    return wx.GetTranslation(message).encode("utf-8")

if __name__ == '__main__':
    __builtin__.__dict__['_'] = wx.GetTranslation#unicode_translation

#Quick hack to be able to find Beremiz IEC tools. Should be config params.
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(base_folder)
sys.path.append(os.path.join(base_folder, "plcopeneditor"))

import wx.lib.buttons, wx.lib.statbmp
from util.TextCtrlAutoComplete import TextCtrlAutoComplete
import cPickle
from util.BrowseValuesLibraryDialog import BrowseValuesLibraryDialog
import types, time, re, platform, time, traceback, commands
from ProjectController import ProjectController, MATIEC_ERROR_MODEL
from util import MiniTextControler
from ProcessLogger import ProcessLogger

from docutils import *
from PLCOpenEditor import IDEFrame, AppendMenu, TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU, DISPLAYMENU, TYPESTREE, INSTANCESTREE, LIBRARYTREE, SCALING, PAGETITLES, USE_AUI
from PLCOpenEditor import EditorPanel, Viewer, TextViewer, GraphicViewer, ResourceEditor, ConfigurationEditor, DataTypeEditor
from PLCControler import LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY

SCROLLBAR_UNIT = 10
WINDOW_COLOUR = wx.Colour(240,240,240)
TITLE_COLOUR = wx.Colour(200,200,220)
CHANGED_TITLE_COLOUR = wx.Colour(220,200,220)
CHANGED_WINDOW_COLOUR = wx.Colour(255,240,240)

if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 16,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 18,
             }

MAX_RECENT_PROJECTS = 10

# Some helpers to tweak GenBitmapTextButtons
# TODO: declare customized classes instead.
gen_mini_GetBackgroundBrush = lambda obj:lambda dc: wx.Brush(obj.GetParent().GetBackgroundColour(), wx.SOLID)
gen_textbutton_GetLabelSize = lambda obj:lambda:(wx.lib.buttons.GenButton._GetLabelSize(obj)[:-1] + (False,))

def make_genbitmaptogglebutton_flat(button):
    button.GetBackgroundBrush = gen_mini_GetBackgroundBrush(button)
    button.labelDelta = 0
    button.SetBezelWidth(0)
    button.SetUseFocusIndicator(False)

# Patch wx.lib.imageutils so that gray is supported on alpha images
import wx.lib.imageutils
from wx.lib.imageutils import grayOut as old_grayOut
def grayOut(anImage):
    if anImage.HasAlpha():
        AlphaData = anImage.GetAlphaData()
    else :
        AlphaData = None

    old_grayOut(anImage)

    if AlphaData is not None:
        anImage.SetAlphaData(AlphaData)

wx.lib.imageutils.grayOut = grayOut

class GenBitmapTextButton(wx.lib.buttons.GenBitmapTextButton):
    def _GetLabelSize(self):
        """ used internally """
        w, h = self.GetTextExtent(self.GetLabel())
        if not self.bmpLabel:
            return w, h, False       # if there isn't a bitmap use the size of the text

        w_bmp = self.bmpLabel.GetWidth()+2
        h_bmp = self.bmpLabel.GetHeight()+2
        height = h + h_bmp
        if w_bmp > w:
            width = w_bmp
        else:
            width = w
        return width, height, False

    def DrawLabel(self, dc, width, height, dw=0, dy=0):
        bmp = self.bmpLabel
        if bmp != None:     # if the bitmap is used
            if self.bmpDisabled and not self.IsEnabled():
                bmp = self.bmpDisabled
            if self.bmpFocus and self.hasFocus:
                bmp = self.bmpFocus
            if self.bmpSelected and not self.up:
                bmp = self.bmpSelected
            bw,bh = bmp.GetWidth(), bmp.GetHeight()
            if not self.up:
                dw = dy = self.labelDelta
            hasMask = bmp.GetMask() != None
        else:
            bw = bh = 0     # no bitmap -> size is zero

        dc.SetFont(self.GetFont())
        if self.IsEnabled():
            dc.SetTextForeground(self.GetForegroundColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)        # size of text
        if not self.up:
            dw = dy = self.labelDelta

        pos_x = (width-bw)/2+dw      # adjust for bitmap and text to centre
        pos_y = (height-bh-th)/2+dy
        if bmp !=None:
            dc.DrawBitmap(bmp, pos_x, pos_y, hasMask) # draw bitmap if available
            pos_x = (width-tw)/2+dw      # adjust for bitmap and text to centre
            pos_y += bh + 2

        dc.DrawText(label, pos_x, pos_y)      # draw the text


class GenStaticBitmap(wx.lib.statbmp.GenStaticBitmap):
    """ Customized GenStaticBitmap, fix transparency redraw bug on wx2.8/win32, 
    and accept image name as __init__ parameter, fail silently if file do not exist"""
    def __init__(self, parent, ID, bitmapname,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = 0,
                 name = "genstatbmp"):
        
        bitmappath = Bpath( "images", bitmapname)
        if os.path.isfile(bitmappath):
            bitmap = wx.Bitmap(bitmappath)
        else:
            bitmap = None
        wx.lib.statbmp.GenStaticBitmap.__init__(self, parent, ID, bitmap,
                 pos, size,
                 style,
                 name)
        
    def OnPaint(self, event):
        dc = wx.PaintDC(self)
        colour = self.GetParent().GetBackgroundColour()
        dc.SetPen(wx.Pen(colour))
        dc.SetBrush(wx.Brush(colour ))
        dc.DrawRectangle(0, 0, *dc.GetSizeTuple())
        if self._bitmap:
            dc.DrawBitmap(self._bitmap, 0, 0, True)

                        
from threading import Lock,Timer,currentThread
MainThread = currentThread().ident
REFRESH_PERIOD = 0.1
from time import time as gettime
class LogPseudoFile:
    """ Base class for file like objects to facilitate StdOut for the Shell."""
    def __init__(self, output, risecall):
        self.red_white = wx.TextAttr("RED", "WHITE")
        self.red_yellow = wx.TextAttr("RED", "YELLOW")
        self.black_white = wx.TextAttr("BLACK", "WHITE")
        self.default_style = None
        self.output = output
        self.risecall = risecall
        # to prevent rapid fire on rising log panel
        self.rising_timer = 0
        self.lock = Lock()
        self.YieldLock = Lock()
        self.RefreshLock = Lock()
        self.stack = []
        self.LastRefreshTime = gettime()
        self.LastRefreshTimer = None

    def write(self, s, style = None):
        if self.lock.acquire():
            self.stack.append((s,style))
            self.lock.release()
            current_time = gettime()
            if self.LastRefreshTimer:
                self.LastRefreshTimer.cancel()
                self.LastRefreshTimer=None
            if current_time - self.LastRefreshTime > REFRESH_PERIOD and self.RefreshLock.acquire(False):
                self._should_write()
            else:
                self.LastRefreshTimer = Timer(REFRESH_PERIOD, self._should_write)
                self.LastRefreshTimer.start()

    def _should_write(self):
        wx.CallAfter(self._write)
        if MainThread == currentThread().ident:
            app = wx.GetApp()
            if app is not None:
                if self.YieldLock.acquire(0):
                    app.Yield()
                    self.YieldLock.release()

    def _write(self):
        if self.output :
            self.output.Freeze(); 
            self.lock.acquire()
            for s, style in self.stack:
                if style is None : style=self.black_white
                if self.default_style != style: 
                    self.output.SetDefaultStyle(style)
                    self.default_style = style
                self.output.AppendText(s)
                self.output.ScrollLines(s.count('\n')+1)
            self.stack = []
            self.lock.release()
            self.output.ShowPosition(self.output.GetLastPosition())
            self.output.Thaw()
            self.LastRefreshTime = gettime()
            try:
                self.RefreshLock.release()
            except:
                pass
            newtime = time.time()
            if newtime - self.rising_timer > 1:
                self.risecall()
            self.rising_timer = newtime

    def write_warning(self, s):
        self.write(s,self.red_white)

    def write_error(self, s):
        self.write(s,self.red_yellow)

    def writeyield(self, s):
        self.write(s)
        wx.GetApp().Yield()

    def flush(self):
        self.output.SetValue("")
    
    def isatty(self):
        return false

[ID_BEREMIZ, ID_BEREMIZMAINSPLITTER, 
 ID_BEREMIZPLCCONFIG, ID_BEREMIZLOGCONSOLE, 
 ID_BEREMIZINSPECTOR] = [wx.NewId() for _init_ctrls in range(5)]

[ID_FILEMENURECENTPROJECTS,
] = [wx.NewId() for _init_ctrls in range(1)]

CONFNODEMENU_POSITION = 3

class Beremiz(IDEFrame):
	
    def _init_coll_MenuBar_Menus(self, parent):
        IDEFrame._init_coll_MenuBar_Menus(self, parent)
        
        parent.Insert(pos=CONFNODEMENU_POSITION, 
                      menu=self.ConfNodeMenu, title=_(u'&ConfNode'))
    
    def _init_utils(self):
        self.ConfNodeMenu = wx.Menu(title='')
        self.RecentProjectsMenu = wx.Menu(title='')
        
        IDEFrame._init_utils(self)
        
    def _init_coll_FileMenu_Items(self, parent):
        AppendMenu(parent, help='', id=wx.ID_NEW,
              kind=wx.ITEM_NORMAL, text=_(u'New\tCTRL+N'))
        AppendMenu(parent, help='', id=wx.ID_OPEN,
              kind=wx.ITEM_NORMAL, text=_(u'Open\tCTRL+O'))
        parent.AppendMenu(ID_FILEMENURECENTPROJECTS, _("&Recent Projects"), self.RecentProjectsMenu)
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_SAVE,
              kind=wx.ITEM_NORMAL, text=_(u'Save\tCTRL+S'))
        AppendMenu(parent, help='', id=wx.ID_SAVEAS,
              kind=wx.ITEM_NORMAL, text=_(u'Save as\tCTRL+SHIFT+S'))
        AppendMenu(parent, help='', id=wx.ID_CLOSE,
              kind=wx.ITEM_NORMAL, text=_(u'Close Tab\tCTRL+W'))
        AppendMenu(parent, help='', id=wx.ID_CLOSE_ALL,
              kind=wx.ITEM_NORMAL, text=_(u'Close Project\tCTRL+SHIFT+W'))
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_PAGE_SETUP,
              kind=wx.ITEM_NORMAL, text=_(u'Page Setup\tCTRL+ALT+P'))
        AppendMenu(parent, help='', id=wx.ID_PREVIEW,
              kind=wx.ITEM_NORMAL, text=_(u'Preview\tCTRL+SHIFT+P'))
        AppendMenu(parent, help='', id=wx.ID_PRINT,
              kind=wx.ITEM_NORMAL, text=_(u'Print\tCTRL+P'))
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_PROPERTIES,
              kind=wx.ITEM_NORMAL, text=_(u'&Properties'))
        parent.AppendSeparator()
        AppendMenu(parent, help='', id=wx.ID_EXIT,
              kind=wx.ITEM_NORMAL, text=_(u'Quit\tCTRL+Q'))
        
        self.Bind(wx.EVT_MENU, self.OnNewProjectMenu, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.OnOpenProjectMenu, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectMenu, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectAsMenu, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnCloseTabMenu, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnCloseProjectMenu, id=wx.ID_CLOSE_ALL)
        self.Bind(wx.EVT_MENU, self.OnPageSetupMenu, id=wx.ID_PAGE_SETUP)
        self.Bind(wx.EVT_MENU, self.OnPreviewMenu, id=wx.ID_PREVIEW)
        self.Bind(wx.EVT_MENU, self.OnPrintMenu, id=wx.ID_PRINT)
        self.Bind(wx.EVT_MENU, self.OnPropertiesMenu, id=wx.ID_PROPERTIES)
        self.Bind(wx.EVT_MENU, self.OnQuitMenu, id=wx.ID_EXIT)
    
        self.AddToMenuToolBar([(wx.ID_NEW, "new.png", _(u'New'), None),
                               (wx.ID_OPEN, "open.png", _(u'Open'), None),
                               (wx.ID_SAVE, "save.png", _(u'Save'), None),
                               (wx.ID_SAVEAS, "saveas.png", _(u'Save As...'), None),
                               (wx.ID_PRINT, "print.png", _(u'Print'), None)])
    
    def _init_coll_HelpMenu_Items(self, parent):
        parent.Append(help='', id=wx.ID_HELP,
              kind=wx.ITEM_NORMAL, text=_(u'Beremiz\tF1'))
        parent.Append(help='', id=wx.ID_ABOUT,
              kind=wx.ITEM_NORMAL, text=_(u'About'))
        self.Bind(wx.EVT_MENU, self.OnBeremizMenu, id=wx.ID_HELP)
        self.Bind(wx.EVT_MENU, self.OnAboutMenu, id=wx.ID_ABOUT)
    
    def _init_coll_PLCConfigMainSizer_Items(self, parent):
        parent.AddSizer(self.PLCParamsSizer, 0, border=10, flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        parent.AddSizer(self.ConfNodeTreeSizer, 0, border=10, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
    def _init_coll_PLCConfigMainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_ConfNodeTreeSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableCol(1)
        
    def _init_beremiz_sizers(self):
        self.PLCConfigMainSizer = wx.FlexGridSizer(cols=1, hgap=2, rows=2, vgap=2)
        self.PLCParamsSizer = wx.BoxSizer(wx.VERTICAL)
        #self.ConfNodeTreeSizer = wx.FlexGridSizer(cols=3, hgap=0, rows=0, vgap=2)
        self.ConfNodeTreeSizer = wx.FlexGridSizer(cols=2, hgap=0, rows=0, vgap=2)
        
        self._init_coll_PLCConfigMainSizer_Items(self.PLCConfigMainSizer)
        self._init_coll_PLCConfigMainSizer_Growables(self.PLCConfigMainSizer)
        self._init_coll_ConfNodeTreeSizer_Growables(self.ConfNodeTreeSizer)
        
        self.PLCConfig.SetSizer(self.PLCConfigMainSizer)
        
    def _init_ctrls(self, prnt):
        IDEFrame._init_ctrls(self, prnt)
        
        self.Bind(wx.EVT_MENU, self.OnOpenWidgetInspector, id=ID_BEREMIZINSPECTOR)
        accels = [wx.AcceleratorEntry(wx.ACCEL_CTRL|wx.ACCEL_ALT, ord('I'), ID_BEREMIZINSPECTOR)]
        for method,shortcut in [("Stop",     wx.WXK_F4),
                                ("Run",      wx.WXK_F5),
                                ("Transfer", wx.WXK_F6),
                                ("Connect",  wx.WXK_F7),
                                ("Build",    wx.WXK_F11)]:
            def OnMethodGen(obj,meth):
                def OnMethod(evt):
                    if obj.CTR is not None:
                       obj.CTR.CallMethod('_'+meth)
                    wx.CallAfter(self.RefreshAll)
                return OnMethod
            newid = wx.NewId()
            self.Bind(wx.EVT_MENU, OnMethodGen(self,method), id=newid)
            accels += [wx.AcceleratorEntry(wx.ACCEL_NORMAL, shortcut,newid)]
        
        self.SetAcceleratorTable(wx.AcceleratorTable(accels))
        
        self.PLCConfig = wx.ScrolledWindow(id=ID_BEREMIZPLCCONFIG,
              name='PLCConfig', parent=self.BottomNoteBook, pos=wx.Point(0, 0),
              size=wx.Size(-1, -1), style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER|wx.HSCROLL|wx.VSCROLL)
        self.PLCConfig.SetBackgroundColour(wx.WHITE)
        self.PLCConfig.Bind(wx.EVT_LEFT_DOWN, self.OnPanelLeftDown)
        self.PLCConfig.Bind(wx.EVT_SIZE, self.OnMoveWindow)
        self.PLCConfig.Bind(wx.EVT_MOUSEWHEEL, self.OnPLCConfigScroll)
        self.MainTabs["PLCConfig"] = (self.PLCConfig, _("Topology"))
        self.BottomNoteBook.InsertPage(0, self.PLCConfig, _("Topology"), True)
        
        self.LogConsole = wx.TextCtrl(id=ID_BEREMIZLOGCONSOLE, value='',
                  name='LogConsole', parent=self.BottomNoteBook, pos=wx.Point(0, 0),
                  size=wx.Size(0, 0), style=wx.TE_MULTILINE|wx.TE_RICH2)
        self.LogConsole.Bind(wx.EVT_LEFT_DCLICK, self.OnLogConsoleDClick)
        self.MainTabs["LogConsole"] = (self.LogConsole, _("Log Console"))
        self.BottomNoteBook.AddPage(*self.MainTabs["LogConsole"])
        if USE_AUI:
            self.BottomNoteBook.Split(self.BottomNoteBook.GetPageIndex(self.LogConsole), wx.RIGHT)
        
        self._init_beremiz_sizers()

    def __init__(self, parent, projectOpen=None, buildpath=None, ctr=None, debug=True):
        IDEFrame.__init__(self, parent, debug)
        self.Log = LogPseudoFile(self.LogConsole,self.RiseLogConsole)
        
        self.local_runtime = None
        self.runtime_port = None
        self.local_runtime_tmpdir = None
        
        self.DisableEvents = False
        # Variable allowing disabling of PLCConfig scroll when Popup shown 
        self.ScrollingEnabled = True
        
        self.LastPanelSelected = None
        
        self.ConfNodeInfos = {}
        
        # Define Tree item icon list
        self.LocationImageList = wx.ImageList(16, 16)
        self.LocationImageDict = {}
        
        # Icons for location items
        for imgname, itemtype in [
            ("CONFIGURATION", LOCATION_CONFNODE),
            ("RESOURCE",      LOCATION_MODULE),
            ("PROGRAM",       LOCATION_GROUP),
            ("VAR_INPUT",     LOCATION_VAR_INPUT),
            ("VAR_OUTPUT",    LOCATION_VAR_OUTPUT),
            ("VAR_LOCAL",     LOCATION_VAR_MEMORY)]:
            self.LocationImageDict[itemtype]=self.LocationImageList.Add(wx.Bitmap(os.path.join(base_folder, "plcopeneditor", 'Images', '%s.png'%imgname)))
        
        # Add beremiz's icon in top left corner of the frame
        self.SetIcon(wx.Icon(Bpath( "images", "brz.ico"), wx.BITMAP_TYPE_ICO))
        
        if projectOpen is None and self.Config.HasEntry("currenteditedproject"):
            projectOpen = str(self.Config.Read("currenteditedproject"))
            if projectOpen == "":
                projectOpen = None
        
        if projectOpen is not None and os.path.isdir(projectOpen):
            self.CTR = ProjectController(self, self.Log)
            self.Controler = self.CTR
            result = self.CTR.LoadProject(projectOpen, buildpath)
            if not result:
                self.LibraryPanel.SetControler(self.Controler)
                self.RefreshConfigRecentProjects(os.path.abspath(projectOpen))
                self._Refresh(TYPESTREE, INSTANCESTREE, LIBRARYTREE)
                self.RefreshAll()
            else:
                self.ResetView()
                self.ShowErrorMessage(result)
        else:
            self.CTR = ctr
            self.Controler = ctr
            if ctr is not None:
                self.LibraryPanel.SetControler(self.Controler)
                self._Refresh(TYPESTREE, INSTANCESTREE, LIBRARYTREE)
                self.RefreshAll()
        if self.EnableDebug:
            self.DebugVariablePanel.SetDataProducer(self.CTR)
        
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        
        self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU, DISPLAYMENU)
        self.RefreshConfNodeMenu()
        self.LogConsole.SetFocus()

    def RiseLogConsole(self):
        self.BottomNoteBook.SetSelection(self.BottomNoteBook.GetPageIndex(self.LogConsole))
        
    def RefreshTitle(self):
        name = _("Beremiz")
        if self.CTR is not None:
            projectname = self.CTR.GetProjectName()
            if self.CTR.ProjectTestModified():
                projectname = "~%s~" % projectname
            self.SetTitle("%s - %s" % (name, projectname))
        else:
            self.SetTitle(name)

    def StartLocalRuntime(self, taskbaricon = True):
        if (self.local_runtime is None) or (self.local_runtime.exitcode is not None):
            # create temporary directory for runtime working directory
            self.local_runtime_tmpdir = tempfile.mkdtemp()
            # choose an arbitrary random port for runtime
            self.runtime_port = int(random.random() * 1000) + 61131
            # launch local runtime
            self.local_runtime = ProcessLogger(self.Log,
                                               "\"%s\" \"%s\" -p %s -i localhost %s %s"%(sys.executable,
                                                           Bpath("Beremiz_service.py"),
                                                           self.runtime_port,
                                                           {False : "-x 0", True :"-x 1"}[taskbaricon],
                                                           self.local_runtime_tmpdir),
                                                           no_gui=False,
                                                           timeout=500, keyword = "working")
            self.local_runtime.spin()
        return self.runtime_port
    
    def KillLocalRuntime(self):
        if self.local_runtime is not None:
            # shutdown local runtime
            self.local_runtime.kill(gently=False)
            # clear temp dir
            shutil.rmtree(self.local_runtime_tmpdir)
            
            self.local_runtime = None

    def OnOpenWidgetInspector(self, evt):
        # Activate the widget inspection tool
        from wx.lib.inspection import InspectionTool
        if not InspectionTool().initialized:
            InspectionTool().Init()

        # Find a widget to be selected in the tree.  Use either the
        # one under the cursor, if any, or this frame.
        wnd = wx.FindWindowAtPointer()
        if not wnd:
            wnd = self
        InspectionTool().Show(wnd, True)

    def OnLogConsoleDClick(self, event):
        wx.CallAfter(self.SearchLineForError)
        event.Skip()

    def SearchLineForError(self):
        if self.CTR is not None:
            text = self.LogConsole.GetRange(0, self.LogConsole.GetInsertionPoint())
            line = self.LogConsole.GetLineText(len(text.splitlines()) - 1)
            result = MATIEC_ERROR_MODEL.match(line)
            if result is not None:
                first_line, first_column, last_line, last_column, error = result.groups()
                infos = self.CTR.ShowError(self.Log,
                                                  (int(first_line), int(first_column)), 
                                                  (int(last_line), int(last_column)))
	
    ## Function displaying an Error dialog in PLCOpenEditor.
    #  @return False if closing cancelled.
    def CheckSaveBeforeClosing(self, title=_("Close Project")):
        if self.CTR.ProjectTestModified():
            dialog = wx.MessageDialog(self,
                                      _("There are changes, do you want to save?"),
                                      title,
                                      wx.YES_NO|wx.CANCEL|wx.ICON_QUESTION)
            answer = dialog.ShowModal()
            dialog.Destroy()
            if answer == wx.ID_YES:
                self.CTR.SaveProject()
            elif answer == wx.ID_CANCEL:
                return False
        return True
    
    def GetTabInfos(self, tab):
        if (isinstance(tab, EditorPanel) and 
            not isinstance(tab, (Viewer, 
                                 TextViewer, 
                                 GraphicViewer, 
                                 ResourceEditor, 
                                 ConfigurationEditor, 
                                 DataTypeEditor))):
            return ("confnode", tab.Controler.CTNFullName())
        elif (isinstance(tab, TextViewer) and 
              (tab.Controler is None or isinstance(tab.Controler, MiniTextControler))):
            return ("confnode", None, tab.GetInstancePath())
        else:
            return IDEFrame.GetTabInfos(self, tab)
    
    def LoadTab(self, notebook, page_infos):
        if page_infos[0] == "confnode":
            if page_infos[1] is None:
                confnode = self.CTR
            else:
                confnode = self.CTR.GetChildByName(page_infos[1])
            return notebook.GetPageIndex(confnode._OpenView(*page_infos[2:]))
        else:
            return IDEFrame.LoadTab(self, notebook, page_infos)
    
    def OnCloseFrame(self, event):
        if self.CTR is None or self.CheckSaveBeforeClosing(_("Close Application")):
            if self.CTR is not None:
                self.CTR.KillDebugThread()
            self.KillLocalRuntime()
            
            self.SaveLastState()
            
            if self.CTR is not None:
                project_path = os.path.realpath(self.CTR.GetProjectPath())
            else:
                project_path = ""
            self.Config.Write("currenteditedproject", project_path)    
            self.Config.Flush()
            
            event.Skip()
        else:
            event.Veto()
    
    def OnMoveWindow(self, event):
        self.GetBestSize()
        self.RefreshScrollBars()
        event.Skip()
    
    def EnableScrolling(self, enable):
        self.ScrollingEnabled = enable
    
    def OnPLCConfigScroll(self, event):
        if self.ScrollingEnabled:
            event.Skip()

    def OnPanelLeftDown(self, event):
        focused = self.FindFocus()
        if isinstance(focused, TextCtrlAutoComplete):
            focused.DismissListBox()
        event.Skip()
    
    def RefreshFileMenu(self):
        self.RefreshRecentProjectsMenu()
        
        MenuToolBar = self.Panes["MenuToolBar"]
        if self.CTR is not None:
            selected = self.TabsOpened.GetSelection()
            if selected >= 0:
                graphic_viewer = isinstance(self.TabsOpened.GetPage(selected), Viewer)
            else:
                graphic_viewer = False
            if self.TabsOpened.GetPageCount() > 0:
                self.FileMenu.Enable(wx.ID_CLOSE, True)
                if graphic_viewer:
                    self.FileMenu.Enable(wx.ID_PREVIEW, True)
                    self.FileMenu.Enable(wx.ID_PRINT, True)
                    MenuToolBar.EnableTool(wx.ID_PRINT, True)
                else:
                    self.FileMenu.Enable(wx.ID_PREVIEW, False)
                    self.FileMenu.Enable(wx.ID_PRINT, False)
                    MenuToolBar.EnableTool(wx.ID_PRINT, False)
            else:
                self.FileMenu.Enable(wx.ID_CLOSE, False)
                self.FileMenu.Enable(wx.ID_PREVIEW, False)
                self.FileMenu.Enable(wx.ID_PRINT, False)
                MenuToolBar.EnableTool(wx.ID_PRINT, False)
            self.FileMenu.Enable(wx.ID_PAGE_SETUP, True)
            project_modified = self.CTR.ProjectTestModified()
            self.FileMenu.Enable(wx.ID_SAVE, project_modified)
            MenuToolBar.EnableTool(wx.ID_SAVE, project_modified)
            self.FileMenu.Enable(wx.ID_SAVEAS, True)
            MenuToolBar.EnableTool(wx.ID_SAVEAS, True)
            self.FileMenu.Enable(wx.ID_PROPERTIES, True)
            self.FileMenu.Enable(wx.ID_CLOSE_ALL, True)
        else:
            self.FileMenu.Enable(wx.ID_CLOSE, False)
            self.FileMenu.Enable(wx.ID_PAGE_SETUP, False)
            self.FileMenu.Enable(wx.ID_PREVIEW, False)
            self.FileMenu.Enable(wx.ID_PRINT, False)
            MenuToolBar.EnableTool(wx.ID_PRINT, False)
            self.FileMenu.Enable(wx.ID_SAVE, False)
            MenuToolBar.EnableTool(wx.ID_SAVE, False)
            self.FileMenu.Enable(wx.ID_SAVEAS, False)
            MenuToolBar.EnableTool(wx.ID_SAVEAS, False)
            self.FileMenu.Enable(wx.ID_PROPERTIES, False)
            self.FileMenu.Enable(wx.ID_CLOSE_ALL, False)
    
    def RefreshRecentProjectsMenu(self):
        for i in xrange(self.RecentProjectsMenu.GetMenuItemCount()):
            item = self.RecentProjectsMenu.FindItemByPosition(0)
            self.RecentProjectsMenu.Delete(item.GetId())
        
        recent_projects = cPickle.loads(str(self.Config.Read("RecentProjects", cPickle.dumps([]))))
        self.FileMenu.Enable(ID_FILEMENURECENTPROJECTS, len(recent_projects) > 0)
        for idx, projectpath in enumerate(recent_projects):
            id = wx.NewId()
            AppendMenu(self.RecentProjectsMenu, help='', id=id, 
                       kind=wx.ITEM_NORMAL, text="%d: %s" % (idx + 1, projectpath))
            self.Bind(wx.EVT_MENU, self.GenerateOpenRecentProjectFunction(projectpath), id=id)
    
    def GenerateOpenRecentProjectFunction(self, projectpath):
        def OpenRecentProject(event):
            if self.CTR is not None and not self.CheckSaveBeforeClosing():
                return
            
            self.OpenProject(projectpath)
        return OpenRecentProject
    
    def GenerateMenuRecursive(self, items, menu):
        for kind, infos in items:
            if isinstance(kind, ListType):
                text, id = infos
                submenu = wx.Menu('')
                self.GenerateMenuRecursive(kind, submenu)
                menu.AppendMenu(id, text, submenu)
            elif kind == wx.ITEM_SEPARATOR:
                menu.AppendSeparator()
            else:
                text, id, help, callback = infos
                AppendMenu(menu, help='', id=id, kind=kind, text=text)
                if callback is not None:
                    self.Bind(wx.EVT_MENU, callback, id=id)
    
    def RefreshConfNodeMenu(self):
        if self.CTR is not None:
            selected = self.TabsOpened.GetSelection()
            if selected >= 0:
                panel = self.TabsOpened.GetPage(selected)
            else:
                panel = None
            if panel != self.LastPanelSelected:
                for i in xrange(self.ConfNodeMenu.GetMenuItemCount()):
                    item = self.ConfNodeMenu.FindItemByPosition(0)
                    self.ConfNodeMenu.Delete(item.GetId())
                self.LastPanelSelected = panel
                if panel is not None:
                    items = panel.GetConfNodeMenuItems()
                else:
                    items = []
                self.MenuBar.EnableTop(CONFNODEMENU_POSITION, len(items) > 0)
                self.GenerateMenuRecursive(items, self.ConfNodeMenu)
            if panel is not None:
                panel.RefreshConfNodeMenu(self.ConfNodeMenu)
        else:
            self.MenuBar.EnableTop(CONFNODEMENU_POSITION, False)
        self.MenuBar.UpdateMenus()
    
    def RefreshScrollBars(self):
        xstart, ystart = self.PLCConfig.GetViewStart()
        window_size = self.PLCConfig.GetClientSize()
        sizer = self.PLCConfig.GetSizer()
        if sizer:
            maxx, maxy = sizer.GetMinSize()
            posx = max(0, min(xstart, (maxx - window_size[0]) / SCROLLBAR_UNIT))
            posy = max(0, min(ystart, (maxy - window_size[1]) / SCROLLBAR_UNIT))
            self.PLCConfig.Scroll(posx, posy)
            self.PLCConfig.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                maxx / SCROLLBAR_UNIT, maxy / SCROLLBAR_UNIT, posx, posy)

    def RefreshPLCParams(self):
        self.Freeze()
        self.ClearSizer(self.PLCParamsSizer)
        
        if self.CTR is not None:    
            plcwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
            if self.CTR.CTNTestModified():
                bkgdclr = CHANGED_TITLE_COLOUR
            else:
                bkgdclr = TITLE_COLOUR
                
            if self.CTR not in self.ConfNodeInfos:
                self.ConfNodeInfos[self.CTR] = {"right_visible" : False}
            
            plcwindow.SetBackgroundColour(TITLE_COLOUR)
            plcwindow.Bind(wx.EVT_LEFT_DOWN, self.OnPanelLeftDown)
            self.PLCParamsSizer.AddWindow(plcwindow, 0, border=0, flag=wx.GROW)
            
            plcwindowsizer = wx.BoxSizer(wx.HORIZONTAL)
            plcwindow.SetSizer(plcwindowsizer)
            
            st = wx.StaticText(plcwindow, -1)
            st.SetFont(wx.Font(faces["size"], wx.DEFAULT, wx.NORMAL, wx.BOLD, faceName = faces["helv"]))
            st.SetLabel(self.CTR.GetProjectName())
            plcwindowsizer.AddWindow(st, 0, border=5, flag=wx.ALL|wx.ALIGN_CENTER)
            
            addbutton_id = wx.NewId()
            addbutton = wx.lib.buttons.GenBitmapButton(id=addbutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'Add.png')),
                  name='AddConfNodeButton', parent=plcwindow, pos=wx.Point(0, 0),
                  size=wx.Size(16, 16), style=wx.NO_BORDER)
            addbutton.SetToolTipString(_("Add a sub confnode"))
            addbutton.Bind(wx.EVT_BUTTON, self.Gen_AddConfNodeMenu(self.CTR), id=addbutton_id)
            plcwindowsizer.AddWindow(addbutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)
    
            plcwindowmainsizer = wx.BoxSizer(wx.VERTICAL)
            plcwindowsizer.AddSizer(plcwindowmainsizer, 0, border=5, flag=wx.ALL)
            
            plcwindowbuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
            plcwindowmainsizer.AddSizer(plcwindowbuttonsizer, 0, border=0, flag=wx.ALIGN_CENTER)
            
            msizer = self.GenerateMethodButtonSizer(self.CTR, plcwindow, not self.ConfNodeInfos[self.CTR]["right_visible"])
            plcwindowbuttonsizer.AddSizer(msizer, 0, border=0, flag=wx.GROW)
            
            paramswindow = wx.Panel(plcwindow, -1, size=wx.Size(-1, -1), style=wx.TAB_TRAVERSAL)
            paramswindow.SetBackgroundColour(TITLE_COLOUR)
            paramswindow.Bind(wx.EVT_LEFT_DOWN, self.OnPanelLeftDown)
            plcwindowbuttonsizer.AddWindow(paramswindow, 0, border=0, flag=0)
            
            psizer = wx.BoxSizer(wx.HORIZONTAL)
            paramswindow.SetSizer(psizer)
            
            confnode_infos = self.CTR.GetParamsAttributes()
            self.RefreshSizerElement(paramswindow, psizer, self.CTR, confnode_infos, None, False)
            
            if not self.ConfNodeInfos[self.CTR]["right_visible"]:
                paramswindow.Hide()
            
            minimizebutton_id = wx.NewId()
            minimizebutton = wx.lib.buttons.GenBitmapToggleButton(id=minimizebutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'Maximize.png')),
                  name='MinimizeButton', parent=plcwindow, pos=wx.Point(0, 0),
                  size=wx.Size(24, 24), style=wx.NO_BORDER)
            make_genbitmaptogglebutton_flat(minimizebutton)
            minimizebutton.SetBitmapSelected(wx.Bitmap(Bpath( 'images', 'Minimize.png')))
            minimizebutton.SetToggle(self.ConfNodeInfos[self.CTR]["right_visible"])
            plcwindowbuttonsizer.AddWindow(minimizebutton, 0, border=5, flag=wx.ALL)
            
            def togglewindow(event):
                if minimizebutton.GetToggle():
                    paramswindow.Show()
                    msizer.SetCols(1)
                else:
                    paramswindow.Hide()
                    msizer.SetCols(len(self.CTR.ConfNodeMethods))
                self.ConfNodeInfos[self.CTR]["right_visible"] = minimizebutton.GetToggle()
                self.PLCConfigMainSizer.Layout()
                self.RefreshScrollBars()
                event.Skip()
            minimizebutton.Bind(wx.EVT_BUTTON, togglewindow, id=minimizebutton_id)
        
            self.ConfNodeInfos[self.CTR]["main"] = plcwindow
            self.ConfNodeInfos[self.CTR]["params"] = paramswindow
            
        self.PLCConfigMainSizer.Layout()
        self.RefreshScrollBars()
        self.Thaw()

    def GenerateEnableButton(self, parent, sizer, confnode):
        enabled = confnode.CTNEnabled()
        if enabled is not None:
            enablebutton_id = wx.NewId()
            enablebutton = wx.lib.buttons.GenBitmapToggleButton(id=enablebutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'Disabled.png')),
                  name='EnableButton', parent=parent, size=wx.Size(16, 16), pos=wx.Point(0, 0), style=0)#wx.NO_BORDER)
            enablebutton.SetToolTipString(_("Enable/Disable this confnode"))
            make_genbitmaptogglebutton_flat(enablebutton)
            enablebutton.SetBitmapSelected(wx.Bitmap(Bpath( 'images', 'Enabled.png')))
            enablebutton.SetToggle(enabled)
            def toggleenablebutton(event):
                res = self.SetConfNodeParamsAttribute(confnode, "BaseParams.Enabled", enablebutton.GetToggle())
                enablebutton.SetToggle(res)
                event.Skip()
            enablebutton.Bind(wx.EVT_BUTTON, toggleenablebutton, id=enablebutton_id)
            sizer.AddWindow(enablebutton, 0, border=0, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        else:
            sizer.AddSpacer(wx.Size(16, 16))
    
    def GenerateMethodButtonSizer(self, confnode, parent, horizontal = True):
        normal_bt_font=wx.Font(faces["size"] / 3, wx.DEFAULT, wx.NORMAL, wx.NORMAL, faceName = faces["helv"])
        mouseover_bt_font=wx.Font(faces["size"] / 3, wx.DEFAULT, wx.NORMAL, wx.NORMAL, underline=True, faceName = faces["helv"])
        if horizontal:
            msizer = wx.FlexGridSizer(cols=len(confnode.ConfNodeMethods))
        else:
            msizer = wx.FlexGridSizer(cols=1)
        for confnode_method in confnode.ConfNodeMethods:
            if "method" in confnode_method and confnode_method.get("shown",True):
                id = wx.NewId()
                label = confnode_method["name"]
                button = GenBitmapTextButton(id=id, parent=parent,
                    bitmap=wx.Bitmap(Bpath( "%s.png"%confnode_method.get("bitmap", os.path.join("images", "Unknown")))), label=label, 
                    name=label, pos=wx.DefaultPosition, style=wx.NO_BORDER)
                button.SetFont(normal_bt_font)
                button.SetToolTipString(confnode_method["tooltip"])
                button.Bind(wx.EVT_BUTTON, self.GetButtonCallBackFunction(confnode, confnode_method["method"]), id=id)
                # a fancy underline on mouseover
                def setFontStyle(b, s):
                    def fn(event):
                        b.SetFont(s)
                        b.Refresh()
                        event.Skip()
                    return fn
                button.Bind(wx.EVT_ENTER_WINDOW, setFontStyle(button, mouseover_bt_font))
                button.Bind(wx.EVT_LEAVE_WINDOW, setFontStyle(button, normal_bt_font))
                #hack to force size to mini
                if not confnode_method.get("enabled",True):
                    button.Disable()
                msizer.AddWindow(button, 0, border=0, flag=wx.ALIGN_CENTER)
        return msizer

    def GenerateParamsPanel(self, confnode, bkgdclr, top_offset=0):
        rightwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
        rightwindow.SetBackgroundColour(bkgdclr)
        
        rightwindowmainsizer = wx.BoxSizer(wx.VERTICAL)
        rightwindow.SetSizer(rightwindowmainsizer)
        
        rightwindowsizer = wx.FlexGridSizer(cols=2, rows=1)
        rightwindowsizer.AddGrowableCol(1)
        rightwindowsizer.AddGrowableRow(0)
        rightwindowmainsizer.AddSizer(rightwindowsizer, 0, border=0, flag=wx.GROW)
        
        msizer = self.GenerateMethodButtonSizer(confnode, rightwindow, not self.ConfNodeInfos[confnode]["right_visible"])
        rightwindowsizer.AddSizer(msizer, 0, border=top_offset, flag=wx.TOP|wx.GROW)
        
        rightparamssizer = wx.BoxSizer(wx.HORIZONTAL)
        rightwindowsizer.AddSizer(rightparamssizer, 0, border=0, flag=wx.ALIGN_RIGHT)
        
        paramswindow = wx.Panel(rightwindow, -1, size=wx.Size(-1, -1))
        paramswindow.SetBackgroundColour(bkgdclr)
        
        psizer = wx.BoxSizer(wx.VERTICAL)
        paramswindow.SetSizer(psizer)
        self.ConfNodeInfos[confnode]["params"] = paramswindow
        
        rightparamssizer.AddWindow(paramswindow, 0, border=5, flag=wx.ALL)
        
        confnode_infos = confnode.GetParamsAttributes()
        if len(confnode_infos) > 0:
            self.RefreshSizerElement(paramswindow, psizer, confnode, confnode_infos, None, False)
            
            if not self.ConfNodeInfos[confnode]["right_visible"]:
                paramswindow.Hide()
            
            rightminimizebutton_id = wx.NewId()
            rightminimizebutton = wx.lib.buttons.GenBitmapToggleButton(id=rightminimizebutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'Maximize.png')),
                  name='MinimizeButton', parent=rightwindow, pos=wx.Point(0, 0),
                  size=wx.Size(24, 24), style=wx.NO_BORDER)
            make_genbitmaptogglebutton_flat(rightminimizebutton)
            rightminimizebutton.SetBitmapSelected(wx.Bitmap(Bpath( 'images', 'Minimize.png')))
            rightminimizebutton.SetToggle(self.ConfNodeInfos[confnode]["right_visible"])
            rightparamssizer.AddWindow(rightminimizebutton, 0, border=5, flag=wx.ALL)
                        
            def togglerightwindow(event):
                if rightminimizebutton.GetToggle():
                    rightparamssizer.Show(0)
                    msizer.SetCols(1)
                else:
                    rightparamssizer.Hide(0)
                    msizer.SetCols(len(confnode.ConfNodeMethods))
                self.ConfNodeInfos[confnode]["right_visible"] = rightminimizebutton.GetToggle()
                self.PLCConfigMainSizer.Layout()
                self.RefreshScrollBars()
                event.Skip()
            rightminimizebutton.Bind(wx.EVT_BUTTON, togglerightwindow, id=rightminimizebutton_id)
        
        return rightwindow
    

    def RefreshConfNodeTree(self):
        self.Freeze()
        self.ClearSizer(self.ConfNodeTreeSizer)
        if self.CTR is not None:
            for child in self.CTR.IECSortedChildren():
                self.GenerateTreeBranch(child)
                if not self.ConfNodeInfos[child]["expanded"]:
                    self.CollapseConfNode(child)
        self.PLCConfigMainSizer.Layout()
        self.RefreshScrollBars()
        self.Thaw()

    def SetConfNodeParamsAttribute(self, confnode, *args, **kwargs):
        res, StructChanged = confnode.SetParamsAttribute(*args, **kwargs)
        if StructChanged:
            wx.CallAfter(self.RefreshConfNodeTree)
        else:
            if confnode == self.CTR:
                bkgdclr = CHANGED_TITLE_COLOUR
                items = ["main", "params"]
            else:
                bkgdclr = CHANGED_WINDOW_COLOUR
                items = ["left", "right", "params"]
            for i in items:
                self.ConfNodeInfos[confnode][i].SetBackgroundColour(bkgdclr)
                self.ConfNodeInfos[confnode][i].Refresh()
        self._Refresh(TITLE, FILEMENU)
        return res

    def ExpandConfNode(self, confnode, force = False):
        for child in self.ConfNodeInfos[confnode]["children"]:
            self.ConfNodeInfos[child]["left"].Show()
            self.ConfNodeInfos[child]["right"].Show()
            if force or self.ConfNodeInfos[child]["expanded"]:
                self.ExpandConfNode(child, force)
                if force:
                    self.ConfNodeInfos[child]["expanded"] = True
        locations_infos = self.ConfNodeInfos[confnode].get("locations_infos", None)
        if locations_infos is not None:
            if force or locations_infos["root"]["expanded"]:
                self.ExpandLocation(locations_infos, "root", force)
                if force:
                    locations_infos["root"]["expanded"] = True
    
    def CollapseConfNode(self, confnode, force = False):
        for child in self.ConfNodeInfos[confnode]["children"]:
            self.ConfNodeInfos[child]["left"].Hide()
            self.ConfNodeInfos[child]["right"].Hide()
            self.CollapseConfNode(child, force)
            if force:
                self.ConfNodeInfos[child]["expanded"] = False
        locations_infos = self.ConfNodeInfos[confnode].get("locations_infos", None)
        if locations_infos is not None:
            self.CollapseLocation(locations_infos, "root", force)
            if force:
                locations_infos["root"]["expanded"] = False

    def ExpandLocation(self, locations_infos, group, force = False, refresh_size=True):
        locations_infos[group]["expanded"] = True
        if group == "root":
            if locations_infos[group]["left"] is not None:
                locations_infos[group]["left"].Show()
            if locations_infos[group]["right"] is not None:
                locations_infos[group]["right"].Show()
        elif locations_infos["root"]["left"] is not None:
            locations_infos["root"]["left"].Expand(locations_infos[group]["item"])
            if force:
                for child in locations_infos[group]["children"]:
                    self.ExpandLocation(locations_infos, child, force, False)
        if locations_infos["root"]["left"] is not None and refresh_size:
            self.RefreshTreeCtrlSize(locations_infos["root"]["left"])
        
    def CollapseLocation(self, locations_infos, group, force = False, refresh_size=True):
        locations_infos[group]["expanded"] = False
        if group == "root":
            if locations_infos[group]["left"] is not None:
                locations_infos[group]["left"].Hide()
            if locations_infos[group]["right"] is not None:
                locations_infos[group]["right"].Hide()
        elif locations_infos["root"]["left"] is not None:
            locations_infos["root"]["left"].Collapse(locations_infos[group]["item"])
            if force:
                for child in locations_infos[group]["children"]:
                    self.CollapseLocation(locations_infos, child, force, False)
        if locations_infos["root"]["left"] is not None and refresh_size:
            self.RefreshTreeCtrlSize(locations_infos["root"]["left"])
    
    def GenerateTreeBranch(self, confnode):
        leftwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
        if confnode.CTNTestModified():
            bkgdclr=CHANGED_WINDOW_COLOUR
        else:
            bkgdclr=WINDOW_COLOUR

        leftwindow.SetBackgroundColour(bkgdclr)
        
        if not self.ConfNodeInfos.has_key(confnode):
            self.ConfNodeInfos[confnode] = {"expanded" : False, "right_visible" : False}
            
        self.ConfNodeInfos[confnode]["children"] = confnode.IECSortedChildren()
        confnode_locations = []
        if len(self.ConfNodeInfos[confnode]["children"]) == 0:
            confnode_locations = confnode.GetVariableLocationTree()["children"]
            if not self.ConfNodeInfos[confnode].has_key("locations_infos"):
                self.ConfNodeInfos[confnode]["locations_infos"] = {"root": {"expanded" : False}}
            
            self.ConfNodeInfos[confnode]["locations_infos"]["root"]["left"] = None
            self.ConfNodeInfos[confnode]["locations_infos"]["root"]["right"] = None
            self.ConfNodeInfos[confnode]["locations_infos"]["root"]["children"] = []
        
        self.ConfNodeTreeSizer.AddWindow(leftwindow, 0, border=0, flag=wx.GROW)
        
        leftwindowsizer = wx.FlexGridSizer(cols=1, rows=2)
        leftwindowsizer.AddGrowableCol(0)
        leftwindow.SetSizer(leftwindowsizer)
        
        leftbuttonmainsizer = wx.FlexGridSizer(cols=3, rows=1)
        leftbuttonmainsizer.AddGrowableCol(0)
        leftwindowsizer.AddSizer(leftbuttonmainsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT) #|wx.TOP
        
        leftbuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        leftbuttonmainsizer.AddSizer(leftbuttonsizer, 0, border=5, flag=wx.GROW|wx.RIGHT)
        
        leftsizer = wx.BoxSizer(wx.VERTICAL)
        leftbuttonsizer.AddSizer(leftsizer, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)

        rolesizer = wx.BoxSizer(wx.HORIZONTAL)
        leftsizer.AddSizer(rolesizer, 0, border=0, flag=wx.GROW|wx.RIGHT)
        
        #self.GenerateEnableButton(leftwindow, rolesizer, confnode)

        roletext = wx.StaticText(leftwindow, -1)
        roletext.SetLabel(confnode.CTNHelp)
        rolesizer.AddWindow(roletext, 0, border=5, flag=wx.RIGHT|wx.ALIGN_LEFT)
        
        confnode_IECChannel = confnode.BaseParams.getIEC_Channel()
        
        iecsizer = wx.BoxSizer(wx.HORIZONTAL)
        leftsizer.AddSizer(iecsizer, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)

        st = wx.StaticText(leftwindow, -1)
        st.SetFont(wx.Font(faces["size"], wx.DEFAULT, wx.NORMAL, wx.BOLD, faceName = faces["helv"]))
        st.SetLabel(confnode.GetFullIEC_Channel())
        iecsizer.AddWindow(st, 0, border=0, flag=0)

        updownsizer = wx.BoxSizer(wx.VERTICAL)
        iecsizer.AddSizer(updownsizer, 0, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        if confnode_IECChannel > 0:
            ieccdownbutton_id = wx.NewId()
            ieccdownbutton = wx.lib.buttons.GenBitmapButton(id=ieccdownbutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'IECCDown.png')),
                  name='IECCDownButton', parent=leftwindow, pos=wx.Point(0, 0),
                  size=wx.Size(16, 16), style=wx.NO_BORDER)
            ieccdownbutton.Bind(wx.EVT_BUTTON, self.GetItemChannelChangedFunction(confnode, confnode_IECChannel - 1), id=ieccdownbutton_id)
            updownsizer.AddWindow(ieccdownbutton, 0, border=0, flag=wx.ALIGN_LEFT)

        ieccupbutton_id = wx.NewId()
        ieccupbutton = wx.lib.buttons.GenBitmapTextButton(id=ieccupbutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'IECCUp.png')),
              name='IECCUpButton', parent=leftwindow, pos=wx.Point(0, 0),
              size=wx.Size(16, 16), style=wx.NO_BORDER)
        ieccupbutton.Bind(wx.EVT_BUTTON, self.GetItemChannelChangedFunction(confnode, confnode_IECChannel + 1), id=ieccupbutton_id)
        updownsizer.AddWindow(ieccupbutton, 0, border=0, flag=wx.ALIGN_LEFT)

        adddeletesizer = wx.BoxSizer(wx.VERTICAL)
        iecsizer.AddSizer(adddeletesizer, 0, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        deletebutton_id = wx.NewId()
        deletebutton = wx.lib.buttons.GenBitmapButton(id=deletebutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'Delete.png')),
              name='DeleteConfNodeButton', parent=leftwindow, pos=wx.Point(0, 0),
              size=wx.Size(16, 16), style=wx.NO_BORDER)
        deletebutton.SetToolTipString(_("Delete this confnode"))
        deletebutton.Bind(wx.EVT_BUTTON, self.GetDeleteButtonFunction(confnode), id=deletebutton_id)
        adddeletesizer.AddWindow(deletebutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)

        if len(confnode.CTNChildrenTypes) > 0:
            addbutton_id = wx.NewId()
            addbutton = wx.lib.buttons.GenBitmapButton(id=addbutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'Add.png')),
                  name='AddConfNodeButton', parent=leftwindow, pos=wx.Point(0, 0),
                  size=wx.Size(16, 16), style=wx.NO_BORDER)
            addbutton.SetToolTipString(_("Add a sub confnode"))
            addbutton.Bind(wx.EVT_BUTTON, self.Gen_AddConfNodeMenu(confnode), id=addbutton_id)
            adddeletesizer.AddWindow(addbutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)
        
        expandbutton_id = wx.NewId()
        expandbutton = wx.lib.buttons.GenBitmapToggleButton(id=expandbutton_id, bitmap=wx.Bitmap(Bpath( 'images', 'plus.png')),
              name='ExpandButton', parent=leftwindow, pos=wx.Point(0, 0),
              size=wx.Size(13, 13), style=wx.NO_BORDER)
        expandbutton.labelDelta = 0
        expandbutton.SetBezelWidth(0)
        expandbutton.SetUseFocusIndicator(False)
        expandbutton.SetBitmapSelected(wx.Bitmap(Bpath( 'images', 'minus.png')))
            
        if len(self.ConfNodeInfos[confnode]["children"]) > 0:
            expandbutton.SetToggle(self.ConfNodeInfos[confnode]["expanded"])
            def togglebutton(event):
                if expandbutton.GetToggle():
                    self.ExpandConfNode(confnode)
                else:
                    self.CollapseConfNode(confnode)
                self.ConfNodeInfos[confnode]["expanded"] = expandbutton.GetToggle()
                self.PLCConfigMainSizer.Layout()
                self.RefreshScrollBars()
                event.Skip()
            expandbutton.Bind(wx.EVT_BUTTON, togglebutton, id=expandbutton_id)
        elif len(confnode_locations) > 0:
            locations_infos = self.ConfNodeInfos[confnode]["locations_infos"]
            expandbutton.SetToggle(locations_infos["root"]["expanded"])
            def togglebutton(event):
                if expandbutton.GetToggle():
                    self.ExpandLocation(locations_infos, "root")
                else:
                    self.CollapseLocation(locations_infos, "root")
                self.ConfNodeInfos[confnode]["expanded"] = expandbutton.GetToggle()
                locations_infos["root"]["expanded"] = expandbutton.GetToggle()
                self.PLCConfigMainSizer.Layout()
                self.RefreshScrollBars()
                event.Skip()
            expandbutton.Bind(wx.EVT_BUTTON, togglebutton, id=expandbutton_id)
        else:
            expandbutton.Enable(False)
        iecsizer.AddWindow(expandbutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        
        tc_id = wx.NewId()
        tc = wx.TextCtrl(leftwindow, tc_id, size=wx.Size(150, 25), style=wx.NO_BORDER)
        tc.SetFont(wx.Font(faces["size"] * 0.75, wx.DEFAULT, wx.NORMAL, wx.BOLD, faceName = faces["helv"]))
        tc.ChangeValue(confnode.MandatoryParams[1].getName())
        tc.Bind(wx.EVT_TEXT, self.GetTextCtrlCallBackFunction(tc, confnode, "BaseParams.Name"), id=tc_id)
        iecsizer.AddWindow(tc, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        
        rightwindow = self.GenerateParamsPanel(confnode, bkgdclr, 8)
        self.ConfNodeTreeSizer.AddWindow(rightwindow, 0, border=0, flag=wx.GROW)
        
        self.ConfNodeInfos[confnode]["left"] = leftwindow
        self.ConfNodeInfos[confnode]["right"] = rightwindow
        for child in self.ConfNodeInfos[confnode]["children"]:
            self.GenerateTreeBranch(child)
            if not self.ConfNodeInfos[child]["expanded"]:
                self.CollapseConfNode(child)
        
        if len(confnode_locations) > 0:
            locations_infos = self.ConfNodeInfos[confnode]["locations_infos"]
            treectrl = wx.TreeCtrl(self.PLCConfig, -1, size=wx.DefaultSize, 
                                   style=wx.TR_HAS_BUTTONS|wx.TR_SINGLE|wx.NO_BORDER|wx.TR_HIDE_ROOT|wx.TR_NO_LINES|wx.TR_LINES_AT_ROOT)
            treectrl.SetImageList(self.LocationImageList)
            treectrl.Bind(wx.EVT_TREE_BEGIN_DRAG, self.GenerateLocationBeginDragFunction(locations_infos))
            treectrl.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.GenerateLocationExpandCollapseFunction(locations_infos, True))
            treectrl.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.GenerateLocationExpandCollapseFunction(locations_infos, False))
            treectrl.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheelTreeCtrl)
            
            treectrl.AddRoot("")
            self.ConfNodeTreeSizer.AddWindow(treectrl, 0, border=0, flag=0)
            
            rightwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
            rightwindow.SetBackgroundColour(wx.WHITE)
            self.ConfNodeTreeSizer.AddWindow(rightwindow, 0, border=0, flag=wx.GROW)
            
            locations_infos["root"]["left"] = treectrl
            locations_infos["root"]["right"] = rightwindow
            for location in confnode_locations:
                locations_infos["root"]["children"].append("root.%s" % location["name"])
                self.GenerateLocationTreeBranch(treectrl, treectrl.GetRootItem(), locations_infos, "root", location)
            if locations_infos["root"]["expanded"]:
                self.ConfNodeTreeSizer.Layout()
                self.ExpandLocation(locations_infos, "root")
            else:
                self.RefreshTreeCtrlSize(treectrl)
    
    def GenerateLocationTreeBranch(self, treectrl, root, locations_infos, parent, location):
        location_name = "%s.%s" % (parent, location["name"])
        if not locations_infos.has_key(location_name):
            locations_infos[location_name] = {"expanded" : False}
        
        if location["type"] in [LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY]:
            label = "%(name)s (%(location)s)" % location
        elif location["location"] != "":
            label = "%(location)s: %(name)s" % location
        else:
            label = location["name"]
        item = treectrl.AppendItem(root, label)
        treectrl.SetPyData(item, location_name)
        treectrl.SetItemImage(item, self.LocationImageDict[location["type"]])
        
        locations_infos[location_name]["item"] = item
        locations_infos[location_name]["children"] = []
        infos = location.copy()
        infos.pop("children")
        locations_infos[location_name]["infos"] = infos
        for child in location["children"]:
            child_name = "%s.%s" % (location_name, child["name"])
            locations_infos[location_name]["children"].append(child_name)
            self.GenerateLocationTreeBranch(treectrl, item, locations_infos, location_name, child)
        if locations_infos[location_name]["expanded"]:
            self.ExpandLocation(locations_infos, location_name)
    
    def GenerateLocationBeginDragFunction(self, locations_infos):
        def OnLocationBeginDragFunction(event):
            item = event.GetItem()
            location_name = locations_infos["root"]["left"].GetPyData(item)
            if location_name is not None:
                infos = locations_infos[location_name]["infos"]
                if infos["type"] in [LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY]:
                    data = wx.TextDataObject(str((infos["location"], "location", infos["IEC_type"], infos["var_name"], infos["description"])))
                    dragSource = wx.DropSource(self)
                    dragSource.SetData(data)
                    dragSource.DoDragDrop()
        return OnLocationBeginDragFunction
    
    def RefreshTreeCtrlSize(self, treectrl):
        rect = self.GetTreeCtrlItemRect(treectrl, treectrl.GetRootItem())
        treectrl.SetMinSize(wx.Size(max(rect.width, rect.x + rect.width) + 20, max(rect.height, rect.y + rect.height) + 20))
        self.PLCConfigMainSizer.Layout()
        self.PLCConfig.Refresh()
        wx.CallAfter(self.RefreshScrollBars)
    
    def OnMouseWheelTreeCtrl(self, event):
        x, y = self.PLCConfig.GetViewStart()
        rotation = - (event.GetWheelRotation() / event.GetWheelDelta()) * 3
        if event.ShiftDown():
            self.PLCConfig.Scroll(x + rotation, y)
        else:
            self.PLCConfig.Scroll(x, y + rotation)
    
    def GetTreeCtrlItemRect(self, treectrl, item):
        item_rect = treectrl.GetBoundingRect(item, True)
        if item_rect is not None:
            minx, miny = item_rect.x, item_rect.y
            maxx, maxy = item_rect.x + item_rect.width, item_rect.y + item_rect.height
        else:
            minx = miny = maxx = maxy = 0
        
        if treectrl.ItemHasChildren(item) and (item == treectrl.GetRootItem() or treectrl.IsExpanded(item)):
            if wx.VERSION >= (2, 6, 0):
                child, item_cookie = treectrl.GetFirstChild(item)
            else:
                child, item_cookie = treectrl.GetFirstChild(item, 0)
            while child.IsOk():
                child_rect = self.GetTreeCtrlItemRect(treectrl, child)
                minx = min(minx, child_rect.x)
                miny = min(miny, child_rect.y)
                maxx = max(maxx, child_rect.x + child_rect.width)
                maxy = max(maxy, child_rect.y + child_rect.height)
                child, item_cookie = treectrl.GetNextChild(item, item_cookie)
                
        return wx.Rect(minx, miny, maxx - minx, maxy - miny)
    
    def GenerateLocationExpandCollapseFunction(self, locations_infos, expand):
        def OnLocationExpandedFunction(event):
            item = event.GetItem()
            location_name = locations_infos["root"]["left"].GetPyData(item)
            if location_name is not None:
                locations_infos[location_name]["expanded"] = expand
                self.RefreshTreeCtrlSize(locations_infos["root"]["left"])
            event.Skip()
        return OnLocationExpandedFunction
    
    def RefreshAll(self):
        self.RefreshPLCParams()
        self.RefreshConfNodeTree()
        
    def GetItemChannelChangedFunction(self, confnode, value):
        def OnConfNodeTreeItemChannelChanged(event):
            res = self.SetConfNodeParamsAttribute(confnode, "BaseParams.IEC_Channel", value)
            event.Skip()
        return OnConfNodeTreeItemChannelChanged
    
    def _GetAddConfNodeFunction(self, name, confnode):
        def OnConfNodeMenu(event):
            wx.CallAfter(self.AddConfNode, name, confnode)
        return OnConfNodeMenu
    
    def Gen_AddConfNodeMenu(self, confnode):
        def AddConfNodeMenu(event):
            main_menu = wx.Menu(title='')
            if len(confnode.CTNChildrenTypes) > 0:
                for name, XSDClass, help in confnode.CTNChildrenTypes:
                    new_id = wx.NewId()
                    main_menu.Append(help=help, id=new_id, kind=wx.ITEM_NORMAL, text=_("Append ")+help)
                    self.Bind(wx.EVT_MENU, self._GetAddConfNodeFunction(name, confnode), id=new_id)
            self.PopupMenuXY(main_menu)
            main_menu.Destroy()
        return AddConfNodeMenu
    
    def GetButtonCallBackFunction(self, confnode, method):
        """ Generate the callbackfunc for a given confnode method"""
        def OnButtonClick(event):
            # Disable button to prevent re-entrant call 
            event.GetEventObject().Disable()
            # Call
            getattr(confnode,method)()
            # Re-enable button 
            event.GetEventObject().Enable()
            # Trigger refresh on Idle
            wx.CallAfter(self.RefreshAll)
            event.Skip()
        return OnButtonClick
    
    def GetChoiceCallBackFunction(self, choicectrl, confnode, path):
        def OnChoiceChanged(event):
            res = self.SetConfNodeParamsAttribute(confnode, path, choicectrl.GetStringSelection())
            choicectrl.SetStringSelection(res)
            event.Skip()
        return OnChoiceChanged
    
    def GetChoiceContentCallBackFunction(self, choicectrl, staticboxsizer, confnode, path):
        def OnChoiceContentChanged(event):
            res = self.SetConfNodeParamsAttribute(confnode, path, choicectrl.GetStringSelection())
            if wx.VERSION < (2, 8, 0):
                self.ParamsPanel.Freeze()
                choicectrl.SetStringSelection(res)
                infos = self.CTR.GetParamsAttributes(path)
                staticbox = staticboxsizer.GetStaticBox()
                staticbox.SetLabel("%(name)s - %(value)s"%infos)
                self.RefreshSizerElement(self.ParamsPanel, staticboxsizer, infos["children"], "%s.%s"%(path, infos["name"]), selected=selected)
                self.ParamsPanelMainSizer.Layout()
                self.ParamsPanel.Thaw()
                self.ParamsPanel.Refresh()
            else:
                wx.CallAfter(self.RefreshAll)
            event.Skip()
        return OnChoiceContentChanged
    
    def GetTextCtrlCallBackFunction(self, textctrl, confnode, path):
        def OnTextCtrlChanged(event):
            res = self.SetConfNodeParamsAttribute(confnode, path, textctrl.GetValue())
            if res != textctrl.GetValue():
                textctrl.ChangeValue(res)
            event.Skip()
        return OnTextCtrlChanged
    
    def GetCheckBoxCallBackFunction(self, chkbx, confnode, path):
        def OnCheckBoxChanged(event):
            res = self.SetConfNodeParamsAttribute(confnode, path, chkbx.IsChecked())
            chkbx.SetValue(res)
            event.Skip()
        return OnCheckBoxChanged
    
    def GetBrowseCallBackFunction(self, name, textctrl, library, value_infos, confnode, path):
        infos = [value_infos]
        def OnBrowseButton(event):
            dialog = BrowseValuesLibraryDialog(self, name, library, infos[0])
            if dialog.ShowModal() == wx.ID_OK:
                value, value_infos = self.SetConfNodeParamsAttribute(confnode, path, dialog.GetValueInfos())
                textctrl.ChangeValue(value)
                infos[0] = value_infos
            dialog.Destroy()
            event.Skip()
        return OnBrowseButton
    
    def ClearSizer(self, sizer):
        staticboxes = []
        for item in sizer.GetChildren():
            if item.IsSizer():
                item_sizer = item.GetSizer()
                self.ClearSizer(item_sizer)
                if isinstance(item_sizer, wx.StaticBoxSizer):
                    staticboxes.append(item_sizer.GetStaticBox())
        sizer.Clear(True)
        for staticbox in staticboxes:
            staticbox.Destroy()
                
    def RefreshSizerElement(self, parent, sizer, confnode, elements, path, clean = True):
        if clean:
            if wx.VERSION < (2, 8, 0):
                self.ClearSizer(sizer)
            else:
                sizer.Clear(True)
        first = True
        for element_infos in elements:
            if path:
                element_path = "%s.%s"%(path, element_infos["name"])
            else:
                element_path = element_infos["name"]
            if element_infos["type"] == "element":
                label = element_infos["name"]
                staticbox = wx.StaticBox(id=-1, label=_(label), 
                    name='%s_staticbox'%element_infos["name"], parent=parent,
                    pos=wx.Point(0, 0), size=wx.Size(10, 0), style=0)
                staticboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
                if first:
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW|wx.TOP)
                else:
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW)
                self.RefreshSizerElement(parent, staticboxsizer, confnode, element_infos["children"], element_path)
            else:
                boxsizer = wx.FlexGridSizer(cols=3, rows=1)
                boxsizer.AddGrowableCol(1)
                if first:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                else:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
                staticbitmap = GenStaticBitmap(ID=-1, bitmapname="%s.png"%element_infos["name"],
                    name="%s_bitmap"%element_infos["name"], parent=parent,
                    pos=wx.Point(0, 0), size=wx.Size(24, 24), style=0)
                boxsizer.AddWindow(staticbitmap, 0, border=5, flag=wx.RIGHT)
                label = element_infos["name"]
                statictext = wx.StaticText(id=-1, label="%s:"%_(label), 
                    name="%s_label"%element_infos["name"], parent=parent, 
                    pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
                boxsizer.AddWindow(statictext, 0, border=5, flag=wx.ALIGN_CENTER_VERTICAL|wx.RIGHT)
                id = wx.NewId()
                if isinstance(element_infos["type"], types.ListType):
                    if isinstance(element_infos["value"], types.TupleType):
                        browse_boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                        boxsizer.AddSizer(browse_boxsizer, 0, border=0, flag=0)
                        
                        textctrl = wx.TextCtrl(id=id, name=element_infos["name"], parent=parent, 
                            pos=wx.Point(0, 0), size=wx.Size(275, 25), style=wx.TE_READONLY)
                        if element_infos["value"] is not None:
                            textctrl.SetValue(element_infos["value"][0])
                            value_infos = element_infos["value"][1]
                        else:
                            value_infos = None
                        browse_boxsizer.AddWindow(textctrl, 0, border=0, flag=0)
                        button_id = wx.NewId()
                        button = wx.Button(id=button_id, name="browse_%s" % element_infos["name"], parent=parent, 
                            label="...", pos=wx.Point(0, 0), size=wx.Size(25, 25))
                        browse_boxsizer.AddWindow(button, 0, border=0, flag=0)
                        button.Bind(wx.EVT_BUTTON, 
                                    self.GetBrowseCallBackFunction(element_infos["name"], textctrl, element_infos["type"], 
                                                                   value_infos, confnode, element_path), 
                                    id=button_id)
                    else:
                        combobox = wx.ComboBox(id=id, name=element_infos["name"], parent=parent, 
                            pos=wx.Point(0, 0), size=wx.Size(300, 28), style=wx.CB_READONLY)
                        boxsizer.AddWindow(combobox, 0, border=0, flag=0)
                        if element_infos["use"] == "optional":
                            combobox.Append("")
                        if len(element_infos["type"]) > 0 and isinstance(element_infos["type"][0], types.TupleType):
                            for choice, xsdclass in element_infos["type"]:
                                combobox.Append(choice)
                            name = element_infos["name"]
                            value = element_infos["value"]
                            staticbox = wx.StaticBox(id=-1, label="%s - %s"%(_(name), _(value)), 
                                name='%s_staticbox'%element_infos["name"], parent=parent,
                                pos=wx.Point(0, 0), size=wx.Size(10, 0), style=0)
                            staticboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
                            sizer.AddSizer(staticboxsizer, 0, border=5, flag=wx.GROW|wx.BOTTOM)
                            self.RefreshSizerElement(parent, staticboxsizer, confnode, element_infos["children"], element_path)
                            callback = self.GetChoiceContentCallBackFunction(combobox, staticboxsizer, confnode, element_path)
                        else:
                            for choice in element_infos["type"]:
                                combobox.Append(choice)
                            callback = self.GetChoiceCallBackFunction(combobox, confnode, element_path)
                        if element_infos["value"] is None:
                            combobox.SetStringSelection("")
                        else:
                            combobox.SetStringSelection(element_infos["value"])
                        combobox.Bind(wx.EVT_COMBOBOX, callback, id=id)
                elif isinstance(element_infos["type"], types.DictType):
                    scmin = -(2**31)
                    scmax = 2**31-1
                    if "min" in element_infos["type"]:
                        scmin = element_infos["type"]["min"]
                    if "max" in element_infos["type"]:
                        scmax = element_infos["type"]["max"]
                    spinctrl = wx.SpinCtrl(id=id, name=element_infos["name"], parent=parent, 
                        pos=wx.Point(0, 0), size=wx.Size(300, 25), style=wx.SP_ARROW_KEYS|wx.ALIGN_RIGHT)
                    spinctrl.SetRange(scmin,scmax)
                    boxsizer.AddWindow(spinctrl, 0, border=0, flag=0)
                    if element_infos["value"] is not None:
                        spinctrl.SetValue(element_infos["value"])
                    spinctrl.Bind(wx.EVT_SPINCTRL, self.GetTextCtrlCallBackFunction(spinctrl, confnode, element_path), id=id)
                else:
                    if element_infos["type"] == "boolean":
                        checkbox = wx.CheckBox(id=id, name=element_infos["name"], parent=parent, 
                            pos=wx.Point(0, 0), size=wx.Size(17, 25), style=0)
                        boxsizer.AddWindow(checkbox, 0, border=0, flag=0)
                        if element_infos["value"] is not None:
                            checkbox.SetValue(element_infos["value"])
                        checkbox.Bind(wx.EVT_CHECKBOX, self.GetCheckBoxCallBackFunction(checkbox, confnode, element_path), id=id)
                    elif element_infos["type"] in ["unsignedLong", "long","integer"]:
                        if element_infos["type"].startswith("unsigned"):
                            scmin = 0
                        else:
                            scmin = -(2**31)
                        scmax = 2**31-1
                        spinctrl = wx.SpinCtrl(id=id, name=element_infos["name"], parent=parent, 
                            pos=wx.Point(0, 0), size=wx.Size(300, 25), style=wx.SP_ARROW_KEYS|wx.ALIGN_RIGHT)
                        spinctrl.SetRange(scmin, scmax)
                        boxsizer.AddWindow(spinctrl, 0, border=0, flag=0)
                        if element_infos["value"] is not None:
                            spinctrl.SetValue(element_infos["value"])
                        spinctrl.Bind(wx.EVT_SPINCTRL, self.GetTextCtrlCallBackFunction(spinctrl, confnode, element_path), id=id)
                    else:
                        choices = cPickle.loads(str(self.Config.Read(element_path, cPickle.dumps([""]))))
                        textctrl = TextCtrlAutoComplete(id=id, 
                                                                     name=element_infos["name"], 
                                                                     parent=parent, 
                                                                     appframe=self, 
                                                                     choices=choices, 
                                                                     element_path=element_path,
                                                                     pos=wx.Point(0, 0), 
                                                                     size=wx.Size(300, 25), 
                                                                     style=0)
                        
                        boxsizer.AddWindow(textctrl, 0, border=0, flag=0)
                        if element_infos["value"] is not None:
                            textctrl.ChangeValue(str(element_infos["value"]))
                        textctrl.Bind(wx.EVT_TEXT, self.GetTextCtrlCallBackFunction(textctrl, confnode, element_path))
            first = False
    
    def ResetView(self):
        IDEFrame.ResetView(self)
        self.ConfNodeInfos = {}
        if self.CTR is not None:
            self.CTR.CloseProject()
        self.CTR = None
        self.Log.flush()
        if self.EnableDebug:
            self.DebugVariablePanel.SetDataProducer(None)
    
    def RefreshConfigRecentProjects(self, projectpath):
        recent_projects = cPickle.loads(str(self.Config.Read("RecentProjects", cPickle.dumps([]))))
        if projectpath in recent_projects:
            recent_projects.remove(projectpath)
        recent_projects.insert(0, projectpath)
        self.Config.Write("RecentProjects", cPickle.dumps(recent_projects[:MAX_RECENT_PROJECTS]))
        self.Config.Flush()
    
    def OnNewProjectMenu(self, event):
        if self.CTR is not None and not self.CheckSaveBeforeClosing():
            return
        
        if not self.Config.HasEntry("lastopenedfolder"):
            defaultpath = os.path.expanduser("~")
        else:
            defaultpath = self.Config.Read("lastopenedfolder")
        
        dialog = wx.DirDialog(self , _("Choose a project"), defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            self.Config.Write("lastopenedfolder", os.path.dirname(projectpath))
            self.Config.Flush()
            self.ResetView()
            ctr = ProjectController(self, self.Log)
            result = ctr.NewProject(projectpath)
            if not result:
                self.CTR = ctr
                self.Controler = self.CTR
                self.LibraryPanel.SetControler(self.Controler)
                self.RefreshConfigRecentProjects(projectpath)
                if self.EnableDebug:
                    self.DebugVariablePanel.SetDataProducer(self.CTR)
                self._Refresh(TYPESTREE, INSTANCESTREE, LIBRARYTREE)
                self.RefreshAll()
            else:
                self.ResetView()
                self.ShowErrorMessage(result)
            self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU)
        dialog.Destroy()
    
    def OnOpenProjectMenu(self, event):
        if self.CTR is not None and not self.CheckSaveBeforeClosing():
            return
        
        if not self.Config.HasEntry("lastopenedfolder"):
            defaultpath = os.path.expanduser("~")
        else:
            defaultpath = self.Config.Read("lastopenedfolder")
        
        dialog = wx.DirDialog(self , _("Choose a project"), defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            self.OpenProject(dialog.GetPath())
        dialog.Destroy()
    
    def OpenProject(self, projectpath):
        if os.path.isdir(projectpath):
            self.Config.Write("lastopenedfolder", os.path.dirname(projectpath))
            self.Config.Flush()
            self.ResetView()
            self.CTR = ProjectController(self, self.Log)
            self.Controler = self.CTR
            result = self.CTR.LoadProject(projectpath)
            if not result:
                self.LibraryPanel.SetControler(self.Controler)
                self.RefreshConfigRecentProjects(projectpath)
                if self.EnableDebug:
                    self.DebugVariablePanel.SetDataProducer(self.CTR)
                self.LoadProjectOrganization()
                self._Refresh(TYPESTREE, INSTANCESTREE, LIBRARYTREE)
                self.RefreshAll()
            else:
                self.ResetView()
                self.ShowErrorMessage(result)
        else:
            self.ShowErrorMessage(_("\"%s\" folder is not a valid Beremiz project\n") % projectpath)
        self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU)
    
    def OnCloseProjectMenu(self, event):
        if self.CTR is not None and not self.CheckSaveBeforeClosing():
            return
        
        self.SaveProjectOrganization()
        self.ResetView()
        self._Refresh(TITLE, EDITORTOOLBAR, FILEMENU, EDITMENU)
        self.RefreshAll()
    
    def OnSaveProjectMenu(self, event):
        if self.CTR is not None:
            self.CTR.SaveProject()
            self.RefreshAll()
            self._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES)
    
    def OnSaveProjectAsMenu(self, event):
        if self.CTR is not None:
            self.CTR.SaveProjectAs()
            self.RefreshAll()
            self._Refresh(TITLE, FILEMENU, EDITMENU, PAGETITLES)
        event.Skip()
    
    def OnPropertiesMenu(self, event):
        self.ShowProperties()
    
    def OnQuitMenu(self, event):
        self.Close()
        
    def OnBeremizMenu(self, event):
        open_pdf(Bpath( "doc", "manual_beremiz.pdf"))
    
    def OnAboutMenu(self, event):
        OpenHtmlFrame(self,_("About Beremiz"), Bpath("doc","about.html"), wx.Size(550, 500))
    
    def OnPouSelectedChanged(self, event):
        wx.CallAfter(self.RefreshConfNodeMenu)
        IDEFrame.OnPouSelectedChanged(self, event)
    
    def OnPageClose(self, event):
        wx.CallAfter(self.RefreshConfNodeMenu)
        IDEFrame.OnPageClose(self, event)
    
    def GetAddButtonFunction(self, confnode, window):
        def AddButtonFunction(event):
            if confnode and len(confnode.CTNChildrenTypes) > 0:
                confnode_menu = wx.Menu(title='')
                for name, XSDClass, help in confnode.CTNChildrenTypes:
                    new_id = wx.NewId()
                    confnode_menu.Append(help=help, id=new_id, kind=wx.ITEM_NORMAL, text=name)
                    self.Bind(wx.EVT_MENU, self._GetAddConfNodeFunction(name, confnode), id=new_id)
                window_pos = window.GetPosition()
                wx.CallAfter(self.PLCConfig.PopupMenu, confnode_menu)
            event.Skip()
        return AddButtonFunction
    
    def GetDeleteButtonFunction(self, confnode):
        def DeleteButtonFunction(event):
            wx.CallAfter(self.DeleteConfNode, confnode)
            event.Skip()
        return DeleteButtonFunction
    
    def AddConfNode(self, ConfNodeType, confnode):
        if self.CTR.CheckProjectPathPerm():
            dialog = wx.TextEntryDialog(self, _("Please enter a name for confnode:"), _("Add ConfNode"), "", wx.OK|wx.CANCEL)
            if dialog.ShowModal() == wx.ID_OK:
                ConfNodeName = dialog.GetValue()
                confnode.CTNAddChild(ConfNodeName, ConfNodeType)
                self.CTR.RefreshConfNodesBlockLists()
                self._Refresh(TITLE, FILEMENU)
                self.RefreshConfNodeTree()
            dialog.Destroy()
    
    def DeleteConfNode(self, confnode):
        if self.CTR.CheckProjectPathPerm():
            dialog = wx.MessageDialog(self, _("Really delete confnode ?"), _("Remove confnode"), wx.YES_NO|wx.NO_DEFAULT)
            if dialog.ShowModal() == wx.ID_YES:
                self.ConfNodeInfos.pop(confnode)
                confnode.CTNRemove()
                del confnode
                self.CTR.RefreshConfNodesBlockLists()
                self._Refresh(TITLE, FILEMENU)
                self.RefreshConfNodeTree()
            dialog.Destroy()
    
#-------------------------------------------------------------------------------
#                               Exception Handler
#-------------------------------------------------------------------------------

Max_Traceback_List_Size = 20

def Display_Exception_Dialog(e_type, e_value, e_tb, bug_report_path):
    trcbck_lst = []
    for i,line in enumerate(traceback.extract_tb(e_tb)):
        trcbck = " " + str(i+1) + _(". ")
        if line[0].find(os.getcwd()) == -1:
            trcbck += _("file : ") + str(line[0]) + _(",   ")
        else:
            trcbck += _("file : ") + str(line[0][len(os.getcwd()):]) + _(",   ")
        trcbck += _("line : ") + str(line[1]) + _(",   ") + _("function : ") + str(line[2])
        trcbck_lst.append(trcbck)
        
    # Allow clicking....
    cap = wx.Window_GetCapture()
    if cap:
        cap.ReleaseMouse()

    dlg = wx.SingleChoiceDialog(None, 
        _("""
An unhandled exception (bug) occured. Bug report saved at :
(%s)

Please be kind enough to send this file to:
dev@automforge.net

You should now restart Beremiz.

Traceback:
""") % bug_report_path +
        str(e_type) + " : " + str(e_value), 
        _("Error"),
        trcbck_lst)
    try:
        res = (dlg.ShowModal() == wx.ID_OK)
    finally:
        dlg.Destroy()

    return res

def get_last_traceback(tb):
    while tb.tb_next:
        tb = tb.tb_next
    return tb


def format_namespace(d, indent='    '):
    return '\n'.join(['%s%s: %s' % (indent, k, repr(v)[:10000]) for k, v in d.iteritems()])


ignored_exceptions = [] # a problem with a line in a module is only reported once per session

def AddExceptHook(path, app_version='[No version]'):#, ignored_exceptions=[]):
    
    def handle_exception(e_type, e_value, e_traceback):
        traceback.print_exception(e_type, e_value, e_traceback) # this is very helpful when there's an exception in the rest of this func
        last_tb = get_last_traceback(e_traceback)
        ex = (last_tb.tb_frame.f_code.co_filename, last_tb.tb_frame.f_lineno)
        if ex not in ignored_exceptions:
            date = time.ctime()
            bug_report_path = path+os.sep+"bug_report_"+date.replace(':','-').replace(' ','_')+".txt"
            result = Display_Exception_Dialog(e_type,e_value,e_traceback,bug_report_path)
            if result:
                ignored_exceptions.append(ex)
                info = {
                    'app-title' : wx.GetApp().GetAppName(), # app_title
                    'app-version' : app_version,
                    'wx-version' : wx.VERSION_STRING,
                    'wx-platform' : wx.Platform,
                    'python-version' : platform.python_version(), #sys.version.split()[0],
                    'platform' : platform.platform(),
                    'e-type' : e_type,
                    'e-value' : e_value,
                    'date' : date,
                    'cwd' : os.getcwd(),
                    }
                if e_traceback:
                    info['traceback'] = ''.join(traceback.format_tb(e_traceback)) + '%s: %s' % (e_type, e_value)
                    last_tb = get_last_traceback(e_traceback)
                    exception_locals = last_tb.tb_frame.f_locals # the locals at the level of the stack trace where the exception actually occurred
                    info['locals'] = format_namespace(exception_locals)
                    if 'self' in exception_locals:
                        info['self'] = format_namespace(exception_locals['self'].__dict__)
                
                output = open(bug_report_path,'w')
                lst = info.keys()
                lst.sort()
                for a in lst:
                    output.write(a+":\n"+str(info[a])+"\n\n")

    #sys.excepthook = lambda *args: wx.CallAfter(handle_exception, *args)
    sys.excepthook = handle_exception

if __name__ == '__main__':
    # Install a exception handle for bug reports
    AddExceptHook(os.getcwd(),updateinfo_url)
    
    frame = Beremiz(None, projectOpen, buildpath)
    splash.Close()
    #wx.Yield()
    frame.Show()
    app.MainLoop()
