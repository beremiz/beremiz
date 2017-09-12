import os
import sys
import unittest
import wx
import time
import traceback
from xvfbwrapper import Xvfb

vdisplay = None


def setUpModule():
    vdisplay = Xvfb(width=1280, height=720)
    vdisplay.start()


def tearDownModule():
    if vdisplay is not None:
        vdisplay.stop()


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
        # time.sleep(0.2)
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
        # open every object in the project tree
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

    def CheckTestProject(self, project):
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

        # user_actions.append([self.app.frame.OnCloseProjectMenu, None])
        self.RunUIActions(user_actions)
        self.FinishApp()

    def GetProjectPath(self, project):
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", project))

    # @unittest.skip("")
    def testStartUp(self):
        """Checks whether the app starts and finishes correctly"""
        self.StartApp()
        self.FinishApp()

    # @unittest.skip("")
    def testOpenExampleProjects(self):
        """Opens, builds and runs user PLC examples from tests directory"""
        prj = [
            "first_steps",
            "logging",
            "svgui",
            "traffic_lights",
            "wxGlade",
            "python",
            "wiimote",
            "wxHMI",
        ]
        for name in prj:
            project = self.GetProjectPath(name)
            print "Testing example " + name
            self.CheckTestProject(project)


if __name__ == '__main__':
    if __package__ is None:
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        global Beremiz
        import Beremiz
    unittest.main()
