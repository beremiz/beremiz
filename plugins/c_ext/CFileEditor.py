import  wx, wx.grid
import  wx.stc  as  stc
import keyword

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

if wx.VERSION >= (2, 8, 0):
    import wx.aui

    class MDICppEditor(wx.aui.AuiMDIChildFrame):
        def __init__(self, parent, name, window, controler):
            wx.aui.AuiMDIChildFrame.__init__(self, parent, -1, title = name)
            
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            self.Viewer = CppEditor(self, name, window, controler)
            
            sizer.AddWindow(self.Viewer, 1, border=0, flag=wx.GROW)
            
            self.SetSizer(sizer)
        
        def GetViewer(self):
            return self.Viewer

    class MDIVariablesEditor(wx.aui.AuiMDIChildFrame):
        def __init__(self, parent, name, window, controler):
            wx.aui.AuiMDIChildFrame.__init__(self, parent, -1, title = name)
            
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            
            self.Viewer = VariablesEditor(self, window, controler)
            
            sizer.AddWindow(self.Viewer, 1, border=0, flag=wx.GROW)
            
            self.SetSizer(sizer)
        
        def GetViewer(self):
            return self.Viewer


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
                 wx.DefaultSize, 0)

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
                elif mod_type&wx.stc.STC_MOD_BEFOREDELETE:
                    if self.CurrentAction == None:
                        self.StartBuffering()
                    elif self.CurrentAction[0] != "Delete" or self.CurrentAction[1] != event.GetPosition() + 1:
                        self.Controler.EndBuffering()
                        self.StartBuffering()
                    self.CurrentAction = ("Delete", event.GetPosition())
        event.Skip()
    
    def OnDoDrop(self, event):
        self.ResetBuffer()
        wx.CallAfter(self.RefreshModel)
        event.Skip()

    def IsViewing(self, name):
        return self.Name == name

    # Buffer the last model state
    def RefreshBuffer(self):
        self.Controler.BufferCFile()
        if self.ParentWindow:
            self.ParentWindow.RefreshTitle()
            self.ParentWindow.RefreshEditMenu()
    
    def StartBuffering(self):
        self.Controler.StartBuffering()
        if self.ParentWindow:
            self.ParentWindow.RefreshTitle()
            self.ParentWindow.RefreshEditMenu()
    
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
            wx.CallAfter(self.RefreshModel)
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


#-------------------------------------------------------------------------------
#                         Helper for VariablesGrid values
#-------------------------------------------------------------------------------

