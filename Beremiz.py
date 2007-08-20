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

import wx

from time import localtime
from datetime import datetime

import os, re, platform, sys, time, traceback, getopt, commands
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "plcopeneditor"))
sys.path.append(os.path.join(base_folder, "CanFestival-3", "objdictgen"))

iec2cc_path = os.path.join(base_folder, "matiec", "iec2cc")
ieclib_path = os.path.join(base_folder, "matiec", "lib")

from PLCOpenEditor import PLCOpenEditor, ProjectDialog
from TextViewer import TextViewer
from plcopen.structures import IEC_KEYWORDS, AddPlugin
from PLCControler import PLCControler

import plugins

__version__ = "$Revision$"

def create(parent):
    return Beremiz(parent)

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

projectOpen = None
if len(args) > 1:
    usage()
    sys.exit()
elif len(args) == 1:
    projectOpen = args[0]
CWD = sys.path[0]

re_texts = {}
re_texts["letter"] = "[A-Za-z]"
re_texts["digit"] = "[0-9]"
LOCATED_MODEL = re.compile("__LOCATED_VAR\(([A-Z]*),([_A-Za-z0-9]*)\)")


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

    def write(self, s):
        if self.default_style != self.black_white: 
            self.output.SetDefaultStyle(self.black_white)
            self.default_style = self.black_white
        self.output.AppendText(s) 

    def write_warning(self, s):
        if self.default_style != self.red_white: 
            self.output.SetDefaultStyle(self.red_white)
            self.default_style = self.red_white
        self.output.AppendText(s) 

    def write_error(self, s):
        if self.default_style != self.red_yellow: 
            self.output.SetDefaultStyle(self.red_yellow)
            self.default_style = self.red_yellow
        self.output.AppendText(s) 

    def flush(self):
        self.output.SetValue("")
    
    def isatty(self):
        return false

