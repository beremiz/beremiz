

import wx
from controls.IDBrowser import IDBrowser
from controls.CertBrowser import CertBrowser
from controls.OwnIdentityPanel import OwnIdentityPanel


class IDManageNB(wx.Notebook):
    def __init__(self, parent, ctr):
        wx.Notebook.__init__(self, parent, -1, size=(21,21), style=
                             wx.BK_DEFAULT
                             #wx.BK_TOP
                             #wx.BK_BOTTOM
                             #wx.BK_LEFT
                             #wx.BK_RIGHT
                             # | wx.NB_MULTILINE
                             )

        # start IDBrowser in manager mode
        self.id_browser = IDBrowser(self, ctr)
        self.AddPage(self.id_browser, "Controllers")

        win = OwnIdentityPanel(self, -1)
        self.AddPage(win, "IDE")

        self.cert_browser = CertBrowser(self, ctr.logger)
        self.AddPage(self.cert_browser, "Servers certificates")


class IDManager(wx.Dialog):
    def __init__(self, parent, ctr):
        wx.Dialog.__init__(self,
                           name='IDManager', parent=parent,
                           title=_('Identity Manager'),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
                           size=(800, 600))

        notebook = IDManageNB(self, ctr)


        self.Bind(wx.EVT_CHAR_HOOK, self.OnEscapeKey)

    def OnEscapeKey(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.EndModal(wx.ID_CANCEL)
        else:
            event.Skip()
