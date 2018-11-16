#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from __future__ import absolute_import
import os
import wx
import wx.dataview as dv
import json

def _GetInitialData(psk_path):
    # [(ID, Desc, LastKnownURI, LastConnect)
    data = []

    data_path = os.path.join(psk_path, 'management.json')

    if os.path.isdir(psk_path):
        # load known keys metadata
        # {ID:(Desc, LastKnownURI, LastConnect)}
        recovered_data = json.loads(open(data_path).read()) \
                         if os.path.exists(data_path) else {}

        # go through all secret files available an build data
        # out of data recoverd from json and list of secret.
        # this implicitly filters IDs out of metadata who's
        # secret is missing
        psk_files = os.listdir(psk_path)
        for filename in psk_files:
           if filename.endswith('.secret'):
               ID = filename[:-7]  # strip filename extension
               meta = recovered_data.get(ID, 
                   ['', # default description
                    None, # last known URI
                    None])  # last connection date
                   
               data.append([ID]+meta)
    return data

def _DeleteID(psk_path, ID):
    secret_path = os.path.join(psk_path, ID+'.secret')
    os.remove(secret_path)

def _SaveData(psk_path, data):
    if not os.path.isdir(psk_path):
        os.mkdir(psk_path)
    data_path = os.path.join(psk_path, 'management.json')
    to_store = {row[0]:row[1:] for row in data}
    with open(data_path, 'w') as f:
        f.write(json.dumps(to_store))

class IDBrowserModel(dv.PyDataViewIndexListModel):
    def __init__(self, psk_path, columncount):
        self.psk_path = psk_path
        self.columncount = columncount
        self.data = _GetInitialData(psk_path)
        dv.PyDataViewIndexListModel.__init__(self, len(self.data))

    def _saveData(self):
        _SaveData(self.psk_path, self.data)

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
    
    def GetAttrByRow(self, row, col, attr):
        if col == 3:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False


    def Compare(self, item1, item2, col, ascending):
        if not ascending: # swap sort order?
            item2, item1 = item1, item2
        row1 = self.GetRow(item1)
        row2 = self.GetRow(item2)
        if col == 0:
            return cmp(int(self.data[row1][col]), int(self.data[row2][col]))
        else:
            return cmp(self.data[row1][col], self.data[row2][col])

    def DeleteRows(self, rows):
        rows = list(rows)
        rows.sort(reverse=True)
        
        for row in rows:
            del self.data[row]
            _DeleteID(self.psk_path, ID)
            self.RowDeleted(row)
        self._saveData()
            
    def AddRow(self, value):
        self.data.append(value)
        self.RowAppended()
        self._saveData()

colflags = dv.DATAVIEW_COL_RESIZABLE|dv.DATAVIEW_COL_SORTABLE
COL_ID,COL_URI,COL_DESC,COL_LAST = range(4)

class IDBrowser(wx.Panel):
    def __init__(self, parent, ctr, SelectURICallBack=None, SelectIDCallBack=None, **kwargs):
        wx.Panel.__init__(self, parent, -1, size=(400,200))

        self.isManager = SelectURICallBack is None and SelectIDCallBack is None 
        self.SelectURICallBack = SelectURICallBack
        self.SelectIDCallBack = SelectIDCallBack

        dvStyle = wx.BORDER_THEME | dv.DV_ROW_LINES
        if self.isManager :
            # no multiple selection in selector mode
            dvStyle |= dv.DV_MULTIPLE
        self.dvc = dv.DataViewCtrl(self, style = dvStyle)
                    
        args = lambda *a,**k:(a,k)

        ColumnsDesc = [
            args(_("ID"), COL_ID, width = 100),
            args(_("Last URI"), COL_URI, width = 80),
            args(_("Description"), COL_DESC, width = 200, 
                mode = dv.DATAVIEW_CELL_EDITABLE 
                       if self.isManager 
                       else dv.DATAVIEW_CELL_INERT),
            args(_("Last connection"),  COL_LAST, width = 100),
        ]

        self.model = IDBrowserModel(
            os.path.join(str(ctr.ProjectPath), 'psk'),
            len(ColumnsDesc))
        self.dvc.AssociateModel(self.model)

        for a,k in ColumnsDesc:
            self.dvc.AppendTextColumn(*a,**dict(k, flags = colflags))

        # TODO : when select,
        #  - update ID field of scheme editor
        #  - enable use URI button

        self.Sizer = wx.BoxSizer(wx.VERTICAL) 
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)

        btnbox = wx.BoxSizer(wx.HORIZONTAL)
        if self.isManager :

            # deletion of secret and metadata
            deleteButton = wx.Button(self, label=_("Delete ID"))
            self.Bind(wx.EVT_BUTTON, self.OnDeleteButton, deleteButton)
            btnbox.Add(deleteButton, 0, wx.LEFT|wx.RIGHT, 5)

            # export all
            exportButton = wx.Button(self, label=_("Export all"))
            self.Bind(wx.EVT_BUTTON, self.OnExportButton, exportButton)
            btnbox.Add(exportButton, 0, wx.LEFT|wx.RIGHT, 5)

            # import with a merge -> duplicates are asked for
            importButton = wx.Button(self, label=_("Import"))
            self.Bind(wx.EVT_BUTTON, self.OnImportButton, importButton)
            btnbox.Add(importButton, 0, wx.LEFT|wx.RIGHT, 5)

        else :
            # selector mode
            # use last known URI button
            # TODO : disable use URI button until something selected
            self.useURIButton = wx.Button(self, label=_("Use last URI"))
            self.Bind(wx.EVT_BUTTON, self.OnUseURIButton, self.useURIButton)
            self.useURIButton.Disable()
            btnbox.Add(self.useURIButton, 0, wx.LEFT|wx.RIGHT, 5)

        self.Sizer.Add(btnbox, 0, wx.TOP|wx.BOTTOM, 5)
        self.Bind(dv.EVT_DATAVIEW_SELECTION_CHANGED, self.OnSelectionChanged, self.dvc)


    def OnDeleteButton(self, evt):
        items = self.dvc.GetSelections()
        rows = [self.model.GetRow(item) for item in items]

        # Ask if user really wants to delete
        if wx.MessageBox(_('Are you sure to delete selected IDs?'),
                         _('Delete IDs'),
                             wx.YES_NO | wx.CENTRE | wx.NO_DEFAULT) != wx.YES:
            return

        self.model.DeleteRows(rows)

    def OnSelectionChanged(self, evt):
        if not self.isManager :
            items = self.dvc.GetSelections()
            somethingSelected = len(items) > 0
            self.useURIButton.Enable(somethingSelected)
            if somethingSelected:
                row = self.model.GetRow(items[0])
                ID = self.model.GetValueByRow(row, COL_ID)
                self.SelectIDCallBack(ID)


    def OnUseURIButton(self, evt):
        row = self.model.GetRow(self.dvc.GetSelections()[0])
        URI = self.model.GetValueByRow(row, COL_URI)
        if URI:
            self.SelectURICallBack(URI)

    def OnExportButton(self, evt):
        # TODO 
        wx.MessageBox(_('?'),
                      _('Mhe'),
                      wx.YES_NO | wx.CENTRE | wx.NO_DEFAULT)

    def OnImportButton(self, evt):
        # TODO 
        wx.MessageBox(_('?'),
                      _('Mhe'),
                      wx.YES_NO | wx.CENTRE | wx.NO_DEFAULT)

