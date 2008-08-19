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
from Zeroconf import *
import socket
import  wx.lib.mixins.listctrl  as  listmix

class TestListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class DiscoveryDialog(wx.Dialog, listmix.ColumnSorterMixin):
    def __init__(self, parent, id=-1, title='Service Discovery'):
        self.my_result=None
        self.itemDataMap = {}
        wx.Dialog.__init__(self, parent, id, title, size=(600,600), style=wx.DEFAULT_DIALOG_STYLE)

        self.list = TestListCtrl(self, -1,
                                 pos=(50,20), 
                                 size=(500,300),
                                 style=wx.LC_REPORT 
                                | wx.LC_EDIT_LABELS
                                | wx.LC_SORT_ASCENDING
                                )
        self.PopulateList()

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnItemDeselected, self.list)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self.list)
        self.Bind(wx.EVT_LIST_DELETE_ITEM, self.OnItemDelete, self.list)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, self.list)
        self.list.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)

        b = wx.Button(self,20, "Connect", (175, 500))
        self.Bind(wx.EVT_BUTTON, self.OnConnect, b)
        b.SetSize(b.GetBestSize())

        b = wx.Button(self, 40, "Cancel", (350, 500))
        self.Bind(wx.EVT_BUTTON, self.OnClose, b)
        b.SetSize(b.GetBestSize())

        #type = "_http._tcp.local."
        type = "_PYRO._tcp.local."
        self.r = Zeroconf()	
        browser = ServiceBrowser(self.r, type, self)		

        listmix.ColumnSorterMixin.__init__(self, 4)
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
        print "OnItemSelected: %s, %s, %s, %s\n"%(self.currentItem,
                            self.list.GetItemText(self.currentItem),
                            self.getColumnText(self.currentItem, 1),
                            self.getColumnText(self.currentItem, 2))
        event.Skip()


    def OnItemDeselected(self, evt):
        item = evt.GetItem()
        print "OnItemDeselected: %d" % evt.m_itemIndex

    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex
        print "OnItemActivated: %s\nTopItem: %s" %(self.list.GetItemText(self.currentItem), self.list.GetTopItem())

    def OnItemDelete(self, event):
        print "OnItemDelete\n"

    def OnColClick(self, event):
        print "OnColClick: %d\n" % event.GetColumn()
        event.Skip()

    def OnColRightClick(self, event):
        item = self.list.GetColumn(event.GetColumn())
        print "OnColRightClick: %d %s\n" %(event.GetColumn(), (item.GetText(), item.GetAlign(),
                                                item.GetWidth(), item.GetImage()))
    def OnDoubleClick(self, event):
        connect_type = self.getColumnText(self.currentItem, 1)
        connect_address = self.getColumnText(self.currentItem, 2)
        connect_port = self.getColumnText(self.currentItem, 3)
        
        uri = self.CreateURI(connect_type, connect_address, connect_port)
        self.my_result=uri
        event.Skip()

    def GetResult(self):
        return self.my_result
        
    def OnClick(self, event):
        print "Click! (%d)\n" %event.GetId()
        index = self.list.GetFocusedItem()
        self.list.DeleteItem(index)	
        print "Service", name, "removed"

    def removeService(self, zeroconf, type, name):
        index = self.list.GetFocusedItem()       
	
    def addService(self, zeroconf, type, name):
        info = self.r.getServiceInfo(type, name)
        typename = type.split(".")[0][1:]
        num_items = self.list.GetItemCount()
        self.itemDataMap[num_items] = (name, "%s"%type, "%s"%str(socket.inet_ntoa(info.getAddress())), "%s"%info.getPort())
        self.list.InsertStringItem(num_items, name.split(".")[0])
        self.list.SetStringItem(num_items, 1, "%s"%typename)
        self.list.SetStringItem(num_items, 2, "%s"%str(socket.inet_ntoa(info.getAddress())))
        self.list.SetStringItem(num_items, 3, "%s"%info.getPort())

    def CreateURI(self, connect_type, connect_address, connect_port):
        uri = "%s://%s:%s"%(connect_type, connect_address, connect_port)
        print uri
        return uri

    def OnAdd(self, event):
        num_items = self.list.GetItemCount()
        self.list.InsertStringItem(num_items, self.tc1.GetValue())
        self.list.SetStringItem(num_items, 1, self.tc2.GetValue())

    def OnRemove(self, event):
        index = self.list.GetFocusedItem()
        self.list.DeleteItem(index)

    def OnConnect(self, event):
        index = self.list.GetFocusedItem()
        print self.list.GetItemData(index)

    def OnClose(self, event):
        self.Close()

    def OnClear(self, event):
        self.list.DeleteAllItems()
