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

__version__ = "$Revision$"

import wx
import wx.lib.buttons
import wx.lib.statbmp

import types

import time

import os, re, platform, sys, time, traceback, getopt, commands

from plugger import PluginsRoot

SCROLLBAR_UNIT = 10
WINDOW_COLOUR = wx.Colour(240,240,240)
TITLE_COLOUR = wx.Colour(200,200,220)

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

CWD = os.path.split(os.path.realpath(__file__))[0]

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
        return wx.lib.buttons.GenBitmapTextButton._GetLabelSize(self)[:-1] + (False,)

class GenStaticBitmap(wx.lib.statbmp.GenStaticBitmap):
    """ Customized GenStaticBitmap, fix transparency redraw bug on wx2.8/win32, 
    and accept image name as __init__ parameter, fail silently if file do not exist"""
    def __init__(self, parent, ID, bitmapname,
                 pos = wx.DefaultPosition, size = wx.DefaultSize,
                 style = 0,
                 name = "genstatbmp"):
        
        bitmappath = os.path.join(CWD, "images", bitmapname)
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

                        
class LogPseudoFile:
    """ Base class for file like objects to facilitate StdOut for the Shell."""
    def __init__(self, output):
        self.red_white = wx.TextAttr("RED", "WHITE")
        self.red_yellow = wx.TextAttr("RED", "YELLOW")
        self.black_white = wx.TextAttr("BLACK", "WHITE")
        self.default_style = None
        self.output = output

    def write(self, s, style = None):
        if style is None : style=self.black_white
        self.output.Freeze(); 
        if self.default_style != style: 
            self.output.SetDefaultStyle(style)
            self.default_style = style
        self.output.AppendText(s)
        self.output.ScrollLines(s.count('\n')+1)
        self.output.ShowPosition(self.output.GetLastPosition())
        self.output.Thaw()

    def write_warning(self, s):
        self.write(s,self.red_white)

    def write_error(self, s):
        self.write(s,self.red_yellow)

    def flush(self):
        self.output.SetValue("")
    
    def isatty(self):
        return false

[ID_BEREMIZ, ID_BEREMIZMAINSPLITTER, 
 ID_BEREMIZPLCCONFIG, ID_BEREMIZLOGCONSOLE, 
] = [wx.NewId() for _init_ctrls in range(4)]

[ID_BEREMIZFILEMENUITEMS0, ID_BEREMIZFILEMENUITEMS1, 
 ID_BEREMIZFILEMENUITEMS2, ID_BEREMIZFILEMENUITEMS3, 
 ID_BEREMIZFILEMENUITEMS5, ID_BEREMIZFILEMENUITEMS7, 
] = [wx.NewId() for _init_coll_FileMenu_Items in range(6)]

[ID_BEREMIZEDITMENUITEMS0, ID_BEREMIZEDITMENUITEMS2, 
 ID_BEREMIZEDITMENUITEMS3, 
] = [wx.NewId() for _init_coll_EditMenu_Items in range(3)]

[ID_BEREMIZRUNMENUITEMS0, ID_BEREMIZRUNMENUITEMS2, 
 ID_BEREMIZRUNMENUITEMS3, ID_BEREMIZRUNMENUITEMS5, 
] = [wx.NewId() for _init_coll_EditMenu_Items in range(4)]

[ID_BEREMIZHELPMENUITEMS0, ID_BEREMIZHELPMENUITEMS1, 
] = [wx.NewId() for _init_coll_HelpMenu_Items in range(2)]

