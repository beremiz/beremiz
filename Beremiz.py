#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C): Edouard TISSERANT and Laurent BESSARD
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
#Lesser General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from wxPython.wx import *
import wx
from time import localtime
from datetime import datetime

import os, re, platform, sys, time, traceback, getopt, commands
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "plcopeneditor"))
sys.path.append(os.path.join(base_folder, "CanFestival-3", "objdictgen"))

from PLCOpenEditor import PLCOpenEditor, ProjectDialog
from PLCControler import PLCControler

from networkedit import networkedit
from nodelist import NodeList
from nodemanager import NodeManager
import config_utils, gen_cfile

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
        self.output = output

    def writelines(self, l):
        map(self.write, l)

    def write(self, s):
        self.output.SetValue(self.output.GetValue() + s) 

    def flush(self):
        self.output.SetValue("")
    
    def isatty(self):
        return false

[wxID_BEREMIZ, wxID_BEREMIZLOGCONSOLE, wxID_BEREMIZEDITPLCBUTTON,
 wxID_BEREMIZBUILDBUTTON, wxID_BEREMIZSIMULATEBUTTON,
 wxID_BEREMIZRUNBUTTON, wxID_BEREMIZBUSLIST,
 wxID_BEREMIZADDBUSBUTTON, wxID_BEREMIZDELETEBUSBUTTON,
] = [wx.NewId() for _init_ctrls in range(9)]

[wxID_BEREMIZFILEMENUITEMS0, wxID_BEREMIZFILEMENUITEMS1, 
 wxID_BEREMIZFILEMENUITEMS2, wxID_BEREMIZFILEMENUITEMS3, 
 wxID_BEREMIZFILEMENUITEMS5, wxID_BEREMIZFILEMENUITEMS7, 
] = [wx.NewId() for _init_coll_FileMenu_Items in range(6)]

[wxID_BEREMIZEDITMENUITEMS0, wxID_BEREMIZEDITMENUITEMS2, 
 wxID_BEREMIZEDITMENUITEMS3, 
] = [wx.NewId() for _init_coll_EditMenu_Items in range(3)]

[wxID_BEREMIZRUNMENUITEMS0, wxID_BEREMIZRUNMENUITEMS2, 
 wxID_BEREMIZRUNMENUITEMS3, wxID_BEREMIZRUNMENUITEMS5, 
] = [wx.NewId() for _init_coll_EditMenu_Items in range(4)]

[wxID_BEREMIZHELPMENUITEMS0, wxID_BEREMIZHELPMENUITEMS1, 
] = [wx.NewId() for _init_coll_HelpMenu_Items in range(2)]

