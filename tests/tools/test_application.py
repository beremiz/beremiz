#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2017: Andrey Skvortsov
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

import os
import sys
import unittest
import pytest
import wx
import time
import traceback
import ddt

import conftest
import Beremiz


class UserApplicationTest(unittest.TestCase):
    def InstallExceptionHandler(self):
        def handle_exception(e_type, e_value, e_traceback):
            # traceback.print_exception(e_type, e_value, e_traceback)
            self.exc_info = [e_type, e_value, e_traceback]
        self.exc_info = None
        self.old_excepthook = sys.excepthook
        sys.excepthook = handle_exception

    def StartApp(self):
        self.app = None

    def FinishApp(self):
        wx.CallAfter(self.app.frame.Close)
        self.app.MainLoop()
        self.app = None

    def setUp(self):
        self.app = None

    def tearDown(self):
        if self.app is not None and self.app.frame is not None:
            self.FinishApp()

    def RunUIActions(self, actions):
        for act in actions:
            wx.CallAfter(*act)
            self.ProcessEvents()

    def CheckForErrors(self):
        if self.exc_info is not None:
            # reraise catched previously exception
            raise self.exc_info[0], self.exc_info[1], self.exc_info[2]

    def ProcessEvents(self):
        for i in range(0, 30):
            self.CheckForErrors()
            wx.Yield()
            time.sleep(0.01)


@ddt.ddt
class BeremizApplicationTest(UserApplicationTest):
    """Test Beremiz as whole application"""
    def StartApp(self):
        self.app = Beremiz.BeremizIDELauncher()
        # disable default exception handler in Beremiz
        self.app.InstallExceptionHandler = lambda: None
        self.InstallExceptionHandler()
        self.app.PreStart()

    def FinishApp(self):
        wx.CallAfter(self.app.frame.Close)
        self.app.MainLoop()
        time.sleep(1)
        self.app = None

    def OpenAllProjectElements(self):
        """Open editor for every object in the project tree"""
        self.app.frame.ProjectTree.ExpandAll()
        self.ProcessEvents()
        item = self.app.frame.ProjectTree.GetRootItem()
        while item is not None:
            self.app.frame.ProjectTree.SelectItem(item, True)
            self.ProcessEvents()
            id = self.app.frame.ProjectTree.GetId()
            event = wx.lib.agw.customtreectrl.TreeEvent(
                wx.lib.agw.customtreectrl.wxEVT_TREE_ITEM_ACTIVATED,
                id, item)
            self.app.frame.OnProjectTreeItemActivated(event)
            self.ProcessEvents()
            item = self.app.frame.ProjectTree.GetNextVisible(item)

    def CheckTestProject(self, name):
        project = self.GetProjectPath(name)
        print "Testing example " + name
        sys.argv = ["", project]
        self.StartApp()
        self.OpenAllProjectElements()

        user_actions = [
            [self.app.frame.SwitchFullScrMode, None],
            [self.app.frame.SwitchFullScrMode, None],
            [self.app.frame.CTR._Clean],
            [self.app.frame.CTR._Build],
            [self.app.frame.CTR._Connect],
            [self.app.frame.CTR._Transfer],
            [self.app.frame.CTR._Run],
            [self.app.frame.CTR._Stop],
            [self.app.frame.CTR._Disconnect],
        ]

        self.RunUIActions(user_actions)
        self.FinishApp()

    def GetProjectPath(self, project):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", project))

    def testStartUp(self):
        """Checks whether the app starts and finishes correctly"""
        self.StartApp()
        self.FinishApp()

    @ddt.data(
        "first_steps",
        "logging",
        "svgui",
        "traffic_lights",
        "wxGlade",
        "python",
        "wiimote",
        "wxHMI",
    )
    @pytest.mark.timeout(30)
    def testCheckProject(self, name):
        self.CheckTestProject(name)


if __name__ == '__main__':
    unittest.main()
