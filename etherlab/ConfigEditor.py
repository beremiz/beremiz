import os

import wx
import wx.grid
import wx.gizmos
import wx.lib.buttons

from controls import CustomGrid, CustomTable, FolderTree
from editors.ConfTreeNodeEditor import ConfTreeNodeEditor, SCROLLBAR_UNIT
from util.BitmapLibrary import GetBitmap

[ETHERCAT_VENDOR, ETHERCAT_GROUP, ETHERCAT_DEVICE] = range(3)

def AppendMenu(parent, help, id, kind, text):
    if wx.VERSION >= (2, 6, 0):
        parent.Append(help=help, id=id, kind=kind, text=text)
    else:
        parent.Append(helpString=help, id=id, kind=kind, item=text)

def GetVariablesTableColnames():
    _ = lambda x : x
    return ["#", _("Name"), _("Index"), _("SubIndex"), _("Type"), _("Access")]

ACCESS_TYPES = {
    'ro': 'R',
    'wo': 'W',
    'rw': 'R/W'}

def GetAccessValue(access, pdo_mapping):
    value = ACCESS_TYPES.get(access)
    if pdo_mapping != "":
        value += "/P"
    return value

class NodeEditor(ConfTreeNodeEditor):
    
    CONFNODEEDITOR_TABS = [
        (_("Ethercat node"), "_create_EthercatNodeEditor")]
    
    def _create_EthercatNodeEditor(self, prnt):
        self.EthercatNodeEditor = wx.Panel(prnt, style=wx.TAB_TRAVERSAL)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        
        variables_label = wx.StaticText(self.EthercatNodeEditor,
              label=_('Variable entries:'))
        main_sizer.AddWindow(variables_label, border=10, flag=wx.TOP|wx.LEFT|wx.RIGHT)
        
        self.VariablesGrid = wx.gizmos.TreeListCtrl(self.EthercatNodeEditor,
              style=wx.TR_DEFAULT_STYLE |
                    wx.TR_ROW_LINES |
                    wx.TR_COLUMN_LINES |
                    wx.TR_HIDE_ROOT |
                    wx.TR_FULL_ROW_HIGHLIGHT)
        self.VariablesGrid.GetMainWindow().Bind(wx.EVT_LEFT_DOWN, 
            self.OnVariablesGridLeftClick)
        main_sizer.AddWindow(self.VariablesGrid, border=10, 
            flag=wx.GROW|wx.BOTTOM|wx.LEFT|wx.RIGHT)
                
        self.EthercatNodeEditor.SetSizer(main_sizer)

        return self.EthercatNodeEditor
    
    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
    
        for colname, colsize, colalign in zip(GetVariablesTableColnames(),
                                              [40, 150, 100, 100, 150, 100],
                                              [wx.ALIGN_RIGHT, wx.ALIGN_LEFT, wx.ALIGN_RIGHT, 
                                               wx.ALIGN_RIGHT, wx.ALIGN_LEFT, wx.ALIGN_LEFT]):
            self.VariablesGrid.AddColumn(_(colname), colsize, colalign)
        self.VariablesGrid.SetMainColumn(1)
    
    def GetBufferState(self):
        return False, False
        
    def RefreshView(self):
        ConfTreeNodeEditor.RefreshView(self)
    
        self.RefreshSlaveInfos()
        
    def RefreshSlaveInfos(self):
        slave_infos = self.Controler.GetSlaveInfos()
        if slave_infos is not None:
            self.RefreshVariablesGrid(slave_infos["entries"])
        else:
            self.RefreshVariablesGrid([])
    
    def RefreshVariablesGrid(self, entries):
        root = self.VariablesGrid.GetRootItem()
        if not root.IsOk():
            root = self.VariablesGrid.AddRoot("Slave entries")
        self.GenerateVariablesGridBranch(root, entries, GetVariablesTableColnames())
        self.VariablesGrid.Expand(root)
        
    def GenerateVariablesGridBranch(self, root, entries, colnames, idx=0):
        item, root_cookie = self.VariablesGrid.GetFirstChild(root)
        
        no_more_items = not item.IsOk()
        for entry in entries:
            idx += 1
            if no_more_items:
                item = self.VariablesGrid.AppendItem(root, "")
            for col, colname in enumerate(colnames):
                if col == 0:
                    self.VariablesGrid.SetItemText(item, str(idx), 0)
                else:
                    value = entry.get(colname, "")
                    if colname == "Access":
                        value = GetAccessValue(value, entry.get("PDOMapping", ""))
                    self.VariablesGrid.SetItemText(item, value, col)
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
                return
            
        event.Skip()