class Beremiz(wx.Frame):
    
    def _init_coll_FileMenu_Items(self, parent):
        parent.Append(help='', id=ID_BEREMIZFILEMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'New\tCTRL+N')
        parent.Append(help='', id=ID_BEREMIZFILEMENUITEMS1,
              kind=wx.ITEM_NORMAL, text=u'Open\tCTRL+O')
        parent.Append(help='', id=ID_BEREMIZFILEMENUITEMS2,
              kind=wx.ITEM_NORMAL, text=u'Save\tCTRL+S')
        parent.Append(help='', id=ID_BEREMIZFILEMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Close Project')
        parent.AppendSeparator()
        parent.Append(help='', id=ID_BEREMIZFILEMENUITEMS5,
              kind=wx.ITEM_NORMAL, text=u'Properties')
        parent.AppendSeparator()
        parent.Append(help='', id=ID_BEREMIZFILEMENUITEMS7,
              kind=wx.ITEM_NORMAL, text=u'Quit\tCTRL+Q')
        self.Bind(wx.EVT_MENU, self.OnNewProjectMenu,
              id=ID_BEREMIZFILEMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnOpenProjectMenu,
              id=ID_BEREMIZFILEMENUITEMS1)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectMenu,
              id=ID_BEREMIZFILEMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnCloseProjectMenu,
              id=ID_BEREMIZFILEMENUITEMS3)
        self.Bind(wx.EVT_MENU, self.OnPropertiesMenu,
              id=ID_BEREMIZFILEMENUITEMS5)
        self.Bind(wx.EVT_MENU, self.OnQuitMenu,
              id=ID_BEREMIZFILEMENUITEMS7)
        
    def _init_coll_EditMenu_Items(self, parent):
        parent.Append(help='', id=ID_BEREMIZEDITMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'Edit PLC\tCTRL+R')
        parent.AppendSeparator()
        parent.Append(help='', id=ID_BEREMIZEDITMENUITEMS2,
              kind=wx.ITEM_NORMAL, text=u'Add Plugin')
        parent.Append(help='', id=ID_BEREMIZEDITMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Delete Plugin')
        self.Bind(wx.EVT_MENU, self.OnEditPLCMenu,
              id=ID_BEREMIZEDITMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnAddMenu,
              id=ID_BEREMIZEDITMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnDeleteMenu,
              id=ID_BEREMIZEDITMENUITEMS3)
    
    def _init_coll_RunMenu_Items(self, parent):
        parent.Append(help='', id=ID_BEREMIZRUNMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'Build\tCTRL+R')
        parent.AppendSeparator()
        parent.Append(help='', id=ID_BEREMIZRUNMENUITEMS2,
              kind=wx.ITEM_NORMAL, text=u'Simulate')
        parent.Append(help='', id=ID_BEREMIZRUNMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Run')
        parent.AppendSeparator()
        parent.Append(help='', id=ID_BEREMIZRUNMENUITEMS5,
              kind=wx.ITEM_NORMAL, text=u'Save Log')
        self.Bind(wx.EVT_MENU, self.OnBuildMenu,
              id=ID_BEREMIZRUNMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnSimulateMenu,
              id=ID_BEREMIZRUNMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnRunMenu,
              id=ID_BEREMIZRUNMENUITEMS3)
        self.Bind(wx.EVT_MENU, self.OnSaveLogMenu,
              id=ID_BEREMIZRUNMENUITEMS5)
    
    def _init_coll_HelpMenu_Items(self, parent):
        parent.Append(help='', id=ID_BEREMIZHELPMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'Beremiz\tF1')
        parent.Append(help='', id=ID_BEREMIZHELPMENUITEMS1,
              kind=wx.ITEM_NORMAL, text=u'About')
        self.Bind(wx.EVT_MENU, self.OnBeremizMenu,
              id=ID_BEREMIZHELPMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnAboutMenu,
              id=ID_BEREMIZHELPMENUITEMS1)
    
    def _init_coll_menuBar1_Menus(self, parent):
        parent.Append(menu=self.FileMenu, title=u'File')
        #parent.Append(menu=self.EditMenu, title=u'Edit')
        #parent.Append(menu=self.RunMenu, title=u'Run')
        parent.Append(menu=self.HelpMenu, title=u'Help')
    
    def _init_utils(self):
        self.menuBar1 = wx.MenuBar()
        self.FileMenu = wx.Menu(title=u'')
        #self.EditMenu = wx.Menu(title=u'')
        #self.RunMenu = wx.Menu(title=u'')
        self.HelpMenu = wx.Menu(title=u'')
        
        self._init_coll_menuBar1_Menus(self.menuBar1)
        self._init_coll_FileMenu_Items(self.FileMenu)
        #self._init_coll_EditMenu_Items(self.EditMenu)
        #self._init_coll_RunMenu_Items(self.RunMenu)
        self._init_coll_HelpMenu_Items(self.HelpMenu)
    
    def _init_coll_PLCConfigMainSizer_Items(self, parent):
        parent.AddSizer(self.PLCParamsSizer, 0, border=10, flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        parent.AddSizer(self.PluginTreeSizer, 0, border=10, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
    def _init_coll_PLCConfigMainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_PluginTreeSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableCol(1)
        
    def _init_sizers(self):
        self.PLCConfigMainSizer = wx.FlexGridSizer(cols=1, hgap=2, rows=2, vgap=2)
        self.PLCParamsSizer = wx.BoxSizer(wx.VERTICAL)
        #self.PluginTreeSizer = wx.FlexGridSizer(cols=3, hgap=0, rows=0, vgap=2)
        self.PluginTreeSizer = wx.FlexGridSizer(cols=2, hgap=0, rows=0, vgap=2)
        
        self._init_coll_PLCConfigMainSizer_Items(self.PLCConfigMainSizer)
        self._init_coll_PLCConfigMainSizer_Growables(self.PLCConfigMainSizer)
        self._init_coll_PluginTreeSizer_Growables(self.PluginTreeSizer)
        
        self.PLCConfig.SetSizer(self.PLCConfigMainSizer)
        
    def _init_ctrls(self, prnt):
        wx.Frame.__init__(self, id=ID_BEREMIZ, name=u'Beremiz',
              parent=prnt, pos=wx.Point(0, 0), size=wx.Size(1000, 600),
              style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN, title=u'Beremiz')
        self._init_utils()
        self.SetClientSize(wx.Size(1000, 600))
        self.SetMenuBar(self.menuBar1)
        self.Bind(wx.EVT_ACTIVATE, self.OnFrameActivated)
        
        if wx.VERSION < (2, 8, 0):
            self.MainSplitter = wx.SplitterWindow(id=ID_BEREMIZMAINSPLITTER,
                  name='MainSplitter', parent=self, point=wx.Point(0, 0),
                  size=wx.Size(0, 0), style=wx.SP_3D)
            self.MainSplitter.SetNeedUpdating(True)
            self.MainSplitter.SetMinimumPaneSize(1)
        
            parent = self.MainSplitter
        else:
            parent = self
        
        self.PLCConfig = wx.ScrolledWindow(id=ID_BEREMIZPLCCONFIG,
              name='PLCConfig', parent=parent, pos=wx.Point(0, 0),
              size=wx.Size(-1, -1), style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER|wx.HSCROLL|wx.VSCROLL)
        self.PLCConfig.SetBackgroundColour(wx.WHITE)
        self.PLCConfig.Bind(wx.EVT_SIZE, self.OnMoveWindow)
        
        self.LogConsole = wx.TextCtrl(id=ID_BEREMIZLOGCONSOLE, value='',
                  name='LogConsole', parent=parent, pos=wx.Point(0, 0),
                  size=wx.Size(0, 0), style=wx.TE_MULTILINE|wx.TE_RICH2)
        
        if wx.VERSION < (2, 8, 0):
            self.MainSplitter.SplitHorizontally(self.PLCConfig, self.LogConsole, -250)
            
        else:
            self.AUIManager = wx.aui.AuiManager(self)
            self.AUIManager.SetDockSizeConstraint(0.5, 0.5)
            
            self.AUIManager.AddPane(self.PLCConfig, wx.aui.AuiPaneInfo().CenterPane())
            
            self.AUIManager.AddPane(self.LogConsole, wx.aui.AuiPaneInfo().
                Caption("Log Console").Bottom().Layer(1).
                BestSize(wx.Size(800, 200)).CloseButton(False))
        
            self.AUIManager.Update()

        self._init_sizers()

    def __init__(self, parent, projectOpen):
        self._init_ctrls(parent)
        
        self.Log = LogPseudoFile(self.LogConsole)
        
        self.PluginRoot = PluginsRoot(self)
        self.DisableEvents = False
        
        self.PluginInfos = {}
        
        if projectOpen:
            self.PluginRoot.LoadProject(projectOpen, self.Log)
            self.RefreshPLCParams()
            self.RefreshPluginTree()
        
        self.RefreshMainMenu()
    
    def OnMoveWindow(self, event):
        self.GetBestSize()
        self.RefreshScrollBars()
        event.Skip()
    
    def OnFrameActivated(self, event):
        if not event.GetActive():
            self.PluginRoot.RefreshPluginsBlockLists()
    
    def RefreshMainMenu(self):
        if self.menuBar1:
            if self.PluginRoot.HasProjectOpened():
##                self.menuBar1.EnableTop(1, True)
##                self.menuBar1.EnableTop(2, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS2, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS3, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS5, True)
            else:
##                self.menuBar1.EnableTop(1, False)
##                self.menuBar1.EnableTop(2, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS2, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS3, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS5, False)

    def RefreshScrollBars(self):
        xstart, ystart = self.PLCConfig.GetViewStart()
        window_size = self.PLCConfig.GetClientSize()
        sizer = self.PLCConfig.GetSizer()
        if sizer:
            maxx, maxy = sizer.GetMinSize()
            self.PLCConfig.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                maxx / SCROLLBAR_UNIT, maxy / SCROLLBAR_UNIT, xstart, ystart)

    def RefreshPLCParams(self):
        self.Freeze()
        self.ClearSizer(self.PLCParamsSizer)
        
        if self.PluginRoot.HasProjectOpened():
            plcwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
            plcwindow.SetBackgroundColour(TITLE_COLOUR)
            self.PLCParamsSizer.AddWindow(plcwindow, 0, border=0, flag=wx.GROW)
            
            plcwindowsizer = wx.BoxSizer(wx.HORIZONTAL)
            plcwindow.SetSizer(plcwindowsizer)
            
            st = wx.StaticText(plcwindow, -1)
            st.SetFont(wx.Font(faces["size"], wx.DEFAULT, wx.NORMAL, wx.BOLD, faceName = faces["helv"]))
            st.SetLabel(self.PluginRoot.GetProjectName())
            plcwindowsizer.AddWindow(st, 0, border=5, flag=wx.ALL|wx.ALIGN_CENTER)
            
            addbutton_id = wx.NewId()
            addbutton = wx.lib.buttons.GenBitmapButton(id=addbutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'Add16x16.png')),
                  name='AddBusButton', parent=plcwindow, pos=wx.Point(0, 0),
                  size=wx.Size(16, 16), style=wx.NO_BORDER)
            addbutton.SetToolTipString("Add a sub plugin")
            addbutton.Bind(wx.EVT_BUTTON, self.Gen_AddPluginMenu(self.PluginRoot), id=addbutton_id)
            plcwindowsizer.AddWindow(addbutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)
    
            plcwindowmainsizer = wx.BoxSizer(wx.VERTICAL)
            plcwindowsizer.AddSizer(plcwindowmainsizer, 0, border=5, flag=wx.ALL)
            
            plcwindowbuttonsizer = wx.BoxSizer(wx.HORIZONTAL)
            plcwindowmainsizer.AddSizer(plcwindowbuttonsizer, 0, border=0, flag=wx.ALIGN_CENTER)
            
            msizer = self.GenerateMethodButtonSizer(self.PluginRoot, plcwindow)
            plcwindowbuttonsizer.AddSizer(msizer, 0, border=0, flag=wx.GROW)
            
            paramswindow = wx.Panel(plcwindow, -1, size=wx.Size(-1, -1))
            paramswindow.SetBackgroundColour(TITLE_COLOUR)
            plcwindowbuttonsizer.AddWindow(paramswindow, 0, border=0, flag=0)
            
            psizer = wx.BoxSizer(wx.HORIZONTAL)
            paramswindow.SetSizer(psizer)
            
            plugin_infos = self.PluginRoot.GetParamsAttributes()
            self.RefreshSizerElement(paramswindow, psizer, self.PluginRoot, plugin_infos, None, False)
            
            paramswindow.Hide()
            
            minimizebutton_id = wx.NewId()
            minimizebutton = wx.lib.buttons.GenBitmapToggleButton(id=minimizebutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'Maximize.png')),
                  name='MinimizeButton', parent=plcwindow, pos=wx.Point(0, 0),
                  size=wx.Size(24, 24), style=wx.NO_BORDER)
            make_genbitmaptogglebutton_flat(minimizebutton)
            minimizebutton.SetBitmapSelected(wx.Bitmap(os.path.join(CWD, 'images', 'Minimize.png')))
            plcwindowbuttonsizer.AddWindow(minimizebutton, 0, border=5, flag=wx.ALL)
            
