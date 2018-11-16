from __future__ import absolute_import

import wx
from connectors import ConnectorSchemes, EditorClassFromScheme
from controls.DiscoveryPanel import DiscoveryPanel
from controls.IDBrowser import IDBrowser

class IDManager(wx.Dialog):
    def __init__(self, parent, ctr):
        self.ctr = ctr
        wx.Dialog.__init__(self,
                           name='IDManager', parent=parent,
                           title=_('URI Editor'),
                           style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        # start IDBrowser in manager mode
        self.browser = IDBrowser(self, ctr)


