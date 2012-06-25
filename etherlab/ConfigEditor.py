import wx
import wx.grid
import wx.gizmos

from controls import CustomGrid, CustomTable
from ConfTreeNodeEditor import ConfTreeNodeEditor, SCROLLBAR_UNIT

[ETHERCAT_VENDOR, ETHERCAT_GROUP, ETHERCAT_DEVICE] = range(3)

def AppendMenu(parent, help, id, kind, text):
    if wx.VERSION >= (2, 6, 0):
        parent.Append(help=help, id=id, kind=kind, text=text)
    else:
        parent.Append(helpString=help, id=id, kind=kind, item=text)

def GetSyncManagersTableColnames():
    _ = lambda x : x
    return ["#", _("Name"), _("Start Address"), _("Default Size"), _("Control Byte"), _("Enable")]

class SyncManagersTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            if col == 0:
                return row
            return self.data[row].get(self.GetColLabelValue(col, False), "")

def GetVariablesTableColnames():
    _ = lambda x : x
    return ["#", _("Name"), _("Index"), _("SubIndex"), _("Type"), _("PDO index"), _("PDO name"), _("PDO type")]

[ID_NODEEDITOR, ID_NODEEDITORVENDORLABEL, 
 ID_NODEEDITORVENDOR, ID_NODEEDITORPRODUCTCODELABEL, 
 ID_NODEEDITORPRODUCTCODE, ID_NODEEDITORREVISIONNUMBERLABEL, 
 ID_NODEEDITORREVISIONNUMBER, ID_NODEEDITORPHYSICSLABEL, 
 ID_NODEEDITORPHYSICS, ID_NODEEDITORSYNCMANAGERSLABEL, 
 ID_NODEEDITORSYNCMANAGERSGRID, ID_NODEEDITORVARIABLESLABEL, 
 ID_NODEEDITORVARIABLESGRID, 
] = [wx.NewId() for _init_ctrls in range(13)]

