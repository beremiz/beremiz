import keyword

import wx
import wx.grid
import wx.stc as stc
import wx.lib.buttons

from controls import CustomGrid, CustomTable
from ConfTreeNodeEditor import ConfTreeNodeEditor
from utils.BitmapLibrary import GetBitmap

if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 10,
              'size2': 8,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 12,
              'size2': 10,
             }


def AppendMenu(parent, help, id, kind, text):
    if wx.VERSION >= (2, 6, 0):
        parent.Append(help=help, id=id, kind=kind, text=text)
    else:
        parent.Append(helpString=help, id=id, kind=kind, item=text)


[ID_CPPEDITOR,
] = [wx.NewId() for _init_ctrls in range(1)]

CPP_KEYWORDS = ["asm", "auto", "bool", "break", "case", "catch", "char", "class", 
    "const", "const_cast", "continue", "default", "delete", "do", "double", 
    "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false", 
    "float", "for", "friend", "goto", "if", "inline", "int", "long", "mutable", 
    "namespace", "new", "operator", "private", "protected", "public", "register", 
    "reinterpret_cast", "return", "short", "signed", "sizeof", "static", 
    "static_cast", "struct", "switch", "template", "this", "throw", "true", "try",
    "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", 
    "void", "volatile", "wchar_t", "while"]

def GetCursorPos(old, new):
    old_length = len(old)
    new_length = len(new)
    common_length = min(old_length, new_length)
    i = 0
    for i in xrange(common_length):
        if old[i] != new[i]:
            break
    if old_length < new_length:
        if common_length > 0 and old[i] != new[i]:
            return i + new_length - old_length
        else:
            return i + new_length - old_length + 1
    elif old_length > new_length or i < min(old_length, new_length) - 1:
        if common_length > 0 and old[i] != new[i]:
            return i
        else:
            return i + 1
    else:
        return None

