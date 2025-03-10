#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.


from operator import eq
import wx
import wx.dataview as dv
from CertManagement import *
from dialogs.MsgConfirmDialog import MsgConfirmDialog


class CertBrowserModel(dv.DataViewIndexListModel):
    def __init__(self, columncount, log):
        self.columncount = columncount
        self.log = log
        self.data = GetData(log)
        dv.DataViewIndexListModel.__init__(self, len(self.data))

    def _saveData(self):
        SaveData(self.data)

    def GetColumnType(self, col):
        return "string"

    def GetValueByRow(self, row, col):
        return self.data[row][col]

    def SetValueByRow(self, value, row, col):
        self.data[row][col] = value
        self._saveData()

    def GetColumnCount(self):
        return len(self.data[0]) if self.data else self.columncount

    def GetCount(self):
        return len(self.data)

    def DeleteRows(self, rows):
        rows = list(rows)
        rows.sort(reverse=True)

        for row in rows:
            DeleteCert(self.data[row][COL_CN])
            del self.data[row]
            self.RowDeleted(row)
        self._saveData()

    def AddRow(self, value):
        self.data.append(value)
        self.RowAppended()
        self._saveData()

    def Import(self, filepath, sircb):
        res = False
        res = ImportCert(filepath, self.log, sircb)
        if res: 
            self.data = GetData(self.log)
            self.Reset(len(self.data))


colflags = dv.DATAVIEW_COL_RESIZABLE | dv.DATAVIEW_COL_SORTABLE


class CertBrowser(wx.Panel):
    def __init__(self, parent, log, **kwargs):
        wx.Panel.__init__(self, parent, -1, size=(800, 600))

        dvStyle = wx.BORDER_THEME | dv.DV_ROW_LINES | dv.DV_MULTIPLE
        self.dvc = dv.DataViewCtrl(self, style=dvStyle)

        def args(*a, **k):
            return (a, k)

        ColumnsDesc = [
            args(_("Cert"), COL_CN, width=70),
            args(_("Description"), COL_DESC, width=300,
                 mode=dv.DATAVIEW_CELL_EDITABLE),
            args(_("Last connection"), COL_LAST, width=120),
        ]

        self.model = CertBrowserModel(len(ColumnsDesc), log)
        self.dvc.AssociateModel(self.model)

        col_list = []
        for a, k in ColumnsDesc:
            col_list.append(
                self.dvc.AppendTextColumn(*a, **dict(k, flags=colflags)))
        col_list[COL_LAST].SetSortOrder(False)

        # TODO : sort by last visit by default

        self.Sizer = wx.BoxSizer(wx.VERTICAL)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)

        btnbox = wx.BoxSizer(wx.HORIZONTAL)

        # deletion of secret and metadata
        deleteButton = wx.Button(self, label=_("Delete certificates"))
        self.Bind(wx.EVT_BUTTON, self.OnDeleteButton, deleteButton)
        btnbox.Add(deleteButton, 0, wx.LEFT | wx.RIGHT, 5)

        # import with a merge -> duplicates are asked for
        importButton = wx.Button(self, label=_("Import certificate"))
        self.Bind(wx.EVT_BUTTON, self.OnImportButton, importButton)
        btnbox.Add(importButton, 0, wx.LEFT | wx.RIGHT, 5)

        self.Sizer.Add(btnbox, 0, wx.TOP | wx.BOTTOM, 5)

    def OnDeleteButton(self, evt):
        items = self.dvc.GetSelections()
        rows = [self.model.GetRow(item) for item in items]

        # Ask if user really wants to delete
        if wx.MessageBox(_('Are you sure to delete selected certificates?'),
                         _('Delete certificates'),
                         wx.YES_NO | wx.CENTRE | wx.NO_DEFAULT) != wx.YES:
            return

        self.model.DeleteRows(rows)

    def ShouldIReplaceCallback(self, existing):
        CN, DESC, LAST = existing
        dlg = MsgConfirmDialog(
            self,
            _("Certificate import"),
            (_("Replace certificate for server named {CN}?") + "\n\n" +
             _("Description:") + " {DESC}\n    " +
             _("Last connection:") + " {LAST}\n\n").format(**locals()),
            None,
            [_("Replace"), _("Keep"), _("Cancel")])

        answer = dlg.ShowModal()  # return value ignored as we have "Ok" only anyhow
        if answer == wx.ID_CANCEL:
            return CANCEL

        if dlg.OptionChecked():
            if answer == wx.ID_YES:
                return REPLACE_ALL
            return KEEP_ALL
        else:
            if answer == wx.ID_YES:
                return REPLACE
            return KEEP

    def OnImportButton(self, evt):
        dialog = wx.FileDialog(self, _("Choose a file"),
                               wildcard=_("Cert files (*.crt)|*.crt|All files|*.*"),
                               style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dialog.ShowModal() == wx.ID_OK:
            self.model.Import(dialog.GetPath(),
                              self.ShouldIReplaceCallback)