#            if len(self.PluginRoot.PlugChildsTypes) > 0:
#                addsizer = self.GenerateAddButtonSizer(self.PluginRoot, plcwindow)
#                plcwindowbuttonsizer.AddSizer(addsizer, 0, border=0, flag=0)
#            else:
#                addsizer = None

            def togglewindow(event):
                if minimizebutton.GetToggle():
                    paramswindow.Show()
                    msizer.SetCols(1)
#                    if addsizer is not None:
#                        addsizer.SetCols(1)
                else:
                    paramswindow.Hide()
                    msizer.SetCols(len(self.PluginRoot.PluginMethods))
#                    if addsizer is not None:
#                        addsizer.SetCols(len(self.PluginRoot.PlugChildsTypes))
                self.PLCConfigMainSizer.Layout()
                self.RefreshScrollBars()
                event.Skip()
            minimizebutton.Bind(wx.EVT_BUTTON, togglewindow, id=minimizebutton_id)
        
        self.PLCConfigMainSizer.Layout()
        self.RefreshScrollBars()
        self.Thaw()

#    def GenerateAddButtonSizer(self, plugin, parent, horizontal = True):
#        if horizontal:
#            addsizer = wx.FlexGridSizer(cols=len(plugin.PluginMethods))
#        else:
#            addsizer = wx.FlexGridSizer(cols=1)
#        for name, XSDClass, help in plugin.PlugChildsTypes:
#            addbutton_id = wx.NewId()
#            addbutton = wx.lib.buttons.GenButton(id=addbutton_id, label="Add %s"%help,
#                  name='AddBusButton', parent=parent, pos=wx.Point(0, 0),
#                  style=wx.NO_BORDER)
#            font = addbutton.GetFont()
#            font.SetUnderlined(True)
#            addbutton.SetFont(font)
#            addbutton._GetLabelSize = gen_textbutton_GetLabelSize(addbutton)
#            addbutton.SetForegroundColour(wx.BLUE)
#            addbutton.SetToolTipString("Add a \"%s\" plugin to this one"%name)
#            addbutton.Bind(wx.EVT_BUTTON, self._GetAddPluginFunction(name, plugin), id=addbutton_id)
#            addsizer.AddWindow(addbutton, 0, border=0, flag=0)
#        return addsizer

    def GenerateMethodButtonSizer(self, plugin, parent, horizontal = True):
        if horizontal:
            msizer = wx.FlexGridSizer(cols=len(plugin.PluginMethods))
        else:
            msizer = wx.FlexGridSizer(cols=1)
        for plugin_method in plugin.PluginMethods:
            if "method" in plugin_method:
                id = wx.NewId()
                button = GenBitmapTextButton(id=id, parent=parent,
                    bitmap=wx.Bitmap(os.path.join(CWD, "%s24x24.png"%plugin_method.get("bitmap", os.path.join("images", "Unknown")))), label=plugin_method["name"], 
                    name=plugin_method["name"], pos=wx.DefaultPosition, style=wx.NO_BORDER)
                button.SetToolTipString(plugin_method["tooltip"])
                button.Bind(wx.EVT_BUTTON, self.GetButtonCallBackFunction(plugin, plugin_method["method"]), id=id)
                #hack to force size to mini
                if not plugin_method.get("enabled",True):
                    button.Disable()
                msizer.AddWindow(button, 0, border=0, flag=0)
        return msizer

    def RefreshPluginTree(self):
        self.Freeze()
        self.ClearSizer(self.PluginTreeSizer)
        if self.PluginRoot.HasProjectOpened():
            index = [0]
            for child in self.PluginRoot.IECSortedChilds():
                self.GenerateTreeBranch(child, index)
                if not self.PluginInfos[child]["expanded"]:
                    self.CollapsePlugin(child)
        self.PLCConfigMainSizer.Layout()
        self.RefreshScrollBars()
        self.Thaw()

    def ExpandPlugin(self, plugin, force = False):
        for child in self.PluginInfos[plugin]["children"]:
            self.PluginTreeSizer.Show(self.PluginInfos[child]["left"])
            self.PluginTreeSizer.Show(self.PluginInfos[child]["middle"])