[ID_BEREMIZ, ID_BEREMIZLOGCONSOLE, ID_BEREMIZEDITPLCBUTTON,
 ID_BEREMIZBUILDBUTTON, ID_BEREMIZSIMULATEBUTTON,
 ID_BEREMIZRUNBUTTON, ID_BEREMIZBUSLIST,
 ID_BEREMIZADDBUSBUTTON, ID_BEREMIZDELETEBUSBUTTON,
] = [wx.NewId() for _init_ctrls in range(9)]

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
              kind=wx.ITEM_NORMAL, text=u'Add Bus')
        parent.Append(help='', id=ID_BEREMIZEDITMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Delete Bus')
        self.Bind(wx.EVT_MENU, self.OnEditPLCMenu,
              id=ID_BEREMIZEDITMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnAddBusMenu,
              id=ID_BEREMIZEDITMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnDeleteBusMenu,
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
    
    def _init_coll_MainGridSizer_Items(self, parent):
        parent.AddSizer(self.ControlPanelSizer, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.LogConsole, 0, border=0, flag=wx.GROW)
        
    def _init_coll_MainGridSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_ControlPanelSizer_Items(self, parent):
        parent.AddSizer(self.ControlButtonSizer, 0, border=0, flag=0)
        parent.AddWindow(self.BusList, 0, border=0, flag=wx.GROW)
        parent.AddSizer(self.BusButtonSizer, 0, border=0, flag=0)
        
        
    def _init_coll_ControlPanelSizer_Growables(self, parent):
        parent.AddGrowableCol(1)
        parent.AddGrowableRow(0)
    
    def _init_coll_ControlButtonSizer_Items(self, parent):
        parent.AddWindow(self.EditPLCButton, 0, border=0, flag=0)
        parent.AddWindow(self.BuildButton, 0, border=0, flag=0)
        parent.AddWindow(self.SimulateButton, 0, border=0, flag=0)
        parent.AddWindow(self.RunButton, 0, border=0, flag=0)

    def _init_coll_BusButtonSizer_Items(self, parent):
        parent.AddWindow(self.AddBusButton, 0, border=0, flag=0)
        parent.AddWindow(self.DeleteBusButton, 0, border=0, flag=0)
        
    def _init_sizers(self):
        self.MainGridSizer = wx.FlexGridSizer(cols=1, hgap=2, rows=2, vgap=2)
        self.ControlPanelSizer = wx.FlexGridSizer(cols=3, hgap=2, rows=1, vgap=2)
        self.ControlButtonSizer = wx.GridSizer(cols=2, hgap=2, rows=2, vgap=2)
        self.BusButtonSizer = wx.BoxSizer(wx.VERTICAL)
        
        self._init_coll_MainGridSizer_Growables(self.MainGridSizer)
        self._init_coll_MainGridSizer_Items(self.MainGridSizer)
        self._init_coll_ControlPanelSizer_Growables(self.ControlPanelSizer)
        self._init_coll_ControlPanelSizer_Items(self.ControlPanelSizer)
        self._init_coll_ControlButtonSizer_Items(self.ControlButtonSizer)
        self._init_coll_BusButtonSizer_Items(self.BusButtonSizer)
        
        self.SetSizer(self.MainGridSizer)
    
    def _init_ctrls(self, prnt):
        wx.Frame.__init__(self, id=ID_BEREMIZ, name=u'Beremiz',
              parent=prnt, pos=wx.Point(0, 0), size=wx.Size(600, 300),
              style=wx.DEFAULT_FRAME_STYLE, title=u'Beremiz')
        self._init_utils()
        self.SetClientSize(wx.Size(600, 300))
        self.SetMenuBar(self.menuBar1)
        
        self.LogConsole = wx.TextCtrl(id=ID_BEREMIZLOGCONSOLE, value='',
              name='LogConsole', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TE_MULTILINE|wx.TE_RICH2)
        
        self.EditPLCButton = wx.Button(id=ID_BEREMIZEDITPLCBUTTON, label='Edit\nPLC',
              name='EditPLCButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.EditPLCButton.Bind(wx.EVT_BUTTON, self.OnEditPLCButton,
              id=ID_BEREMIZEDITPLCBUTTON)
        
        self.BuildButton = wx.Button(id=ID_BEREMIZBUILDBUTTON, label='Build',
              name='BuildButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.BuildButton.Bind(wx.EVT_BUTTON, self.OnBuildButton,
              id=ID_BEREMIZBUILDBUTTON)
        
        self.SimulateButton = wx.Button(id=ID_BEREMIZSIMULATEBUTTON, label='Simul',
              name='SimulateButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.EditPLCButton.Bind(wx.EVT_BUTTON, self.OnSimulateButton,
              id=ID_BEREMIZSIMULATEBUTTON)
        
        self.RunButton = wx.Button(id=ID_BEREMIZRUNBUTTON, label='Run',
              name='RunButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.RunButton.Bind(wx.EVT_BUTTON, self.OnRunButton,
              id=ID_BEREMIZRUNBUTTON)
        
        self.BusList = wx.ListBox(choices=[], id=ID_BEREMIZBUSLIST,
              name='BusList', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(-1, -1), style=wx.LB_SINGLE|wx.LB_NEEDED_SB)
        self.BusList.Bind(wx.EVT_LISTBOX_DCLICK, self.OnBusListDClick,
              id=ID_BEREMIZBUSLIST)
        
        self.AddBusButton = wx.Button(id=ID_BEREMIZADDBUSBUTTON, label='Add',
              name='AddBusButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.AddBusButton.Bind(wx.EVT_BUTTON, self.OnAddBusButton,
              id=ID_BEREMIZADDBUSBUTTON)
        
        self.DeleteBusButton = wx.Button(id=ID_BEREMIZDELETEBUSBUTTON, label='Delete',
              name='DeleteBusButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.DeleteBusButton.Bind(wx.EVT_BUTTON, self.OnDeleteBusButton,
              id=ID_BEREMIZDELETEBUSBUTTON)
        
        self._init_sizers()
    
    def __init__(self, parent):
        self._init_ctrls(parent)
        
        for name in plugins.__all__:
            module = getattr(plugins, name)
            if len(module.BlockList) > 0:
                function = module.GetBlockGenerationFunction(self)
                blocklist = module.BlockList
                for blocktype in blocklist["list"]:
                    blocktype["generate"] = function
                AddPlugin(module.BlockList)
        
        self.CurrentProjectPath = ""
        
        self.PLCManager = None
        self.PLCEditor = None
        self.BusManagers = {}
        
        self.Log = LogPseudoFile(self.LogConsole)
        
        if projectOpen:
            self.OpenProject(projectOpen)
            
        self.RefreshButtons()
        self.RefreshMainMenu()
        
    def RefreshButtons(self):
        if self.CurrentProjectPath == "":
            self.LogConsole.Enable(False)
            self.EditPLCButton.Enable(False)
            self.BuildButton.Enable(False)
            self.SimulateButton.Enable(False)
            self.RunButton.Enable(False)
            self.BusList.Enable(False)
            self.AddBusButton.Enable(False)
            self.DeleteBusButton.Enable(False)
        else:
            self.LogConsole.Enable(True)
            self.EditPLCButton.Enable(True)
            self.BuildButton.Enable(True)
            self.SimulateButton.Enable(True)
            self.RunButton.Enable(True)
            self.BusList.Enable(True)
            self.AddBusButton.Enable(True)
            self.DeleteBusButton.Enable(True)

    def RefreshBusList(self):
        selected = self.BusList.GetStringSelection()
        self.BusList.Clear()
        busidlist = self.BusManagers.keys()
        busidlist.sort()
        for id in busidlist:
            bus_infos = self.BusManagers[id]
            self.BusList.Append("0x%2.2X\t%s\t%s"%(id, bus_infos["Type"], bus_infos["Name"]))
        if selected != "":
            self.BusList.SetStringSelection(selected)

    def RefreshMainMenu(self):
        if self.menuBar1:
            if self.CurrentProjectPath == "":
                self.menuBar1.EnableTop(1, False)
                self.menuBar1.EnableTop(2, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS2, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS3, False)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS5, False)
            else:
                self.menuBar1.EnableTop(1, True)
                self.menuBar1.EnableTop(2, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS2, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS3, True)
                self.FileMenu.Enable(ID_BEREMIZFILEMENUITEMS5, True)

    def OnNewProjectMenu(self, event):
        if self.CurrentProjectPath != "":
            defaultpath = self.CurrentProjectPath
        else:
            defaultpath = os.getcwd()
        dialog = wx.DirDialog(self , "Choose a project", defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            dialog.Destroy()
            if os.path.isdir(projectpath) and len(os.listdir(projectpath)) == 0:
                os.mkdir(os.path.join(projectpath, "eds"))
                self.PLCManager = PLCControler()
                plc_file = os.path.join(projectpath, "plc.xml")
                dialog = ProjectDialog(self)
                if dialog.ShowModal() == wx.ID_OK:
                    values = dialog.GetValues()
                    values["creationDateTime"] = datetime(*localtime()[:6])
                    self.PLCManager.CreateNewProject(values.pop("projectName"))
                    self.PLCManager.SetProjectProperties(properties=values)
                    self.PLCManager.SaveXMLFile(plc_file)
                    self.CurrentProjectPath = projectpath
                dialog.Destroy()
                self.RefreshButtons()
                self.RefreshMainMenu()
            else:
                message = wx.MessageDialog(self, "Folder choosen isn't empty. You can't use it for a new project!", "ERROR", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
        event.Skip()
    
    def OpenProject(self, projectpath):
        try:
            if not os.path.isdir(projectpath):
                raise Exception
            self.BusManagers = {}
            configpath = os.path.join(projectpath, ".project")
            if not os.path.isfile(configpath):
                raise Exception
            file = open(configpath, "r")
            lines = [line.strip() for line in file.readlines() if line.strip() != ""]
            if lines[0] != "Beremiz":
                file.close()
                raise Exception
            for bus_id, bus_type, bus_name in [line.split(" ") for line in lines[1:]]:
                id = int(bus_id, 16)
                controller = getattr(plugins, bus_type).controller
                if controller != None:
                    manager = controller()
                    result = manager.LoadProject(projectpath, bus_name)
                    if not result:
                        self.BusManagers[id] = {"Name" : bus_name, "Type" : bus_type, "Manager" : manager, "Editor" : None}
                    else:
                        message = wx.MessageDialog(self, result, "Error", wx.OK|wx.ICON_ERROR)
                        message.ShowModal()
                        message.Destroy()
                else:
                    self.BusManagers[id] = {"Name" : bus_name, "Type" : bus_type, "Manager" : None, "Editor" : None}
            file.close()
            self.PLCManager = PLCControler()
            plc_file = os.path.join(projectpath, "plc.xml")
            if os.path.isfile(plc_file):
                self.PLCManager.OpenXMLFile(plc_file)
                self.CurrentProjectPath = projectpath
            else:
                dialog = ProjectDialog(self)
                if dialog.ShowModal() == wx.ID_OK:
                    values = dialog.GetValues()
                    projectname = values.pop("projectName")
                    values["creationDateTime"] = datetime(*localtime()[:6])
                    self.PLCManager.CreateNewProject(projectname)
                    self.PLCManager.SetProjectProperties(values)
                    self.PLCManager.SaveXMLFile(plc_file)
                    self.CurrentProjectPath = projectpath
                dialog.Destroy()
            self.RefreshBusList()
            self.RefreshButtons()
            self.RefreshMainMenu()
        except Exception, message:
            message = wx.MessageDialog(self, "\"%s\" folder is not a valid Beremiz project\n%s"%(projectpath,message), "Error", wx.OK|wx.ICON_ERROR)
            message.ShowModal()
            message.Destroy()
    
    def OnOpenProjectMenu(self, event):
        if self.CurrentProjectPath != "":
            defaultpath = self.CurrentProjectPath
        else:
            defaultpath = os.getcwd()
        dialog = wx.DirDialog(self , "Choose a project", defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            self.OpenProject(dialog.GetPath())
            dialog.Destroy()
        event.Skip()
    
    def OnCloseProjectMenu(self, event):
        self.PLCManager = None
        self.CurrentProjectPath = projectpath
        self.RefreshButtons()
        self.RefreshMainMenu()
        event.Skip()
    
    def OnSaveProjectMenu(self, event):
        self.PLCManager.SaveXMLFile()
        cpjfilepath = os.path.join(self.CurrentProjectPath, "nodelist.cpj")
        file = open(cpjfilepath, "w")
        file.write("")
        file.close()
        configpath = os.path.join(self.CurrentProjectPath, ".project")
        file = open(configpath, "w")
        file.write("Beremiz\n")
        busidlist = self.BusManagers.keys()
        busidlist.sort()
        for id in busidlist:
            bus_infos = self.BusManagers[id]
            file.write("0x%2.2X %s %s\n"%(id, bus_infos["Type"], bus_infos["Name"]))
            bus_infos["Manager"].SaveProject(bus_infos["Name"])
        file.close()
        event.Skip()
    
    def OnPropertiesMenu(self, event):
        event.Skip()
    
    def OnQuitMenu(self, event):
        self.Close()
        event.Skip()
    
    def OnEditPLCMenu(self, event):
        self.EditPLC()
        event.Skip()
    
    def OnAddBusMenu(self, event):
        self.AddBus()
        event.Skip()
    
    def OnDeleteBusMenu(self, event):
        self.DeleteBus()
        event.Skip()

    def OnBuildMenu(self, event):
        self.BuildAutom()
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

    def OnEditPLCButton(self, event):
        self.EditPLC()
        event.Skip()
    
    def OnBuildButton(self, event):
        self.BuildAutom()
        event.Skip()
    
    def OnSimulateButton(self, event):
        event.Skip()
        
    def OnRunButton(self, event):
        event.Skip()
    
    def OnAddBusButton(self, event):
        self.AddBus()
        event.Skip()
    
    def OnDeleteBusButton(self, event):
        self.DeleteBus()
        event.Skip()
    
    def OnBusListDClick(self, event):
        selected = event.GetSelection()
        busidlist = self.BusManagers.keys()
        busidlist.sort()
        bus_infos = self.BusManagers[busidlist[selected]]
        view = getattr(plugins, bus_infos["Type"]).view
        if view != None:
            if bus_infos["Editor"] == None:
                editor = view(self, bus_infos["Manager"])
                editor.SetBusId(busidlist[selected])
                editor.Show()
                bus_infos["Editor"] = editor
        event.Skip()
    
    def CloseEditor(self, bus_id):
        if self.BusManagers.get(bus_id, None) != None:
            self.BusManagers[bus_id]["Editor"] = None
    
    def AddBus(self):
        dialog = AddBusDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.GetValues()
            if values["busID"].startswith("0x"):
                bus_id = int(values["busID"], 16)
            else:
                bus_id = int(values["busID"])
            if self.BusManagers.get(bus_id, None) == None:
                controller = getattr(plugins, values["busType"]).controller
                if controller != None:
                    manager = controller()
                    result = manager.LoadProject(self.CurrentProjectPath, values["busName"])
                    if not result:
                        self.BusManagers[bus_id] = {"Name" : values["busName"], "Type" : values["busType"], "Manager" : manager, "Editor" : None}
                    else:
                        message = wx.MessageDialog(self, result, "Error", wx.OK|wx.ICON_ERROR)
                        message.ShowModal()
                        message.Destroy()
                else:
                    self.BusManagers[bus_id] = {"Name" : values["busName"], "Type" : values["busType"], "Manager" : None, "Editor" : None}
            else:
                message = wx.MessageDialog(self, "The bus ID \"0x%2.2X\" is already used!"%bus_id, "Error", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
            self.RefreshBusList()
        dialog.Destroy()
    
    def DeleteBus(self):
        busidlist = self.BusManagers.keys()
        busidlist.sort()
        list = ["0x%2.2X\t%s\t%s"%(id, self.BusManagers[id]["Type"], self.BusManagers[id]["Name"]) for id in busidlist]
        dialog = wx.SingleChoiceDialog(self, "Select Bus to delete:", "Bus Delete", list, wx.OK|wx.CANCEL)
        if dialog.ShowModal() == wx.ID_OK:
            selected = dialog.GetSelection()
            editor = self.BusManagers[busidlist[selected]]["Editor"]
            if editor:
                editor.Close()
            self.BusManagers.pop(busidlist[selected])
            self.RefreshBusList()
        dialog.Destroy()
    
    def EditPLC(self):
        if not self.PLCEditor:
            self.PLCEditor = PLCOpenEditor(self, self.PLCManager)
            self.PLCEditor.RefreshProjectTree()
            self.PLCEditor.RefreshFileMenu()
            self.PLCEditor.RefreshEditMenu()
            self.PLCEditor.RefreshToolBar()
            self.PLCEditor.Show()

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
                outdata += outchunk
                outlen += 1
                self.Log.write(outchunk)
            if errfd in ready[0]:
                errchunk = errfile.readline()
                if errchunk == '': erreof = 1
                errdata += errchunk
                errlen += 1
                self.Log.write_warning(errchunk)
            if outeof and erreof : break
            if errlen > sz_limit or outlen > sz_limit : 
                os.kill(child.pid, signal.SIGTERM)
                self.Log.write_error("Output size reached limit -- killed\n")
                break
        err = child.wait()
        return (err, outdata, errdata)

    def BuildAutom(self):
        if self.PLCManager:
            self.TargetDir = os.path.join(self.CurrentProjectPath, "build")
            if not os.path.exists(self.TargetDir):
                os.mkdir(self.TargetDir)
            self.Log.flush()
            #sys.stdout = self.Log
            try:
                self.Log.write("Generating IEC-61131 code...\n")
                plc_file = os.path.join(self.TargetDir, "plc.st")
                result = self.PLCManager.GenerateProgram(plc_file)
                if not result:
                    raise Exception, "Error : ST/IL/SFC code generator returned %d"%result
                self.Log.write("Compiling ST Program in to C Program...\n")
                status, result, err_result = self.LogCommand("%s %s -I %s %s"%(iec2cc_path, plc_file, ieclib_path, self.TargetDir))
                if status:
                    new_dialog = wx.Frame(None)
                    ST_viewer = TextViewer(new_dialog, None, None)
                    #ST_viewer.Enable(False)
                    ST_viewer.SetKeywords(IEC_KEYWORDS)
                    ST_viewer.SetText(file(plc_file).read())
                    new_dialog.Show()
                    raise Exception, "Error : IEC to C compiler returned %d"%status
                self.Log.write("Extracting Located Variables...\n")
                location_file = open(os.path.join(self.TargetDir,"LOCATED_VARIABLES.h"))
                locations = []
                lines = [line.strip() for line in location_file.readlines()]
                for line in lines:
                    result = LOCATED_MODEL.match(line)
                    if result:
                        locations.append(result.groups())
                self.Log.write("Generating Network Configurations...\n")
                for bus_id, bus_infos in self.BusManagers.items():
                    if bus_infos["Manager"]:
                        filepath = "%s.c"%os.path.join(self.TargetDir, gen_cfile.FormatName(bus_infos["Name"]))
                        result = bus_infos["Manager"].GenerateBus(filepath, bus_id, locations)
                        if result:
                            raise Exception, "Bus with id \"0x%2.2X\" can't be generated!"%bus_id
                self.Log.write("Generating Makefiles...\n")
                
                self.Log.write("Compiling Project...\n")
                
                self.Log.write("\nBuild Project completed\n")
            except Exception, message:
                self.Log.write_error("\nBuild Failed\n")
                self.Log.write(str(message))
                pass
            #sys.stdout = sys.__stdout__
                
#-------------------------------------------------------------------------------
#                             Add Bus Dialog
#-------------------------------------------------------------------------------

[ID_ADDBUSDIALOG, ID_ADDBUSDIALOGBUSID, 
 ID_ADDBUSDIALOGBUSNAME, ID_ADDBUSDIALOGBUSTYPE, 
 ID_ADDBUSDIALOGSTATICTEXT1, ID_ADDBUSDIALOGSTATICTEXT2, 
 ID_ADDBUSDIALOGSTATICTEXT3,
] = [wx.NewId() for _init_ctrls in range(7)]

class AddBusDialog(wx.Dialog):
    def _init_coll_flexGridSizer1_Items(self, parent):
        parent.AddSizer(self.MainSizer, 0, border=20, flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        parent.AddSizer(self.ButtonSizer, 0, border=20, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
    def _init_coll_flexGridSizer1_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(0)
    
    def _init_coll_MainSizer_Items(self, parent):
        parent.AddWindow(self.staticText1, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.BusId, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.staticText2, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.BusType, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.staticText3, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.BusName, 0, border=0, flag=wx.GROW)
        
    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(1)
        
    def _init_sizers(self):
        self.flexGridSizer1 = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        self.MainSizer = wx.FlexGridSizer(cols=2, hgap=0, rows=3, vgap=15)

        self._init_coll_flexGridSizer1_Items(self.flexGridSizer1)
        self._init_coll_flexGridSizer1_Growables(self.flexGridSizer1)
        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_MainSizer_Growables(self.MainSizer)

        self.SetSizer(self.flexGridSizer1)

    def _init_ctrls(self, prnt):
        wx.Dialog.__init__(self, id=ID_ADDBUSDIALOG,
              name='PouDialog', parent=prnt, pos=wx.Point(376, 183),
              size=wx.Size(300, 200), style=wx.DEFAULT_DIALOG_STYLE,
              title='Create a new POU')
        self.SetClientSize(wx.Size(300, 200))

        self.staticText1 = wx.StaticText(id=ID_ADDBUSDIALOGSTATICTEXT1,
              label='Bus ID:', name='staticText1', parent=self,
              pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)

        self.BusId = wx.TextCtrl(id=ID_ADDBUSDIALOGBUSID,
              name='BusId', parent=self, pos=wx.Point(0, 0), 
              size=wx.Size(0, 24), style=0)

        self.staticText2 = wx.StaticText(id=ID_ADDBUSDIALOGSTATICTEXT2,
              label='Bus Type:', name='staticText2', parent=self,
              pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)

        self.BusType = wx.Choice(id=ID_ADDBUSDIALOGBUSTYPE,
              name='BusType', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=0)
        
        self.staticText3 = wx.StaticText(id=ID_ADDBUSDIALOGSTATICTEXT3,
              label='Bus Name:', name='staticText3', parent=self,
              pos=wx.Point(0, 0), size=wx.Size(100, 17), style=0)

        self.BusName = wx.TextCtrl(id=ID_ADDBUSDIALOGBUSNAME,
              name='BusName', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=0)
        
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.ButtonSizer.GetAffirmativeButton().GetId())
        
        self._init_sizers()

    def __init__(self, parent):
        self._init_ctrls(parent)
        
        for option in [""] + plugins.__all__:
            self.BusType.Append(option)
    
    def OnOK(self, event):
        error = []
        bus_id = self.BusId.GetValue()
        if bus_id == "":
            error.append("Bus ID")
        if self.BusType.GetStringSelection() == "":
            error.append("Bus Type")
        if self.BusName.GetValue() == "":
            error.append("Bus Name")
        if len(error) > 0:
            text = ""
            for i, item in enumerate(error):
                if i == 0:
                    text += item
                elif i == len(error) - 1:
                    text += " and %s"%item
                else:
                    text += ", %s"%item 
            message = wxMessageDialog(self, "Form isn't complete. %s must be filled!"%text, "Error", wxOK|wxICON_ERROR)
            message.ShowModal()
            message.Destroy()
        elif bus_id.startswith("0x"):
            try:
                bus_id = int(bus_id, 16)
                self.EndModal(wx.ID_OK)
            except:
                message = wxMessageDialog(self, "Bus ID must be a decimal or hexadecimal number!", "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        elif not bus_id.startswith("-"):
            try:
                bus_id = int(bus_id)
                self.EndModal(wx.ID_OK)
            except:
                message = wxMessageDialog(self, "Bus ID must be a decimal or hexadecimal number!", "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        else:
            message = wxMessageDialog(self, "Bus Id must be greater than 0!", "Error", wxOK|wxICON_ERROR)
            message.ShowModal()
            message.Destroy()

    def SetValues(self, values):
        for item, value in values.items():
            if item == "busID":
                self.BusID.SetValue(value)
            elif item == "busType":
                self.BusType.SetStringSelection(value)
            elif item == "busName":
                self.BusName.SetValue(value)
                
    def GetValues(self):
        values = {}
        values["busID"] = self.BusId.GetValue()
        values["busType"] = self.BusType.GetStringSelection()
        values["busName"] = self.BusName.GetValue()
        return values

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
    app = wx.PySimpleApp()
    wx.InitAllImageHandlers()
    
    # Install a exception handle for bug reports
    AddExceptHook(os.getcwd(),__version__)
    
    frame = Beremiz(None)

    frame.Show()
    app.MainLoop()