class VariablesTable(wx.grid.PyGridTableBase):
    
    """
    A custom wxGrid Table using user supplied data
    """
    def __init__(self, parent, data, colnames):
        # The base class must be initialized *first*
        wx.grid.PyGridTableBase.__init__(self)
        self.data = data
        self.colnames = colnames
        self.Parent = parent
        # XXX
        # we need to store the row length and collength to
        # see if the table has changed size
        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
    
    def GetNumberCols(self):
        return len(self.colnames)
        
    def GetNumberRows(self):
        return len(self.data)

    def GetColLabelValue(self, col):
        if col < len(self.colnames):
            return self.colnames[col]

    def GetRowLabelValues(self, row):
        return row

    def GetValue(self, row, col):
        if row < self.GetNumberRows():
            if col == 0:
                return row + 1
            else:
                return str(self.data[row].get(self.GetColLabelValue(col), ""))
    
    def GetValueByName(self, row, colname):
        if row < self.GetNumberRows():
            return self.data[row].get(colname, None)
        return None

    def SetValue(self, row, col, value):
        if col < len(self.colnames):
            self.data[row][self.GetColLabelValue(col)] = value
    
    def SetValueByName(self, row, colname, value):
        if row < self.GetNumberRows():
            self.data[row][colname] = value
        
    def ResetView(self, grid):
        """
        (wxGrid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        grid.BeginBatch()
        for current, new, delmsg, addmsg in [
            (self._rows, self.GetNumberRows(), wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (self._cols, self.GetNumberCols(), wx.grid.GRIDTABLE_NOTIFY_COLS_DELETED, wx.grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:
            if new < current:
                msg = wx.grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = wx.grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues(grid)
        grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
        # update the column rendering scheme
        self._updateColAttrs(grid)

        # update the scrollbars and the displayed part of the grid
        grid.AdjustScrollbars()
        grid.ForceRefresh()

    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)

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
                colname = self.GetColLabelValue(col)
                grid.SetReadOnly(row, col, False)
                
                if colname == "Name":
                    editor = wx.grid.GridCellTextEditor()
                elif colname == "Class":
                    editor = wx.grid.GridCellChoiceEditor()
                    editor.SetParameters("input,output")
                elif colname == "Type":
                    pass
                else:
                    grid.SetReadOnly(row, col, True)
                
                grid.SetCellEditor(row, col, editor)
                grid.SetCellRenderer(row, col, renderer)
                
                grid.SetCellBackgroundColour(row, col, wx.WHITE)
    
    def SetData(self, data):
        self.data = data
    
    def GetData(self):
        return self.data
    
    def GetCurrentIndex(self):
        return self.CurrentIndex
    
    def SetCurrentIndex(self, index):
        self.CurrentIndex = index
    
    def AppendRow(self, row_content):
        self.data.append(row_content)

    def RemoveRow(self, row_index):
        self.data.pop(row_index)

    def MoveRow(self, row_index, move, grid):
        new_index = max(0, min(row_index + move, len(self.data) - 1))
        if new_index != row_index:
            self.data.insert(new_index, self.data.pop(row_index))
            grid.SetGridCursor(new_index, grid.GetGridCursorCol())

    def GetRow(self, row_index):
        return self.data[row_index]

    def Empty(self):
        self.data = []
        self.editors = []


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
              size=wx.Size(0, 0), style=wx.SUNKEN_BORDER)
        
        self.VariablesGrid = wx.grid.Grid(id=ID_VARIABLESEDITORVARIABLESGRID,
              name='VariablesGrid', parent=self, pos=wx.Point(0, 0), 
              size=wx.Size(-1, -1), style=wx.VSCROLL)
        self.VariablesGrid.SetFont(wx.Font(12, 77, wx.NORMAL, wx.NORMAL, False,
              'Sans'))
        self.VariablesGrid.SetLabelFont(wx.Font(10, 77, wx.NORMAL, wx.NORMAL,
              False, 'Sans'))
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
        self.Bind(wx.EVT_BUTTON, self.OnAddVariableButton, id=ID_VARIABLESEDITORADDVARIABLEBUTTON)

        self.DeleteVariableButton = wx.Button(id=ID_VARIABLESEDITORDELETEVARIABLEBUTTON, label='Delete Variable',
              name='DeleteVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(122, 32), style=0)
        self.Bind(wx.EVT_BUTTON, self.OnDeleteVariableButton, id=ID_VARIABLESEDITORDELETEVARIABLEBUTTON)

        self.UpVariableButton = wx.Button(id=ID_VARIABLESEDITORUPVARIABLEBUTTON, label='^',
              name='UpVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(32, 32), style=0)
        self.Bind(wx.EVT_BUTTON, self.OnUpVariableButton, id=ID_VARIABLESEDITORUPVARIABLEBUTTON)

        self.DownVariableButton = wx.Button(id=ID_VARIABLESEDITORDOWNVARIABLEBUTTON, label='v',
              name='DownVariableButton', parent=self, pos=wx.Point(0, 0),
              size=wx.Size(32, 32), style=0)
        self.Bind(wx.EVT_BUTTON, self.OnDownVariableButton, id=ID_VARIABLESEDITORDOWNVARIABLEBUTTON)

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
        self.VariablesGrid.SetRowLabelSize(0)
        for col in range(self.Table.GetNumberCols()):
            attr = wx.grid.GridCellAttr()
            attr.SetAlignment(self.ColAlignements[col], wx.ALIGN_CENTRE)
            self.VariablesGrid.SetColAttr(col, attr)
            self.VariablesGrid.SetColSize(col, self.ColSizes[col])
        self.Table.ResetView(self.VariablesGrid)

    def IsViewing(self, name):
        return name == "Variables"

    def RefreshModel(self):
        self.Controler.SetVariables(self.Table.GetData())
        self.RefreshBuffer()
        
    def ResetBuffer(self):
        pass

    # Buffer the last model state
    def RefreshBuffer(self):
        self.Controler.BufferCFile()
        self.ParentWindow.RefreshTitle()
        self.ParentWindow.RefreshEditMenu()

    def RefreshView(self):
        self.Table.SetData(self.Controler.GetVariables())
        self.Table.ResetView(self.VariablesGrid)
    
    def OnAddVariableButton(self, event):
        self.Table.AppendRow(self.VariablesDefaultValue.copy())
        self.RefreshModel()
        self.RefreshView()
        event.Skip()

    def OnDeleteVariableButton(self, event):
        row = self.VariablesGrid.GetGridCursorRow()
        self.Table.RemoveRow(row)
        self.RefreshModel()
        self.RefreshView()
        event.Skip()

    def OnUpVariableButton(self, event):
        row = self.VariablesGrid.GetGridCursorRow()
        self.Table.MoveRow(row, -1, self.VariablesGrid)
        self.RefreshModel()
        self.RefreshView()
        event.Skip()

    def OnDownVariableButton(self, event):
        row = self.VariablesGrid.GetGridCursorRow()
        self.Table.MoveRow(row, 1, self.VariablesGrid)
        self.RefreshModel()
        self.RefreshView()
        event.Skip()

    def OnVariablesGridCellChange(self, event):
        self.RefreshModel()
        self.RefreshView()
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
            for datatype in self.Controler.GetDataTypes(basetypes = False):
                new_id = wx.NewId()
                AppendMenu(datatype_menu, help='', id=new_id, kind=wx.ITEM_NORMAL, text=datatype)
                self.Bind(wx.EVT_MENU, self.GetVariableTypeFunction(datatype), id=new_id)
            type_menu.AppendMenu(wx.NewId(), "User Data Types", datatype_menu)
            rect = self.VariablesGrid.BlockToDeviceRect((row, col), (row, col))
            self.VariablesGrid.PopupMenuXY(type_menu, rect.x + rect.width, rect.y + self.VariablesGrid.GetColLabelSize())
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
            else:
                dir = "%Q"
                for i in xrange(row):
                    if self.Table.GetValueByName(i, "Class") == "input":
                        num += 1
            data_type = self.Table.GetValueByName(row, "Type")
            base_location = ".".join(map(lambda x:str(x), self.Controler.GetCurrentLocation()))
            location = "%s%s%s.%d"%(dir, self.Controler.GetSizeOfType(data_type), base_location, num)
            data = wx.TextDataObject(str((location, "location", data_type)))
            dragSource = wx.DropSource(self.VariablesGrid)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        event.Skip()
    

#-------------------------------------------------------------------------------
#                          SVGUIEditor Main Frame Class
#-------------------------------------------------------------------------------

if wx.VERSION >= (2, 8, 0):
    base_class = wx.aui.AuiMDIParentFrame
else:
    base_class = wx.Frame

CFILE_PARTS = ["Includes", "Variables", "Globals", "Init", "CleanUp", "Retrieve", 
               "Publish"]

[ID_CFILEEDITOR, ID_CFILEEDITORMAINSPLITTER, 
 ID_CFILEEDITORCFILETREE, CFILEEDITORPARTSOPENED, 
] = [wx.NewId() for _init_ctrls in range(4)]

class CFileEditor(base_class):
    
    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    
    def _init_coll_EditMenu_Items(self, parent):
        AppendMenu(parent, help='', id=wx.ID_REFRESH,
              kind=wx.ITEM_NORMAL, text=u'Refresh\tCTRL+R')
        AppendMenu(parent, help='', id=wx.ID_UNDO,
              kind=wx.ITEM_NORMAL, text=u'Undo\tCTRL+Z')
        AppendMenu(parent, help='', id=wx.ID_REDO,
              kind=wx.ITEM_NORMAL, text=u'Redo\tCTRL+Y')
        self.Bind(wx.EVT_MENU, self.OnRefreshMenu, id=wx.ID_REFRESH)
        self.Bind(wx.EVT_MENU, self.OnUndoMenu, id=wx.ID_UNDO)
        self.Bind(wx.EVT_MENU, self.OnRedoMenu, id=wx.ID_REDO)
    
    def _init_coll_MenuBar_Menus(self, parent):
        parent.Append(menu=self.EditMenu, title=u'&Edit')
    
    def _init_utils(self):
        self.MenuBar = wx.MenuBar()

        self.EditMenu = wx.Menu(title='')
        
        self._init_coll_MenuBar_Menus(self.MenuBar)
        self._init_coll_EditMenu_Items(self.EditMenu)
        
    def _init_ctrls(self, prnt):
        if wx.VERSION >= (2, 8, 0):
            wx.aui.AuiMDIParentFrame.__init__(self, winid=ID_CFILEEDITOR, name=u'CFileEditor', 
                  parent=prnt, pos=wx.DefaultPosition, size=wx.Size(800, 650),
                  style=wx.DEFAULT_FRAME_STYLE|wx.SUNKEN_BORDER|wx.CLIP_CHILDREN, title=u'CFileEditor')
        else:
            wx.Frame.__init__(self, id=ID_CFILEEDITOR, name=u'CFileEditor',
                  parent=prnt, pos=wx.DefaultPosition, size=wx.Size(800, 650),
                  style=wx.DEFAULT_FRAME_STYLE, title=u'CFileEditor')
        self._init_utils()
        self.SetClientSize(wx.Size(1000, 600))
        self.SetMenuBar(self.MenuBar)
        self.Bind(wx.EVT_CLOSE, self.OnCloseFrame)
        
        self.Bind(wx.EVT_MENU, self.OnSaveMenu, id=wx.ID_SAVE)
        accel = wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_CTRL, 83, wx.ID_SAVE)])
        self.SetAcceleratorTable(accel)
        
        if wx.VERSION >= (2, 8, 0):
            self.AUIManager = wx.aui.AuiManager(self)
            self.AUIManager.SetDockSizeConstraint(0.5, 0.5)
        
        if wx.VERSION < (2, 8, 0):
            self.MainSplitter = wx.SplitterWindow(id=ID_CFILEEDITORMAINSPLITTER, 
                  name='MainSplitter', parent=self, point=wx.Point(0, 0),
                  size=wx.Size(-1, -1), style=wx.SP_3D)
            self.MainSplitter.SetNeedUpdating(True)
            self.MainSplitter.SetMinimumPaneSize(1)
        
            self.CFileTree = wx.TreeCtrl(id=ID_CFILEEDITORCFILETREE, 
                  name='CFileTree', parent=self.MainSplitter, pos=wx.Point(0, 0),
                  size=wx.Size(-1, -1), style=wx.TR_HAS_BUTTONS|wx.TR_SINGLE|wx.SUNKEN_BORDER)
        else:
            self.CFileTree = wx.TreeCtrl(id=ID_CFILEEDITORCFILETREE, 
                  name='CFileTree', parent=self, pos=wx.Point(0, 0),
                  size=wx.Size(-1, -1), style=wx.TR_HAS_BUTTONS|wx.TR_SINGLE|wx.SUNKEN_BORDER)
            self.AUIManager.AddPane(self.CFileTree, wx.aui.AuiPaneInfo().Caption("CFile Tree").Left().Layer(1).BestSize(wx.Size(200, 500)).CloseButton(False))
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnCFileTreeItemSelected, 
              id=ID_CFILEEDITORCFILETREE)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnCFileTreeItemActivated,
              id=ID_CFILEEDITORCFILETREE)
        
        if wx.VERSION < (2, 8, 0):
            self.PartsOpened = wx.Notebook(id=ID_CFILEEDITORPARTSOPENED,
                  name='PartsOpened', parent=self.MainSplitter, pos=wx.Point(0,
                  0), size=wx.Size(0, 0), style=0)
            if wx.VERSION >= (2, 6, 0):
                self.PartsOpened.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED,
                    self.OnPartSelectedChanged, id=CFILEEDITORPARTSOPENED)
            else:
                wx.EVT_NOTEBOOK_PAGE_CHANGED(self.PartsOpened, CFILEEDITORPARTSOPENED,
                    self.OnPartSelectedChanged)
            
            self.MainSplitter.SplitVertically(self.ProjectTree, self.PartsOpened, 200)
        
        self.StatusBar = wx.StatusBar( name='HelpBar',
              parent=self, style=wx.ST_SIZEGRIP)
        self.SetStatusBar(self.StatusBar)
        
        if wx.VERSION >= (2, 8, 0):
            self.AUIManager.Update()
    
    def __init__(self, parent, controler):
        self._init_ctrls(parent)
        
        self.Controler = controler

        self.InitCFileTree()
        self.RefreshTitle()
        self.RefreshEditMenu()

    def OnCloseFrame(self, event):
        if wx.VERSION >= (2, 8, 0):
            self.AUIManager.UnInit()
        if getattr(self, "_onclose", None) is not None:
            self._onclose()
        event.Skip()

    def OnCloseTabMenu(self, event):
        selected = self.GetPageSelection()
        if selected >= 0:
            self.DeletePage(selected)
        event.Skip()

    def OnSaveMenu(self, event):
        if getattr(self, "_onsave", None) != None:
            self._onsave()
        self.RefreshTitle()
        self.RefreshEditMenu()
        event.Skip()

#-------------------------------------------------------------------------------
#                            Notebook Unified Functions
#-------------------------------------------------------------------------------

    def GetPageCount(self):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                return notebook.GetPageCount()
            else:
                return 0
        else:
            return self.PartsOpened.GetPageCount()
    
    def GetPage(self, idx):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                return notebook.GetPage(idx).GetViewer()
            else:
                return None
        else:
            return self.PartsOpened.GetPage(idx)

    def GetPageSelection(self):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                return notebook.GetSelection()
            else:
                return -1
        else:
            return self.PartsOpened.GetSelection()

    def SetPageSelection(self, idx):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                notebook.SetSelection(idx)
        else:
            self.PartsOpened.SetSelection(idx)

    def DeletePage(self, idx):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                notebook.DeletePage(idx)
        else:
            self.PartsOpened.DeletePage(idx)

    def DeleteAllPages(self):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                for idx in xrange(notebook.GetPageCount()):
                    notebook.DeletePage(0)
        else:
            self.PartsOpened.DeleteAllPages()

    def SetPageText(self, idx, text):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                return notebook.SetPageText(idx, text)
        else:
            return self.PartsOpened.SetPageText(idx, text)

    def SetPageBitmap(self, idx, bitmap):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                return notebook.SetPageBitmap(idx, bitmap)
        else:
            return self.PartsOpened.SetPageImage(idx, bitmap)

    def GetPageText(self, idx):
        if wx.VERSION >= (2, 8, 0):
            notebook = self.GetNotebook()
            if notebook is not None:
                return notebook.GetPageText(idx)
            else:
                return ""
        else:
            return self.PartsOpened.GetPageText(idx)

    def IsOpened(self, name):
        for idx in xrange(self.GetPageCount()):
            if self.GetPage(idx).IsViewing(name):
                return idx
        return None

    def RefreshTitle(self):
        self.SetTitle("CFileEditor - %s"%self.Controler.GetFilename())
        
#-------------------------------------------------------------------------------
#                          Edit Project Menu Functions
#-------------------------------------------------------------------------------

    def RefreshEditMenu(self):
        if self.EditMenu:
            undo, redo = self.Controler.GetBufferState()
            self.EditMenu.Enable(wx.ID_UNDO, undo)
            self.EditMenu.Enable(wx.ID_REDO, redo)

    def OnRefreshMenu(self, event):
        selected = self.GetPageSelection()
        if selected != -1:
            window = self.GetPage(selected)
            window.RefreshView()
        event.Skip()

    def OnUndoMenu(self, event):
        self.Controler.LoadPrevious()
        selected = self.GetPageSelection()        
        if selected != -1:
            window = self.GetPage(selected)
            window.RefreshView()
        self.RefreshTitle()
        self.RefreshEditMenu()
        event.Skip()
    
    def OnRedoMenu(self, event):
        self.Controler.LoadNext()
        selected = self.GetPageSelection()
        if selected != -1:
            window = self.GetPage(selected)
            window.RefreshView()
        self.RefreshTitle()
        self.RefreshEditMenu()
        event.Skip()
        
#-------------------------------------------------------------------------------
#                      CFile Editor Panels Management Functions
#-------------------------------------------------------------------------------
    
    def OnPartSelectedChanged(self, event):
        if wx.VERSION < (2, 8, 0) or event.GetActive():
            old_selected = self.GetPageSelection()
            if old_selected >= 0:
                self.GetPage(old_selected).ResetBuffer()
            if wx.VERSION >= (2, 8, 0):
                window = event.GetEventObject().GetViewer()
            else:
                selected = event.GetSelection()
                if selected >= 0:
                    window = self.GetPage(selected)
                else:
                    window = None
            if window:
                window.RefreshView()
        event.Skip()

#-------------------------------------------------------------------------------
#                         CFile Tree Management Functions
#-------------------------------------------------------------------------------

    def InitCFileTree(self):
        root = self.CFileTree.AddRoot("C File")
        for name in CFILE_PARTS:
            self.CFileTree.AppendItem(root, name)
        self.CFileTree.Expand(root)

    def OnCFileTreeItemActivated(self, event):
        self.EditCFilePart(self.CFileTree.GetItemText(event.GetItem()))
        event.Skip()

    def OnCFileTreeItemSelected(self, event):
        select_item = event.GetItem()
        self.EditCFilePart(self.CFileTree.GetItemText(event.GetItem()), True)
        event.Skip()
        
    def EditCFilePart(self, name, onlyopened = False):
        openedidx = self.IsOpened(name)
        if openedidx is not None:
            old_selected = self.GetPageSelection()
            if old_selected != openedidx:
                if old_selected >= 0:
                    self.GetPage(old_selected).ResetBuffer()
                self.SetPageSelection(openedidx)
            self.GetPage(openedidx).RefreshView()
        elif not onlyopened:
            if wx.VERSION >= (2, 8, 0):
                if name == "Variables":
                    new_window = MDIVariablesEditor(self, name, self, self.Controler)
                else:
                    new_window = MDICppEditor(self, name, self, self.Controler)
                new_window.Bind(wx.EVT_ACTIVATE, self.OnPartSelectedChanged)
                new_window.Layout()
            else:
                if name == "Variables":
                    new_window = VariablesEditor(self.TabsOpened, self, self.Controler)
                    self.TabsOpened.AddPage(new_window, name)
                else:
                    new_window = CppEditor(self.TabsOpened, name, self, self.Controler)
                    self.TabsOpened.AddPage(new_window, name)
            openedidx = self.IsOpened(name)
            old_selected = self.GetPageSelection()
            if old_selected != openedidx:
                if old_selected >= 0:
                    self.GetPage(old_selected).ResetBuffer()
            for i in xrange(self.GetPageCount()):
                window = self.GetPage(i)
                if window.IsViewing(name):
                    self.SetPageSelection(i)
                    window.RefreshView()
                    window.SetFocus()
