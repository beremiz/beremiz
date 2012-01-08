import wx
import wx.grid

from controls import CustomGrid, CustomTable, EditorPanel

[ETHERCAT_VENDOR, ETHERCAT_GROUP, ETHERCAT_DEVICE] = range(3)

def AppendMenu(parent, help, id, kind, text):
    if wx.VERSION >= (2, 6, 0):
        parent.Append(help=help, id=id, kind=kind, text=text)
    else:
        parent.Append(helpString=help, id=id, kind=kind, item=text)

[ID_SLAVETYPECHOICEDIALOG, ID_SLAVETYPECHOICEDIALOGSTATICTEXT1,
 ID_SLAVETYPECHOICEDIALOGSLAVETYPESLIBRARY
] = [wx.NewId() for _init_ctrls in range(3)]

class SlaveTypeChoiceDialog(wx.Dialog):
    
    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    
    def _init_coll_flexGridSizer1_Items(self, parent):
        parent.AddWindow(self.staticText1, 0, border=20, flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        parent.AddWindow(self.SlaveTypesLibrary, 0, border=20, flag=wx.GROW|wx.LEFT|wx.RIGHT)
        parent.AddSizer(self.ButtonSizer, 0, border=20, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
    
    def _init_coll_flexGridSizer1_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_sizers(self):
        self.flexGridSizer1 = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=10)
        
        self._init_coll_flexGridSizer1_Items(self.flexGridSizer1)
        self._init_coll_flexGridSizer1_Growables(self.flexGridSizer1)
        
        self.SetSizer(self.flexGridSizer1)

    def _init_ctrls(self, prnt):
        wx.Dialog.__init__(self, id=ID_SLAVETYPECHOICEDIALOG,
              name='SlaveTypeChoiceDialog', parent=prnt,
              size=wx.Size(600, 400), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
              title=_('Browse slave types library'))
        self.SetClientSize(wx.Size(600, 400))

        self.staticText1 = wx.StaticText(id=ID_SLAVETYPECHOICEDIALOGSTATICTEXT1,
              label=_('Choose a slave type:'), name='staticText1', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.SlaveTypesLibrary = wx.TreeCtrl(id=ID_SLAVETYPECHOICEDIALOGSLAVETYPESLIBRARY,
              name='TypeTree', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.TR_HAS_BUTTONS|wx.TR_SINGLE|wx.SUNKEN_BORDER|wx.TR_HIDE_ROOT|wx.TR_LINES_AT_ROOT)
        
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        if wx.VERSION >= (2, 5, 0):
            self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.ButtonSizer.GetAffirmativeButton().GetId())
        else:
            self.Bind(wx.EVT_BUTTON, self.OnOK, id=self.ButtonSizer.GetChildren()[0].GetSizer().GetChildren()[0].GetWindow().GetId())
        
        self._init_sizers()

    def __init__(self, parent, controler, default=None):
        self._init_ctrls(parent)
        
        slaves_types = controler.GetSlaveTypesLibrary()
        
        root = self.SlaveTypesLibrary.AddRoot("")
        self.GenerateSlaveTypesLibraryTreeBranch(root, slaves_types, default)

    def GenerateSlaveTypesLibraryTreeBranch(self, root, children, default):
        for infos in children:
            item = self.SlaveTypesLibrary.AppendItem(root, infos["name"])
            if infos["type"] == ETHERCAT_DEVICE:
                self.SlaveTypesLibrary.SetPyData(item, infos["infos"])
                if infos["infos"] == default:
                    self.SlaveTypesLibrary.SelectItem(item)
                    self.SlaveTypesLibrary.EnsureVisible(item)
            else:
                self.GenerateSlaveTypesLibraryTreeBranch(item, infos["children"], default)

    def GetType(self):
        selected = self.SlaveTypesLibrary.GetSelection()
        return self.SlaveTypesLibrary.GetPyData(selected)

    def OnOK(self, event):
        selected = self.SlaveTypesLibrary.GetSelection()
        if not selected.IsOk() or self.SlaveTypesLibrary.GetPyData(selected) is None:
            message = wx.MessageDialog(self, _("No valid slave type selected!"), _("Error"), wx.OK|wx.ICON_ERROR)
            message.ShowModal()
            message.Destroy()
        else:
            self.EndModal(wx.ID_OK)


def GetVariablesTableColnames():
    _ = lambda x : x
    return ["#", _("Index"), _("SubIndex"), _("Name"), _("Type"), _("PDO index"), _("PDO name"), _("PDO type")]

class PDOsTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            if col == 0:
                return row + 1
            colname = self.GetColLabelValue(col, False)
            value = self.data[row].get(colname, "")
            if colname == "Type":
                value = _(value)
            return value

class VariablesTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            if col == 0:
                return row + 1
            return self.data[row].get(self.GetColLabelValue(col, False), "")

[ID_SLAVEPANEL, ID_SLAVEPANELTYPELABEL,
 ID_SLAVEPANELTYPE, ID_SLAVEPANELTYPEBROWSE, 
 ID_SLAVEPANELALIASLABEL, ID_SLAVEPANELALIAS, 
 ID_SLAVEPANELPOSLABEL, ID_SLAVEPANELPOS, 
 ID_SLAVEPANELSLAVEINFOSSTATICBOX, ID_SLAVEPANELVENDORLABEL, 
 ID_SLAVEPANELVENDOR, ID_SLAVEPANELPRODUCTCODELABEL, 
 ID_SLAVEPANELPRODUCTCODE, ID_SLAVEPANELREVISIONNUMBERLABEL, 
 ID_SLAVEPANELREVISIONNUMBER, ID_SLAVEPANELPHYSICSLABEL, 
 ID_SLAVEPANELPHYSICS, ID_SLAVEPANELPDOSLABEL, 
 ID_SLAVEPANELPDOSGRID, ID_SLAVEPANELVARIABLESLABEL, 
 ID_SLAVEPANELVARIABLESGRID, 
] = [wx.NewId() for _init_ctrls in range(21)]

class SlavePanel(wx.Panel):
    
    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    
    def _init_coll_MainSizer_Items(self, parent):
        parent.AddSizer(self.PositionSizer, 0, border=5, flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        parent.AddSizer(self.SlaveInfosBoxSizer, 0, border=5, flag=wx.GROW|wx.ALIGN_RIGHT|wx.LEFT|wx.RIGHT)
    
    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_PositionSizer_Items(self, parent):
        parent.AddWindow(self.TypeLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        parent.AddSizer(self.TypeSizer, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.AliasLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        parent.AddWindow(self.Alias, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.PosLabel, 0, border=0, flag=wx.ALIGN_CENTER_VERTICAL)
        parent.AddWindow(self.Pos, 0, border=0, flag=wx.GROW)
    
    def _init_coll_PositionSizer_Growables(self, parent):
        parent.AddGrowableCol(1)
        parent.AddGrowableCol(3)
        parent.AddGrowableCol(5)
        parent.AddGrowableRow(0)
    
    def _init_coll_TypeSizer_Items(self, parent):
        parent.AddWindow(self.Type, 1, border=0, flag=0)
        parent.AddWindow(self.TypeBrowse, 0, border=0, flag=0)
    
    def _init_coll_SlaveInfosBoxSizer_Items(self, parent):
        parent.AddSizer(self.SlaveInfosSizer, 1, border=5, flag=wx.GROW|wx.ALL)
    
    def _init_coll_SlaveInfosSizer_Items(self, parent):
        parent.AddSizer(self.SlaveInfosDetailsSizer, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.VariablesLabel, 0, border=0, flag=wx.GROW)
        parent.AddWindow(self.VariablesGrid, 0, border=0, flag=wx.GROW)
        
    def _init_coll_SlaveInfosSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(2)
        
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
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        self.PositionSizer = wx.FlexGridSizer(cols=6, hgap=5, rows=1, vgap=0)
        self.TypeSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SlaveInfosBoxSizer = wx.StaticBoxSizer(self.SlaveInfosStaticBox, wx.VERTICAL)
        self.SlaveInfosSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=5)
        self.SlaveInfosDetailsSizer = wx.FlexGridSizer(cols=4, hgap=5, rows=2, vgap=5)
        
        self._init_coll_MainSizer_Growables(self.MainSizer)
        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_PositionSizer_Growables(self.PositionSizer)
        self._init_coll_PositionSizer_Items(self.PositionSizer)
        self._init_coll_TypeSizer_Items(self.TypeSizer)
        self._init_coll_SlaveInfosBoxSizer_Items(self.SlaveInfosBoxSizer)
        self._init_coll_SlaveInfosSizer_Growables(self.SlaveInfosSizer)
        self._init_coll_SlaveInfosSizer_Items(self.SlaveInfosSizer)
        self._init_coll_SlaveInfosDetailsSizer_Growables(self.SlaveInfosDetailsSizer)
        self._init_coll_SlaveInfosDetailsSizer_Items(self.SlaveInfosDetailsSizer)
        
        self.SetSizer(self.MainSizer)
    
    def _init_ctrls(self, prnt):
        wx.Panel.__init__(self, id=ID_SLAVEPANEL, name='SlavePanel', parent=prnt,
              size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        
        self.TypeLabel = wx.StaticText(id=ID_SLAVEPANELTYPELABEL,
              label=_('Type:'), name='TypeLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Type = wx.TextCtrl(id=ID_SLAVEPANELTYPE, value='',
              name='Type', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.TypeBrowse = wx.Button(id=ID_SLAVEPANELTYPEBROWSE, label='...',
              name='TypeBrowse', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(30, 24), style=0)
        self.Bind(wx.EVT_BUTTON, self.OnTypeBrowseClick, id=ID_SLAVEPANELTYPEBROWSE)
        
        self.AliasLabel = wx.StaticText(id=ID_SLAVEPANELALIASLABEL,
              label=_('Alias:'), name='AliasLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Alias = wx.SpinCtrl(id=ID_SLAVEPANELALIAS,
              name='Alias', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.SP_ARROW_KEYS, min=0, max=0xffff)
        self.Bind(wx.EVT_SPINCTRL, self.OnAliasChanged, id=ID_SLAVEPANELALIAS)
        
        self.PosLabel = wx.StaticText(id=ID_SLAVEPANELPOSLABEL,
              label=_('Position:'), name='PositionLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Pos = wx.SpinCtrl(id=ID_SLAVEPANELPOS,
              name='Pos', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.SP_ARROW_KEYS, min=0, max=0xffff)
        self.Bind(wx.EVT_SPINCTRL, self.OnPositionChanged, id=ID_SLAVEPANELPOS)
        
        self.SlaveInfosStaticBox = wx.StaticBox(id=ID_SLAVEPANELSLAVEINFOSSTATICBOX,
              label=_('Slave infos:'), name='SlaveInfosStaticBox', parent=self,
              pos=wx.Point(0, 0), size=wx.Size(0, 0), style=0)
        
        self.VendorLabel = wx.StaticText(id=ID_SLAVEPANELVENDORLABEL,
              label=_('Vendor:'), name='VendorLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Vendor = wx.TextCtrl(id=ID_SLAVEPANELVENDOR, value='',
              name='Vendor', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.ProductCodeLabel = wx.StaticText(id=ID_SLAVEPANELPRODUCTCODELABEL,
              label=_('Product code:'), name='ProductCodeLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.ProductCode = wx.TextCtrl(id=ID_SLAVEPANELPRODUCTCODE, value='',
              name='ProductCode', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.RevisionNumberLabel = wx.StaticText(id=ID_SLAVEPANELREVISIONNUMBERLABEL,
              label=_('Revision number:'), name='RevisionNumberLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.RevisionNumber = wx.TextCtrl(id=ID_SLAVEPANELREVISIONNUMBER, value='',
              name='RevisionNumber', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.PhysicsLabel = wx.StaticText(id=ID_SLAVEPANELPHYSICSLABEL,
              label=_('Physics:'), name='PhysicsLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.Physics = wx.TextCtrl(id=ID_SLAVEPANELPHYSICS, value='',
              name='Physics', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(0, 24), style=wx.TE_READONLY)
        
        self.VariablesLabel =  wx.StaticText(id=ID_SLAVEPANELVARIABLESLABEL,
              label=_('Variable entries:'), name='VariablesLabel', parent=self,
              pos=wx.Point(0, 0), size=wx.DefaultSize, style=0)
        
        self.VariablesGrid = CustomGrid(id=ID_SLAVEPANELPDOSGRID,
              name='PDOsGrid', parent=self, pos=wx.Point(0, 0), 
              size=wx.Size(0, 0), style=wx.VSCROLL)
        if wx.VERSION >= (2, 5, 0):
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnVariablesGridCellLeftClick)
        else:
            wx.grid.EVT_GRID_CELL_LEFT_CLICK(self.VariablesGrid, self.OnVariablesGridCellLeftClick)
        
        self._init_sizers()
    
    def __init__(self, parent, controler, window, slave):
        self._init_ctrls(parent)
        
        self.Controler = controler
        self.ParentWindow = window
        self.Slave = slave
        
        self.VariablesTable = VariablesTable(self, [], GetVariablesTableColnames())
        self.VariablesGrid.SetTable(self.VariablesTable)
        self.VariablesGridColAlignements = [wx.ALIGN_RIGHT, wx.ALIGN_RIGHT, wx.ALIGN_RIGHT, 
                                            wx.ALIGN_LEFT, wx.ALIGN_LEFT, wx.ALIGN_RIGHT, 
                                            wx.ALIGN_LEFT, wx.ALIGN_LEFT]
        self.VariablesGridColSizes = [40, 100, 100, 150, 150, 100, 150, 100]
        self.VariablesGrid.SetRowLabelSize(0)
        for col in range(self.VariablesTable.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(self.VariablesGridColAlignements[col], wx.ALIGN_CENTRE)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColMinimalWidth(col, self.VariablesGridColSizes[col])
            self.VariablesGrid.AutoSizeColumn(col, False)
        
        self.RefreshView()
    
    def GetSlaveTitle(self):
        type_infos = self.Controler.GetSlaveType(self.Slave)
        return "%s (%d:%d)" % (type_infos["device_type"], self.Slave[0], self.Slave[1])
    
    def GetSlave(self):
        return self.Slave
    
    def SetSlave(self, slave):
        if self.Slave != slave:
            self.Slave = slave
            self.RefreshView()

    def RefreshView(self):
        self.Alias.SetValue(self.Slave[0])
        self.Pos.SetValue(self.Slave[1])
        slave_infos = self.Controler.GetSlaveInfos(self.Slave)
        if slave_infos is not None:
            self.Type.SetValue(slave_infos["device_type"])
            self.Vendor.SetValue(slave_infos["vendor"])
            self.ProductCode.SetValue(slave_infos["product_code"])
            self.RevisionNumber.SetValue(slave_infos["revision_number"])
            self.Physics.SetValue(slave_infos["physics"])
            self.VariablesTable.SetData(slave_infos["variables"])
            self.VariablesTable.ResetView(self.VariablesGrid)
        else:
            type_infos = self.Controler.GetSlaveType(self.Slave)
            self.Type.SetValue(type_infos["device_type"])
        
    def OnAliasChanged(self, event):
        alias = self.Alias.GetValue()
        if alias != self.Slave[0]:
            result = self.Controler.SetSlavePos(self.Slave[:2], alias = alias)
            if result is not None:
                message = wx.MessageDialog(self, result, _("Error"), wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
            else:
                wx.CallAfter(self.ParentWindow.RefreshView, (alias, self.Slave[1]))
                wx.CallAfter(self.ParentWindow.RefreshParentWindow)
        event.Skip()
        
    def OnPositionChanged(self, event):
        position = self.Pos.GetValue()
        if position != self.Slave[1]:
            result = self.Controler.SetSlavePos(self.Slave, position = position)
            if result is not None:
                message = wx.MessageDialog(self, result, _("Error"), wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
            else:
                wx.CallAfter(self.ParentWindow.RefreshView, (self.Slave[0], position))
                wx.CallAfter(self.ParentWindow.RefreshParentWindow)
        event.Skip()

    def OnTypeBrowseClick(self, event):
        dialog = SlaveTypeChoiceDialog(self, self.Controler, self.Controler.GetSlaveType(self.Slave))
        if dialog.ShowModal() == wx.ID_OK:
            result = self.Controler.SetSlaveType(self.Slave, dialog.GetType())
            if result is not None:
                message = wx.MessageDialog(self, result, _("Error"), wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
            else:
                wx.CallAfter(self.RefreshView)
                wx.CallAfter(self.ParentWindow.RefreshSlaveNodesTitles)
                wx.CallAfter(self.ParentWindow.RefreshParentWindow)
        dialog.Destroy()
        event.Skip()

    def OnVariablesGridCellLeftClick(self, event):
        if event.GetCol() == 0:
            row = event.GetRow()
            data_type = self.VariablesTable.GetValueByName(row, "Type")
            var_name = self.VariablesTable.GetValueByName(row, "Name")
            entry_index = self.Controler.ExtractHexDecValue(self.VariablesTable.GetValueByName(row, "Index"))
            entry_subindex = self.VariablesTable.GetValueByName(row, "SubIndex")
            if self.VariablesTable.GetValueByName(row, "PDO type") == "Transmit":
                dir = "%I"
            else:
                dir = "%Q"
            location = "%s%s" % (dir, self.Controler.GetSizeOfType(data_type)) + \
                       ".".join(map(lambda x:str(x), self.Controler.GetCurrentLocation() + self.Slave + (entry_index, entry_subindex)))
            data = wx.TextDataObject(str((location, "location", data_type, var_name, "")))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        event.Skip()

[ID_CONFIGEDITOR, ID_CONFIGEDITORADDSLAVEBUTTON,
 ID_CONFIGEDITORDELETESLAVEBUTTON, ID_CONFIGEDITORSLAVENODES,
] = [wx.NewId() for _init_ctrls in range(4)]

class ConfigEditor(EditorPanel):
    
    ID = ID_CONFIGEDITOR
    
    def _init_coll_MainSizer_Items(self, parent):
        parent.AddSizer(self.ButtonSizer, 0, border=5, flag=wx.ALIGN_RIGHT|wx.TOP|wx.LEFT|wx.RIGHT)
        parent.AddWindow(self.SlaveNodes, 0, border=5, flag=wx.GROW|wx.BOTTOM|wx.LEFT|wx.RIGHT)

    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(1)
    
    def _init_coll_ButtonSizer_Items(self, parent):
        parent.AddWindow(self.AddSlaveButton, 0, border=5, flag=wx.RIGHT)
        parent.AddWindow(self.DeleteSlaveButton, 0, border=5, flag=0)
        
    def _init_sizers(self):
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        self.ButtonSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_MainSizer_Growables(self.MainSizer)
        self._init_coll_ButtonSizer_Items(self.ButtonSizer)
        
        self.Editor.SetSizer(self.MainSizer)
    
    def _init_Editor(self, prnt):
        self.Editor = wx.Panel(id=-1, parent=prnt, pos=wx.Point(0, 0), 
                size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
    
        self.AddSlaveButton = wx.Button(id=ID_CONFIGEDITORADDSLAVEBUTTON, label=_('Add slave'),
              name='AddSlaveButton', parent=self.Editor, pos=wx.Point(0, 0),
              size=wx.DefaultSize, style=0)
        self.Bind(wx.EVT_BUTTON, self.OnAddSlaveButtonClick, id=ID_CONFIGEDITORADDSLAVEBUTTON)
        
        self.DeleteSlaveButton = wx.Button(id=ID_CONFIGEDITORDELETESLAVEBUTTON, label=_('Delete slave'),
              name='DeleteSlaveButton', parent=self.Editor, pos=wx.Point(0, 0),
              size=wx.DefaultSize, style=0)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteSlaveButtonClick, id=ID_CONFIGEDITORDELETESLAVEBUTTON)
        
        self.SlaveNodes = wx.Notebook(id=ID_CONFIGEDITORSLAVENODES,
              name='SlaveNodes', parent=self.Editor, pos=wx.Point(0, 0),
              size=wx.Size(0, 0), style=wx.NB_LEFT)
        
        self._init_sizers()
    
    def __init__(self, parent, controler, window):
        EditorPanel.__init__(self, parent, "", window, controler)
        
        img = wx.Bitmap(self.Controler.GetIconPath("Cfile.png"), wx.BITMAP_TYPE_PNG).ConvertToImage()
        self.SetIcon(wx.BitmapFromImage(img.Rescale(16, 16)))
    
    def __del__(self):
        self.Controler.OnCloseEditor()
    
    def GetTitle(self):
        fullname = self.Controler.PlugFullName()
        if not self.Controler.ConfigIsSaved():
            return "~%s~" % fullname
        return fullname
    
    def GetBufferState(self):
        return self.Controler.GetBufferState()
        
    def Undo(self):
        self.Controler.LoadPrevious()
        self.RefreshView()
            
    def Redo(self):
        self.Controler.LoadNext()
        self.RefreshView()
    
    def RefreshView(self, slave_pos=None):
        slaves = self.Controler.GetSlaves()
        for i, slave in enumerate(slaves):
            if i < self.SlaveNodes.GetPageCount():
                panel = self.SlaveNodes.GetPage(i)
                panel.SetSlave(slave)
            else:
                panel = SlavePanel(self.SlaveNodes, self.Controler, self, slave)
                self.SlaveNodes.AddPage(panel, "")
        while self.SlaveNodes.GetPageCount() > len(slaves):
            self.SlaveNodes.RemovePage(len(slaves))
        self.RefreshSlaveNodesTitles()
        self.RefreshButtons()
        if slave_pos is not None:
            self.SelectSlave(slave_pos)
    
    def RefreshParentWindow(self):
        self.ParentWindow.RefreshTitle()
        self.ParentWindow.RefreshFileMenu()
        self.ParentWindow.RefreshEditMenu()
        self.ParentWindow.RefreshPageTitles()
    
    def RefreshSlaveNodesTitles(self):
        for idx in xrange(self.SlaveNodes.GetPageCount()):
            panel = self.SlaveNodes.GetPage(idx)
            self.SlaveNodes.SetPageText(idx, panel.GetSlaveTitle())
            
    def RefreshButtons(self):
        self.DeleteSlaveButton.Enable(self.SlaveNodes.GetPageCount() > 0)
    
    def SelectSlave(self, slave):
        for idx in xrange(self.SlaveNodes.GetPageCount()):
            panel = self.SlaveNodes.GetPage(idx)
            if panel.GetSlave() == slave:
                self.SlaveNodes.SetSelection(idx)
                return
    
    def OnAddSlaveButtonClick(self, event):
        slave = self.Controler.AddSlave()
        self.RefreshParentWindow()
        wx.CallAfter(self.RefreshView, slave)
        event.Skip()
    
    def OnDeleteSlaveButtonClick(self, event):
        selected = self.SlaveNodes.GetSelection()
        if selected != -1:
            panel = self.SlaveNodes.GetPage(selected)
            if self.Controler.RemoveSlave(panel.GetSlave()[:2]):
                self.RefreshParentWindow()
                wx.CallAfter(self.RefreshView)
            