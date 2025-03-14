#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

import os
import wx
import PSKManagement as PSK
import CertManagement
from dialogs.MsgConfirmDialog import MsgConfirmDialog


class OwnIdentityPanel(wx.Panel):
    def __init__(self, parent, log, **kwargs):
        wx.Panel.__init__(self, parent, -1, size=(800, 600))
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        psk_part = wx.StaticBoxSizer(wx.VERTICAL, self, "PSK")

        self.psk_text = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.BORDER_NONE)

        self.RefreshPSKText()

        psk_part.Add(self.psk_text, 1, border=5, flag=wx.GROW | wx.ALL)

        psk_btn_box = wx.BoxSizer(wx.HORIZONTAL)

        exportButton = wx.Button(self, label=_("Export PSK"))
        self.Bind(wx.EVT_BUTTON, self.OnPSKExportButton, exportButton)
        psk_btn_box.Add(exportButton, 0, wx.LEFT | wx.RIGHT, 5)

        importButton = wx.Button(self, label=_("Import PSK"))
        self.Bind(wx.EVT_BUTTON, self.OnPSKImportButton, importButton)
        psk_btn_box.Add(importButton, 0, wx.LEFT | wx.RIGHT, 5)

        regenButton = wx.Button(self, label=_("Regen PSK"))
        self.Bind(wx.EVT_BUTTON, self.OnPSKRegenButton, regenButton)
        psk_btn_box.Add(regenButton, 0, wx.LEFT | wx.RIGHT, 5)

        psk_part.Add(psk_btn_box, 0, border=5, flag=wx.GROW | wx.ALL)
        main_sizer.Add(psk_part, 1, border=5, flag=wx.GROW | wx.ALL)

        cert_part = wx.StaticBoxSizer(wx.VERTICAL, self, "Client Certificate")

        self.cert_text = wx.TextCtrl(self, style=wx.TE_READONLY | wx.TE_MULTILINE | wx.BORDER_NONE)

        self.RefreshCertText()

        cert_part.Add(self.cert_text, 1, border=5, flag=wx.GROW | wx.ALL)

        cert_btn_box = wx.BoxSizer(wx.HORIZONTAL)

        importClientCertButton = wx.Button(self, label=_("Import certificate"))
        self.Bind(wx.EVT_BUTTON, self.OnImportClientCertButton, importClientCertButton)
        cert_btn_box.Add(importClientCertButton, 0, wx.LEFT | wx.RIGHT, 5)

        deleteClientCertButton = wx.Button(self, label=_("Delete certificate"))
        self.Bind(wx.EVT_BUTTON, self.OnDeleteClientCertButton, deleteClientCertButton)
        cert_btn_box.Add(deleteClientCertButton, 0, wx.LEFT | wx.RIGHT, 5)

        cert_part.Add(cert_btn_box, 0, border=5, flag=wx.GROW | wx.ALL)
        main_sizer.Add(cert_part, 1, border=5, flag=wx.GROW | wx.ALL)

        self.SetSizer(main_sizer)


    ### PSK ###

    def OnPSKExportButton(self, event):
        dialog = wx.FileDialog(self, _("Export IDE PSK"),
            wildcard=_("PLCOpen files (*.psk)|*.psk|All files|*.*"),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)

        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            error = None

            if os.path.isdir(os.path.dirname(filepath)):
                try:
                    PSK.ExportIDEIdentity(filepath)
                except Exception as e:
                    error = _("Can't save PSK to file %s. Error: %s") % filepath
            else:
                error = _("\"%s\" is not a valid folder!") % os.path.dirname(filepath)

            if error:
                dlg = wx.MessageDialog(self, error, _("Error"), wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
                dlg.Destroy()

        dialog.Destroy()

    def _confirm_overwrite_identity(self):
        dialog = wx.MessageDialog(self,
            _("This will replace IDE Identity. Confirm ?"),
            _("Warning"), wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION)
        answer = dialog.ShowModal()
        dialog.Destroy()
        return answer == wx.ID_YES

    def OnPSKImportButton(self, event):
        dialog = wx.FileDialog(self, _("Choose a file"),
            wildcard=_("PSK files (*.psk)|*.psk|All files|*.*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            if self._confirm_overwrite_identity():
                PSK.ImportIDEIdentity(dialog.GetPath())
        self.RefreshPSKText()

    def OnPSKRegenButton(self, event):
        if self._confirm_overwrite_identity():
            PSK.RemoveIDEIdentity()
            self.RefreshPSKText()

    def RefreshPSKText(self):
        try:
            IDE_ID, secret = PSK.GetIDEIdentity()
            text = "Current ID: " + IDE_ID
        except Exception as e:
            text = "Failed retrieving IDE ID: " + str(e)

        self.psk_text.SetValue(text)

    ### Certificates ###

    def OnImportClientCertButton(self, event):
        dialog = wx.FileDialog(self, _("Choose a file"),
            wildcard=_("Certificate files (*.crt)|*.crt|All files|*.*"),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            if self._confirm_overwrite_identity():
                CertManagement.ImportClientCert(dialog.GetPath())
        self.RefreshCertText()

    def OnDeleteClientCertButton(self, event):
        if self._confirm_overwrite_identity():
            CertManagement.RemoveClientCert()
            self.RefreshCertText()

    def RefreshCertText(self):
        text = CertManagement.GetClientCertificateInfo()
        self.cert_text.SetValue(text)