class CppEditor(stc.StyledTextCtrl):

    fold_symbols = 3
    
    def __init__(self, parent, name, window, controler):
        stc.StyledTextCtrl.__init__(self, parent, ID_CPPEDITOR, wx.DefaultPosition, 
                 wx.Size(0, 0), 0)

        self.SetMarginType(1, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(1, 25)

        self.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.SetLexer(stc.STC_LEX_CPP)
        self.SetKeyWords(0, " ".join(CPP_KEYWORDS))

        self.SetProperty("fold", "1")
        self.SetProperty("tab.timmy.whinge.level", "1")
        self.SetMargins(0,0)

        self.SetViewWhiteSpace(False)
        #self.SetBufferedDraw(False)
        #self.SetViewEOL(True)
        #self.SetEOLMode(stc.STC_EOL_CRLF)
        #self.SetUseAntiAliasing(True)
        
        self.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.SetEdgeColumn(78)

        # Setup a margin to hold fold markers
        #self.SetFoldFlags(16)  ###  WHAT IS THIS VALUE?  WHAT ARE THE OTHER FLAGS?  DOES IT MATTER?
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)
        self.SetMarginWidth(2, 12)

        if self.fold_symbols == 0:
            # Arrow pointing right for contracted folders, arrow pointing down for expanded
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "black", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     "white", "black")
            
        elif self.fold_symbols == 1:
            # Plus for contracted folders, minus for expanded
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, "white", "black")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, "white", "black")

        elif self.fold_symbols == 2:
            # Like a flattened tree control using circular headers and curved joins
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_CIRCLEMINUS,          "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLEPLUS,           "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,                "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE,         "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_CIRCLEPLUSCONNECTED,  "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_CIRCLEMINUSCONNECTED, "white", "#404040")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNERCURVE,         "white", "#404040")

        elif self.fold_symbols == 3:
            # Like a flattened tree control using square headers
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
            self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           "white", "#808080")


        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        # Make some styles,  The lexer defines what each style is used for, we
        # just have to define what each style looks like.  This set is adapted from
        # Scintilla sample property files.

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(helv)s,size:%(size2)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#FF0000,bold")

        self.StyleSetSpec(stc.STC_C_COMMENT, 'fore:#408060')
        self.StyleSetSpec(stc.STC_C_COMMENTLINE, 'fore:#408060')
        self.StyleSetSpec(stc.STC_C_COMMENTDOC, 'fore:#408060')
        self.StyleSetSpec(stc.STC_C_NUMBER, 'fore:#0076AE')
        self.StyleSetSpec(stc.STC_C_WORD, 'bold,fore:#800056')
        self.StyleSetSpec(stc.STC_C_STRING, 'fore:#2a00ff')
        self.StyleSetSpec(stc.STC_C_PREPROCESSOR, 'bold,fore:#800056')
        self.StyleSetSpec(stc.STC_C_OPERATOR, 'bold')
        self.StyleSetSpec(stc.STC_C_STRINGEOL, 'back:#FFD5FF')
        
        # register some images for use in the AutoComplete box.
        #self.RegisterImage(1, images.getSmilesBitmap())
        self.RegisterImage(1, 
            wx.ArtProvider.GetBitmap(wx.ART_DELETE, size=(16,16)))
        self.RegisterImage(2, 
            wx.ArtProvider.GetBitmap(wx.ART_NEW, size=(16,16)))
        self.RegisterImage(3, 
            wx.ArtProvider.GetBitmap(wx.ART_COPY, size=(16,16)))

        # Indentation size
        self.SetTabWidth(2)
        self.SetUseTabs(0)

        self.Controler = controler
        self.ParentWindow = window
        
        self.DisableEvents = True
        self.Name = name
        self.CurrentAction = None
        
        self.SetModEventMask(wx.stc.STC_MOD_BEFOREINSERT|wx.stc.STC_MOD_BEFOREDELETE)

        self.Bind(wx.stc.EVT_STC_DO_DROP, self.OnDoDrop, id=ID_CPPEDITOR)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.OnModification, id=ID_CPPEDITOR)
    
    def OnModification(self, event):
        if not self.DisableEvents:
            mod_type = event.GetModificationType()
            if not (mod_type&wx.stc.STC_PERFORMED_UNDO or mod_type&wx.stc.STC_PERFORMED_REDO):
                if mod_type&wx.stc.STC_MOD_BEFOREINSERT:
                    if self.CurrentAction == None:
                        self.StartBuffering()
                    elif self.CurrentAction[0] != "Add" or self.CurrentAction[1] != event.GetPosition() - 1:
                        self.Controler.EndBuffering()
                        self.StartBuffering()
                    self.CurrentAction = ("Add", event.GetPosition())
                    wx.CallAfter(self.RefreshModel)
                elif mod_type&wx.stc.STC_MOD_BEFOREDELETE:
                    if self.CurrentAction == None:
                        self.StartBuffering()
                    elif self.CurrentAction[0] != "Delete" or self.CurrentAction[1] != event.GetPosition() + 1:
                        self.Controler.EndBuffering()
                        self.StartBuffering()
                    self.CurrentAction = ("Delete", event.GetPosition())
                    wx.CallAfter(self.RefreshModel)
        event.Skip()
    
    def OnDoDrop(self, event):
        self.ResetBuffer()
        wx.CallAfter(self.RefreshModel)
        event.Skip()

    # Buffer the last model state
    def RefreshBuffer(self):
        self.Controler.BufferCFile()
        if self.ParentWindow is not None:
            self.ParentWindow.RefreshTitle()
            self.ParentWindow.RefreshFileMenu()
            self.ParentWindow.RefreshEditMenu()
            self.ParentWindow.RefreshPageTitles()
    
    def StartBuffering(self):
        self.Controler.StartBuffering()
        if self.ParentWindow is not None:
            self.ParentWindow.RefreshTitle()
            self.ParentWindow.RefreshFileMenu()
            self.ParentWindow.RefreshEditMenu()
            self.ParentWindow.RefreshPageTitles()
    
    def ResetBuffer(self):
        if self.CurrentAction != None:
            self.Controler.EndBuffering()
            self.CurrentAction = None

    def RefreshView(self):
        self.ResetBuffer()
        self.DisableEvents = True
        old_cursor_pos = self.GetCurrentPos()
        old_text = self.GetText()
        new_text = self.Controler.GetPartText(self.Name)
        self.SetText(new_text)
        new_cursor_pos = GetCursorPos(old_text, new_text)
        if new_cursor_pos != None:
            self.GotoPos(new_cursor_pos)
        else:
            self.GotoPos(old_cursor_pos)
        self.ScrollToColumn(0)
        self.EmptyUndoBuffer()
        self.DisableEvents = False
        
        self.Colourise(0, -1)

    def DoGetBestSize(self):
        return self.ParentWindow.GetPanelBestSize()

    def RefreshModel(self):
        self.Controler.SetPartText(self.Name, self.GetText())

    def OnKeyPressed(self, event):
        if self.CallTipActive():
            self.CallTipCancel()
        key = event.GetKeyCode()

        if key == 32 and event.ControlDown():
            pos = self.GetCurrentPos()

            # Tips
            if event.ShiftDown():
                pass
