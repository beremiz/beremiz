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


import wx
import wx.lib.mixins.listctrl as listmix
from connectors.ZeroConfListener import ZeroConfListenerClass

class AutoWidthListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, name, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, wx.ID_ANY, pos, size, style, name=name)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

class DiscoveryPanel(wx.Panel, listmix.ColumnSorterMixin):

    def _init_coll_MainSizer_Items(self, parent):
        parent.Add(self.staticText1,    0, border=20, flag=wx.TOP | wx.LEFT | wx.RIGHT | wx.GROW)
        parent.Add(self.ServicesList,   0, border=20, flag=wx.LEFT | wx.RIGHT | wx.GROW)
        parent.Add(self.ButtonGridSizer, 0, border=20, flag=wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.GROW)

    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)

    def _init_coll_ButtonGridSizer_Items(self, parent):
        parent.Add(self.RefreshButton, 0, border=0, flag=0)
        # parent.Add(self.ByIPCheck, 0, border=0, flag=0)

    def _init_coll_ButtonGridSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(0)

    def _init_sizers(self):
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=10)
        self.ButtonGridSizer = wx.FlexGridSizer(cols=2, hgap=5, rows=1, vgap=0)

        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_MainSizer_Growables(self.MainSizer)
        self._init_coll_ButtonGridSizer_Items(self.ButtonGridSizer)
        self._init_coll_ButtonGridSizer_Growables(self.ButtonGridSizer)

        self.SetSizer(self.MainSizer)

    def _init_list_ctrl(self):
        # Set up list control
        self.ServicesList = AutoWidthListCtrl(
            name='ServicesList', parent=self, pos=wx.Point(0, 0), size=wx.Size(0, 0),
            style=wx.LC_REPORT | wx.LC_EDIT_LABELS | wx.LC_SORT_ASCENDING | wx.LC_SINGLE_SEL)
        for col, (label, width) in enumerate([
                (_('NAME'), 150), (_('TYPE'), 150), (_('IP'), 150), (_('PORT'), 150)]):
            self.ServicesList.InsertColumn(col, label)
        self.ServicesList.SetInitialSize(wx.Size(-1, 300))
            
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.ServicesList)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self.ServicesList)

    def _init_ctrls(self, prnt):
        self.staticText1 = wx.StaticText(
            label=_('Services available:'), name='staticText1', parent=self,
            pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)

        self.RefreshButton = wx.Button(
            label=_('Refresh'), name='RefreshButton', parent=self,
            pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        self.RefreshButton.Bind(wx.EVT_BUTTON, self.OnRefreshButton)

        # self.ByIPCheck = wx.CheckBox(self, label=_("Use IP instead of Service Name"))
        # self.ByIPCheck.SetValue(True)

        self._init_sizers()
        self.Fit()

    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        self.parent = parent

        self._init_list_ctrl()
        listmix.ColumnSorterMixin.__init__(self, 4)

        self._init_ctrls(parent)

        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

        self.itemDataMap = {}
        self.nextItemId = 0

        self.URI = None

        self.LatestSelection = None

        self.ZeroConfListener = None

        self.RefreshList()


    def _cleanup(self):
        if self.ZeroConfListener is not None:
            self.ZeroConfListener.stop()
            self.ZeroConfListener = None

    def OnDestroy(self, event):
        self._cleanup()
        event.Skip()

    def RefreshList(self):
        self.ServicesList.DeleteAllItems()
        self.ZeroConfListener = ZeroConfListenerClass(self)

    def OnRefreshButton(self, event):
        self.RefreshList()

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.ServicesList

    def getColumnText(self, index, col):
        item = self.ServicesList.GetItem(index, col)
        return item.GetText()

    def OnItemSelected(self, event):
        self.SetURI(event.GetIndex())
        event.Skip()

    def OnItemActivated(self, event):
        self.SetURI(event.GetIndex())
        self.parent.EndModal(wx.ID_OK)
        event.Skip()

#    def SetURI(self, idx):
#        connect_type = self.getColumnText(idx, 1)
#        connect_address = self.getColumnText(idx, 2)
#        connect_port = self.getColumnText(idx, 3)
#
#        self.URI = "%s://%s:%s"%(connect_type, connect_address, connect_port)

    def SetURI(self, idx):
        self.LatestSelection = idx

    def GetURI(self):
        if self.LatestSelection is not None:
            # if self.ByIPCheck.IsChecked():
            svcname, scheme, host, port = \
                [self.getColumnText(self.LatestSelection, col) for col in range(4)]
            return ("%s://%s:%s#%s" % (scheme, host, port, svcname)) \
                if scheme[-1] == "S" \
                else ("%s://%s:%s" % (scheme, host, port))
            # else:
            #     svcname = self.getColumnText(self.LatestSelection, 0)
            #     connect_type = self.getColumnText(self.LatestSelection, 1)
            #     return str("MDNS://%s" % svcname)
        return None

    def removeService(self, name):
        wx.CallAfter(self._removeService, name)

    def _removeService(self, name):
        '''
        called when a service with the desired type goes offline.
        '''

        # loop through the list items looking for the service that went offline
        for idx in range(self.ServicesList.GetItemCount()):
            # this is the unique identifier assigned to the item
            item_id = self.ServicesList.GetItemData(idx)

            # this is the full typename that was received by addService
            item_name = self.itemDataMap[item_id][4]

            if item_name == name:
                self.ServicesList.DeleteItem(idx)
                break

    def addService(self, typename, ip, port, name):
        wx.CallAfter(self._addService, typename, ip, port, name)

    def _addService(self, typename, ip, port, name):
        '''
        called when a service with the desired type is discovered.
        '''
        svcname = name.split(".")[0]

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
        self.itemDataMap[self.nextItemId] = [svcname, typename, ip, port, name]

        self.nextItemId += 1
