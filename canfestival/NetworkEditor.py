#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
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

from networkeditortemplate import NetworkEditorTemplate
from editors.ConfTreeNodeEditor import ConfTreeNodeEditor

class NetworkEditor(ConfTreeNodeEditor, NetworkEditorTemplate):

    CONFNODEEDITOR_TABS = [
        (_("CANOpen network"), "_create_NetworkEditor")]

    def _create_NetworkEditor(self, prnt):
        self.NetworkEditor = wx.Panel(
            id=wx.ID_ANY, parent=prnt, pos=wx.Point(0, 0),
            size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)

        NetworkEditorTemplate._init_ctrls(self, self.NetworkEditor)

        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=1, vgap=0)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)

        main_sizer.Add(self.NetworkNodes, 0, border=5, flag=wx.GROW | wx.ALL)

        self.NetworkEditor.SetSizer(main_sizer)

        return self.NetworkEditor

    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
        NetworkEditorTemplate.__init__(self, controler, window, False)

        self.RefreshNetworkNodes()
        self.RefreshBufferState()

    def __del__(self):
        self.Controler.OnCloseEditor(self)

    menu_refs = {}
    def GetConfNodeMenuItems(self):
        add_menu = [(wx.ITEM_NORMAL, (_('SDO Server'), '', self.OnAddSDOServerMenu)),
                    (wx.ITEM_NORMAL, (_('SDO Client'), '', self.OnAddSDOClientMenu)),
                    (wx.ITEM_NORMAL, (_('PDO Transmit'), '', self.OnAddPDOTransmitMenu)),
                    (wx.ITEM_NORMAL, (_('PDO Receive'), '', self.OnAddPDOReceiveMenu)),
                    (wx.ITEM_NORMAL, (_('Map Variable'), '', self.OnAddMapVariableMenu)),
                    (wx.ITEM_NORMAL, (_('User Type'), '', self.OnAddUserTypeMenu))]

        profile = self.Manager.GetCurrentProfileName()
        if profile not in ("None", "DS-301"):
            other_profile_text = _("%s Profile") % profile
            add_menu.append((wx.ITEM_SEPARATOR, None))
            for text, _indexes in self.Manager.GetCurrentSpecificMenu():
                add_menu.append((wx.ITEM_NORMAL, (text, '', self.GetProfileCallBack(text))))
        else:
            other_profile_text = _('Other Profile')

        master_menu = [(wx.ITEM_NORMAL, (_('DS-301 Profile'), '', self.OnCommunicationMenu)),
                       (wx.ITEM_NORMAL, (_('DS-302 Profile'), '', self.OnOtherCommunicationMenu)),
                       (wx.ITEM_NORMAL, (other_profile_text, '', self.OnEditProfileMenu)),
                       (wx.ITEM_SEPARATOR, None),
                       (add_menu, (_('Add')))]

        return [(wx.ITEM_NORMAL, (_('Add slave'), '', self.OnAddSlaveMenu)),
                (wx.ITEM_NORMAL, (_('Remove slave'), '', self.OnRemoveSlaveMenu)),
                (wx.ITEM_SEPARATOR, None),
                (master_menu, (_('Master')), self.menu_refs, "master")]

    def RefreshMainMenu(self):
        pass

    def RefreshConfNodeMenu(self, confnode_menu):
        master_item = self.menu_refs.get("master")
        if master_item:
            master_item.Enable(self.NetworkNodes.GetSelection() == 0)

    def RefreshView(self):
        ConfTreeNodeEditor.RefreshView(self)
        self.RefreshCurrentIndexList()

    def RefreshBufferState(self):
        NetworkEditorTemplate.RefreshBufferState(self)
        self.ParentWindow.RefreshTitle()
        self.ParentWindow.RefreshFileMenu()
        self.ParentWindow.RefreshEditMenu()
        self.ParentWindow.RefreshPageTitles()

    def OnNodeSelectedChanged(self, event):
        NetworkEditorTemplate.OnNodeSelectedChanged(self, event)
        wx.CallAfter(self.ParentWindow.RefreshEditMenu)
