
import wx

from controls import EditorPanel, ProjectPropertiesPanel
from ConfTreeNodeEditor import ConfTreeNodeEditor, WINDOW_COLOUR

class ProjectNodeEditor(ConfTreeNodeEditor):
    
    VARIABLE_PANEL_TYPE = "config"
    ENABLE_REQUIRED = True
    
    def _init_Editor(self, prnt):
        self.Editor = wx.ScrolledWindow(prnt, -1, size=wx.Size(-1, -1),
                style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER|wx.HSCROLL|wx.VSCROLL)
        self.Editor.SetBackgroundColour(WINDOW_COLOUR)
        self.Editor.Bind(wx.EVT_SIZE, self.OnWindowResize)
        self.Editor.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheel)
        self.ParamsEditor = self.Editor
        
        # Variable allowing disabling of Editor scroll when Popup shown 
        self.ScrollingEnabled = True
        
        self.ParamsEditorSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=5)
        self.ParamsEditorSizer.AddGrowableCol(0)
        self.ParamsEditorSizer.AddGrowableRow(1)
        
        self.Editor.SetSizer(self.ParamsEditorSizer)
        
        
        buttons_sizer = self.GenerateMethodButtonSizer()
        self.ParamsEditorSizer.AddSizer(buttons_sizer, 0, border=5, 
                                        flag=wx.GROW|wx.LEFT|wx.RIGHT|wx.TOP)
        
        projectproperties_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.ParamsEditorSizer.AddSizer(projectproperties_sizer, 0, border=5, 
                                        flag=wx.LEFT|wx.RIGHT|wx.BOTTOM)
        
        if self.SHOW_PARAMS:
            self.ConfNodeParamsSizer = wx.BoxSizer(wx.VERTICAL)
            projectproperties_sizer.AddSizer(self.ConfNodeParamsSizer, 0, border=5, 
                                             flag=wx.RIGHT)
        else:
            self.ConfNodeParamsSizer = None
        
        self.ProjectProperties = ProjectPropertiesPanel(self.Editor, self.Controler, self.ParentWindow, self.ENABLE_REQUIRED)
        projectproperties_sizer.AddWindow(self.ProjectProperties, 0, border=0, flag=0)
        
    def __init__(self, parent, controler, window):
        configuration = controler.GetProjectMainConfigurationName()
        if configuration is not None:
            tagname = controler.ComputeConfigurationName(configuration)
        else:
            tagname = ""
        
        ConfTreeNodeEditor.__init__(self, parent, controler, window, tagname)

    def GetTagName(self):
        return self.Controler.CTNName()
    
    def GetTitle(self):
        fullname = self.Controler.CTNName()
        if self.Controler.CTNTestModified():
            return "~%s~" % fullname
        return fullname
    
    def RefreshView(self, variablepanel=True):
        EditorPanel.RefreshView(self, variablepanel)
        if self.ConfNodeParamsSizer is not None:
            self.RefreshConfNodeParamsSizer()
        self.ProjectProperties.RefreshView()

    def GetBufferState(self):
        return self.Controler.GetBufferState()
        
    def Undo(self):
        self.Controler.LoadPrevious()
        self.ParentWindow.CloseTabsWithoutModel()
            
    def Redo(self):
        self.Controler.LoadNext()
        self.ParentWindow.CloseTabsWithoutModel()
    