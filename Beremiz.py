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

import types

import os, re, platform, sys, time, traceback, getopt, commands

from plugger import PluginsRoot

def CHECK_WX_VERSION(major, minor, release):
    return not (wx.MAJOR_VERSION < major or wx.MINOR_VERSION < minor or wx.RELEASE_NUMBER < release)

class LogPseudoFile:
    """ Base class for file like objects to facilitate StdOut for the Shell."""
    def __init__(self, output = None):
        self.red_white = wx.TextAttr("RED", "WHITE")
        self.red_yellow = wx.TextAttr("RED", "YELLOW")
        self.black_white = wx.TextAttr("BLACK", "WHITE")
        self.default_style = None
        self.output = output

    def writelines(self, l):
        map(self.write, l)

    def write(self, s, style = None):
        if not style : style=self.black_white
        if self.default_style != style: 
            self.output.SetDefaultStyle(style)
            self.default_style = style
        self.output.AppendText(s) 

    def write_warning(self, s):
        self.write(s,self.red_white)

    def write_error(self, s):
        self.write(s,self.red_yellow)

    def flush(self):
        self.output.SetValue("")
    
    def isatty(self):
        return false

    def LogCommand(self, Command, sz_limit = 100):

        import os, popen2, fcntl, select, signal
        
        child = popen2.Popen3(Command, 1) # capture stdout and stderr from command
        child.tochild.close()             # don't need to talk to child
        outfile = child.fromchild 
        outfd = outfile.fileno()
        errfile = child.childerr
        errfd = errfile.fileno()
        outdata = errdata = ''
        outeof = erreof = 0
        outlen = errlen = 0
        while 1:
            ready = select.select([outfd,errfd],[],[]) # wait for input
            if outfd in ready[0]:
                outchunk = outfile.readline()
                if outchunk == '': outeof = 1 
                else : outlen += 1
                outdata += outchunk
                self.write(outchunk)
            if errfd in ready[0]:
                errchunk = errfile.readline()
                if errchunk == '': erreof = 1 
                else : errlen += 1
                errdata += errchunk
                self.write_warning(errchunk)
            if outeof and erreof : break
            if errlen > sz_limit or outlen > sz_limit : 
                os.kill(child.pid, signal.SIGTERM)
                self.write_error("Output size reached limit -- killed\n")
                break
        err = child.wait()
        return (err, outdata, errdata)