##                self.CallTipSetBackground("yellow")
##                self.CallTipShow(pos, 'lots of of text: blah, blah, blah\n\n'
##                                 'show some suff, maybe parameters..\n\n'
##                                 'fubar(param1, param2)')
            # Code completion
            else:
                self.AutoCompSetIgnoreCase(False)  # so this needs to match

                # Images are specified with a appended "?type"
                self.AutoCompShow(0, " ".join([word + "?1" for word in CPP_KEYWORDS]))
        else:
            event.Skip()

    def OnKillFocus(self, event):
        self.AutoCompCancel()
        event.Skip()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            styleBefore = self.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            styleAfter = self.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            self.BraceHighlight(braceAtCaret, braceOpposite)
            #pt = self.PointFromPosition(braceOpposite)
            #self.Refresh(True, wxRect(pt.x, pt.y, 5,5))
            #print pt
            #self.Refresh(False)


    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)


    def FoldAll(self):
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1



    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def Cut(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.CmdKeyExecute(wx.stc.STC_CMD_CUT)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()
    
    def Copy(self):
        self.CmdKeyExecute(wx.stc.STC_CMD_COPY)
    
    def Paste(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.CmdKeyExecute(wx.stc.STC_CMD_PASTE)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()


#-------------------------------------------------------------------------------
#                         Helper for VariablesGrid values
#-------------------------------------------------------------------------------

class VariablesTable(CustomTable):
    
    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            if col == 0:
                return row + 1
            else:
                return str(self.data[row].get(self.GetColLabelValue(col, False), ""))
    
    def _updateColAttrs(self, grid):
        """
        wxGrid -> update the column attributes to add the
        appropriate renderer given the column name.

        Otherwise default to the default renderer.
        """
        
        typelist = None
        accesslist = None
        for row in range(self.GetNumberRows()):
            for col in range(self.GetNumberCols()):
                editor = None
                renderer = None
                colname = self.GetColLabelValue(col, False)
                
                if colname == "Name":
                    editor = wx.grid.GridCellTextEditor()
                elif colname == "Class":
                    editor = wx.grid.GridCellChoiceEditor()
                    editor.SetParameters("input,memory,output")
                elif colname == "Type":
                    pass
                else:
                    grid.SetReadOnly(row, col, True)
                
                grid.SetCellEditor(row, col, editor)
                grid.SetCellRenderer(row, col, renderer)
                
                grid.SetCellBackgroundColour(row, col, wx.WHITE)
            self.ResizeRow(grid, row)
    

[ID_VARIABLESEDITOR, ID_VARIABLESEDITORVARIABLESGRID,
 ID_VARIABLESEDITORADDVARIABLEBUTTON, ID_VARIABLESEDITORDELETEVARIABLEBUTTON, 
 ID_VARIABLESEDITORUPVARIABLEBUTTON, ID_VARIABLESEDITORDOWNVARIABLEBUTTON
] = [wx.NewId() for _init_ctrls in range(6)]

class VariablesEditor(wx.Panel):
    
    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    
    def _init_coll_MainSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(0)

    def _init_coll_MainSizer_Items(self, parent):
        parent.AddWindow(self.VariablesGrid, 0, border=0, flag=wx.GROW)
        parent.AddSizer(self.ButtonsSizer, 0, border=0, flag=wx.GROW)

    def _init_coll_ButtonsSizer_Growables(self, parent):
        parent.AddGrowableCol(0)
        parent.AddGrowableRow(0)

    def _init_coll_ButtonsSizer_Items(self, parent):
        parent.AddWindow(self.AddVariableButton, 0, border=0, flag=wx.ALIGN_RIGHT)
        parent.AddWindow(self.DeleteVariableButton, 0, border=0, flag=0)
        parent.AddWindow(self.UpVariableButton, 0, border=0, flag=0)
        parent.AddWindow(self.DownVariableButton, 0, border=0, flag=0)

    def _init_sizers(self):
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=4)
        self.ButtonsSizer = wx.FlexGridSizer(cols=5, hgap=5, rows=1, vgap=0)
        
        self._init_coll_MainSizer_Growables(self.MainSizer)
        self._init_coll_MainSizer_Items(self.MainSizer)
        self._init_coll_ButtonsSizer_Growables(self.ButtonsSizer)
        self._init_coll_ButtonsSizer_Items(self.ButtonsSizer)
        
        self.SetSizer(self.MainSizer)

    def _init_ctrls(self, prnt):
        wx.Panel.__init__(self, id=ID_VARIABLESEDITOR, name='', parent=prnt,
              size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        
        self.VariablesGrid = CustomGrid(id=ID_VARIABLESEDITORVARIABLESGRID,
              name='VariablesGrid', parent=self, pos=wx.Point(0, 0), 
              size=wx.Size(-1, -1), style=wx.VSCROLL)
        if wx.VERSION >= (2, 5, 0):
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnVariablesGridCellChange)
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnVariablesGridCellLeftClick)
            self.VariablesGrid.Bind(wx.grid.EVT_GRID_EDITOR_SHOWN, self.OnVariablesGridEditorShown)
        else:
            wx.grid.EVT_GRID_CELL_CHANGE(self.VariablesGrid, self.OnVariablesGridCellChange)
            wx.grid.EVT_GRID_CELL_LEFT_CLICK(self.VariablesGrid, self.OnVariablesGridCellLeftClick)
            wx.grid.EVT_GRID_EDITOR_SHOWN(self.VariablesGrid, self.OnVariablesGridEditorShown)
        
        self.AddVariableButton = wx.Button(id=ID_VARIABLESEDITORADDVARIABLEBUTTON, label='Add Variable',
              name='AddVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(122, 32), style=0)
        
        self.DeleteVariableButton = wx.Button(id=ID_VARIABLESEDITORDELETEVARIABLEBUTTON, label='Delete Variable',
              name='DeleteVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(122, 32), style=0)
        
        self.UpVariableButton = wx.Button(id=ID_VARIABLESEDITORUPVARIABLEBUTTON, label='^',
              name='UpVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(32, 32), style=0)
        
        self.DownVariableButton = wx.Button(id=ID_VARIABLESEDITORDOWNVARIABLEBUTTON, label='v',
              name='DownVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(32, 32), style=0)
        
        self._init_sizers()

    def __init__(self, parent, window, controler):
        self._init_ctrls(parent)
        
        self.ParentWindow = window
        self.Controler = controler
        
        self.VariablesDefaultValue = {"Name" : "", "Class" : "input", "Type" : ""}
        self.Table = VariablesTable(self, [], ["#", "Name", "Class", "Type"])
        self.ColAlignements = [wx.ALIGN_RIGHT, wx.ALIGN_LEFT, wx.ALIGN_LEFT, wx.ALIGN_LEFT]
        self.ColSizes = [40, 200, 150, 150]
        self.VariablesGrid.SetTable(self.Table)
        self.VariablesGrid.SetButtons({"Add": self.AddVariableButton,
                                       "Delete": self.DeleteVariableButton,
                                       "Up": self.UpVariableButton,
                                       "Down": self.DownVariableButton})
        
        def _AddVariable(new_row):
            self.Table.InsertRow(new_row, self.VariablesDefaultValue.copy())
            self.RefreshModel()
            self.RefreshView()
            return new_row
        setattr(self.VariablesGrid, "_AddRow", _AddVariable)
        
        def _DeleteVariable(row):
            self.Table.RemoveRow(row)
            self.RefreshModel()
            self.RefreshView()
        setattr(self.VariablesGrid, "_DeleteRow", _DeleteVariable)
        
        def _MoveVariable(row, move):
            new_row = self.Table.MoveRow(row, move)
            if new_row != row:
                self.RefreshModel()
                self.RefreshView()
            return new_row
        setattr(self.VariablesGrid, "_MoveRow", _MoveVariable)
        
        self.VariablesGrid.SetRowLabelSize(0)
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(self.ColAlignements[col], wx.ALIGN_CENTRE)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColSize(col, self.ColSizes[col])
        self.Table.ResetView(self.VariablesGrid)

    def RefreshModel(self):
        self.Controler.SetVariables(self.Table.GetData())
        self.RefreshBuffer()
        
    # Buffer the last model state
    def RefreshBuffer(self):
        self.Controler.BufferCFile()
        self.ParentWindow.RefreshTitle()
        self.ParentWindow.RefreshFileMenu()
        self.ParentWindow.RefreshEditMenu()
        self.ParentWindow.RefreshPageTitles()

    def RefreshView(self):
        self.Table.SetData(self.Controler.GetVariables())
        self.Table.ResetView(self.VariablesGrid)
        self.VariablesGrid.RefreshButtons()
    
    def DoGetBestSize(self):
        return self.ParentWindow.GetPanelBestSize()
    
    def OnVariablesGridCellChange(self, event):
        self.RefreshModel()
        wx.CallAfter(self.RefreshView)
        event.Skip()

    def OnVariablesGridEditorShown(self, event):
        row, col = event.GetRow(), event.GetCol() 
        if self.Table.GetColLabelValue(col) == "Type":
            type_menu = wx.Menu(title='')
            base_menu = wx.Menu(title='')
            for base_type in self.Controler.GetBaseTypes():
                new_id = wx.NewId()
                AppendMenu(base_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=base_type)
                self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(base_type), id=new_id)
            type_menu.AppendMenu(wx.NewId(), "Base Types", base_menu)
            datatype_menu = wx.Menu(title='')
            for datatype in self.Controler.GetDataTypes(basetypes=False, only_locatables=True):
                new_id = wx.NewId()
                AppendMenu(datatype_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=datatype)
                self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(datatype), id=new_id)
            type_menu.AppendMenu(wx.NewId(), "User Data Types", datatype_menu)
            rect = self.VariablesGrid.BlockToDeviceRect((row, col), (row, col))
            
            self.VariablesGrid.PopupMenuXY(type_menu, rect.x + rect.width, rect.y + self.VariablesGrid.GetColLabelSize())
            type_menu.Destroy()
            event.Veto()
        else:
            event.Skip()

    def GetVariableTypeFunction(self, base_type):
        def VariableTypeFunction(event):
            row = self.VariablesGrid.GetGridCursorRow()
            self.Table.SetValueByName(row, "Type", base_type)
            self.Table.ResetView(self.VariablesGrid)
            self.RefreshModel()
            self.RefreshView()
            event.Skip()
        return VariableTypeFunction

    def OnVariablesGridCellLeftClick(self, event):
        if event.GetCol() == 0:
            row = event.GetRow()
            num = 0
            if self.Table.GetValueByName(row, "Class") == "input":
                dir = "%I"
                for i in xrange(row):
                    if self.Table.GetValueByName(i, "Class") == "input":
                        num += 1
            elif self.Table.GetValueByName(row, "Class") == "memory":
                dir = "%M"
                for i in xrange(row):
                    if self.Table.GetValueByName(i, "Class") == "memory":
                        num += 1
            else:
                dir = "%Q"
                for i in xrange(row):
                    if self.Table.GetValueByName(i, "Class") == "output":
                        num += 1
            data_type = self.Table.GetValueByName(row, "Type")
            var_name = self.Table.GetValueByName(row, "Name")
            base_location = ".".join(map(lambda x:str(x), self.Controler.GetCurrentLocation()))
            location = "%s%s%s.%d"%(dir, self.Controler.GetSizeOfType(data_type), base_location, num)
            data = wx.TextDataObject(str((location, "location", data_type, var_name, "")))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        event.Skip()
    

#-------------------------------------------------------------------------------
#                          SVGUIEditor Main Frame Class
#-------------------------------------------------------------------------------

CFILE_PARTS = [
    ("Includes", CppEditor), 
    ("Variables", VariablesEditor), 
    ("Globals", CppEditor), 
    ("Init", CppEditor), 
    ("CleanUp", CppEditor), 
    ("Retrieve", CppEditor), 
    ("Publish", CppEditor),
]

class FoldPanelCaption(wx.lib.buttons.GenBitmapTextToggleButton):
    
    def GetBackgroundBrush(self, dc):
        colBg = self.GetBackgroundColour()
        brush = wx.Brush(colBg, wx.SOLID)
        if self.style & wx.BORDER_NONE:
            myAttr = self.GetDefaultAttributes()
            parAttr = self.GetParent().GetDefaultAttributes()
            myDef = colBg == myAttr.colBg
            parDef = self.GetParent().GetBackgroundColour() == parAttr.colBg
            if myDef and parDef:
                if wx.Platform == "__WXMAC__":
                    brush.MacSetTheme(1) # 1 == kThemeBrushDialogBackgroundActive
                elif wx.Platform == "__WXMSW__":
                    if self.DoEraseBackground(dc):
                        brush = None
            elif myDef and not parDef:
                colBg = self.GetParent().GetBackgroundColour()
                brush = wx.Brush(colBg, wx.SOLID)
        return brush
    
    def DrawLabel(self, dc, width, height, dx=0, dy=0):
        bmp = self.bmpLabel
        if bmp is not None:     # if the bitmap is used
            if self.bmpDisabled and not self.IsEnabled():
                bmp = self.bmpDisabled
            if self.bmpFocus and self.hasFocus:
                bmp = self.bmpFocus
            if self.bmpSelected and not self.up:
                bmp = self.bmpSelected
            bw,bh = bmp.GetWidth(), bmp.GetHeight()
            hasMask = bmp.GetMask() is not None
        else:
            bw = bh = 0     # no bitmap -> size is zero
        
        dc.SetFont(self.GetFont())
        if self.IsEnabled():
            dc.SetTextForeground(self.GetForegroundColour())
        else:
            dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT))

        label = self.GetLabel()
        tw, th = dc.GetTextExtent(label)        # size of text
        
        if bmp is not None:
            dc.DrawBitmap(bmp, width - bw - 2, (height-bh)/2, hasMask) # draw bitmap if available
        
        dc.DrawText(label, 2, (height-th)/2)      # draw the text

        dc.SetPen(wx.Pen(self.GetForegroundColour()))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(0, 0, width, height)