CIA402NodeEditor = NodeEditor


def GetModulesTableColnames():
    _ = lambda x : x
    return [_("Name"), _("PDO alignment (bits)")]

class LibraryEditorPanel(wx.ScrolledWindow):
    
    def __init__(self, parent, module_library, buttons):
        wx.ScrolledWindow.__init__(self, parent,
            style=wx.TAB_TRAVERSAL|wx.HSCROLL|wx.VSCROLL)
        self.Bind(wx.EVT_SIZE, self.OnResize)
        
        self.ModuleLibrary = module_library
    
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=4, vgap=5)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(1)
        main_sizer.AddGrowableRow(3)
        
        ESI_files_label = wx.StaticText(self, 
            label=_("ESI Files:"))
        main_sizer.AddWindow(ESI_files_label, border=10, 
            flag=wx.TOP|wx.LEFT|wx.RIGHT)
        
        folder_tree_sizer = wx.FlexGridSizer(cols=2, hgap=5, rows=1, vgap=0)
        folder_tree_sizer.AddGrowableCol(0)
        folder_tree_sizer.AddGrowableRow(0)
        main_sizer.AddSizer(folder_tree_sizer, border=10, 
            flag=wx.GROW|wx.LEFT|wx.RIGHT)
        
        self.ESIFiles = FolderTree(self, self.GetPath(), editable=False)
        self.ESIFiles.SetFilter(".xml")
        self.ESIFiles.SetMinSize(wx.Size(600, 300))
        folder_tree_sizer.AddWindow(self.ESIFiles, flag=wx.GROW)
        
        buttons_sizer = wx.BoxSizer(wx.VERTICAL)
        folder_tree_sizer.AddSizer(buttons_sizer, 
            flag=wx.ALIGN_CENTER_VERTICAL)
        
        for idx, (name, bitmap, help, callback) in enumerate(buttons):
            button = wx.lib.buttons.GenBitmapButton(self, 
                  bitmap=GetBitmap(bitmap), 
                  size=wx.Size(28, 28), style=wx.NO_BORDER)
            button.SetToolTipString(help)
            setattr(self, name, button)
            if idx > 0:
                flag = wx.TOP
            else:
                flag = 0
            if callback is None:
                callback = getattr(self, "On" + name, None)
            if callback is not None:
                self.Bind(wx.EVT_BUTTON, callback, button)
            buttons_sizer.AddWindow(button, border=10, flag=flag)
        
        modules_label = wx.StaticText(self, 
            label=_("Modules library:"))
        main_sizer.AddSizer(modules_label, border=10, 
            flag=wx.LEFT|wx.RIGHT)
        
        self.ModulesGrid = wx.gizmos.TreeListCtrl(self,
              style=wx.TR_DEFAULT_STYLE |
                    wx.TR_ROW_LINES |
                    wx.TR_COLUMN_LINES |
                    wx.TR_HIDE_ROOT |
                    wx.TR_FULL_ROW_HIGHLIGHT)
        self.ModulesGrid.SetMinSize(wx.Size(600, 300))
        self.ModulesGrid.GetMainWindow().Bind(wx.EVT_LEFT_DCLICK,
            self.OnModulesGridLeftDClick)
        main_sizer.AddWindow(self.ModulesGrid, border=10, 
            flag=wx.GROW|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        for colname, colsize, colalign in zip(GetModulesTableColnames(),
                                              [400, 150],
                                              [wx.ALIGN_LEFT, wx.ALIGN_RIGHT]):
            self.ModulesGrid.AddColumn(_(colname), colsize, colalign)
        self.ModulesGrid.SetMainColumn(0)
    
    def GetPath(self):
        return self.ModuleLibrary.GetPath()
    
    def GetSelectedFilePath(self):
        return self.ESIFiles.GetPath()
    
    def RefreshView(self):
        self.ESIFiles.RefreshTree()
        self.RefreshModulesGrid()
    
    def RefreshModulesGrid(self):
        root = self.ModulesGrid.GetRootItem()
        if not root.IsOk():
            root = self.ModulesGrid.AddRoot("Modules")
        self.GenerateModulesGridBranch(root, 
            self.ModuleLibrary.GetModulesLibrary(), 
            GetVariablesTableColnames())
        self.ModulesGrid.Expand(root)
            
    def GenerateModulesGridBranch(self, root, modules, colnames):
        item, root_cookie = self.ModulesGrid.GetFirstChild(root)
        
        no_more_items = not item.IsOk()
        for module in modules:
            if no_more_items:
                item = self.ModulesGrid.AppendItem(root, "")
            self.ModulesGrid.SetItemText(item, module["name"], 0)
            if module["infos"] is not None:
                self.ModulesGrid.SetItemText(item, str(module["infos"]["alignment"]), 1)
            else:
                self.ModulesGrid.SetItemBackgroundColour(item, wx.LIGHT_GREY)
            self.ModulesGrid.SetItemPyData(item, module["infos"])
            self.GenerateModulesGridBranch(item, module["children"], colnames)
            if not no_more_items:
                item, root_cookie = self.ModulesGrid.GetNextChild(root, root_cookie)
                no_more_items = not item.IsOk()
        
        if not no_more_items:
            to_delete = []
            while item.IsOk():
                to_delete.append(item)
                item, root_cookie = self.ModulesGrid.GetNextChild(root, root_cookie)
            for item in to_delete:
                self.ModulesGrid.Delete(item)
    
    def OnImportButton(self, event):
        dialog = wx.FileDialog(self,
             _("Choose an XML file"), 
             os.getcwd(), "",  
             _("XML files (*.xml)|*.xml|All files|*.*"), wx.OPEN)
        
        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            if self.ModuleLibrary.ImportModuleLibrary(filepath):
                wx.CallAfter(self.RefreshView)
            else:
                message = wx.MessageDialog(self, 
                    _("No such XML file: %s\n") % filepath, 
                    _("Error"), wx.OK|wx.ICON_ERROR)
                message.ShowModal()
                message.Destroy()
        dialog.Destroy()
        
        event.Skip()
    
    def OnDeleteButton(self, event):
        filepath = self.GetSelectedFilePath()
        if os.path.isfile(filepath):
            folder, filename = os.path.split(filepath)
            
            dialog = wx.MessageDialog(self, 
                  _("Do you really want to delete the file '%s'?") % filename, 
                  _("Delete File"), wx.YES_NO|wx.ICON_QUESTION)
            remove = dialog.ShowModal() == wx.ID_YES
            dialog.Destroy()
            
            if remove:
                os.remove(filepath)
                self.ModuleLibrary.LoadModules()
                wx.CallAfter(self.RefreshView)
        event.Skip()
    
    def OnModulesGridLeftDClick(self, event):
        item, flags, col = self.ModulesGrid.HitTest(event.GetPosition())
        if item.IsOk():
            entry_infos = self.ModulesGrid.GetItemPyData(item)
            if entry_infos is not None and col == 1:
                dialog = wx.TextEntryDialog(self, 
                    _("Set PDO alignment (bits):"),
                    _("%s PDO alignment") % self.ModulesGrid.GetItemText(item), 
                    str(entry_infos["alignment"]))
                
                if dialog.ShowModal() == wx.ID_OK:
                    try:
                        self.ModuleLibrary.SetAlignment(
                            entry_infos["vendor"],
                            entry_infos["product_code"],
                            entry_infos["revision_number"],
                            int(dialog.GetValue()))
                        wx.CallAfter(self.RefreshModulesGrid)
                    except ValueError:
                        message = wx.MessageDialog(self, 
                            _("Module PDO alignment must be an integer!"), 
                            _("Error"), wx.OK|wx.ICON_ERROR)
                        message.ShowModal()
                        message.Destroy()
                    
                dialog.Destroy()
        
        event.Skip()
    
    def OnResize(self, event):
        self.GetBestSize()
        xstart, ystart = self.GetViewStart()
        window_size = self.GetClientSize()
        maxx, maxy = self.GetMinSize()
        posx = max(0, min(xstart, (maxx - window_size[0]) / SCROLLBAR_UNIT))
        posy = max(0, min(ystart, (maxy - window_size[1]) / SCROLLBAR_UNIT))
        self.Scroll(posx, posy)
        self.SetScrollbars(SCROLLBAR_UNIT, SCROLLBAR_UNIT, 
                maxx / SCROLLBAR_UNIT, maxy / SCROLLBAR_UNIT, posx, posy)
        event.Skip()

class DatabaseManagementDialog(wx.Dialog):
    
    def __init__(self, parent, database):
        wx.Dialog.__init__(self, parent,
              size=wx.Size(700, 500), title=_('ESI Files Database management'),
              style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        
        main_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=10)
        main_sizer.AddGrowableCol(0)
        main_sizer.AddGrowableRow(0)
        
        self.DatabaseEditor = LibraryEditorPanel(self, database,
            [("ImportButton", "ImportESI", _("Import file to ESI files database"), None),
             ("DeleteButton", "remove_element", _("Remove file from database"), None)])
        main_sizer.AddWindow(self.DatabaseEditor, border=10,
            flag=wx.GROW|wx.TOP|wx.LEFT|wx.RIGHT)
        
        button_sizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        button_sizer.GetAffirmativeButton().SetLabel(_("Add file to project"))
        button_sizer.GetCancelButton().SetLabel(_("Close"))
        main_sizer.AddSizer(button_sizer, border=10, 
              flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        
        self.SetSizer(main_sizer)
        
        self.DatabaseEditor.RefreshView()
        
    def GetValue(self):
        return self.DatabaseEditor.GetSelectedFilePath()

class LibraryEditor(ConfTreeNodeEditor):
    
    CONFNODEEDITOR_TABS = [
        (_("Modules Library"), "_create_ModuleLibraryEditor")]
    
    def _create_ModuleLibraryEditor(self, prnt):
        self.ModuleLibraryEditor = LibraryEditorPanel(prnt,
            self.Controler.GetModulesLibraryInstance(),
            [("ImportButton", "ImportESI", _("Import ESI file"), None),
             ("AddButton", "ImportDatabase", _("Add file from ESI files database"), self.OnAddButton),
             ("DeleteButton", "remove_element", _("Remove file from library"), None)])
        
        return self.ModuleLibraryEditor

    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
    
        self.RefreshView()
    
    def RefreshView(self):
        ConfTreeNodeEditor.RefreshView(self)
        self.ModuleLibraryEditor.RefreshView()

    def OnAddButton(self, event):
        dialog = DatabaseManagementDialog(self, 
            self.Controler.GetModulesDatabaseInstance())
        
        if dialog.ShowModal() == wx.ID_OK:
            module_library = self.Controler.GetModulesLibraryInstance()
            module_library.ImportModuleLibrary(dialog.GetValue())
            
        dialog.Destroy()
        
        wx.CallAfter(self.ModuleLibraryEditor.RefreshView)
        
        event.Skip()

