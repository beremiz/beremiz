
import wx

from controls import ProjectPropertiesPanel, VariablePanel
from EditorPanel import EditorPanel
from ConfTreeNodeEditor import ConfTreeNodeEditor

class ProjectNodeEditor(ConfTreeNodeEditor):
    
    SHOW_BASE_PARAMS = False
    ENABLE_REQUIRED = True
    CONFNODEEDITOR_TABS = [
        (_("Config variables"), "_create_VariablePanel"),
        (_("Project properties"), "_create_ProjectPropertiesPanel")]
    
    def _create_VariablePanel(self, prnt):
        self.VariableEditorPanel = VariablePanel(prnt, self, self.Controler, "config", self.Debug)
        self.VariableEditorPanel.SetTagName(self.TagName)
    
        return self.VariableEditorPanel
    
    def _create_ProjectPropertiesPanel(self, prnt):
        self.ProjectProperties = ProjectPropertiesPanel(prnt, self.Controler, self.ParentWindow, self.ENABLE_REQUIRED)
        
        return self.ProjectProperties
    
    def __init__(self, parent, controler, window):
        configuration = controler.GetProjectMainConfigurationName()
        if configuration is not None:
            tagname = controler.ComputeConfigurationName(configuration)
        else:
            tagname = ""
        
        ConfTreeNodeEditor.__init__(self, parent, controler, window, tagname)
        
        buttons_sizer = self.GenerateMethodButtonSizer()
        self.MainSizer.InsertSizer(0, buttons_sizer, 0, border=5, flag=wx.ALL)
        self.MainSizer.Layout()
        
        self.VariableEditor = self.VariableEditorPanel

    def GetTagName(self):
        return self.Controler.CTNName()
    
    def SetTagName(self, tagname):
        self.TagName = tagname
        if self.VariableEditor is not None:
            self.VariableEditor.SetTagName(tagname)
    
    def GetTitle(self):
        fullname = _(self.Controler.CTNName())
        if self.Controler.CTNTestModified():
            return "~%s~" % fullname
        return fullname
    
    def RefreshView(self, variablepanel=True):
        ConfTreeNodeEditor.RefreshView(self)
        self.VariableEditorPanel.RefreshView()
        self.ProjectProperties.RefreshView()

    def GetBufferState(self):
        return self.Controler.GetBufferState()
        
    def Undo(self):
        self.Controler.LoadPrevious()
        self.ParentWindow.CloseTabsWithoutModel()
            
    def Redo(self):
        self.Controler.LoadNext()
        self.ParentWindow.CloseTabsWithoutModel()
    