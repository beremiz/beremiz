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

from time import localtime
from datetime import datetime
import types

import os, re, platform, sys, time, traceback, getopt, commands
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "plcopeneditor"))
sys.path.append(os.path.join(base_folder, "CanFestival-3", "objdictgen"))
sys.path.append(os.path.join(base_folder, "wxsvg", "svgui", "defeditor"))

iec2cc_path = os.path.join(base_folder, "matiec", "iec2cc")
ieclib_path = os.path.join(base_folder, "matiec", "lib")

from PLCOpenEditor import PLCOpenEditor, ProjectDialog
from TextViewer import TextViewer
from plcopen.structures import IEC_KEYWORDS#, AddPlugin
from plugger import PluginsRoot

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

class AttributesTable(wx.grid.PyGridTableBase):
    
    """
    A custom wxGrid Table using user supplied data
    """
    def __init__(self, parent, data, colnames):
        # The base class must be initialized *first*
        wx.grid.PyGridTableBase.__init__(self)
        self.data = data
        self.colnames = colnames
        self.Parent = parent
        # XXX
        # we need to store the row length and collength to
        # see if the table has changed size
        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
    
    def GetNumberCols(self):
        return len(self.colnames)
        
    def GetNumberRows(self):
        return len(self.data)

    def GetColLabelValue(self, col):
        if col < len(self.colnames):
            return self.colnames[col]

    def GetRowLabelValues(self, row):
        return row

    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            name = str(self.data[row].get(self.GetColLabelValue(col), ""))
            return name
    
    def GetValueByName(self, row, colname):
        return self.data[row].get(colname)

    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            self.data[row][self.GetColLabelValue(col)] = value
        
    def ResetView(self, grid):
        """
        (wxGrid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        grid.BeginBatch()
        for current, new, delmsg, addmsg in [
            (self._rows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:
            if new < current:
                msg = wx.grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues(grid)
        grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
        # update the column rendering scheme
        self._updateColAttrs(grid)

        # update the scrollbars and the displayed part of the grid
        grid.AdjustScrollbars()
        grid.ForceRefresh()

    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)

    def _updateColAttrs(self, grid):
        """
        wxGrid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                editor = None
                renderer = None
                align = wx.ALIGN_LEFT
                colname = self.GetColLabelValue(col)
                grid.SetReadOnly(row, col, False)
                
                if colname == "Value":
                    colSize = 100
                    value_type = self.data[row]["Type"]
                    if isinstance(value_type, types.ListType):
                        editor = wx.grid.GridCellChoiceEditor()
                        editor.SetParameters(",".join(value_type))
                    elif value_type == "boolean":
                        editor = wx.grid.GridCellChoiceEditor()
                        editor.SetParameters("True,False")
                    elif value_type in ["unsignedLong","long","integer"]:
                        editor = wx.grid.GridCellNumberEditor()
                        align = wx.ALIGN_RIGHT
                    elif value_type == "decimal":
                        editor = wx.grid.GridCellFloatEditor()
                        align = wx.ALIGN_RIGHT
                    else:
                        editor = wx.grid.GridCellTextEditor()
                else:
                    colSize = 120
                    grid.SetReadOnly(row, col, True)
                
                attr = wx.grid.GridCellAttr()
                attr.SetAlignment(align, wx.ALIGN_CENTRE)
                grid.SetColAttr(col, attr)
                grid.SetColSize(col, colSize)
                                    
                grid.SetCellEditor(row, col, editor)
                grid.SetCellRenderer(row, col, renderer)
                
                grid.SetCellBackgroundColour(row, col, wx.WHITE)
    
    def SetData(self, data):
        self.data = data
    
    def GetData(self):
        return self.data
    
    def AppendRow(self, row_content):
        self.data.append(row_content)

    def RemoveRow(self, row_index):
        self.data.pop(row_index)

    def GetRow(self, row_index):
        return self.data[row_index]

    def Empty(self):
        self.data = []

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
    
    def _init_coll_ParamsPanelMainSizer_Items(self, parent):
        parent.AddSizer(self.ParamsPanelChildSizer, 1, border=10, flag=wx.GROW|wx.ALL)
        parent.AddSizer(self.ParamsPanelPluginSizer, 1, border=10, flag=wx.GROW|wx.ALL)
        parent.AddWindow(self.AttributesGrid, 2, border=10, flag=wx.GROW|wx.TOP|wx.RIGHT|wx.BOTTOM)
        
    def _init_coll_ParamsPanelChildSizer_Items(self, parent):
        parent.AddWindow(self.ParamsEnable, 0, border=5, flag=wx.GROW|wx.BOTTOM)
        parent.AddWindow(self.ParamsStaticText1, 0, border=5, flag=wx.GROW|wx.BOTTOM)
        parent.AddWindow(self.ParamsIECChannel, 0, border=0, flag=wx.GROW)
    
    def _init_coll_ParamsPanelPluginSizer_Items(self, parent):
        parent.AddWindow(self.ParamsStaticText2, 0, border=5, flag=wx.GROW|wx.BOTTOM)
        parent.AddWindow(self.ParamsTargetType, 0, border=0, flag=wx.GROW)
        
    def _init_sizers(self):
        self.LeftGridSizer = wx.FlexGridSizer(cols=1, hgap=2, rows=2, vgap=2)
        self.ButtonGridSizer = wx.FlexGridSizer(cols=3, hgap=2, rows=1, vgap=2)
        self.ParamsPanelMainSizer = wx.StaticBoxSizer(self.ParamsStaticBox, wx.HORIZONTAL)
        self.ParamsPanelChildSizer = wx.BoxSizer(wx.VERTICAL)
        self.ParamsPanelPluginSizer = wx.BoxSizer(wx.VERTICAL)
        
        self._init_coll_LeftGridSizer_Growables(self.LeftGridSizer)
        self._init_coll_LeftGridSizer_Items(self.LeftGridSizer)
        self._init_coll_ButtonGridSizer_Growables(self.ButtonGridSizer)
        self._init_coll_ButtonGridSizer_Items(self.ButtonGridSizer)
        self._init_coll_ParamsPanelMainSizer_Items(self.ParamsPanelMainSizer)
        self._init_coll_ParamsPanelChildSizer_Items(self.ParamsPanelChildSizer)
        self._init_coll_ParamsPanelPluginSizer_Items(self.ParamsPanelPluginSizer)
        
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
        
        self.ParamsPanel = wx.Panel(id=ID_BEREMIZPARAMSPANEL, 
              name='ParamsPanel', parent=self.SecondSplitter, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        
        self.ParamsStaticBox = wx.StaticBox(id=ID_BEREMIZPARAMSSTATICBOX,
              label='', name='staticBox1', parent=self.ParamsPanel,
              pos=wx.Point(0, 0), size=wx.Size(0, 0), style=0)
        
        self.ParamsEnable = wx.CheckBox(id=ID_BEREMIZPARAMSENABLE,
              label='Plugin enabled', name='ParamsEnable', parent=self.ParamsPanel,
              pos=wx.Point(0, 0), size=wx.Size(0, 24), style=0)
        self.Bind(wx.EVT_CHECKBOX, self.OnParamsEnableChanged, id=ID_BEREMIZPARAMSENABLE)
        
        self.ParamsStaticText1 = wx.StaticText(id=ID_BEREMIZPARAMSSTATICTEXT1,
              label='IEC Channel:', name='ParamsStaticText1', parent=self.ParamsPanel,
              pos=wx.Point(0, 0), size=wx.Size(0, 17), style=0)
        
        self.ParamsIECChannel = wx.SpinCtrl(id=ID_BEREMIZPARAMSIECCHANNEL,
              name='ParamsIECChannel', parent=self.ParamsPanel, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.SP_ARROW_KEYS, min=0)
        self.Bind(wx.EVT_SPINCTRL, self.OnParamsIECChannelChanged, id=ID_BEREMIZPARAMSIECCHANNEL)

        self.ParamsStaticText2 = wx.StaticText(id=ID_BEREMIZPARAMSSTATICTEXT2,
              label='Target Type:', name='ParamsStaticText2', parent=self.ParamsPanel,
              pos=wx.Point(0, 0), size=wx.Size(0, 17), style=0)

        self.ParamsTargetType = wx.Choice(id=ID_BEREMIZPARAMSTARGETTYPE, 
              name='TargetType', choices=[""], parent=self.ParamsPanel, 
              pos=wx.Point(0, 0), size=wx.Size(0, 24), style=wx.LB_SINGLE)
        self.Bind(wx.EVT_CHOICE, self.OnParamsTargetTypeChanged, id=ID_BEREMIZPARAMSTARGETTYPE)

        self.AttributesGrid = wx.grid.Grid(id=ID_BEREMIZPARAMSATTRIBUTESGRID,
              name='AttributesGrid', parent=self.ParamsPanel, pos=wx.Point(0, 0), 
              size=wx.Size(0, 150), style=wx.VSCROLL)
        self.AttributesGrid.SetFont(wx.Font(12, 77, wx.NORMAL, wx.NORMAL, False,
              'Sans'))
        self.AttributesGrid.SetLabelFont(wx.Font(10, 77, wx.NORMAL, wx.NORMAL,
              False, 'Sans'))
        self.AttributesGrid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnAttributesGridCellChange)

        self.LogConsole = wx.TextCtrl(id=ID_BEREMIZLOGCONSOLE, value='',
              name='LogConsole', parent=self.SecondSplitter, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TE_MULTILINE|wx.TE_RICH2)
        
        self.SecondSplitter.SplitHorizontally(self.ParamsPanel, self.LogConsole,
              -250)
        
        self._init_sizers()

    def __init__(self, parent, projectOpen):
        self._init_ctrls(parent)
        
        self.Log = LogPseudoFile(self.LogConsole)
        
        self.PluginRoot = PluginsRoot()
        for value in self.PluginRoot.GetTargetTypes():
            self.ParamsTargetType.Append(value)
        
        self.Table = AttributesTable(self, [], ["Attribute", "Value"])
        self.AttributesGrid.SetTable(self.Table)
        self.AttributesGrid.SetRowLabelSize(0)
        
        if projectOpen:
            self.PluginRoot.LoadProject(projectOpen)
            self.RefreshPluginTree()
        
        self.PLCEditor = None
        
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
        self.GenerateTreeBranch(root, infos)
        self.PluginTree.Expand(self.PluginTree.GetRootItem())
        self.RefreshPluginParams()

    def GenerateTreeBranch(self, root, infos):
        to_delete = []
        if root.IsOk():
            self.PluginTree.SetItemText(root, infos["name"])
        else:
            root = self.PluginTree.AddRoot(infos["name"])
        self.PluginTree.SetPyData(root, infos["type"])
        item, root_cookie = self.PluginTree.GetFirstChild(root)
        if len(infos["values"]) > 0:
            for values in infos["values"]:
                if not item.IsOk():
                    item = self.PluginTree.AppendItem(root, "")
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
            self.ParamsStaticBox.SetLabel(plugin.BaseParams.getName())
            if plugin == self.PluginRoot:
                self.ParamsPanelMainSizer.Hide(self.ParamsPanelChildSizer)
                self.ParamsPanelMainSizer.Show(self.ParamsPanelPluginSizer)
                self.ParamsTargetType.SetStringSelection(self.PluginRoot.GetTargetType())
            else:
                self.ParamsPanelMainSizer.Show(self.ParamsPanelChildSizer)
                self.ParamsPanelMainSizer.Hide(self.ParamsPanelPluginSizer)
                self.ParamsEnable.SetValue(plugin.BaseParams.getEnabled())
                self.ParamsEnable.Enable(True)
                self.ParamsStaticText1.Enable(True)
                self.ParamsIECChannel.SetValue(plugin.BaseParams.getIEC_Channel())
                self.ParamsIECChannel.Enable(True)
            self.ParamsPanelMainSizer.Layout()
            self.RefreshAttributesGrid()
            
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
    
    def RefreshAttributesGrid(self):
        plugin = self.GetSelectedPlugin()
        if not plugin:
            self.Table.Empty()
        else:
            if plugin == self.PluginRoot:
                attr_infos = self.PluginRoot.GetTargetAttributes()
            else:
                attr_infos = plugin.GetPlugParamsAttributes()
            data = []
            for infos in attr_infos:
                data.append({"Attribute" : infos["name"], "Value" : infos["value"],
                    "Type" : infos["type"]})
            self.Table.SetData(data)
        self.Table.ResetView(self.AttributesGrid)
    
    def OnParamsEnableChanged(self, event):
        plugin = self.GetSelectedPlugin()
        if plugin and plugin != self.PluginRoot:
            plugin.BaseParams.setEnabled(event.Checked())
        event.Skip()
    
    def OnParamsIECChannelChanged(self, event):
        plugin = self.GetSelectedPlugin()
        if plugin and plugin != self.PluginRoot:
            plugin.BaseParams.setIEC_Channel(self.ParamsIECChannel.GetValue())
        event.Skip()
    
    def OnParamsTargetTypeChanged(self, event):
        plugin = self.GetSelectedPlugin()
        if plugin and plugin == self.PluginRoot:
            self.PluginRoot.ChangeTargetType(self.ParamsTargetType.GetStringSelection())
            self.RefreshAttributesGrid()
        event.Skip()
    
    def OnAttributesGridCellChange(self, event):
        row = event.GetRow()
        plugin = self.GetSelectedPlugin()
        if plugin:
            name = self.Table.GetValueByName(row, "Attribute")
            value = self.Table.GetValueByName(row, "Value")
            if plugin == self.PluginRoot:
                self.PluginRoot.SetTargetAttribute(name, value)
            else:
                plugin.SetPlugParamsAttribute(name, value)
        event.Skip()
    
    def OnNewProjectMenu(self, event):
        defaultpath = self.PluginRoot.GetProjectPath()
        if defaultpath == "":
            defaultpath = os.getcwd()
        dialog = wx.DirDialog(self , "Choose a project", defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            dialog.Destroy()
            if os.path.isdir(projectpath) and len(os.listdir(projectpath)) == 0:
                dialog = ProjectDialog(self)
                if dialog.ShowModal() == wx.ID_OK:
                    values = dialog.GetValues()
                    values["creationDateTime"] = datetime(*localtime()[:6])
                    self.PluginRoot.NewProject(projectpath, values)
                    self.RefreshPluginTree()
                    self.RefreshButtons()
                    self.RefreshMainMenu()
                dialog.Destroy()
            else:
                message = wx.MessageDialog(self, "Folder choosen isn't empty. You can't use it for a new project!", "ERROR", wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
        event.Skip()
    
    def OnOpenProjectMenu(self, event):
        defaultpath = self.PluginRoot.GetProjectPath()
        if defaultpath == "":
            defaultpath = os.getcwd()
        dialog = wx.DirDialog(self , "Choose a project", defaultpath, wx.DD_NEW_DIR_BUTTON)
        if dialog.ShowModal() == wx.ID_OK:
            projectpath = dialog.GetPath()
            if os.path.isdir(projectpath):
                result = self.PluginRoot.LoadProject(projectpath)
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
    
    def EditPLC(self):
        if not self.PLCEditor:
            self.PLCEditor = PLCOpenEditor(self, self.PluginRoot.PLCManager)
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
                else : outlen += 1
                outdata += outchunk
                self.Log.write(outchunk)
            if errfd in ready[0]:
                errchunk = errfile.readline()
                if errchunk == '': erreof = 1 
                else : errlen += 1
                errdata += errchunk
                self.Log.write_warning(errchunk)
            if outeof and erreof : break
            if errlen > sz_limit or outlen > sz_limit : 
                os.kill(child.pid, signal.SIGTERM)
                self.Log.write_error("Output size reached limit -- killed\n")
                break
        err = child.wait()
        return (err, outdata, errdata)

    def BuildAutom(self):
        LOCATED_MODEL = re.compile("__LOCATED_VAR\(([A-Z]*),([_A-Za-z0-9]*)\)")
        
        if self.PLCManager:
            self.TargetDir = os.path.join(self.CurrentProjectPath, "build")
            if not os.path.exists(self.TargetDir):
                os.mkdir(self.TargetDir)
            self.Log.flush()
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
                C_files = result.splitlines()
                C_files.remove("POUS.c")
                C_files = map(lambda filename:os.path.join(self.TargetDir, filename), C_files)
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
                        c_filename = "%s.c"%os.path.join(self.TargetDir, gen_cfile.FormatName(bus_infos["Name"]))
                        result = bus_infos["Manager"].GenerateBus(c_filename, locations)
                        if result:
                            raise Exception
                        else:
                            C_files.append(c_filename)
                self.Log.write("Generating Makefiles...\n")
                self.Log.write(str(C_files))
                
                self.Log.write("Compiling Project...\n")
                
                self.Log.write("\nBuild Project completed\n")
            except Exception, message:
                self.Log.write_error("\nBuild Failed\n")
                self.Log.write(str(message))
                pass
                
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
