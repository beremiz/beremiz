#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov <andrej.skvortzov@gmail.com>
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

import socket
import wx
import  wx.lib.mixins.listctrl  as  listmix
from util.Zeroconf import *

import connectors

service_type = '_PYRO._tcp.local.'

class AutoWidthListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, id, name, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, id, pos, size, style, name=name)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

[ID_DISCOVERYDIALOG, ID_DISCOVERYDIALOGSTATICTEXT1, 
 ID_DISCOVERYDIALOGSERVICESLIST, ID_DISCOVERYDIALOGREFRESHBUTTON, 
 ID_DISCOVERYDIALOGLOCALBUTTON, ID_DISCOVERYDIALOGIPBUTTON, 
] = [wx.NewId() for _init_ctrls in range(6)]

class DiscoveryDialog(wx.Dialog, listmix.ColumnSorterMixin):
    
    def _init_coll_MainSizer_Items(self, parent):
        parent.AddWindow(self.staticText1, 0, border=20, flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW)
        parent.AddWindow(self.ServicesList, 0, border=20, flag=wx.LEFT|wx.RIGHT|wx.GROW)
        parent.AddSizer(self.ButtonGridSizer, 0, border=20, flag=wx.LEFT|wx.RIGHT|wx.BOTTOM|wx.GROW)
        
    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_ButtonGridSizer_Items(self, parent):
        parent.AddWindow(self.RefreshButton, 0, border=0, flag=0)
        parent.AddWindow(self.LocalButton, 0, border=0, flag=0)
        parent.AddWindow(self.IpButton, 0, border=0, flag=0)
        parent.AddSizer(self.ButtonSizer, 0, border=0, flag=0)
        
    def _init_coll_ButtonGridSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableCol(1)
        parent.AddGrowableRow(0)
    
    def _init_sizers(self):
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=10)
        self.ButtonGridSizer = wx.FlexGridSizer(cols=4, hgap=5, rows=1, vgap=0)
        
        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_MainSizer_Growables(self.MainSizer)
        self._init_coll_ButtonGridSizer_Items(self.ButtonGridSizer)
        self._init_coll_ButtonGridSizer_Growables(self.ButtonGridSizer)
        
        self.SetSizer(self.MainSizer)
    
    def _init_ctrls(self, prnt):
        wx.Dialog.__init__(self, id=ID_DISCOVERYDIALOG, 
              name='DiscoveryDialog', parent=prnt, style=wx.DEFAULT_DIALOG_STYLE,
              title=_('Service Discovery'))
        
        self.staticText1 = wx.StaticText(id=ID_DISCOVERYDIALOGSTATICTEXT1,
              label=_('Services available:'), name='staticText1', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        # Set up list control
        self.ServicesList = AutoWidthListCtrl(id=ID_DISCOVERYDIALOGSERVICESLIST,
              name='ServicesList', parent=self, pos=wx.Point(0, 0), size=wx.Size(0, 0), 
              style=wx.LC_REPORT|wx.LC_EDIT_LABELS|wx.LC_SORT_ASCENDING|wx.LC_SINGLE_SEL)
        self.ServicesList.InsertColumn(0, _('NAME'))
        self.ServicesList.InsertColumn(1, _('TYPE'))
        self.ServicesList.InsertColumn(2, _('IP'))
        self.ServicesList.InsertColumn(3, _('PORT'))
        self.ServicesList.SetColumnWidth(0, 150)
        self.ServicesList.SetColumnWidth(1, 150)
        self.ServicesList.SetColumnWidth(2, 150)
        self.ServicesList.SetColumnWidth(3, 150)
        self.ServicesList.SetInitialSize(wx.Size(-1, 300))
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, id=ID_DISCOVERYDIALOGSERVICESLIST)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, id=ID_DISCOVERYDIALOGSERVICESLIST)
        
        listmix.ColumnSorterMixin.__init__(self, 4)
        
        self.RefreshButton = wx.Button(id=ID_DISCOVERYDIALOGREFRESHBUTTON,
              label=_('Refresh'), name='RefreshButton', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        self.Bind(wx.EVT_BUTTON, self.OnRefreshButton, id=ID_DISCOVERYDIALOGREFRESHBUTTON)
        
        self.LocalButton = wx.Button(id=ID_DISCOVERYDIALOGLOCALBUTTON,
              label=_('Local'), name='LocalButton', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        self.Bind(wx.EVT_BUTTON, self.OnLocalButton, id=ID_DISCOVERYDIALOGLOCALBUTTON)

        self.IpButton = wx.Button(id=ID_DISCOVERYDIALOGIPBUTTON,
              label=_('Add IP'), name='IpButton', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        self.Bind(wx.EVT_BUTTON, self.OnIpButton, id=ID_DISCOVERYDIALOGIPBUTTON)
        
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTER)
        
        self._init_sizers()
        self.Fit()
        
    def __init__(self, parent):
        self._init_ctrls(parent)
        
        self.itemDataMap = {}
        self.nextItemId = 0
        
        self.URI = None
        self.Browser = None
        
        self.ZeroConfInstance = Zeroconf()
        self.RefreshList()
        self.LatestSelection=None
        
    def __del__(self):
        if self.Browser is not None : self.Browser.cancel()
        self.ZeroConfInstance.close()
        
    def RefreshList(self):
        if self.Browser is not None : self.Browser.cancel()
        self.Browser = ServiceBrowser(self.ZeroConfInstance, service_type, self)

    def OnRefreshButton(self, event):
        self.ServicesList.DeleteAllItems()
        self.RefreshList()

    def OnLocalButton(self, event):
        self.URI = "LOCAL://"
        self.EndModal(wx.ID_OK)
        event.Skip()

    def OnIpButton(self, event):
        if self.LatestSelection is not None:
            l = lambda col : self.getColumnText(self.LatestSelection,col)
            self.URI = "%s://%s:%s"%tuple(map(l,(1,2,3)))
            self.EndModal(wx.ID_OK)
        event.Skip()

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.ServicesList

    def getColumnText(self, index, col):
        item = self.ServicesList.GetItem(index, col)
        return item.GetText()

    def OnItemSelected(self, event):
        self.SetURI(event.m_itemIndex)
        event.Skip()

    def OnItemActivated(self, event):
        self.SetURI(event.m_itemIndex)
        self.EndModal(wx.ID_OK)
        event.Skip()

#    def SetURI(self, idx):
#        connect_type = self.getColumnText(idx, 1)
#        connect_address = self.getColumnText(idx, 2)
#        connect_port = self.getColumnText(idx, 3)
#        
#        self.URI = "%s://%s:%s"%(connect_type, connect_address, connect_port)

    def SetURI(self, idx):
        self.LatestSelection = idx
        svcname = self.getColumnText(idx, 0) 
        connect_type = self.getColumnText(idx, 1)
        self.URI = "%s://%s"%(connect_type, svcname + '.' + service_type)
        
    def GetURI(self):
        return self.URI
        
    def removeService(self, zeroconf, _type, name):
        wx.CallAfter(self._removeService, name)


    def _removeService(self, name):
        '''
        called when a service with the desired type goes offline.
        '''
        
        # loop through the list items looking for the service that went offline
        for idx in xrange(self.ServicesList.GetItemCount()):
            # this is the unique identifier assigned to the item
            item_id = self.ServicesList.GetItemData(idx)

            # this is the full typename that was received by addService
            item_name = self.itemDataMap[item_id][4]

            if item_name == name:
                self.ServicesList.DeleteItem(idx)
                break
        
    def addService(self, zeroconf, _type, name):
        wx.CallAfter(self._addService, _type, name)

    def _addService(self, _type, name):
        '''
        called when a service with the desired type is discovered.
        '''
        info = self.ZeroConfInstance.getServiceInfo(_type, name)

        svcname  = name.split(".")[0]
        typename = _type.split(".")[0][1:]
        ip       = str(socket.inet_ntoa(info.getAddress()))
        port     = info.getPort()

        num_items = self.ServicesList.GetItemCount()

        # display the new data in the list
        new_item = self.ServicesList.InsertStringItem(num_items, svcname)
        self.ServicesList.SetStringItem(new_item, 1, "%s" % typename)
        self.ServicesList.SetStringItem(new_item, 2, "%s" % ip)
        self.ServicesList.SetStringItem(new_item, 3, "%s" % port)

        # record the new data for the ColumnSorterMixin
        # we assign every list item a unique id (that won't change when items
        # are added or removed)
        self.ServicesList.SetItemData(new_item, self.nextItemId)
 
        # the value of each column has to be stored in the itemDataMap
        # so that ColumnSorterMixin knows how to sort the column.

        # "name" is included at the end so that self.removeService
        # can access it.
        self.itemDataMap[self.nextItemId] = [ svcname, typename, ip, port, name ]

        self.nextItemId += 1
        