[ID_CFILEEDITOR, ID_CFILEEDITORMAINSPLITTER, 
 ID_CFILEEDITORCFILETREE, ID_CFILEEDITORPARTSOPENED, 
] = [wx.NewId() for _init_ctrls in range(4)]

class CFileEditor(ConfTreeNodeEditor):
    
    def _init_ConfNodeEditor(self, prnt):
        self.ConfNodeEditor = wx.Panel(id=ID_CFILEEDITOR, parent=prnt, pos=wx.Point(0, 0), 
                size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL)
        
        self.Panels = {}
        self.MainSizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2 * len(CFILE_PARTS) + 1, vgap=0)
        self.MainSizer.AddGrowableCol(0)
        
        for idx, (name, panel_class) in enumerate(CFILE_PARTS):
            button_id = wx.NewId()
            button = FoldPanelCaption(id=button_id, name='FoldPanelCaption_%s' % name, 
                  label=name, bitmap=GetBitmap("CollapsedIconData"), 
                  parent=self.ConfNodeEditor, pos=wx.Point(0, 0),
                  size=wx.Size(0, 20), style=wx.NO_BORDER|wx.ALIGN_LEFT)
            button.SetBitmapSelected(GetBitmap("ExpandedIconData"))
            button.Bind(wx.EVT_BUTTON, self.GenPanelButtonCallback(name), id=button_id)
            self.MainSizer.AddWindow(button, 0, border=0, flag=wx.TOP|wx.GROW)
            
            if panel_class == VariablesEditor:
                panel = VariablesEditor(self.ConfNodeEditor, self.ParentWindow, self.Controler)
            else:
                panel = panel_class(self.ConfNodeEditor, name, self.ParentWindow, self.Controler)
            self.MainSizer.AddWindow(panel, 0, border=0, flag=wx.BOTTOM|wx.GROW)
            panel.Hide()
            
            self.Panels[name] = {"button": button, "panel": panel, "expanded": False, "row": 2 * idx + 1}
        
        self.Spacer = wx.Panel(self.ConfNodeEditor, -1)
        self.SpacerExpanded = True
        self.MainSizer.AddWindow(self.Spacer, 0, border=0, flag=wx.GROW)
        
        self.MainSizer.AddGrowableRow(2 * len(CFILE_PARTS))
        
        self.ConfNodeEditor.SetSizer(self.MainSizer)
    
    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
    
    def GetBufferState(self):
        return self.Controler.GetBufferState()
        
    def Undo(self):
        self.Controler.LoadPrevious()
        self.RefreshView()
            
    def Redo(self):
        self.Controler.LoadNext()
        self.RefreshView()
    
    def RefreshView(self):
        ConfTreeNodeEditor.RefreshView(self)
        
        for infos in self.Panels.itervalues():
            infos["panel"].RefreshView()

    def GenPanelButtonCallback(self, name):
        def PanelButtonCallback(event):
            self.TogglePanel(name)
        return PanelButtonCallback

    def ExpandPanel(self, name):
        infos = self.Panels.get(name, None)
        if infos is not None and not infos["expanded"]:
            infos["expanded"] = True
            infos["button"].SetToggle(True)
            infos["panel"].Show()
            self.MainSizer.AddGrowableRow(infos["row"])
        
            self.RefreshSizerLayout()
    
    def CollapsePanel(self, name):
        infos = self.Panels.get(name, None)
        if infos is not None and infos["expanded"]:
            infos["expanded"] = False
            infos["button"].SetToggle(False)
            infos["panel"].Hide()
            self.MainSizer.RemoveGrowableRow(infos["row"])
        
            self.RefreshSizerLayout()
        
    def TogglePanel(self, name):
        infos = self.Panels.get(name, None)
        if infos is not None:
            infos["expanded"] = not infos["expanded"]
            infos["button"].SetToggle(infos["expanded"])
            if infos["expanded"]:
                infos["panel"].Show()
                self.MainSizer.AddGrowableRow(infos["row"])
            else:
                infos["panel"].Hide()
                self.MainSizer.RemoveGrowableRow(infos["row"])
            
            self.RefreshSizerLayout()
    
    def RefreshSizerLayout(self):
        expand_spacer = True
        for infos in self.Panels.itervalues():
            expand_spacer = expand_spacer and not infos["expanded"]
        
        if self.SpacerExpanded != expand_spacer:
            self.SpacerExpanded = expand_spacer
            if expand_spacer:
                self.Spacer.Show()
                self.MainSizer.AddGrowableRow(2 * len(CFILE_PARTS))
            else:
                self.Spacer.Hide()
                self.MainSizer.RemoveGrowableRow(2 * len(CFILE_PARTS))
        
        self.MainSizer.Layout()
            