class NodeEditor(ConfTreeNodeEditor):
    
    ID = ID_NODEEDITOR
    
    def _init_coll_MainSizer_Items(self, parent):
        parent.AddSizer(self.SlaveInfosDetailsSizer, 0, border=5, flag=wx.TOP|wx.LEFT|wx.RIGHT|wx.GROW)
        parent.AddWindow(self.SyncManagersLabel, 0, border=5, flag=wx.LEFT|wx.RIGHT|wx.GROW)
        parent.AddWindow(self.SyncManagersGrid, 0, border=5, flag=wx.LEFT|wx.RIGHT|wx.GROW)
        parent.AddWindow(self.VariablesLabel, 0, border=5, flag=wx.LEFT|wx.RIGHT|wx.GROW)
        parent.AddWindow(self.VariablesGrid, 0, border=5, flag=wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.GROW)
        
    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(2, 1)
        parent.AddGrowableRow(4, 2)
        
    def _init_coll_SlaveInfosDetailsSizer_Items(self, parent):
        parent.AddWindow(self.VendorLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL|wx.GROW)
        parent.AddWindow(self.Vendor, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.ProductCodeLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL|wx.GROW)
        parent.AddWindow(self.ProductCode, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.RevisionNumberLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL|wx.GROW)
        parent.AddWindow(self.RevisionNumber, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.PhysicsLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL|wx.GROW)
        parent.AddWindow(self.Physics, 0, border=0, flag=wx.GROW)
        
    def _init_coll_SlaveInfosDetailsSizer_Growables(self, parent):
        parent.AddGrowableCol(1)
        parent.AddGrowableCol(3)
    
    def _init_sizers(self):
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=5, vgap=5)
        self.SlaveInfosDetailsSizer = wx.FlexGridSizer(cols=4, hgap=5, rows=2, vgap=5)
        
        self._init_coll_MainSizer_Growables(self.MainSizer)
        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_SlaveInfosDetailsSizer_Growables(self.SlaveInfosDetailsSizer)
        self._init_coll_SlaveInfosDetailsSizer_Items(self.SlaveInfosDetailsSizer)
        
        self.ConfNodeEditor.SetSizer(self.MainSizer)

    def _init_ConfNodeEditor(self, prnt):
        self.ConfNodeEditor = wx.ScrolledWindow(id=-1, name='SlavePanel', parent=prnt,
              size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER|wx.HSCROLL|wx.VSCROLL)
        self.ConfNodeEditor.Bind(wx.EVT_SIZE, self.OnConfNodeEditorResize)
        
        self.VendorLabel = wx.StaticText(id=ID_NODEEDITORVENDORLABEL,
              label=_('Vendor:'), name='VendorLabel', parent=self.ConfNodeEditor,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Vendor = wx.TextCtrl(id=ID_NODEEDITORVENDOR, value='',
              name='Vendor', parent=self.ConfNodeEditor, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.ProductCodeLabel = wx.StaticText(id=ID_NODEEDITORPRODUCTCODELABEL,
              label=_('Product code:'), name='ProductCodeLabel', parent=self.ConfNodeEditor,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.ProductCode = wx.TextCtrl(id=ID_NODEEDITORPRODUCTCODE, value='',
              name='ProductCode', parent=self.ConfNodeEditor, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.RevisionNumberLabel = wx.StaticText(id=ID_NODEEDITORREVISIONNUMBERLABEL,
              label=_('Revision number:'), name='RevisionNumberLabel', parent=self.ConfNodeEditor,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.RevisionNumber = wx.TextCtrl(id=ID_NODEEDITORREVISIONNUMBER, value='',
              name='RevisionNumber', parent=self.ConfNodeEditor, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.PhysicsLabel = wx.StaticText(id=ID_NODEEDITORPHYSICSLABEL,
              label=_('Physics:'), name='PhysicsLabel', parent=self.ConfNodeEditor,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Physics = wx.TextCtrl(id=ID_NODEEDITORPHYSICS, value='',
              name='Physics', parent=self.ConfNodeEditor, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.SyncManagersLabel =  wx.StaticText(id=ID_NODEEDITORSYNCMANAGERSLABEL,
              label=_('Sync managers:'), name='SyncManagersLabel', parent=self.ConfNodeEditor,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.SyncManagersGrid = CustomGrid(id=ID_NODEEDITORSYNCMANAGERSGRID,
              name='SyncManagersGrid', parent=self.ConfNodeEditor, pos=wx.Point(0, 0), 
              size=wx.Size(0, 200), style=wx.VSCROLL)
        
        self.VariablesLabel =  wx.StaticText(id=ID_NODEEDITORVARIABLESLABEL,
              label=_('Variable entries:'), name='VariablesLabel', parent=self.ConfNodeEditor,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.VariablesGrid = wx.gizmos.TreeListCtrl(id=ID_NODEEDITORVARIABLESGRID,
              name='VariablesGrid', parent=self.ConfNodeEditor, pos=wx.Point(0, 0), 
              size=wx.Size(0, 400), style=wx.TR_DEFAULT_STYLE |
                                          wx.TR_ROW_LINES |
                                          wx.TR_COLUMN_LINES |
                                          wx.TR_HIDE_ROOT |
                                          wx.TR_FULL_ROW_HIGHLIGHT)
        self.VariablesGrid.GetMainWindow().Bind(wx.EVT_LEFT_DOWN, self.OnVariablesGridLeftClick)
                
        self._init_sizers()
    
    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
    
        self.SyncManagersTable = SyncManagersTable(self, [], GetSyncManagersTableColnames())
        self.SyncManagersGrid.SetTable(self.SyncManagersTable)
        self.SyncManagersGridColAlignements = [wx.ALIGN_RIGHT, wx.ALIGN_LEFT, wx.ALIGN_RIGHT, 
                                               wx.ALIGN_RIGHT, wx.ALIGN_RIGHT, wx.ALIGN_RIGHT]
        self.SyncManagersGridColSizes = [40, 150, 100, 100, 100, 100]
        self.SyncManagersGrid.SetRowLabelSize(0)
        for col in range(self.SyncManagersTable.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(self.SyncManagersGridColAlignements[col], wx.ALIGN_CENTRE)
            self.SyncManagersGrid.SetColAttr(col, attr)
            self.SyncManagersGrid.SetColMinimalWidth(col, self.SyncManagersGridColSizes[col])
            self.SyncManagersGrid.AutoSizeColumn(col, False)
        
        for colname, colsize, colalign in zip(GetVariablesTableColnames(),
                                              [40, 150, 100, 100, 150, 100, 150, 100],
                                              [wx.ALIGN_RIGHT, wx.ALIGN_LEFT, wx.ALIGN_RIGHT, 
                                               wx.ALIGN_RIGHT, wx.ALIGN_LEFT, wx.ALIGN_RIGHT, 
                                               wx.ALIGN_LEFT, wx.ALIGN_LEFT]):
            self.VariablesGrid.AddColumn(colname, colsize, colalign)
        self.VariablesGrid.SetMainColumn(1)
    
    def GetBufferState(self):
        return False, False
        
    def RefreshView(self):
        ConfTreeNodeEditor.RefreshView(self)
    
        self.RefreshSlaveInfos()
        
    def RefreshSlaveInfos(self):
        slave_infos = self.Controler.GetSlaveInfos()
        if slave_infos is not None:
            self.Vendor.SetValue(slave_infos["vendor"])
            self.ProductCode.SetValue(slave_infos["product_code"])
            self.RevisionNumber.SetValue(slave_infos["revision_number"])
            self.Physics.SetValue(slave_infos["physics"])
            self.SyncManagersTable.SetData(slave_infos["sync_managers"])
            self.SyncManagersTable.ResetView(self.SyncManagersGrid)
            self.RefreshVariablesGrid(slave_infos["entries"])
        else:
            self.Vendor.SetValue("")
            self.ProductCode.SetValue("")
            self.RevisionNumber.SetValue("")
            self.Physics.SetValue("")
            self.SyncManagersTable.SetData([])
            self.SyncManagersTable.ResetView(self.SyncManagersGrid)
            self.RefreshVariablesGrid([])
    
    def RefreshVariablesGrid(self, entries):
        root = self.VariablesGrid.GetRootItem()
        if not root.IsOk():
            root = self.VariablesGrid.AddRoot("Slave entries")
        self.GenerateVariablesGridBranch(root, entries, GetVariablesTableColnames())
        self.VariablesGrid.Expand(root)
        
    def GenerateVariablesGridBranch(self, root, entries, colnames, idx=0):
        if wx.VERSION >= (2, 6, 0):
            item, root_cookie = self.VariablesGrid.GetFirstChild(root)
        else:
            item, root_cookie = self.VariablesGrid.GetFirstChild(root, 0)
        
        no_more_items = not item.IsOk()
        for entry in entries:
            idx += 1
            if no_more_items:
                item = self.VariablesGrid.AppendItem(root, "")
            for col, colname in enumerate(colnames):
                if col == 0:
                    self.VariablesGrid.SetItemText(item, str(idx), 0)
                else:
                    self.VariablesGrid.SetItemText(item, entry.get(colname, ""), col)
            if entry["PDOMapping"] == "":
                self.VariablesGrid.SetItemBackgroundColour(item, wx.LIGHT_GREY)
            self.VariablesGrid.SetItemPyData(item, entry)
            idx = self.GenerateVariablesGridBranch(item, entry["children"], colnames, idx)
            if not no_more_items:
                item, root_cookie = self.VariablesGrid.GetNextChild(root, root_cookie)
                no_more_items = not item.IsOk()
        
        if not no_more_items:
            to_delete = []
            while item.IsOk():
                to_delete.append(item)
                item, root_cookie = self.VariablesGrid.GetNextChild(root, root_cookie)
            for item in to_delete:
                self.VariablesGrid.Delete(item)
        
        return idx

    def OnVariablesGridLeftClick(self, event):
        item, flags, col = self.VariablesGrid.HitTest(event.GetPosition())
        if item.IsOk():
            entry = self.VariablesGrid.GetItemPyData(item)
            data_type = entry.get("Type", "")
            pdo_mapping = entry.get("PDOMapping", "")
            
            if (col == -1 and pdo_mapping != "" and
                self.Controler.GetSizeOfType(data_type) is not None):
                
                entry_index = self.Controler.ExtractHexDecValue(entry.get("Index", "0"))
                entry_subindex = self.Controler.ExtractHexDecValue(entry.get("SubIndex", "0"))
                var_name = "%s_%4.4x_%2.2x" % (self.Controler.CTNName(), entry_index, entry_subindex)
                if pdo_mapping == "R":
                    dir = "%I"
                else:
                    dir = "%Q"
                location = "%s%s" % (dir, self.Controler.GetSizeOfType(data_type)) + \
                           ".".join(map(lambda x:str(x), self.Controler.GetCurrentLocation() + (self.Controler.GetSlavePos(), entry_index, entry_subindex)))
                
                data = wx.TextDataObject(str((location, "location", data_type, var_name, "")))
                dragSource = wx.DropSource(self.VariablesGrid)
                dragSource.SetData(data)
                dragSource.DoDragDrop()
            
        event.Skip()

    def OnConfNodeEditorResize(self, event):
        self.ConfNodeEditor.GetBestSize()
        xstart, ystart = self.ConfNodeEditor.GetViewStart()
        window_size = self.ConfNodeEditor.GetClientSize()
        maxx, maxy = self.ConfNodeEditor.GetMinSize()
        posx = max(0, min(xstart, (maxx - window_size[0]) / SCROLLBAR_UNIT))
        posy = max(0, min(ystart, (maxy - window_size[1]) / SCROLLBAR_UNIT))
        self.ConfNodeEditor.Scroll(posx, posy)
        self.ConfNodeEditor.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                maxx / SCROLLBAR_UNIT, maxy / SCROLLBAR_UNIT, posx, posy)
        event.Skip()

CIA402NodeEditor = NodeEditor