[ID_BEREMIZ, ID_BEREMIZMAINSPLITTER, 
 ID_BEREMIZSECONDSPLITTER, ID_BEREMIZLEFTPANEL, 
 ID_BEREMIZPARAMSPANEL, ID_BEREMIZLOGCONSOLE, 
 ID_BEREMIZPLUGINTREE, ID_BEREMIZPLUGINCHILDS, 
 ID_BEREMIZADDBUTTON, ID_BEREMIZDELETEBUTTON,
 ID_BEREMIZPARAMSSTATICBOX, ID_BEREMIZPARAMSENABLE, 
 ID_BEREMIZPARAMSTARGETTYPE, ID_BEREMIZPARAMSIECCHANNEL, 
 ID_BEREMIZPARAMSSTATICTEXT1, ID_BEREMIZPARAMSSTATICTEXT2, 
 ID_BEREMIZPARAMSATTRIBUTESGRID,
] = [wx.NewId() for _init_ctrls in range(17)]

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
        parent.Append(menu=self.EditMenu, title=u'Edit')
        parent.Append(menu=self.RunMenu, title=u'Run')
        parent.Append(menu=self.HelpMenu, title=u'Help')
    
    def _init_utils(self):
        self.menuBar1 = wx.MenuBar()
        self.FileMenu = wx.Menu(title=u'')
        self.EditMenu = wx.Menu(title=u'')
        self.RunMenu = wx.Menu(title=u'')
        self.HelpMenu = wx.Menu(title=u'')
        
        self._init_coll_menuBar1_Menus(self.menuBar1)
        self._init_coll_FileMenu_Items(self.FileMenu)
        self._init_coll_EditMenu_Items(self.EditMenu)
        self._init_coll_RunMenu_Items(self.RunMenu)
        self._init_coll_HelpMenu_Items(self.HelpMenu)
    
    def _init_coll_LeftGridSizer_Items(self, parent):
        parent.AddWindow(self.PluginTree, 0, border=0, flag=wx.GROW)
        parent.AddSizer(self.ButtonGridSizer, 0, border=0, flag=wx.GROW)
        
    def _init_coll_LeftGridSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(0)
    
    def _init_coll_ButtonGridSizer_Items(self, parent):
        parent.AddWindow(self.PluginChilds, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.AddButton, 0, border=0, flag=0)
        parent.AddWindow(self.DeleteButton, 0, border=0, flag=0)
        
    def _init_coll_ButtonGridSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(0)
        
    def _init_sizers(self):
        self.LeftGridSizer = wx.FlexGridSizer(cols=1, hgap=2, rows=2, vgap=2)
        self.ButtonGridSizer = wx.FlexGridSizer(cols=3, hgap=2, rows=1, vgap=2)
        self.ParamsPanelMainSizer = wx.BoxSizer(wx.VERTICAL)
        
        self._init_coll_LeftGridSizer_Growables(self.LeftGridSizer)
        self._init_coll_LeftGridSizer_Items(self.LeftGridSizer)
        self._init_coll_ButtonGridSizer_Growables(self.ButtonGridSizer)
        self._init_coll_ButtonGridSizer_Items(self.ButtonGridSizer)
        
        self.LeftPanel.SetSizer(self.LeftGridSizer)
        self.ParamsPanel.SetSizer(self.ParamsPanelMainSizer)
    
    def _init_ctrls(self, prnt):
        wx.Frame.__init__(self, id=ID_BEREMIZ, name=u'Beremiz',
              parent=prnt, pos=wx.Point(0, 0), size=wx.Size(1000, 600),
              style=wx.DEFAULT_FRAME_STYLE, title=u'Beremiz')
        self._init_utils()
        self.SetClientSize(wx.Size(1000, 600))
        self.SetMenuBar(self.menuBar1)
        
        self.MainSplitter = wx.SplitterWindow(id=ID_BEREMIZMAINSPLITTER,
              name='MainSplitter', parent=self, point=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.SP_3D)
        self.MainSplitter.SetNeedUpdating(True)
        self.MainSplitter.SetMinimumPaneSize(1)
        
        self.LeftPanel = wx.Panel(id=ID_BEREMIZLEFTPANEL, 
              name='LeftPanel', parent=self.MainSplitter, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        
        self.PluginTree = wx.TreeCtrl(id=ID_BEREMIZPLUGINTREE,
              name='PluginTree', parent=self.LeftPanel, pos=wx.Point(0, 0),
              size=wx.Size(-1, -1), style=wx.TR_HAS_BUTTONS|wx.TR_SINGLE|wx.SUNKEN_BORDER)
        self.PluginTree.Bind(wx.EVT_RIGHT_UP, self.OnPluginTreeRightUp)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnPluginTreeItemSelected,
              id=ID_BEREMIZPLUGINTREE)
        
        self.PluginChilds = wx.Choice(id=ID_BEREMIZPLUGINCHILDS,
              name='PluginChilds', parent=self.LeftPanel, pos=wx.Point(0, 0),
              size=wx.Size(-1, -1), style=0)
        
        self.AddButton = wx.Button(id=ID_BEREMIZADDBUTTON, label='Add',
              name='AddBusButton', parent=self.LeftPanel, pos=wx.Point(0, 0),
              size=wx.Size(48, 30), style=0)
        self.AddButton.Bind(wx.EVT_BUTTON, self.OnAddButton,
              id=ID_BEREMIZADDBUTTON)
        
        self.DeleteButton = wx.Button(id=ID_BEREMIZDELETEBUTTON, label='Delete',
              name='DeleteBusButton', parent=self.LeftPanel, pos=wx.Point(0, 0),
              size=wx.Size(64, 30), style=0)
        self.DeleteButton.Bind(wx.EVT_BUTTON, self.OnDeleteButton,
              id=ID_BEREMIZDELETEBUTTON)
        
        self.SecondSplitter = wx.SplitterWindow(id=ID_BEREMIZSECONDSPLITTER,
              name='SecondSplitter', parent=self.MainSplitter, point=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.SP_3D)
        self.SecondSplitter.SetNeedUpdating(True)
        self.SecondSplitter.SetMinimumPaneSize(1)
        
        self.MainSplitter.SplitVertically(self.LeftPanel, self.SecondSplitter,
              300)
        
        self.ParamsPanel = wx.ScrolledWindow(id=ID_BEREMIZPARAMSPANEL, 
              name='ParamsPanel', parent=self.SecondSplitter, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        self.ParamsPanel.SetScrollbars(10, 10, 0, 0, 0, 0)
        
        self.LogConsole = wx.TextCtrl(id=ID_BEREMIZLOGCONSOLE, value='',
              name='LogConsole', parent=self.SecondSplitter, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TE_MULTILINE|wx.TE_RICH2)
        
        self.SecondSplitter.SplitHorizontally(self.ParamsPanel, self.LogConsole,
              -250)
        
        self._init_sizers()

    def __init__(self, parent, projectOpen):
        self._init_ctrls(parent)
        
        self.Log = LogPseudoFile(self.LogConsole)
        
        self.PluginRoot = PluginsRoot(self)
        
        if projectOpen:
            self.PluginRoot.LoadProject(projectOpen, self.Log)
            self.RefreshPluginTree()
        
        self.RefreshPluginParams()
        self.RefreshButtons()
        self.RefreshMainMenu()
        
    def RefreshButtons(self):
        if self.PluginRoot.HasProjectOpened():
            self.PluginChilds.Enable(True)
            self.AddButton.Enable(True)
            self.DeleteButton.Enable(True)
        else:
            self.PluginChilds.Enable(False)
            self.AddButton.Enable(False)
            self.DeleteButton.Enable(False)
        
    def RefreshMainMenu(self):
        if self.menuBar1:
            if self.PluginRoot.HasProjectOpened():
                self.menuBar1.EnableTop(1, True)
                self.menuBar1.EnableTop(2, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS2, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS3, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS5, True)
            else:
                self.menuBar1.EnableTop(1, False)
                self.menuBar1.EnableTop(2, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS2, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS3, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS5, False)

    def RefreshPluginTree(self):
        infos = self.PluginRoot.GetPlugInfos()
        root = self.PluginTree.GetRootItem()
        if not root.IsOk():
            root = self.PluginTree.AddRoot(infos["name"])
        self.GenerateTreeBranch(root, infos, True)
        self.PluginTree.Expand(self.PluginTree.GetRootItem())
        self.RefreshPluginParams()

    def GenerateTreeBranch(self, root, infos, first = False):
        to_delete = []
        self.PluginTree.SetItemText(root, infos["name"])
        self.PluginTree.SetPyData(root, infos["type"])
        item, root_cookie = self.PluginTree.GetFirstChild(root)
        for values in infos["values"]:
            if not item.IsOk():
                item = self.PluginTree.AppendItem(root, "")
                if wx.VERSION < (2, 7, 0):
                    item, root_cookie = self.PluginTree.GetNextChild(root, root_cookie)
            self.GenerateTreeBranch(item, values)
            item, root_cookie = self.PluginTree.GetNextChild(root, root_cookie)
        while item.IsOk():
            to_delete.append(item)
            item, root_cookie = self.PluginTree.GetNextChild(root, root_cookie)
        for item in to_delete:
            self.PluginTree.Delete(item)

    def GetSelectedPlugin(self):
        selected = self.PluginTree.GetSelection()
        if not selected.IsOk():
            return None
        if selected == self.PluginTree.GetRootItem():
            return self.PluginRoot
        else:
            name = self.PluginTree.GetItemText(selected)
            item = self.PluginTree.GetItemParent(selected)
            while item.IsOk() and item != self.PluginTree.GetRootItem():
                name = "%s.%s"%(self.PluginTree.GetItemText(item), name)
                item = self.PluginTree.GetItemParent(item)
            return self.PluginRoot.GetChildByName(name)

    def OnPluginTreeItemSelected(self, event):
        wx.CallAfter(self.RefreshPluginParams)
        event.Skip()
    
    def _GetAddPluginFunction(self, name):
        def OnPluginMenu(event):
            self.AddPlugin(name)
            event.Skip()
        return OnPluginMenu
    
    def OnPluginTreeRightUp(self, event):
        plugin = self.GetSelectedPlugin()
        if plugin:
            main_menu = wx.Menu(title='')
            if len(plugin.PlugChildsTypes) > 0:
                plugin_menu = wx.Menu(title='')
                for name, XSDClass in self.GetSelectedPlugin().PlugChildsTypes:
                    new_id = wx.NewId()
                    plugin_menu.Append(help='', id=new_id, kind=wx.ITEM_NORMAL, text=name)
                    self.Bind(wx.EVT_MENU, self._GetAddPluginFunction(name), id=new_id)
                main_menu.AppendMenu(-1, "Add", plugin_menu, '')
            new_id = wx.NewId()
            main_menu.Append(help='', id=new_id, kind=wx.ITEM_NORMAL, text="Delete")
            self.Bind(wx.EVT_MENU, self.OnDeleteButton, id=new_id)
            rect = self.PluginTree.GetBoundingRect(self.PluginTree.GetSelection())
            self.PluginTree.PopupMenuXY(main_menu, rect.x + rect.width, rect.y)
        event.Skip()
    
    def RefreshPluginParams(self):
        plugin = self.GetSelectedPlugin()
        if not plugin:
            # Refresh ParamsPanel
            self.ParamsPanel.Hide()
            
            # Refresh PluginChilds
            self.PluginChilds.Clear()
            self.PluginChilds.Enable(False)
            self.AddButton.Enable(False)
            self.DeleteButton.Enable(False)
        else:
            # Refresh ParamsPanel
            self.ParamsPanel.Show()
            infos = plugin.GetParamsAttributes()
            self.RefreshSizerElement(self.ParamsPanelMainSizer, infos, None)
            if len(plugin.PluginMethods) > 0:
                boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                self.ParamsPanelMainSizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                for name, method in plugin.PluginMethods:
                    if method:
                        id = wx.NewId()
                        button = wx.Button(id=id, label=name, name=name, parent=self.ParamsPanel, 
                            pos=wx.Point(0, 0), style=wx.BU_EXACTFIT)
                        button.Bind(wx.EVT_BUTTON, self.GetButtonCallBackFunction(plugin, method), id=id)
                        boxsizer.AddWindow(button, 0, border=5, flag=wx.GROW|wx.RIGHT)
            self.ParamsPanelMainSizer.Layout()
            
            # Refresh PluginChilds
            self.PluginChilds.Clear()
            if len(plugin.PlugChildsTypes) > 0:
                self.PluginChilds.Append("")
                for name, XSDClass in plugin.PlugChildsTypes:
                    self.PluginChilds.Append(name)
                self.PluginChilds.Enable(True)
                self.AddButton.Enable(True)
            else:
                self.PluginChilds.Enable(False)
                self.AddButton.Enable(False)
            self.DeleteButton.Enable(True)
    
    def GetButtonCallBackFunction(self, plugin, method):
        def OnButtonClick(event):
            method(plugin, self.Log)
            event.Skip()
        return OnButtonClick
    
    def GetChoiceCallBackFunction(self, choicectrl, path):
        def OnChoiceChanged(event):
            plugin = self.GetSelectedPlugin()
            if plugin:
                plugin.SetParamsAttribute(path, choicectrl.GetStringSelection())
            event.Skip()
        return OnChoiceChanged
    
    def GetChoiceContentCallBackFunction(self, choicectrl, staticboxsizer, path):
        def OnChoiceContentChanged(event):
            plugin = self.GetSelectedPlugin()
            if plugin:
                plugin.SetParamsAttribute(path, choicectrl.GetStringSelection())
                infos = self.PluginRoot.GetParamsAttributes(path)
                staticbox = staticboxsizer.GetStaticBox()
                staticbox.SetLabel("%(name)s - %(value)s"%infos)
                self.ParamsPanel.Freeze()
                self.RefreshSizerElement(staticboxsizer, infos["children"], "%s.%s"%(path, infos["name"]))
                self.ParamsPanelMainSizer.Layout()
                self.ParamsPanel.Thaw()
                self.ParamsPanel.Refresh()
            event.Skip()
        return OnChoiceContentChanged
    
    def GetTextCtrlCallBackFunction(self, textctrl, path):
        def OnTextCtrlChanged(event):
            plugin = self.GetSelectedPlugin()
            if plugin:
                plugin.SetParamsAttribute(path, textctrl.GetValue())
            event.Skip()
        return OnTextCtrlChanged
    
    def GetCheckBoxCallBackFunction(self, textctrl, path):
        def OnCheckBoxChanged(event):
            plugin = self.GetSelectedPlugin()
            if plugin:
                plugin.SetParamsAttribute(path, textctrl.IsChecked())
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
                
    def RefreshSizerElement(self, sizer, elements, path):
        if wx.VERSION >= (2, 7, 0):
            sizer.Clear(True)
        else:
            self.ClearSizer(sizer)
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
                statictext = wx.StaticText(id=-1, label="%s:"%element_infos["name"], 
                    name="%s_label"%element_infos["name"], parent=self.ParamsPanel, 
                    pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)
                boxsizer.AddWindow(statictext, 0, border=0, flag=0)
                id = wx.NewId()
                choicectrl = wx.Choice(id=id, name=element_infos["name"], parent=self.ParamsPanel, 
                    pos=wx.Point(0, 0), size=wx.Size(150, 25), style=0)
                boxsizer.AddWindow(choicectrl, 0, border=0, flag=0)
                choicectrl.Append("")
                if len(element_infos["type"]) > 0 and isinstance(element_infos["type"][0], types.TupleType):
                    for choice, xsdclass in element_infos["type"]:
                        choicectrl.Append(choice)
                    staticbox = wx.StaticBox(id=-1, label="%(name)s - %(value)s"%element_infos, 
                        name='%s_staticbox'%element_infos["name"], parent=self.ParamsPanel,
                        pos=wx.Point(0, 0), size=wx.Size(0, 0), style=0)
                    staticboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW)
                    self.RefreshSizerElement(staticboxsizer, element_infos["children"], element_path)
                    callback = self.GetChoiceContentCallBackFunction(choicectrl, staticboxsizer, element_path)
                else:
                    for choice in element_infos["type"]:
                        choicectrl.Append(choice)
                    callback = self.GetChoiceCallBackFunction(choicectrl, element_path)
                choicectrl.Bind(wx.EVT_CHOICE, callback, id=id)
                if element_infos["value"]:
                    choicectrl.SetStringSelection(element_infos["value"])
            elif isinstance(element_infos["type"], types.DictType):
                boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                if first:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                else:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
                statictext = wx.StaticText(id=-1, label="%s:"%element_infos["name"], 
                    name="%s_label"%element_infos["name"], parent=self.ParamsPanel, 
                    pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)
                boxsizer.AddWindow(statictext, 0, border=0, flag=wx.TOP|wx.LEFT|wx.BOTTOM)
                id = wx.NewId()
                scmin = -(2**31)
                scmax = 2**31-1
                if "min" in element_infos["type"]:
                    scmin = element_infos["type"]["min"]
                if "max" in element_infos["type"]:
                    scmax = element_infos["type"]["max"]
                spinctrl = wx.SpinCtrl(id=id, name=element_infos["name"], parent=self.ParamsPanel, 
                    pos=wx.Point(0, 0), size=wx.Size(150, 25), style=wx.SP_ARROW_KEYS|wx.ALIGN_RIGHT)
                spinctrl.SetRange(scmin,scmax)
                boxsizer.AddWindow(spinctrl, 0, border=0, flag=0)
                spinctrl.Bind(wx.EVT_SPINCTRL, self.GetTextCtrlCallBackFunction(spinctrl, element_path), id=id)
                spinctrl.SetValue(element_infos["value"])
            elif element_infos["type"] == "element":
                staticbox = wx.StaticBox(id=-1, label=element_infos["name"], 
                    name='%s_staticbox'%element_infos["name"], parent=self.ParamsPanel,
                    pos=wx.Point(0, 0), size=wx.Size(0, 0), style=0)
                staticboxsizer = wx.StaticBoxSizer(staticbox, wx.VERTICAL)
                if first:
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW|wx.TOP)
                else:
                    sizer.AddSizer(staticboxsizer, 0, border=0, flag=wx.GROW)
                self.RefreshSizerElement(staticboxsizer, element_infos["children"], element_path)
            else:
                boxsizer = wx.BoxSizer(wx.HORIZONTAL)
                if first:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.ALL)
                else:
                    sizer.AddSizer(boxsizer, 0, border=5, flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.BOTTOM)
                statictext = wx.StaticText(id=-1, label="%s:"%element_infos["name"], 
                    name="%s_label"%element_infos["name"], parent=self.ParamsPanel, 
                    pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)
                boxsizer.AddWindow(statictext, 0, border=0, flag=0)
                id = wx.NewId()
                if element_infos["type"] == "boolean":
                    checkbox = wx.CheckBox(id=id, name=element_infos["name"], parent=self.ParamsPanel, 
                        pos=wx.Point(0, 0), size=wx.Size(17, 25), style=0)
                    boxsizer.AddWindow(checkbox, 0, border=0, flag=0)
                    checkbox.Bind(wx.EVT_CHECKBOX, self.GetCheckBoxCallBackFunction(checkbox, element_path), id=id)
                    checkbox.SetValue(element_infos["value"])
                elif element_infos["type"] in ["unsignedLong", "long","integer"]:
                    if element_infos["type"].startswith("unsigned"):
                        scmin = 0
                    else:
                        scmin = -(2**31)
                    scmax = 2**31-1
                    spinctrl = wx.SpinCtrl(id=id, name=element_infos["name"], parent=self.ParamsPanel, 
                        pos=wx.Point(0, 0), size=wx.Size(150, 25), style=wx.SP_ARROW_KEYS|wx.ALIGN_RIGHT)
                    spinctrl.SetRange(scmin, scmax)
                    boxsizer.AddWindow(spinctrl, 0, border=0, flag=0)
                    spinctrl.Bind(wx.EVT_SPINCTRL, self.GetTextCtrlCallBackFunction(spinctrl, element_path), id=id)
                    spinctrl.SetValue(element_infos["value"])
                else:
                    textctrl = wx.TextCtrl(id=id, name=element_infos["name"], parent=self.ParamsPanel, 
                        pos=wx.Point(0, 0), size=wx.Size(150, 25), style=0)
                    boxsizer.AddWindow(textctrl, 0, border=0, flag=0)
                    textctrl.Bind(wx.EVT_TEXT, self.GetTextCtrlCallBackFunction(textctrl, element_path), id=id)
                    textctrl.SetValue(str(element_infos["value"]))
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
                self.RefreshPluginTree()
                self.RefreshButtons()
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
                    self.RefreshPluginTree()
                    self.RefreshButtons()
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
        self.PLCManager = None
        self.CurrentProjectPath = projectpath
        self.RefreshButtons()
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
    
    def CloseEditor(self, bus_id):
        if self.BusManagers.get(bus_id, None) != None:
            self.BusManagers[bus_id]["Editor"] = None
    
    def AddPlugin(self, PluginType):
        dialog = wx.TextEntryDialog(self, "Please enter a name for plugin:", "Add Plugin", "", wx.OK|wx.CANCEL)
        if dialog.ShowModal() == wx.ID_OK:
            PluginName = dialog.GetValue()
            plugin = self.GetSelectedPlugin()
            plugin.PlugAddChild(PluginName, PluginType)
            self.RefreshPluginTree()
        dialog.Destroy()
    
    def DeletePlugin(self):
        pass

#-------------------------------------------------------------------------------
#                               Exception Handler
#-------------------------------------------------------------------------------

Max_Traceback_List_Size = 20

def Display_Exception_Dialog(e_type,e_value,e_tb):
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
An error happens.

Click on OK for saving an error report.

Please contact LOLITech at:
+33 (0)3 29 52 95 67
bugs_Beremiz@lolitech.fr


Error:
""" +
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
            result = Display_Exception_Dialog(e_type,e_value,e_traceback)
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
                    'date' : time.ctime(),
                    'cwd' : os.getcwd(),
                    }
                if e_traceback:
                    info['traceback'] = ''.join(traceback.format_tb(e_traceback)) + '%s: %s' % (e_type, e_value)
                    last_tb = get_last_traceback(e_traceback)
                    exception_locals = last_tb.tb_frame.f_locals # the locals at the level of the stack trace where the exception actually occurred
                    info['locals'] = format_namespace(exception_locals)
                    if 'self' in exception_locals:
                        info['self'] = format_namespace(exception_locals['self'].__dict__)
                
                output = open(path+os.sep+"bug_report_"+info['date'].replace(':','-').replace(' ','_')+".txt",'w')
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

    frame.Show()
    app.MainLoop()
