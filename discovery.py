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
from Zeroconf import *
import socket
import  wx.lib.mixins.listctrl  as  listmix

class AutoWidthListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class DiscoveryDialog(wx.Dialog, listmix.ColumnSorterMixin):
    def __init__(self, parent, id=-1, title='Service Discovery'):
        self.my_result=None
        wx.Dialog.__init__(self, parent, id, title, size=(600,600), style=wx.DEFAULT_DIALOG_STYLE)

        # set up dialog sizer

        sizer = wx.FlexGridSizer(2, 1, 2, 2)  # rows, cols, vgap, hgap
        sizer.AddGrowableRow(0)
        sizer.AddGrowableCol(0)

        # set up list control

        self.list = AutoWidthListCtrl(self, -1,
                                      #pos=(50,20), 
                                      #size=(500,300),
                                      style=wx.LC_REPORT 
                                     | wx.LC_EDIT_LABELS
                                     | wx.LC_SORT_ASCENDING
                                     | wx.LC_SINGLE_SEL 
                                     )
        sizer.Add(self.list, 1, wx.EXPAND)

        btsizer = wx.FlexGridSizer(1, 6, 2, 2)  # rows, cols, vgap, hgap
        
        sizer.Add(btsizer, 1, wx.EXPAND)

        self.PopulateList()

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self.list)

        # set up buttons

        local_id = wx.NewId()
        b = wx.Button(self, local_id, "Refresh")
        self.Bind(wx.EVT_BUTTON, self.OnRefreshButton, b)
        btsizer.Add(b)

        btsizer.AddSpacer(0)
        btsizer.AddGrowableCol(1)

        local_id = wx.NewId()
        b = wx.Button(self, local_id, "Local")
        self.Bind(wx.EVT_BUTTON, self.ChooseLocalID, b)
        btsizer.Add(b)

        btsizer.AddSpacer(0)
        btsizer.AddGrowableCol(3)

        b = wx.Button(self, wx.ID_CANCEL, "Cancel")
        self.Bind(wx.EVT_BUTTON, self.OnCancel, b)
        btsizer.Add(b)

        b = wx.Button(self, wx.ID_OK, "OK")
        self.Bind(wx.EVT_BUTTON, self.OnOk, b)
        b.SetDefault()
        btsizer.Add(b)

        self.SetSizer(sizer)

        listmix.ColumnSorterMixin.__init__(self, 4)

        # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
        self.itemDataMap = {}

        # a counter used to assign a unique id to each listctrl item
        self.nextItemId = 0

        self.browser = None
        self.zConfInstance = Zeroconf()
        self.RefreshList()

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def RefreshList(self):
        type = "_WGPLC._tcp.local."
        self.browser = ServiceBrowser(self.zConfInstance, type, self)        

    def OnRefreshButton(self, event):
        self.list.DeleteAllItems()
        self.browser.cancel()
        self.RefreshList()

    def OnClose(self, event):
        self.zConfInstance.close()
        event.Skip()

    def OnCancel(self, event):
        self.zConfInstance.close()
        event.Skip()

    def OnOk(self, event):
        self.zConfInstance.close()
        event.Skip()

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.list

    def PopulateList(self):
        self.list.InsertColumn(0, 'NAME')
        self.list.InsertColumn(1, 'TYPE')
        self.list.InsertColumn(2, 'IP')
        self.list.InsertColumn(3, 'PORT')
        self.list.SetColumnWidth(0, 150)
        self.list.SetColumnWidth(1, 150)
        self.list.SetColumnWidth(2, 150)
        self.list.SetColumnWidth(3, 150)

    def getColumnText(self, index, col):
        item = self.list.GetItem(index, col)
        return item.GetText()

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex
        self.setresult()
        event.Skip()

    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex
        self.setresult()
        self.Close()
        event.Skip()

    def setresult(self):
        connect_type = self.getColumnText(self.currentItem, 1)
        connect_address = self.getColumnText(self.currentItem, 2)
        connect_port = self.getColumnText(self.currentItem, 3)
        
        uri = self.CreateURI(connect_type, connect_address, connect_port)
        self.my_result=uri

    def GetResult(self):
        return self.my_result
        
    def removeService(self, zeroconf, type, name):
        '''
        called when a service with the desired type goes offline.
        '''

        # loop through the list items looking for the service that went offline
        for idx in xrange(self.list.GetItemCount()):
            # this is the unique identifier assigned to the item
            item_id = self.list.GetItemData(idx)

            # this is the full typename that was received by addService
            item_name = self.itemDataMap[item_id][4]

            if item_name == name:
                self.list.DeleteItem(idx)
                break

    def addService(self, zeroconf, type, name):
        '''
        called when a service with the desired type is discovered.
        '''

        info = self.zConfInstance.getServiceInfo(type, name)

        svcname  = name.split(".")[0]
        typename = type.split(".")[0][1:]
        ip       = str(socket.inet_ntoa(info.getAddress()))
        port     = info.getPort()

        num_items = self.list.GetItemCount()

        # display the new data in the list
        new_item = self.list.InsertStringItem(num_items, svcname)
        self.list.SetStringItem(new_item, 1, "%s" % typename)
        self.list.SetStringItem(new_item, 2, "%s" % ip)
        self.list.SetStringItem(new_item, 3, "%s" % port)

        # record the new data for the ColumnSorterMixin
        # we assign every list item a unique id (that won't change when items
        # are added or removed)
        self.list.SetItemData(new_item, self.nextItemId)
 
        # the value of each column has to be stored in the itemDataMap
        # so that ColumnSorterMixin knows how to sort the column.

        # "name" is included at the end so that self.removeService
        # can access it.
        self.itemDataMap[self.nextItemId] = [ svcname, typename, ip, port, name ]

        self.nextItemId += 1

    def CreateURI(self, connect_type, connect_address, connect_port):
        uri = "%s://%s:%s"%(connect_type, connect_address, connect_port)
        return uri

    def ChooseLocalID(self, event):
        self.my_result = "LOCAL://"
        self.Close()
