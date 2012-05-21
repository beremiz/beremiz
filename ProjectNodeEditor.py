
import wx

from ConfTreeNodeEditor import ConfTreeNodeEditor, WINDOW_COLOUR

class ProjectNodeEditor(ConfTreeNodeEditor):
    
    VARIABLE_PANEL_TYPE = "config"
    
    def _init_Editor(self, prnt):
        self.Editor = wx.ScrolledWindow(prnt, -1, size=wx.Size(-1, -1),
                style=wx.TAB_TRAVERSAL|wx.SUNKEN_BORDER|wx.HSCROLL|wx.VSCROLL)
        self.Editor.SetBackgroundColour(WINDOW_COLOUR)
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
        
        self.ConfNodeParamsSizer = wx.BoxSizer(wx.VERTICAL)
        self.ParamsEditorSizer.AddSizer(self.ConfNodeParamsSizer, 0, border=5, 
                                        flag=wx.LEFT|wx.RIGHT|wx.BOTTOM)
        
        self.RefreshConfNodeParamsSizer()
        
    def __init__(self, parent, controler, window):
        configuration = controler.GetProjectMainConfigurationName()
        if configuration is not None:
            tagname = controler.ComputeConfigurationName(configuration)
        else:
            tagname = ""
        
        ConfTreeNodeEditor.__init__(self, parent, tagname, controler, window)

    def GetTagName(self):
        return self.Controler.CTNName()
    
    def GetTitle(self):
        fullname = self.Controler.CTNName()
        if self.Controler.CTNTestModified():
            return "~%s~" % fullname
        return fullname

        