#            self.PluginTreeSizer.Show(self.PluginInfos[child]["right"])
            if force or not self.PluginInfos[child]["expanded"]:
                self.ExpandPlugin(child, force)
                if force:
                    self.PluginInfos[child]["expanded"] = True
    
    def CollapsePlugin(self, plugin, force = False):
        for child in self.PluginInfos[plugin]["children"]:
            self.PluginTreeSizer.Hide(self.PluginInfos[child]["left"])
            self.PluginTreeSizer.Hide(self.PluginInfos[child]["middle"])
#            self.PluginTreeSizer.Hide(self.PluginInfos[child]["right"])
            if force or self.PluginInfos[child]["expanded"]:
                self.CollapsePlugin(child, force)
                if force:
                    self.PluginInfos[child]["expanded"] = False

    def GenerateTreeBranch(self, plugin, index):
        leftwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
        leftwindow.SetBackgroundColour(WINDOW_COLOUR)
        
        if plugin not in self.PluginInfos:
            self.PluginInfos[plugin] = {"expanded" : False, "left_visible" : False, "middle_visible" : False}
            
        self.PluginInfos[plugin]["children"] = plugin.IECSortedChilds()
        
        self.PluginTreeSizer.AddWindow(leftwindow, 0, border=0, flag=wx.GROW)
        
        leftwindowsizer = wx.FlexGridSizer(cols=1, rows=3)
        leftwindowsizer.AddGrowableCol(0)
        leftwindowsizer.AddGrowableRow(2)
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

        enablebutton_id = wx.NewId()
        enablebutton = wx.lib.buttons.GenBitmapToggleButton(id=enablebutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'Disabled.png')),
              name='EnableButton', parent=leftwindow, size=wx.Size(16, 16), pos=wx.Point(0, 0), style=0)#wx.NO_BORDER)
        enablebutton.SetToolTipString("Enable/Disable this plugin")
        make_genbitmaptogglebutton_flat(enablebutton)
        enablebutton.SetBitmapSelected(wx.Bitmap(os.path.join(CWD, 'images', 'Enabled.png')))
        enablebutton.SetToggle(plugin.MandatoryParams[1].getEnabled())
        def toggleenablebutton(event):
            res, StructChanged = plugin.SetParamsAttribute("BaseParams.Enabled", enablebutton.GetToggle(), self.Log)
            if StructChanged: wx.CallAfter(self.RefreshPluginTree)
            enablebutton.SetToggle(res)
            event.Skip()
        enablebutton.Bind(wx.EVT_BUTTON, toggleenablebutton, id=enablebutton_id)
        rolesizer.AddWindow(enablebutton, 0, border=0, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)

        roletext = wx.StaticText(leftwindow, -1)
        roletext.SetLabel(plugin.PlugHelp)
        rolesizer.AddWindow(roletext, 0, border=5, flag=wx.RIGHT|wx.ALIGN_LEFT)
        
        plugin_IECChannel = plugin.BaseParams.getIEC_Channel()
        
        iecsizer = wx.BoxSizer(wx.HORIZONTAL)
        leftsizer.AddSizer(iecsizer, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)

        st = wx.StaticText(leftwindow, -1)
        st.SetFont(wx.Font(faces["size"], wx.DEFAULT, wx.NORMAL, wx.BOLD, faceName = faces["helv"]))
        st.SetLabel(plugin.GetFullIEC_Channel())
        iecsizer.AddWindow(st, 0, border=0, flag=0)

        updownsizer = wx.BoxSizer(wx.VERTICAL)
        iecsizer.AddSizer(updownsizer, 0, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        if plugin_IECChannel > 0:
            ieccdownbutton_id = wx.NewId()
            ieccdownbutton = wx.lib.buttons.GenBitmapButton(id=ieccdownbutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'IECCDown.png')),
                  name='IECCDownButton', parent=leftwindow, pos=wx.Point(0, 0),
                  size=wx.Size(16, 16), style=wx.NO_BORDER)
            ieccdownbutton.Bind(wx.EVT_BUTTON, self.GetItemChannelChangedFunction(plugin, plugin_IECChannel - 1), id=ieccdownbutton_id)
            updownsizer.AddWindow(ieccdownbutton, 0, border=0, flag=wx.ALIGN_LEFT)

        ieccupbutton_id = wx.NewId()
        ieccupbutton = wx.lib.buttons.GenBitmapTextButton(id=ieccupbutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'IECCUp.png')),
              name='IECCUpButton', parent=leftwindow, pos=wx.Point(0, 0),
              size=wx.Size(16, 16), style=wx.NO_BORDER)
        ieccupbutton.Bind(wx.EVT_BUTTON, self.GetItemChannelChangedFunction(plugin, plugin_IECChannel + 1), id=ieccupbutton_id)
        updownsizer.AddWindow(ieccupbutton, 0, border=0, flag=wx.ALIGN_LEFT)

        adddeletesizer = wx.BoxSizer(wx.VERTICAL)
        iecsizer.AddSizer(adddeletesizer, 0, border=5, flag=wx.LEFT|wx.ALIGN_CENTER_VERTICAL)

        deletebutton_id = wx.NewId()
        deletebutton = wx.lib.buttons.GenBitmapButton(id=deletebutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'Delete16x16.png')),
              name='DeleteBusButton', parent=leftwindow, pos=wx.Point(0, 0),
              size=wx.Size(16, 16), style=wx.NO_BORDER)
        deletebutton.SetToolTipString("Delete this plugin")
        deletebutton.Bind(wx.EVT_BUTTON, self.GetDeleteButtonFunction(plugin), id=deletebutton_id)
        adddeletesizer.AddWindow(deletebutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)

        if len(plugin.PlugChildsTypes) > 0:
            addbutton_id = wx.NewId()
            addbutton = wx.lib.buttons.GenBitmapButton(id=addbutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'Add16x16.png')),
                  name='AddBusButton', parent=leftwindow, pos=wx.Point(0, 0),
                  size=wx.Size(16, 16), style=wx.NO_BORDER)
            addbutton.SetToolTipString("Add a sub plugin")
            addbutton.Bind(wx.EVT_BUTTON, self.Gen_AddPluginMenu(plugin), id=addbutton_id)
            adddeletesizer.AddWindow(addbutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)
        
        if len(self.PluginInfos[plugin]["children"]) > 0:
            expandbutton_id = wx.NewId()
            expandbutton = wx.lib.buttons.GenBitmapToggleButton(id=expandbutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'plus.png')),
                  name='ExpandButton', parent=leftwindow, pos=wx.Point(0, 0),
                  size=wx.Size(13, 13), style=wx.NO_BORDER)
            expandbutton.labelDelta = 0
            expandbutton.SetBezelWidth(0)
            expandbutton.SetUseFocusIndicator(False)
            expandbutton.SetBitmapSelected(wx.Bitmap(os.path.join(CWD, 'images', 'minus.png')))
            expandbutton.SetToggle(self.PluginInfos[plugin]["expanded"])
            
            def togglebutton(event):
                if expandbutton.GetToggle():
                    self.ExpandPlugin(plugin)
                else:
                    self.CollapsePlugin(plugin)
                self.PluginInfos[plugin]["expanded"] = expandbutton.GetToggle()
                self.PLCConfigMainSizer.Layout()
                self.RefreshScrollBars()
                event.Skip()
            expandbutton.Bind(wx.EVT_BUTTON, togglebutton, id=expandbutton_id)
            leftbuttonsizer.AddWindow(expandbutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
        
        tc_id = wx.NewId()
        tc = wx.TextCtrl(leftwindow, tc_id, size=wx.Size(150, 35), style=wx.TE_PROCESS_ENTER|wx.NO_BORDER)
        tc.SetFont(wx.Font(faces["size"] * 0.75, wx.DEFAULT, wx.NORMAL, wx.BOLD, faceName = faces["helv"]))
        tc.SetValue(plugin.MandatoryParams[1].getName())
        tc.Bind(wx.EVT_TEXT_ENTER, self.GetTextCtrlCallBackFunction(tc, plugin, "BaseParams.Name"), id=tc_id)
        leftbuttonsizer.AddWindow(tc, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER_VERTICAL)
       

        leftminimizebutton_id = wx.NewId()
        leftminimizebutton = wx.lib.buttons.GenBitmapToggleButton(id=leftminimizebutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'ShowVars.png')),
              name='MinimizeButton', parent=leftwindow, pos=wx.Point(0, 0),
              size=wx.Size(24, 24), style=wx.NO_BORDER)
        make_genbitmaptogglebutton_flat(leftminimizebutton)
        leftminimizebutton.SetBitmapSelected(wx.Bitmap(os.path.join(CWD, 'images', 'HideVars.png')))
        leftminimizebutton.SetToggle(self.PluginInfos[plugin]["left_visible"])
        def toggleleftwindow(event):
            if leftminimizebutton.GetToggle():
                leftwindowsizer.Show(1)
            else:
                leftwindowsizer.Hide(1)
            self.PluginInfos[plugin]["left_visible"] = leftminimizebutton.GetToggle()
            self.PLCConfigMainSizer.Layout()
            self.RefreshScrollBars()
            event.Skip()
        leftminimizebutton.Bind(wx.EVT_BUTTON, toggleleftwindow, id=leftminimizebutton_id)
        leftbuttonmainsizer.AddWindow(leftminimizebutton, 0, border=5, flag=wx.RIGHT|wx.ALIGN_CENTER)

        locations = plugin.GetLocations()
        lb = wx.ListBox(leftwindow, -1, size=wx.Size(-1, max(1, min(len(locations), 4)) * 25), style=wx.NO_BORDER)
        for location in locations:
            lb.Append(location["NAME"].replace("__", "%").replace("_", "."))
        if not self.PluginInfos[plugin]["left_visible"]:
            lb.Hide()
        self.PluginInfos[plugin]["variable_list"] = lb
        leftwindowsizer.AddWindow(lb, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)

        middlewindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
        middlewindow.SetBackgroundColour(wx.Colour(240,240,240))
        
        self.PluginTreeSizer.AddWindow(middlewindow, 0, border=0, flag=wx.GROW)
        
        middlewindowmainsizer = wx.BoxSizer(wx.VERTICAL)
        middlewindow.SetSizer(middlewindowmainsizer)
        
        middlewindowsizer = wx.FlexGridSizer(cols=2, rows=1)
        middlewindowsizer.AddGrowableCol(1)
        middlewindowsizer.AddGrowableRow(0)
        middlewindowmainsizer.AddSizer(middlewindowsizer, 0, border=8, flag=wx.TOP|wx.GROW)
        
        msizer = self.GenerateMethodButtonSizer(plugin, middlewindow, not self.PluginInfos[plugin]["middle_visible"])
        middlewindowsizer.AddSizer(msizer, 0, border=0, flag=wx.GROW)
        
        middleparamssizer = wx.BoxSizer(wx.HORIZONTAL)
        middlewindowsizer.AddSizer(middleparamssizer, 0, border=0, flag=wx.ALIGN_RIGHT)
        
        paramswindow = wx.Panel(middlewindow, -1, size=wx.Size(-1, -1))
        paramswindow.SetBackgroundColour(WINDOW_COLOUR)
        
        psizer = wx.BoxSizer(wx.HORIZONTAL)
        paramswindow.SetSizer(psizer)
        
        middleparamssizer.AddWindow(paramswindow, 0, border=5, flag=wx.ALL)
        
        plugin_infos = plugin.GetParamsAttributes()
        self.RefreshSizerElement(paramswindow, psizer, plugin, plugin_infos, None, False)
        
        if not self.PluginInfos[plugin]["middle_visible"]:
            paramswindow.Hide()
        
        middleminimizebutton_id = wx.NewId()
        middleminimizebutton = wx.lib.buttons.GenBitmapToggleButton(id=middleminimizebutton_id, bitmap=wx.Bitmap(os.path.join(CWD, 'images', 'Maximize.png')),
              name='MinimizeButton', parent=middlewindow, pos=wx.Point(0, 0),
              size=wx.Size(24, 24), style=wx.NO_BORDER)
        make_genbitmaptogglebutton_flat(middleminimizebutton)
        middleminimizebutton.SetBitmapSelected(wx.Bitmap(os.path.join(CWD, 'images', 'Minimize.png')))
        middleminimizebutton.SetToggle(self.PluginInfos[plugin]["middle_visible"])
        middleparamssizer.AddWindow(middleminimizebutton, 0, border=5, flag=wx.ALL)
        
