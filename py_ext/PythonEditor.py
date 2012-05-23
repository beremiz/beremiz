import wx
import wx.grid
import wx.stc  as  stc
import keyword

from ConfTreeNodeEditor import ConfTreeNodeEditor

if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 10,
              'size2': 8,
             }
elif wx.Platform == '__WXMAC__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Monaco',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 12,
              'size2': 10,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 12,
              'size2': 10,
             }

[ID_PYTHONEDITOR,
] = [wx.NewId() for _init_ctrls in range(1)]

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

class PythonEditor(ConfTreeNodeEditor):

    fold_symbols = 3
    
    def _init_ConfNodeEditor(self, prnt):
        self.ConfNodeEditor = stc.StyledTextCtrl(id=ID_PYTHONEDITOR, parent=prnt,
                 name="TextViewer", pos=wx.DefaultPosition, 
                 size=wx.DefaultSize, style=0)

        self.ConfNodeEditor.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.ConfNodeEditor.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.ConfNodeEditor.SetLexer(stc.STC_LEX_PYTHON)
        self.ConfNodeEditor.SetKeyWords(0, " ".join(keyword.kwlist))

        self.ConfNodeEditor.SetProperty("fold", "1")
        self.ConfNodeEditor.SetProperty("tab.timmy.whinge.level", "1")
        self.ConfNodeEditor.SetMargins(0,0)

        self.ConfNodeEditor.SetViewWhiteSpace(False)
        
        self.ConfNodeEditor.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.ConfNodeEditor.SetEdgeColumn(78)

        # Set up the numbers in the margin for margin #1
        self.ConfNodeEditor.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
        self.ConfNodeEditor.SetMarginWidth(1, 40)

        # Setup a margin to hold fold markers
        self.ConfNodeEditor.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.ConfNodeEditor.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.ConfNodeEditor.SetMarginSensitive(2, True)
        self.ConfNodeEditor.SetMarginWidth(2, 12)

        if self.fold_symbols == 0:
            # Arrow pointing right for contracted folders, arrow pointing down for expanded
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, "black", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW, "black", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "black", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "black", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     "white", "black")
            
        elif self.fold_symbols == 1:
            # Plus for contracted folders, minus for expanded
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, "white", "black")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, "white", "black")

        elif self.fold_symbols == 2:
            # Like a flattened tree control using circular headers and curved joins
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_CIRCLEMINUS,          "white", "#404040")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLEPLUS,           "white", "#404040")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,                "white", "#404040")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE,         "white", "#404040")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_CIRCLEPLUSCONNECTED,  "white", "#404040")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_CIRCLEMINUSCONNECTED, "white", "#404040")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNERCURVE,         "white", "#404040")

        elif self.fold_symbols == 3:
            # Like a flattened tree control using square headers
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          "white", "#808080")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           "white", "#808080")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             "white", "#808080")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           "white", "#808080")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
            self.ConfNodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           "white", "#808080")


        self.ConfNodeEditor.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.ConfNodeEditor.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.ConfNodeEditor.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        # Global default style
        if wx.Platform == '__WXMSW__':
            self.ConfNodeEditor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Courier New')
        elif wx.Platform == '__WXMAC__':
            # TODO: if this looks fine on Linux too, remove the Mac-specific case 
            # and use this whenever OS != MSW.
            self.ConfNodeEditor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Monaco')
        else:
            defsize = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
            self.ConfNodeEditor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Courier,size:%d'%defsize)

        # Clear styles and revert to default.
        self.ConfNodeEditor.StyleClearAll()

        # Following style specs only indicate differences from default.
        # The rest remains unchanged.

        # Line numbers in margin
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,'fore:#000000,back:#99A9C2')    
        # Highlighted brace
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,'fore:#00009D,back:#FFFF00')
        # Unmatched brace
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,'fore:#00009D,back:#FF0000')
        # Indentation guide
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_STYLE_INDENTGUIDE, "fore:#CDCDCD")

        # Python styles
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_DEFAULT, 'fore:#000000')
        # Comments
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_COMMENTLINE,  'fore:#008000,back:#F0FFF0')
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_COMMENTBLOCK, 'fore:#008000,back:#F0FFF0')
        # Numbers
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_NUMBER, 'fore:#008080')
        # Strings and characters
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_STRING, 'fore:#800080')
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_CHARACTER, 'fore:#800080')
        # Keywords
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_WORD, 'fore:#000080,bold')
        # Triple quotes
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_TRIPLE, 'fore:#800080,back:#FFFFEA')
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_TRIPLEDOUBLE, 'fore:#800080,back:#FFFFEA')
        # Class names
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_CLASSNAME, 'fore:#0000FF,bold')
        # Function names
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_DEFNAME, 'fore:#008080,bold')
        # Operators
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_OPERATOR, 'fore:#800000,bold')
        # Identifiers. I leave this as not bold because everything seems
        # to be an identifier if it doesn't match the above criterae
        self.ConfNodeEditor.StyleSetSpec(wx.stc.STC_P_IDENTIFIER, 'fore:#000000')

        # Caret color
        self.ConfNodeEditor.SetCaretForeground("BLUE")
        # Selection background
        self.ConfNodeEditor.SetSelBackground(1, '#66CCFF')

        self.ConfNodeEditor.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.ConfNodeEditor.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        
        # register some images for use in the AutoComplete box.
        #self.RegisterImage(1, images.getSmilesBitmap())
        self.ConfNodeEditor.RegisterImage(1, 
            wx.ArtProvider.GetBitmap(wx.ART_DELETE, size=(16,16)))
        self.ConfNodeEditor.RegisterImage(2, 
            wx.ArtProvider.GetBitmap(wx.ART_NEW, size=(16,16)))
        self.ConfNodeEditor.RegisterImage(3, 
            wx.ArtProvider.GetBitmap(wx.ART_COPY, size=(16,16)))

        # Indentation and tab stuff
        self.ConfNodeEditor.SetIndent(4)               # Proscribed indent size for wx
        self.ConfNodeEditor.SetIndentationGuides(True) # Show indent guides
        self.ConfNodeEditor.SetBackSpaceUnIndents(True)# Backspace unindents rather than delete 1 space
        self.ConfNodeEditor.SetTabIndents(True)        # Tab key indents
        self.ConfNodeEditor.SetTabWidth(4)             # Proscribed tab size for wx
        self.ConfNodeEditor.SetUseTabs(False)          # Use spaces rather than tabs, or
                                        # TabTimmy will complain!    
        # White space
        self.ConfNodeEditor.SetViewWhiteSpace(False)   # Don't view white space

        # EOL: Since we are loading/saving ourselves, and the
        # strings will always have \n's in them, set the STC to
        # edit them that way.            
        self.ConfNodeEditor.SetEOLMode(wx.stc.STC_EOL_LF)
        self.ConfNodeEditor.SetViewEOL(False)
        
        # No right-edge mode indicator
        self.ConfNodeEditor.SetEdgeMode(stc.STC_EDGE_NONE)
        
        self.ConfNodeEditor.SetModEventMask(wx.stc.STC_MOD_BEFOREINSERT|wx.stc.STC_MOD_BEFOREDELETE)

        self.ConfNodeEditor.Bind(wx.stc.EVT_STC_DO_DROP, self.OnDoDrop, id=ID_PYTHONEDITOR)
        self.ConfNodeEditor.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.ConfNodeEditor.Bind(wx.stc.EVT_STC_MODIFIED, self.OnModification, id=ID_PYTHONEDITOR)


    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
        
        self.DisableEvents = False
        self.CurrentAction = None
    
    def GetBufferState(self):
        return self.Controler.GetBufferState()
        
    def Undo(self):
        self.Controler.LoadPrevious()
        self.RefreshView()
            
    def Redo(self):
        self.Controler.LoadNext()
        self.RefreshView()
    
    def OnModification(self, event):
        if not self.DisableEvents:
            mod_type = event.GetModificationType()
            if not (mod_type&wx.stc.STC_PERFORMED_UNDO or mod_type&wx.stc.STC_PERFORMED_REDO):
                if mod_type&wx.stc.STC_MOD_BEFOREINSERT:
                    if self.CurrentAction is None:
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
        self.Controler.BufferPython()
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
        ConfTreeNodeEditor.RefreshView(self)
        
        self.ResetBuffer()
        self.DisableEvents = True
        old_cursor_pos = self.ConfNodeEditor.GetCurrentPos()
        old_text = self.ConfNodeEditor.GetText()
        new_text = self.Controler.GetPythonCode()
        self.ConfNodeEditor.SetText(new_text)
        new_cursor_pos = GetCursorPos(old_text, new_text)
        if new_cursor_pos != None:
            self.ConfNodeEditor.GotoPos(new_cursor_pos)
        else:
            self.ConfNodeEditor.GotoPos(old_cursor_pos)
        self.ConfNodeEditor.ScrollToColumn(0)
        self.ConfNodeEditor.EmptyUndoBuffer()
        self.DisableEvents = False
        
        self.ConfNodeEditor.Colourise(0, -1)

    def RefreshModel(self):
        self.Controler.SetPythonCode(self.ConfNodeEditor.GetText())

    def OnKeyPressed(self, event):
        if self.ConfNodeEditor.CallTipActive():
            self.ConfNodeEditor.CallTipCancel()
        key = event.GetKeyCode()

        if key == 32 and event.ControlDown():
            pos = self.ConfNodeEditor.GetCurrentPos()

            # Code completion
            if not event.ShiftDown():
                self.ConfNodeEditor.AutoCompSetIgnoreCase(False)  # so this needs to match

                # Images are specified with a appended "?type"
                self.ConfNodeEditor.AutoCompShow(0, " ".join([word + "?1" for word in keyword.kwlist]))
        else:
            event.Skip()

    def OnKillFocus(self, event):
        self.ConfNodeEditor.AutoCompCancel()
        event.Skip()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.ConfNodeEditor.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.ConfNodeEditor.GetCharAt(caretPos - 1)
            styleBefore = self.ConfNodeEditor.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.ConfNodeEditor.GetCharAt(caretPos)
            styleAfter = self.ConfNodeEditor.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.ConfNodeEditor.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.ConfNodeEditor.BraceBadLight(braceAtCaret)
        else:
            self.ConfNodeEditor.BraceHighlight(braceAtCaret, braceOpposite)

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.ConfNodeEditor.LineFromPosition(evt.GetPosition())

                if self.ConfNodeEditor.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.ConfNodeEditor.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.ConfNodeEditor.GetFoldExpanded(lineClicked):
                            self.ConfNodeEditor.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.ConfNodeEditor.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ConfNodeEditor.ToggleFold(lineClicked)


    def FoldAll(self):
        lineCount = self.ConfNodeEditor.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.ConfNodeEditor.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.ConfNodeEditor.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.ConfNodeEditor.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.ConfNodeEditor.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.ConfNodeEditor.GetLastChild(lineNum, -1)
                    self.ConfNodeEditor.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.ConfNodeEditor.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1



    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.ConfNodeEditor.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ConfNodeEditor.ShowLines(line, line)
                else:
                    self.ConfNodeEditor.HideLines(line, line)
            else:
                if doExpand:
                    self.ConfNodeEditor.ShowLines(line, line)

            if level == -1:
                level = self.ConfNodeEditor.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.ConfNodeEditor.SetFoldExpanded(line, True)
                    else:
                        self.ConfNodeEditor.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.ConfNodeEditor.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def Cut(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.ConfNodeEditor.CmdKeyExecute(wx.stc.STC_CMD_CUT)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()
    
    def Copy(self):
        self.ConfNodeEditor.CmdKeyExecute(wx.stc.STC_CMD_COPY)
    
    def Paste(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.ConfNodeEditor.CmdKeyExecute(wx.stc.STC_CMD_PASTE)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()