class Beremiz(wx.Frame):
    
    def _init_coll_FileMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_BEREMIZFILEMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'New\tCTRL+N')
        parent.Append(help='', id=wxID_BEREMIZFILEMENUITEMS1,
              kind=wx.ITEM_NORMAL, text=u'Open\tCTRL+O')
        parent.Append(help='', id=wxID_BEREMIZFILEMENUITEMS2,
              kind=wx.ITEM_NORMAL, text=u'Save\tCTRL+S')
        parent.Append(help='', id=wxID_BEREMIZFILEMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Close Project')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_BEREMIZFILEMENUITEMS5,
              kind=wx.ITEM_NORMAL, text=u'Properties')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_BEREMIZFILEMENUITEMS7,
              kind=wx.ITEM_NORMAL, text=u'Quit\tCTRL+Q')
        self.Bind(wx.EVT_MENU, self.OnNewProjectMenu,
              id=wxID_BEREMIZFILEMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnOpenProjectMenu,
              id=wxID_BEREMIZFILEMENUITEMS1)
        self.Bind(wx.EVT_MENU, self.OnSaveProjectMenu,
              id=wxID_BEREMIZFILEMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnCloseProjectMenu,
              id=wxID_BEREMIZFILEMENUITEMS3)
        self.Bind(wx.EVT_MENU, self.OnPropertiesMenu,
              id=wxID_BEREMIZFILEMENUITEMS5)
        self.Bind(wx.EVT_MENU, self.OnQuitMenu,
              id=wxID_BEREMIZFILEMENUITEMS7)
        
    def _init_coll_EditMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_BEREMIZEDITMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'Edit PLC\tCTRL+R')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_BEREMIZEDITMENUITEMS2,
              kind=wx.ITEM_NORMAL, text=u'Add Bus')
        parent.Append(help='', id=wxID_BEREMIZEDITMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Delete Bus')
        self.Bind(wx.EVT_MENU, self.OnEditPLCMenu,
              id=wxID_BEREMIZEDITMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnAddBusMenu,
              id=wxID_BEREMIZEDITMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnDeleteBusMenu,
              id=wxID_BEREMIZEDITMENUITEMS3)
    
    def _init_coll_RunMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_BEREMIZRUNMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'Build\tCTRL+R')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_BEREMIZRUNMENUITEMS2,
              kind=wx.ITEM_NORMAL, text=u'Simulate')
        parent.Append(help='', id=wxID_BEREMIZRUNMENUITEMS3,
              kind=wx.ITEM_NORMAL, text=u'Run')
        parent.AppendSeparator()
        parent.Append(help='', id=wxID_BEREMIZRUNMENUITEMS5,
              kind=wx.ITEM_NORMAL, text=u'Save Log')
        self.Bind(wx.EVT_MENU, self.OnBuildMenu,
              id=wxID_BEREMIZRUNMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnSimulateMenu,
              id=wxID_BEREMIZRUNMENUITEMS2)
        self.Bind(wx.EVT_MENU, self.OnRunMenu,
              id=wxID_BEREMIZRUNMENUITEMS3)
        self.Bind(wx.EVT_MENU, self.OnSaveLogMenu,
              id=wxID_BEREMIZRUNMENUITEMS5)
    
    def _init_coll_HelpMenu_Items(self, parent):
        # generated method, don't edit

        parent.Append(help='', id=wxID_BEREMIZHELPMENUITEMS0,
              kind=wx.ITEM_NORMAL, text=u'Beremiz\tF1')
        parent.Append(help='', id=wxID_BEREMIZHELPMENUITEMS1,
              kind=wx.ITEM_NORMAL, text=u'About')
        self.Bind(wx.EVT_MENU, self.OnBeremizMenu,
              id=wxID_BEREMIZHELPMENUITEMS0)
        self.Bind(wx.EVT_MENU, self.OnAboutMenu,
              id=wxID_BEREMIZHELPMENUITEMS1)
    
    def _init_coll_menuBar1_Menus(self, parent):
        # generated method, don't edit

        parent.Append(menu=self.FileMenu, title=u'File')
        parent.Append(menu=self.EditMenu, title=u'Edit')
        parent.Append(menu=self.RunMenu, title=u'Run')
        parent.Append(menu=self.HelpMenu, title=u'Help')
    
    def _init_utils(self):
        # generated method, don't edit
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
        # generated method, don't edit

        parent.AddSizer(self.ControlPanelSizer, 0, border=0, flag=wxGROW)
        parent.AddWindow(self.LogConsole, 0, border=0, flag=wxGROW)
        
    def _init_coll_MainGridSizer_Growables(self, parent):
        # generated method, don't edit

        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_ControlPanelSizer_Items(self, parent):
        # generated method, don't edit
        
        parent.AddSizer(self.ControlButtonSizer, 0, border=0, flag=0)
        parent.AddWindow(self.BusList, 0, border=0, flag=wxGROW)
        parent.AddSizer(self.BusButtonSizer, 0, border=0, flag=0)
        
        
    def _init_coll_ControlPanelSizer_Growables(self, parent):
        # generated method, don't edit

        parent.AddGrowableCol(1)
        parent.AddGrowableRow(0)
    
    def _init_coll_ControlButtonSizer_Items(self, parent):
        # generated method, don't edit

        parent.AddWindow(self.EditPLCButton, 0, border=0, flag=0)
        parent.AddWindow(self.BuildButton, 0, border=0, flag=0)
        parent.AddWindow(self.SimulateButton, 0, border=0, flag=0)
        parent.AddWindow(self.RunButton, 0, border=0, flag=0)

    def _init_coll_BusButtonSizer_Items(self, parent):
        # generated method, don't edit

        parent.AddWindow(self.AddBusButton, 0, border=0, flag=0)
        parent.AddWindow(self.DeleteBusButton, 0, border=0, flag=0)
        
    def _init_sizers(self):
        # generated method, don't edit
        self.MainGridSizer = wx.FlexGridSizer(cols=1, hgap=2, rows=2, vgap=2)
        
        self.ControlPanelSizer = wx.FlexGridSizer(cols=3, hgap=2, rows=1, vgap=2)
        
        self.ControlButtonSizer = wx.GridSizer(cols=2, hgap=2, rows=2, vgap=2)
        
        self.BusButtonSizer = wx.BoxSizer(wxVERTICAL)
        
        self._init_coll_MainGridSizer_Growables(self.MainGridSizer)
        self._init_coll_MainGridSizer_Items(self.MainGridSizer)
        self._init_coll_ControlPanelSizer_Growables(self.ControlPanelSizer)
        self._init_coll_ControlPanelSizer_Items(self.ControlPanelSizer)
        self._init_coll_ControlButtonSizer_Items(self.ControlButtonSizer)
        self._init_coll_BusButtonSizer_Items(self.BusButtonSizer)
        
        self.SetSizer(self.MainGridSizer)
    
    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Frame.__init__(self, id=wxID_BEREMIZ, name=u'Beremiz',
              parent=prnt, pos=wx.Point(0, 0), size=wx.Size(600, 300),
              style=wx.DEFAULT_FRAME_STYLE, title=u'Beremiz')
        self._init_utils()
        self.SetClientSize(wx.Size(600, 300))
        self.SetMenuBar(self.menuBar1)
        
        self.LogConsole = wx.TextCtrl(id=wxID_BEREMIZLOGCONSOLE, value='',
              name='LogConsole', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wxTE_MULTILINE)
        
        self.EditPLCButton = wx.Button(id=wxID_BEREMIZEDITPLCBUTTON, label='Edit\nPLC',
              name='EditPLCButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.EditPLCButton.Bind(wx.EVT_BUTTON, self.OnEditPLCButton,
              id=wxID_BEREMIZEDITPLCBUTTON)
        
        self.BuildButton = wx.Button(id=wxID_BEREMIZBUILDBUTTON, label='Build',
              name='BuildButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.BuildButton.Bind(wx.EVT_BUTTON, self.OnBuildButton,
              id=wxID_BEREMIZBUILDBUTTON)
        
        self.SimulateButton = wx.Button(id=wxID_BEREMIZSIMULATEBUTTON, label='Simul',
              name='SimulateButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.EditPLCButton.Bind(wx.EVT_BUTTON, self.OnSimulateButton,
              id=wxID_BEREMIZSIMULATEBUTTON)
        
        self.RunButton = wx.Button(id=wxID_BEREMIZRUNBUTTON, label='Run',
              name='RunButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.RunButton.Bind(wx.EVT_BUTTON, self.OnRunButton,
              id=wxID_BEREMIZRUNBUTTON)
        
        self.BusList = wx.ListBox(choices=[], id=wxID_BEREMIZBUSLIST,
              name='BusList', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(-1, -1), style=wxLB_SINGLE|wxLB_NEEDED_SB)
        self.BusList.Bind(wx.EVT_LISTBOX_DCLICK, self.OnBusListDClick,
              id=wxID_BEREMIZBUSLIST)
        
        self.AddBusButton = wx.Button(id=wxID_BEREMIZADDBUSBUTTON, label='Add',
              name='AddBusButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.AddBusButton.Bind(wx.EVT_BUTTON, self.OnAddBusButton,
              id=wxID_BEREMIZADDBUSBUTTON)
        
        self.DeleteBusButton = wx.Button(id=wxID_BEREMIZDELETEBUSBUTTON, label='Delete',
              name='DeleteBusButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(48, 48), style=0)
        self.DeleteBusButton.Bind(wx.EVT_BUTTON, self.OnDeleteBusButton,
              id=wxID_BEREMIZDELETEBUSBUTTON)
        
        self._init_sizers()
    
    def __init__(self, parent):
        self._init_ctrls(parent)
        
        self.CurrentProjectPath = ""
        
        self.PLCManager = None
        self.PLCEditor = None
        self.BusManagers = {}
        
        self.Log = LogPseudoFile(self.LogConsole)
        
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
                self.FileMenu.Enable(wxID_BEREMIZFILEMENUITEMS2, False)
                self.FileMenu.Enable(wxID_BEREMIZFILEMENUITEMS3, False)
                self.FileMenu.Enable(wxID_BEREMIZFILEMENUITEMS5, False)
            else:
                self.menuBar1.EnableTop(1, True)
                self.menuBar1.EnableTop(2, True)
                self.FileMenu.Enable(wxID_BEREMIZFILEMENUITEMS2, True)
                self.FileMenu.Enable(wxID_BEREMIZFILEMENUITEMS3, True)
                self.FileMenu.Enable(wxID_BEREMIZFILEMENUITEMS5, True)

    def OnNewProjectMenu(self, event):
        if self.CurrentProjectPath != "":
            defaultpath = self.CurrentProjectPath
        else:
            defaultpath = os.getcwd()
        dialog = wxDirDialog(self , "Choose a project", defaultpath, wxDD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wxID_OK:
            projectpath = dialog.GetPath()
            dialog.Destroy()
            if os.path.isdir(projectpath) and len(os.listdir(projectpath)) == 0:
                os.mkdir(os.path.join(projectpath, "eds"))
                self.PLCManager = PLCControler()
                plc_file = os.path.join(projectpath, "plc.xml")
                dialog = ProjectDialog(self)
                if dialog.ShowModal() == wxID_OK:
                    values = dialog.GetValues()
                    projectname = values.pop("projectName")
                    values["creationDateTime"] = datetime(*localtime()[:6])
                    self.PLCManager.CreateNewProject(projectname)
                    self.PLCManager.SetProjectProperties(values)
                    self.PLCManager.SaveXMLFile(plc_file)
                    self.CurrentProjectPath = projectpath
                dialog.Destroy()
                self.RefreshButtons()
                self.RefreshMainMenu()
            else:
                message = wxMessageDialog(self, "Folder choosen isn't empty. You can't use it for a new project!", "ERROR", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        event.Skip()
    
    def OnOpenProjectMenu(self, event):
        if self.CurrentProjectPath != "":
            defaultpath = self.CurrentProjectPath
        else:
            defaultpath = os.getcwd()
        dialog = wxDirDialog(self , "Choose a project", defaultpath, wxDD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wxID_OK:
            projectpath = dialog.GetPath()
            dialog.Destroy()
            if os.path.isdir(projectpath):
                self.BusManagers = {}
                configpath = os.path.join(projectpath, ".project")
                if os.path.isfile(configpath):
                    file = open(configpath, "r")
                    for bus_id, bus_type, bus_name in [line.strip().split(" ") for line in file.readlines() if line.strip() != ""]:
                        if bus_type == "CanFestival":
                            id = int(bus_id, 16)
                            manager = NodeManager(os.path.join(base_folder, "CanFestival-3", "objdictgen"))
                            nodelist = NodeList(manager)
                            result = nodelist.LoadProject(projectpath, bus_name)
                            if not result:
                                self.BusManagers[id] = {"Name" : bus_name, "Type" : bus_type, "NodeList" : nodelist, "Editor" : None}
                            else:
                                message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                                message.ShowModal()
                                message.Destroy()
                        else:
                            self.BusManagers[id] = {"Name" : bus_name, "Type" : bus_type}
                    file.close()
                self.PLCManager = PLCControler()
                plc_file = os.path.join(projectpath, "plc.xml")
                if os.path.isfile(plc_file):
                    self.PLCManager.OpenXMLFile(plc_file)
                    self.CurrentProjectPath = projectpath
                else:
                    dialog = ProjectDialog(self)
                    if dialog.ShowModal() == wxID_OK:
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
        busidlist = self.BusManagers.keys()
        busidlist.sort()
        for id in busidlist:
            bus_infos = self.BusManagers[id]
            file.write("0x%2.2X %s %s\n"%(id, bus_infos["Type"], bus_infos["Name"]))
            bus_infos["NodeList"].SaveProject(bus_infos["Name"])
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
        if bus_infos["Type"] == "CanFestival":
            if bus_infos["Editor"] == None:
                netedit = networkedit(self, bus_infos["NodeList"])
                netedit.SetBusId(busidlist[selected])
                netedit.Show()
                bus_infos["Editor"] = netedit
        event.Skip()
    
    def CloseEditor(self, bus_id):
        if self.BusManagers.get(bus_id, None) != None:
            self.BusManagers[bus_id]["Editor"] = None
    
    def AddBus(self):
        dialog = AddBusDialog(self)
        if dialog.ShowModal() == wxID_OK:
            values = dialog.GetValues()
            if values["busID"].startswith("0x"):
                bus_id = int(values["busID"], 16)
            else:
                bus_id = int(values["busID"])
            if self.BusManagers.get(bus_id, None) == None:
                if values["busType"] == "CanFestival":
                    manager = NodeManager(os.path.join(base_folder, "CanFestival-3", "objdictgen"))
                    nodelist = NodeList(manager)
                    result = nodelist.LoadProject(self.CurrentProjectPath, values["busName"])
                    if not result:
                        self.BusManagers[bus_id] = {"Name" : values["busName"], "Type" : values["busType"], "NodeList" : nodelist, "Editor" : None}
                    else:
                        message = wxMessageDialog(self, result, "Error", wxOK|wxICON_ERROR)
                        message.ShowModal()
                        message.Destroy()
                else:
                    self.BusManagers[bus_id] = {"Name" : values["busName"], "Type" : values["busType"]}
            else:
                message = wxMessageDialog(self, "The bus ID \"0x%2.2X\" is already used!"%bus_id, "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
            self.RefreshBusList()
        dialog.Destroy()
    
    def DeleteBus(self):
        busidlist = self.BusManagers.keys()
        busidlist.sort()
        list = ["0x%2.2X\t%s\t%s"%(id, self.BusManagers[id]["Type"], self.BusManagers[id]["Name"]) for id in busidlist]
        dialog = wxSingleChoiceDialog(self, "Select Bus to delete:", "Bus Delete", list, wxOK|wxCANCEL)
        if dialog.ShowModal() == wxID_OK:
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

    def BuildAutom(self):
        if self.PLCManager:
            self.TargetDir = os.path.join(self.CurrentProjectPath, "build")
            if not os.path.exists(self.TargetDir):
                os.mkdir(self.TargetDir)
            self.Log.flush()
            sys.stdout = self.Log
            try:
                print "Building ST Program..."
                plc_file = os.path.join(self.TargetDir, "plc.st")
                result = self.PLCManager.GenerateProgram(plc_file)
                if not result:
                    raise Exception
                print "Compiling ST Program in to C Program..."
                status, result = commands.getstatusoutput("../matiec/iec2cc %s -I ../matiec/lib %s"%(plc_file, self.TargetDir))
                if status:
                    print result
                    raise Exception
                print "Extracting Located Variables..."
                location_file = open(os.path.join(self.TargetDir,"LOCATED_VARIABLES.h"))
                locations = []
                lines = [line.strip() for line in location_file.readlines()]
                for line in lines:
                    result = LOCATED_MODEL.match(line)
                    if result:
                        locations.append(result.groups())
                print "Generating Network Configurations..."
                for bus_id, bus_infos in self.BusManagers.items():
                    if bus_infos["Type"] == "CanFestival":
                        master = config_utils.GenerateConciseDCF(locations, bus_id, bus_infos["NodeList"])
                        result = gen_cfile.GenerateFile("%s.c"%os.path.join(self.TargetDir, gen_cfile.FormatName(bus_infos["Name"])), master)
                        if result:
                            raise Exception
                print "Generating Makefiles..."
                
                print "Compiling Project..."
                
                print "\nBuild Project completed"
            except Exception, message:
                pass
            sys.stdout = sys.__stdout__
                
#-------------------------------------------------------------------------------
#                             Add Bus Dialog
#-------------------------------------------------------------------------------

[wxID_ADDBUSDIALOG, wxID_ADDBUSDIALOGMAINPANEL, 
 wxID_ADDBUSDIALOGBUSID, wxID_ADDBUSDIALOGBUSNAME, 
 wxID_ADDBUSDIALOGBUSTYPE, wxID_ADDBUSDIALOGSTATICTEXT1,
 wxID_ADDBUSDIALOGSTATICTEXT2, wxID_ADDBUSDIALOGSTATICTEXT3,
] = [wx.NewId() for _init_ctrls in range(8)]

class AddBusDialog(wx.Dialog):
    def _init_coll_flexGridSizer1_Items(self, parent):
        # generated method, don't edit

        parent.AddWindow(self.MainPanel, 0, border=0, flag=0)

    def _init_sizers(self):
        # generated method, don't edit
        self.flexGridSizer1 = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)

        self._init_coll_flexGridSizer1_Items(self.flexGridSizer1)

        self.SetSizer(self.flexGridSizer1)

    def _init_ctrls(self, prnt):
        # generated method, don't edit
        wx.Dialog.__init__(self, id=wxID_ADDBUSDIALOG,
              name='PouDialog', parent=prnt, pos=wx.Point(376, 183),
              size=wx.Size(300, 200), style=wx.DEFAULT_DIALOG_STYLE,
              title='Create a new POU')
        self.SetClientSize(wx.Size(300, 200))

        self.MainPanel = wx.Panel(id=wxID_ADDBUSDIALOGMAINPANEL,
              name='MainPanel', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(300, 200), style=wx.TAB_TRAVERSAL)
        self.MainPanel.SetAutoLayout(True)

        self.staticText1 = wx.StaticText(id=wxID_ADDBUSDIALOGSTATICTEXT1,
              label='Bus ID:', name='staticText1', parent=self.MainPanel,
              pos=wx.Point(24, 24), size=wx.Size(95, 17), style=0)

        self.BusId = wx.TextCtrl(id=wxID_ADDBUSDIALOGBUSID,
              name='BusId', parent=self.MainPanel, pos=wx.Point(104, 24), 
              size=wx.Size(150, 24), style=0)

        self.staticText2 = wx.StaticText(id=wxID_ADDBUSDIALOGSTATICTEXT2,
              label='Bus Type:', name='staticText2', parent=self.MainPanel,
              pos=wx.Point(24, 64), size=wx.Size(95, 17), style=0)

        self.BusType = wx.Choice(id=wxID_ADDBUSDIALOGBUSTYPE,
              name='BusType', parent=self.MainPanel, pos=wx.Point(104, 64),
              size=wx.Size(150, 24), style=0)
        
        self.staticText3 = wx.StaticText(id=wxID_ADDBUSDIALOGSTATICTEXT3,
              label='Bus Name:', name='staticText3', parent=self.MainPanel,
              pos=wx.Point(24, 104), size=wx.Size(95, 17), style=0)

        self.BusName = wx.TextCtrl(id=wxID_ADDBUSDIALOGBUSNAME,
              name='BusName', parent=self.MainPanel, pos=wx.Point(104, 104),
              size=wx.Size(150, 24), style=0)
        
        self._init_sizers()

    def __init__(self, parent):
        self._init_ctrls(parent)
        self.ButtonSizer = self.CreateButtonSizer(wxOK|wxCANCEL|wxCENTRE)
        self.flexGridSizer1.Add(self.ButtonSizer, 1, wxALIGN_RIGHT)
        
        for option in ["CanFestival","SVGUI"]:
            self.BusType.Append(option)
        
        EVT_BUTTON(self, self.ButtonSizer.GetAffirmativeButton().GetId(), self.OnOK)
    
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
                self.EndModal(wxID_OK)
            except:
                message = wxMessageDialog(self, "Bus ID must be a decimal or hexadecimal number!", "Error", wxOK|wxICON_ERROR)
                message.ShowModal()
                message.Destroy()
        elif not bus_id.startswith("-"):
            try:
                bus_id = int(bus_id)
                self.EndModal(wxID_OK)
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

def wxAddExceptHook(path, app_version='[No version]'):#, ignored_exceptions=[]):
    
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
    app = wxPySimpleApp()
    wxInitAllImageHandlers()
    
    # Install a exception handle for bug reports
    wxAddExceptHook(os.getcwd(),__version__)
    
    frame = Beremiz(None)

    frame.Show()
    app.MainLoop()