#        rightwindow = wx.Panel(self.PLCConfig, -1, size=wx.Size(-1, -1))
#        rightwindow.SetBackgroundColour(wx.Colour(240,240,240))
#        
#        self.PluginTreeSizer.AddWindow(rightwindow, 0, border=0, flag=wx.GROW)
#        
#        rightsizer = wx.BoxSizer(wx.VERTICAL)
#        rightwindow.SetSizer(rightsizer)
#        
#        rightmainsizer = wx.BoxSizer(wx.VERTICAL)
#        rightsizer.AddSizer(rightmainsizer, 0, border=5, flag=wx.ALL)
#        
#        if len(plugin.PlugChildsTypes) > 0:
#            addsizer = self.GenerateAddButtonSizer(plugin, rightwindow)
#            rightmainsizer.AddSizer(addsizer, 0, border=4, flag=wx.TOP)
#        else:
#            addsizer = None
            
        def togglemiddlerightwindow(event):
            if middleminimizebutton.GetToggle():
                middleparamssizer.Show(0)
                msizer.SetCols(1)
#                if addsizer is not None:
#                    addsizer.SetCols(1)
            else:
                middleparamssizer.Hide(0)
                msizer.SetCols(len(plugin.PluginMethods))
#                if addsizer is not None:
#                    addsizer.SetCols(len(plugin.PlugChildsTypes))
            self.PluginInfos[plugin]["middle_visible"] = middleminimizebutton.GetToggle()
            self.PLCConfigMainSizer.Layout()
            self.RefreshScrollBars()
            event.Skip()
        middleminimizebutton.Bind(wx.EVT_BUTTON, togglemiddlerightwindow, id=middleminimizebutton_id)
        
        self.PluginInfos[plugin]["left"] = index[0]
        self.PluginInfos[plugin]["middle"] = index[0] + 1
