from __future__ import absolute_import

import wx
from zope.interface import Interface, Attribute
from zope.interface.verify import verifyObject
from connectors import connectors_dialog, ConnectorDialog, GetConnectorFromURI


[ID_URIWIZARDDIALOG, ID_URITYPECHOICE] = [wx.NewId() for _init_ctrls in range(2)]


class IConnectorPanel(Interface):
    """This is interface for panel of seperate connector type"""
    uri = Attribute("""uri of connections""")
    type = Attribute("""type of connector""")

    def SetURI(uri):     # pylint: disable=no-self-argument
        """methode for set uri"""

    def GetURI():        # pylint: disable=no-self-argument
        """metohde for get uri"""


class UriLocationEditor(wx.Dialog):
    def _init_ctrls(self, parent):
        self.UriTypeChoice = wx.Choice(parent=self, id=ID_URIWIZARDDIALOG, choices=self.URITYPES)
        self.UriTypeChoice.SetSelection(0)
        self.Bind(wx.EVT_CHOICE, self.OnTypeChoice, self.UriTypeChoice)
        self.PanelSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ButtonSizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

    def _init_sizers(self):
        self.mainSizer = wx.BoxSizer(wx.VERTICAL)
        typeSizer = wx.BoxSizer(wx.HORIZONTAL)
        typeSizer.Add(wx.StaticText(self, wx.ID_ANY, _("URI type:")), border=5, flag=wx.ALIGN_CENTER_VERTICAL | wx.ALL)
        typeSizer.Add(self.UriTypeChoice, border=5, flag=wx.ALL)
        self.mainSizer.Add(typeSizer)

        self.mainSizer.Add(self.PanelSizer, border=5, flag=wx.ALL)
        self.mainSizer.Add(self.ButtonSizer, border=5, flag=wx.BOTTOM | wx.ALIGN_CENTER_HORIZONTAL)
        self.SetSizer(self.mainSizer)
        self.Layout()
        self.Fit()

    def __init__(self, parent, uri):
        wx.Dialog.__init__(self, id=ID_URIWIZARDDIALOG,
                           name='UriLocationEditor', parent=parent,
                           title='Uri location')
        self.URITYPES = [_("- Select URI type -")]
        for connector_type, connector_function in connectors_dialog.iteritems():
            try:
                connector_function['function']()
                self.URITYPES.append(connector_type)
            except Exception:
                pass

        self.selected = None
        self.parrent = parent
        self.logger = self.parrent.CTR.logger
        self._init_ctrls(parent)
        self._init_sizers()
        self.SetURI(uri)
        self.CenterOnParent()

    def OnTypeChoice(self, event):
        self._removePanelType()
        index = event.GetSelection()
        if index > 0:
            self.selected = event.GetString()
            self.panelType = self._getConnectorDialog(self.selected)
            if self.panelType:
                self.PanelSizer.Add(self.panelType)
                self.mainSizer.Layout()
                self.Fit()
                self.panelType.Refresh()

    def SetURI(self, uri):
        self._removePanelType()
        uri_list = uri.strip().split(":")
        if uri_list:
            uri_type = uri_list[0].upper()
            type = GetConnectorFromURI(uri_type)
            if type:
                self.selected = type
                self.UriTypeChoice.SetStringSelection(self.selected)
                self.panelType = self._getConnectorDialog(self.selected)
                if self.panelType:
                    self.panelType.SetURI(uri)
                    self.PanelSizer.Add(self.panelType)
                    self.PanelSizer.Layout()
                    self.mainSizer.Layout()
                    self.Fit()
                    self.panelType.Refresh()

    def GetURI(self):
        if not self.selected or not self.panelType:
            return ""
        else:
            return self.panelType.GetURI()

    def _removePanelType(self):
        for i in range(self.PanelSizer.GetItemCount()):
            item = self.PanelSizer.GetItem(i)
            item.DeleteWindows()
            self.PanelSizer.Remove(i)
            self.Fit()
        self.PanelSizer.Layout()

    def _getConnectorDialog(self, connectorType):
        connector = ConnectorDialog(connectorType, self)
        if connector and IConnectorPanel.providedBy(connector):
            if verifyObject(IConnectorPanel, connector):
                return connector
        else:
            return None
