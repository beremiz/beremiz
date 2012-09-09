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

import os

import wx

from plcopen.structures import LOCATIONDATATYPES
from PLCControler import LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY

#-------------------------------------------------------------------------------
#                                   Helpers
#-------------------------------------------------------------------------------

CWD = os.path.split(os.path.split(os.path.realpath(__file__))[0])[0]

def GetDirChoiceOptions():
    _ = lambda x : x
    return [(_("All"), [LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY]), 
            (_("Input"), [LOCATION_VAR_INPUT]), 
            (_("Output"), [LOCATION_VAR_OUTPUT]), 
            (_("Memory"), [LOCATION_VAR_MEMORY])]
DIRCHOICE_OPTIONS_FILTER = dict([(_(option), filter) for option, filter in GetDirChoiceOptions()])

# turn LOCATIONDATATYPES inside-out
LOCATION_SIZES = {}
for size, types in LOCATIONDATATYPES.iteritems():
    for type in types:
        LOCATION_SIZES[type] = size

#-------------------------------------------------------------------------------
#                            Browse Locations Dialog
#-------------------------------------------------------------------------------

class BrowseLocationsDialog(wx.Dialog):
    
    def __init__(self, parent, var_type, locations):
        wx.Dialog.__init__(self, parent,  
              size=wx.Size(600, 400), title=_('Browse Locations'))
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        locations_label = wx.StaticText(self, label=_('Locations available:'))
        main_sizer.AddWindow(locations_label, border=20, 
              flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW)
        
        self.LocationsTree = wx.TreeCtrl(self, 
              style=wx.TR_HAS_BUTTONS|wx.TR_SINGLE|wx.SUNKEN_BORDER|wx.TR_HIDE_ROOT|wx.TR_LINES_AT_ROOT)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnLocationsTreeItemActivated, 
                  self.LocationsTree)
        main_sizer.AddWindow(self.LocationsTree, border=20, 
              flag=wx.LEFT|wx.RIGHT|wx.GROW)
        
        button_gridsizer = wx.FlexGridSizer(cols=3, hgap=5, rows=1, vgap=0)
        button_gridsizer.AddGrowableCol(2)
        button_gridsizer.AddGrowableRow(0)
        main_sizer.AddSizer(button_gridsizer, border=20, 
              flag=wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.GROW)
        
        direction_label = wx.StaticText(self, label=_('Direction:'))
        button_gridsizer.AddWindow(direction_label,
              flag=wx.ALIGN_CENTER_VERTICAL)
        
        self.DirChoice = wx.ComboBox(self, style=wx.CB_READONLY)
        self.Bind(wx.EVT_COMBOBOX, self.OnDirChoice, self.DirChoice)
        button_gridsizer.AddWindow(self.DirChoice,
              flag=wx.ALIGN_CENTER_VERTICAL)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, button_sizer.GetAffirmativeButton())
        button_gridsizer.AddWindow(button_sizer, flag=wx.ALIGN_RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.VarType = var_type
        self.Locations = locations
        
        # Define Tree item icon list
        self.TreeImageList = wx.ImageList(16, 16)
        self.TreeImageDict = {}
        
        # Icons for items
        for imgname, itemtype in [
            ("CONFIGURATION", LOCATION_CONFNODE), 
            ("RESOURCE",      LOCATION_MODULE), 
            ("PROGRAM",       LOCATION_GROUP), 
            ("VAR_INPUT",     LOCATION_VAR_INPUT), 
            ("VAR_OUTPUT",    LOCATION_VAR_OUTPUT), 
            ("VAR_LOCAL",     LOCATION_VAR_MEMORY)]:
            self.TreeImageDict[itemtype]=self.TreeImageList.Add(wx.Bitmap(os.path.join(CWD, 'Images', '%s.png'%imgname)))
        
        # Assign icon list to TreeCtrls
        self.LocationsTree.SetImageList(self.TreeImageList)
        
        # Set a options for the choice
        for option, filter in GetDirChoiceOptions():
            self.DirChoice.Append(_(option))
        self.DirChoice.SetStringSelection(_("All"))
        self.RefreshFilter()
        
        self.RefreshLocationsTree()
    
    def RefreshFilter(self):
        self.Filter = DIRCHOICE_OPTIONS_FILTER[self.DirChoice.GetStringSelection()]
    
    def RefreshLocationsTree(self):
        root = self.LocationsTree.GetRootItem()
        if not root.IsOk():
            root = self.LocationsTree.AddRoot("")
        self.GenerateLocationsTreeBranch(root, self.Locations)
    
    def GenerateLocationsTreeBranch(self, root, locations):
        to_delete = []
        item, root_cookie = self.LocationsTree.GetFirstChild(root)
        for loc_infos in locations:
            infos = loc_infos.copy()
            if infos["type"] in [LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP] or\
               infos["type"] in self.Filter and (infos["IEC_type"] == self.VarType or
               infos["IEC_type"] is None and LOCATION_SIZES[self.VarType] == infos["size"]):
                children = [child for child in infos.pop("children")]
                if not item.IsOk():
                    item = self.LocationsTree.AppendItem(root, infos["name"])
                    if wx.Platform != '__WXMSW__':
                        item, root_cookie = self.LocationsTree.GetNextChild(root, root_cookie)
                else:
                    self.LocationsTree.SetItemText(item, infos["name"])
                self.LocationsTree.SetPyData(item, infos)
                self.LocationsTree.SetItemImage(item, self.TreeImageDict[infos["type"]])
                self.GenerateLocationsTreeBranch(item, children)
                item, root_cookie = self.LocationsTree.GetNextChild(root, root_cookie)
        while item.IsOk():
            to_delete.append(item)
            item, root_cookie = self.LocationsTree.GetNextChild(root, root_cookie)
        for item in to_delete:
            self.LocationsTree.Delete(item)
    
    def OnLocationsTreeItemActivated(self, event):
        infos = self.LocationsTree.GetPyData(event.GetItem())
        if infos["type"] not in [LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP]:
            wx.CallAfter(self.EndModal, wx.ID_OK)
        event.Skip()
    
    def OnDirChoice(self, event):
        self.RefreshFilter()
        self.RefreshLocationsTree()
        
    def GetValues(self):
        selected = self.LocationsTree.GetSelection()
        return self.LocationsTree.GetPyData(selected)
        
    def OnOK(self, event):
        selected = self.LocationsTree.GetSelection()
        var_infos = None
        if selected.IsOk():
            var_infos = self.LocationsTree.GetPyData(selected)
        if var_infos is None or var_infos["type"] in [LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP]:
            dialog = wx.MessageDialog(self, _("A location must be selected!"), _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)