#        self.PluginInfos[plugin]["right"] = index[0] + 2
#        index[0] += 3
        index[0] += 2
        for child in self.PluginInfos[plugin]["children"]:
            self.GenerateTreeBranch(child, index)
            if not self.PluginInfos[child]["expanded"]:
                self.CollapsePlugin(child)

    def RefreshVariableLists(self):
        for plugin, infos in self.PluginInfos.items():
            locations = plugin.GetLocations()
            infos["variable_list"].SetSize(wx.Size(-1, max(1, min(len(locations), 4)) * 25))
            infos["variable_list"].Clear()
            for location in locations:
                infos["variable_list"].Append(location["NAME"].replace("__", "%").replace("_", "."))
        self.PLCConfigMainSizer.Layout()
        self.RefreshScrollBars()
        
    def RefreshAll(self):
        self.RefreshPLCParams()
        self.RefreshPluginTree()
        
    def GetItemChannelChangedFunction(self, plugin, value):
        def OnPluginTreeItemChannelChanged(event):
            res, StructChanged = plugin.SetParamsAttribute("BaseParams.IEC_Channel", value, self.Log)
            wx.CallAfter(self.RefreshPluginTree)
            event.Skip()
        return OnPluginTreeItemChannelChanged
    
    def _GetAddPluginFunction(self, name, plugin):
        def OnPluginMenu(event):
            wx.CallAfter(self.AddPlugin, name, plugin)
            event.Skip()
        return OnPluginMenu
    
    def Gen_AddPluginMenu(self, plugin):
        def AddPluginMenu(event):
            main_menu = wx.Menu(title='')
            if len(plugin.PlugChildsTypes) > 0:
                for name, XSDClass, help in plugin.PlugChildsTypes:
                    new_id = wx.NewId()
                    main_menu.Append(help=help, id=new_id, kind=wx.ITEM_NORMAL, text="Append "+help)
                    self.Bind(wx.EVT_MENU, self._GetAddPluginFunction(name, plugin), id=new_id)
            self.PopupMenuXY(main_menu)
            event.Skip()
        return AddPluginMenu
    
    def GetButtonCallBackFunction(self, plugin, method):
        """ Generate the callbackfunc for a given plugin method"""
        def OnButtonClick(event):
            # Disable button to prevent re-entrant call 
            event.GetEventObject().Disable()
            # Call
            getattr(plugin,method)(self.Log)
            # Re-enable button 
            event.GetEventObject().Enable()
            # Trigger refresh on Idle
            wx.CallAfter(self.RefreshAll)
            event.Skip()
        return OnButtonClick
    
    def GetChoiceCallBackFunction(self, choicectrl, plugin, path):
        def OnChoiceChanged(event):
            res, StructChanged = plugin.SetParamsAttribute(path, choicectrl.GetStringSelection(), self.Log)
            if StructChanged: wx.CallAfter(self.RefreshPluginTree)
            choicectrl.SetStringSelection(res)
            event.Skip()
        return OnChoiceChanged
    
    def GetChoiceContentCallBackFunction(self, choicectrl, staticboxsizer, plugin, path):
        def OnChoiceContentChanged(event):
            res, StructChanged = plugin.SetParamsAttribute(path, choicectrl.GetStringSelection(), self.Log)
            if StructChanged: wx.CallAfter(self.RefreshPluginTree)
            choicectrl.SetStringSelection(res)
            infos = self.PluginRoot.GetParamsAttributes(path)
            staticbox = staticboxsizer.GetStaticBox()
            staticbox.SetLabel("%(name)s - %(value)s"%infos)
            if wx.VERSION < (2, 8, 0):
                self.ParamsPanel.Freeze()
                self.RefreshSizerElement(self.ParamsPanel, staticboxsizer, infos["children"], "%s.%s"%(path, infos["name"]), selected=selected)
                self.ParamsPanelMainSizer.Layout()
                self.ParamsPanel.Thaw()
                self.ParamsPanel.Refresh()
            else:
                wx.CallAfter(self.RefreshPluginTree)
            event.Skip()
        return OnChoiceContentChanged
    
    def GetTextCtrlCallBackFunction(self, textctrl, plugin, path):
        def OnTextCtrlChanged(event):
            res, StructChanged = plugin.SetParamsAttribute(path, textctrl.GetValue(), self.Log)
            if StructChanged: wx.CallAfter(self.RefreshPluginTree)
            textctrl.SetValue(res)
            event.Skip()
        return OnTextCtrlChanged
    
    def GetCheckBoxCallBackFunction(self, chkbx, plugin, path):
        def OnCheckBoxChanged(event):
            res, StructChanged = plugin.SetParamsAttribute(path, chkbx.IsChecked(), self.Log)
            if StructChanged: wx.CallAfter(self.RefreshPluginTree)
            chkbx.SetValue(res)
            event.Skip()
        return OnCheckBoxChanged
    
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
                
    def RefreshSizerElement(self, parent, sizer, plugin, elements, path, clean = True):
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
            if isinstance(element_infos["type"], types.ListType):
                boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                if first:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                else:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
                staticbitmap = GenStaticBitmap(ID=-1, bitmapname="%s.png"%element_infos["name"],
                    name="%s_bitmap"%element_infos["name"], parent=parent,
                    pos=wx.Point(0, 0), size=wx.Size(24, 24), style=0)
                boxsizer.AddWindow(staticbitmap, 0, border=5, flag=wx.RIGHT)
                statictext = wx.StaticText(id=-1, label="%s:"%element_infos["name"], 
                    name="%s_label"%element_infos["name"], parent=parent, 
                    pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)
                boxsizer.AddWindow(statictext, 0, border=4, flag=wx.TOP)
                id = wx.NewId()
                choicectrl = wx.Choice(id=id, name=element_infos["name"], parent=parent, 
                    pos=wx.Point(0, 0), size=wx.Size(150, 25), style=0)
                boxsizer.AddWindow(choicectrl, 0, border=0, flag=0)
                choicectrl.Append("")
                if len(element_infos["type"]) > 0 and isinstance(element_infos["type"][0], types.TupleType):
                    for choice, xsdclass in element_infos["type"]:
                        choicectrl.Append(choice)
                    staticbox = wx.StaticBox(id=-1, label="%(name)s - %(value)s"%element_infos, 
                        name='%s_staticbox'%element_infos["name"], parent=parent,
                        pos=wx.Point(0, 0), size=wx.Size(0, 0), style=0)
                    staticboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
                    sizer.AddSizer(staticboxsizer, 0, border=5, flag=wx.GROW|wx.BOTTOM)
                    self.RefreshSizerElement(parent, staticboxsizer, plugin, element_infos["children"], element_path)
                    callback = self.GetChoiceContentCallBackFunction(choicectrl, staticboxsizer, plugin, element_path)
                else:
                    for choice in element_infos["type"]:
                        choicectrl.Append(choice)
                    callback = self.GetChoiceCallBackFunction(choicectrl, plugin, element_path)
                if element_infos["value"]:
                    choicectrl.SetStringSelection(element_infos["value"])
                choicectrl.Bind(wx.EVT_CHOICE, callback, id=id)
            elif isinstance(element_infos["type"], types.DictType):
                boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                if first:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                else:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
                staticbitmap = GenStaticBitmap(ID=-1, bitmapname="%s.png"%element_infos["name"],
                    name="%s_bitmap"%element_infos["name"], parent=parent,
                    pos=wx.Point(0, 0), size=wx.Size(24, 24), style=0)
                boxsizer.AddWindow(staticbitmap, 0, border=5, flag=wx.RIGHT)
                statictext = wx.StaticText(id=-1, label="%s:"%element_infos["name"], 
                    name="%s_label"%element_infos["name"], parent=parent, 
                    pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)
                boxsizer.AddWindow(statictext, 0, border=4, flag=wx.TOP)
                id = wx.NewId()
                scmin = -(2**31)
                scmax = 2**31-1
                if "min" in element_infos["type"]:
                    scmin = element_infos["type"]["min"]
                if "max" in element_infos["type"]:
                    scmax = element_infos["type"]["max"]
                spinctrl = wx.SpinCtrl(id=id, name=element_infos["name"], parent=parent, 
                    pos=wx.Point(0, 0), size=wx.Size(150, 25), style=wx.SP_ARROW_KEYS|wx.ALIGN_RIGHT)
                spinctrl.SetRange(scmin,scmax)
                boxsizer.AddWindow(spinctrl, 0, border=0, flag=0)
                spinctrl.SetValue(element_infos["value"])
                spinctrl.Bind(wx.EVT_SPINCTRL, self.GetTextCtrlCallBackFunction(spinctrl, plugin, element_path), id=id)
            elif element_infos["type"] == "element":
                staticbox = wx.StaticBox(id=-1, label=element_infos["name"], 
                    name='%s_staticbox'%element_infos["name"], parent=parent,
                    pos=wx.Point(0, 0), size=wx.Size(0, 0), style=0)
                staticboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
                if first:
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW|wx.TOP)
                else:
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW)
                self.RefreshSizerElement(parent, staticboxsizer, plugin, element_infos["children"], element_path)
            else:
                boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                if first:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                else:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
                staticbitmap = GenStaticBitmap(ID=-1, bitmapname="%s.png"%element_infos["name"],
                    name="%s_bitmap"%element_infos["name"], parent=parent,
                    pos=wx.Point(0, 0), size=wx.Size(24, 24), style=0)
                boxsizer.AddWindow(staticbitmap, 0, border=5, flag=wx.RIGHT)

                statictext = wx.StaticText(id=-1, label="%s:"%element_infos["name"], 
                    name="%s_label"%element_infos["name"], parent=parent, 
                    pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)
                boxsizer.AddWindow(statictext, 0, border=4, flag=wx.TOP)
                id = wx.NewId()
                if element_infos["type"] == "boolean":
                    checkbox = wx.CheckBox(id=id, name=element_infos["name"], parent=parent, 
                        pos=wx.Point(0, 0), size=wx.Size(17, 25), style=0)
                    boxsizer.AddWindow(checkbox, 0, border=0, flag=0)
                    checkbox.SetValue(element_infos["value"])
                    checkbox.Bind(wx.EVT_CHECKBOX, self.GetCheckBoxCallBackFunction(checkbox, plugin, element_path), id=id)
                elif element_infos["type"] in ["unsignedLong", "long","integer"]:
                    if element_infos["type"].startswith("unsigned"):
                        scmin = 0
                    else:
                        scmin = -(2**31)
                    scmax = 2**31-1
                    spinctrl = wx.SpinCtrl(id=id, name=element_infos["name"], parent=parent, 
                        pos=wx.Point(0, 0), size=wx.Size(150, 25), style=wx.SP_ARROW_KEYS|wx.ALIGN_RIGHT)
                    spinctrl.SetRange(scmin, scmax)
                    boxsizer.AddWindow(spinctrl, 0, border=0, flag=0)
                    spinctrl.SetValue(element_infos["value"])
                    spinctrl.Bind(wx.EVT_SPINCTRL, self.GetTextCtrlCallBackFunction(spinctrl, plugin, element_path), id=id)
                else:
                    textctrl = wx.TextCtrl(id=id, name=element_infos["name"], parent=parent, 
                        pos=wx.Point(0, 0), size=wx.Size(150, 25), style=wx.TE_PROCESS_ENTER)
                    boxsizer.AddWindow(textctrl, 0, border=0, flag=0)
                    textctrl.SetValue(str(element_infos["value"]))
                    textctrl.Bind(wx.EVT_TEXT_ENTER, self.GetTextCtrlCallBackFunction(textctrl, plugin, element_path), id=id)
                    textctrl.Bind(wx.EVT_KILL_FOCUS, self.GetTextCtrlCallBackFunction(textctrl, plugin, element_path))
            first = False
    
    def OnNewProjectMenu(self, event):
        defaultpath = self.PluginRoot.GetProjectPath()
        if not defaultpath:
            defaultpath = os.getcwd()
        dialog = wx.DirDialog(self , "Choose a project", defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            dialog.Destroy()
            res = self.PluginRoot.NewProject(projectpath)
            if not res :
                self.RefreshPLCParams()
                self.RefreshPluginTree()
                self.RefreshMainMenu()
            else:
                message = wx.MessageDialog(self, res, "ERROR", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
        event.Skip()
    
    def OnOpenProjectMenu(self, event):
        defaultpath = self.PluginRoot.GetProjectPath()
        if not defaultpath:
            defaultpath = os.getcwd()
        dialog = wx.DirDialog(self , "Choose a project", defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            if os.path.isdir(projectpath):
                result = self.PluginRoot.LoadProject(projectpath, self.Log)
                if not result:
                    self.RefreshPLCParams()
                    self.RefreshPluginTree()
                    self.RefreshMainMenu()
                else:
                    message = wx.MessageDialog(self, result, "Error", wx.OK|wx.ICON_ERROR)
                    message.ShowModal()
                    message.Destroy()
            else:
                message = wx.MessageDialog(self, "\"%s\" folder is not a valid Beremiz project\n"%projectpath, "Error", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
            dialog.Destroy()
        event.Skip()
    
    def OnCloseProjectMenu(self, event):
        self.PluginInfos = {}
        self.RefreshPLCParams()
        self.RefreshPluginTree()
        self.RefreshMainMenu()
        event.Skip()
    
    def OnSaveProjectMenu(self, event):
        if self.PluginRoot.HasProjectOpened():
            self.PluginRoot.SaveProject()
        event.Skip()
    
    def OnPropertiesMenu(self, event):
        event.Skip()
    
    def OnQuitMenu(self, event):
        self.Close()
        event.Skip()
    
    def OnEditPLCMenu(self, event):
        self.EditPLC()
        event.Skip()
    
    def OnAddMenu(self, event):
        self.AddPlugin()
        event.Skip()
    
    def OnDeleteMenu(self, event):
        self.DeletePlugin()
        event.Skip()

    def OnBuildMenu(self, event):
        #self.BuildAutom()
        event.Skip()

    def OnSimulateMenu(self, event):
        event.Skip()
    
    def OnRunMenu(self, event):
        event.Skip()
    
    def OnSaveLogMenu(self, event):
        event.Skip()
    
    def OnBeremizMenu(self, event):
        event.Skip()
    
    def OnAboutMenu(self, event):
        event.Skip()
    
    def OnAddButton(self, event):
        PluginType = self.PluginChilds.GetStringSelection()
        if PluginType != "":
            self.AddPlugin(PluginType)
        event.Skip()
    
    def OnDeleteButton(self, event):
        self.DeletePlugin()
        event.Skip()
    
    def GetAddButtonFunction(self, plugin, window):
        def AddButtonFunction(event):
            if plugin and len(plugin.PlugChildsTypes) > 0:
                plugin_menu = wx.Menu(title='')
                for name, XSDClass, help in plugin.PlugChildsTypes:
                    new_id = wx.NewId()
                    plugin_menu.Append(help=help, id=new_id, kind=wx.ITEM_NORMAL, text=name)
                    self.Bind(wx.EVT_MENU, self._GetAddPluginFunction(name, plugin), id=new_id)
                window_pos = window.GetPosition()
                wx.CallAfter(self.PLCConfig.PopupMenu, plugin_menu)
            event.Skip()
        return AddButtonFunction
    
    def GetDeleteButtonFunction(self, plugin):
        def DeleteButtonFunction(event):
            wx.CallAfter(self.DeletePlugin, plugin)
            event.Skip()
        return DeleteButtonFunction
    
    def AddPlugin(self, PluginType, plugin):
        dialog = wx.TextEntryDialog(self, "Please enter a name for plugin:", "Add Plugin", "", wx.OK|wx.CANCEL)
        if dialog.ShowModal() == wx.ID_OK:
            PluginName = dialog.GetValue()
            plugin.PlugAddChild(PluginName, PluginType, self.Log)
            self.RefreshPluginTree()
        dialog.Destroy()
    
    def DeletePlugin(self, plugin):
        dialog = wx.MessageDialog(self, "Really delete plugin ?", "Remove plugin", wx.YES_NO|wx.NO_DEFAULT)
        if dialog.ShowModal() == wx.ID_YES:
            self.PluginInfos.pop(plugin)
            plugin.PlugRemove()
            del plugin
            self.RefreshPluginTree()
        dialog.Destroy()

#-------------------------------------------------------------------------------
#                               Exception Handler
#-------------------------------------------------------------------------------

Max_Traceback_List_Size = 20

def Display_Exception_Dialog(e_type, e_value, e_tb, bug_report_path):
    trcbck_lst = []
    for i,line in enumerate(traceback.extract_tb(e_tb)):
        trcbck = " " + str(i+1) + ". "
        if line[0].find(os.getcwd()) == -1:
            trcbck += "file : " + str(line[0]) + ",   "
        else:
            trcbck += "file : " + str(line[0][len(os.getcwd()):]) + ",   "
        trcbck += "line : " + str(line[1]) + ",   " + "function : " + str(line[2])
        trcbck_lst.append(trcbck)
        
    # Allow clicking....
    cap = wx.Window_GetCapture()
    if cap:
        cap.ReleaseMouse()

    dlg = wx.SingleChoiceDialog(None, 
        """
An unhandled exception (bug) occured. Bug report saved at :
(%s)

Please be kind enough to send this file to:
bugs_beremiz@lolitech.fr

You should now restart Beremiz.

Traceback:
""" % bug_report_path +
        str(e_type) + " : " + str(e_value), 
        "Error",
        trcbck_lst)
    try:
        res = (dlg.ShowModal() == wx.ID_OK)
    finally:
        dlg.Destroy()

    return res

def Display_Error_Dialog(e_value):
    message = wxMessageDialog(None, str(e_value), "Error", wxOK|wxICON_ERROR)
    message.ShowModal()
    message.Destroy()

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
        if str(e_value).startswith("!!!"):
            Display_Error_Dialog(e_value)
        elif ex not in ignored_exceptions:
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
    def usage():
        print "\nUsage of Beremiz.py :"
        print "\n   %s [Projectpath]\n"%sys.argv[0]
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.GetoptError:
        # print help information and exit:
        usage()
        sys.exit(2)
    
    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
    
    if len(args) > 1:
        usage()
        sys.exit()
    elif len(args) == 1:
        projectOpen = args[0]
    else:
        projectOpen = None
    
    app = wx.PySimpleApp()
    wx.InitAllImageHandlers()
    
    # Install a exception handle for bug reports
    AddExceptHook(os.getcwd(),__version__)
    
    frame = Beremiz(None, projectOpen)
    
    # Add beremiz's icon in top left corner of the frame
    if wx.Platform == '__WXMSW__':
        winicon = wx.Icon(os.path.join(CWD,"brz.ico"),wx.BITMAP_TYPE_ICO)
        frame.SetIcon(winicon)
    else:
		linicon = wx.Icon(os.path.join(CWD,"brz.png"),wx.BITMAP_TYPE_PNG)
		frame.SetIcon(linicon)
    frame.Show()
    app.MainLoop()
