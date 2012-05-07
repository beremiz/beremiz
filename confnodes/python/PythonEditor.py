import  wx, wx.grid
import  wx.stc  as  stc
import keyword

from controls import EditorPanel

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

class PythonEditor(EditorPanel):

    fold_symbols = 3
    
    def _init_Editor(self, prnt):
        self.Editor = stc.StyledTextCtrl(id=ID_PYTHONEDITOR, parent=prnt,
                 name="TextViewer", pos=wx.DefaultPosition, 
                 size=wx.DefaultSize, style=0)

        self.Editor.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.Editor.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.Editor.SetLexer(stc.STC_LEX_PYTHON)
        self.Editor.SetKeyWords(0, " ".join(keyword.kwlist))

        self.Editor.SetProperty("fold", "1")
        self.Editor.SetProperty("tab.timmy.whinge.level", "1")
        self.Editor.SetMargins(0,0)

        self.Editor.SetViewWhiteSpace(False)
        
        self.Editor.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.Editor.SetEdgeColumn(78)

        # Set up the numbers in the margin for margin #1
        self.Editor.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
        self.Editor.SetMarginWidth(1, 40)

        # Setup a margin to hold fold markers
        self.Editor.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.Editor.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.Editor.SetMarginSensitive(2, True)
        self.Editor.SetMarginWidth(2, 12)

        if self.fold_symbols == 0:
            # Arrow pointing right for contracted folders, arrow pointing down for expanded
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, "black", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW, "black", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "black", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "black", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     "white", "black")
            
        elif self.fold_symbols == 1:
            # Plus for contracted folders, minus for expanded
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, "white", "black")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, "white", "black")

        elif self.fold_symbols == 2:
            # Like a flattened tree control using circular headers and curved joins
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_CIRCLEMINUS,          "white", "#404040")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLEPLUS,           "white", "#404040")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,                "white", "#404040")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE,         "white", "#404040")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_CIRCLEPLUSCONNECTED,  "white", "#404040")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_CIRCLEMINUSCONNECTED, "white", "#404040")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNERCURVE,         "white", "#404040")

        elif self.fold_symbols == 3:
            # Like a flattened tree control using square headers
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          "white", "#808080")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           "white", "#808080")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             "white", "#808080")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           "white", "#808080")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
            self.Editor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           "white", "#808080")


        self.Editor.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Editor.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.Editor.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        # Global default style
        if wx.Platform == '__WXMSW__':
            self.Editor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Courier New')
        elif wx.Platform == '__WXMAC__':
            # TODO: if this looks fine on Linux too, remove the Mac-specific case 
            # and use this whenever OS != MSW.
            self.Editor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Monaco')
        else:
            defsize = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
            self.Editor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Courier,size:%d'%defsize)

        # Clear styles and revert to default.
        self.Editor.StyleClearAll()

        # Following style specs only indicate differences from default.
        # The rest remains unchanged.

        # Line numbers in margin
        self.Editor.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER,'fore:#000000,back:#99A9C2')    
        # Highlighted brace
        self.Editor.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT,'fore:#00009D,back:#FFFF00')
        # Unmatched brace
        self.Editor.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD,'fore:#00009D,back:#FF0000')
        # Indentation guide
        self.Editor.StyleSetSpec(wx.stc.STC_STYLE_INDENTGUIDE, "fore:#CDCDCD")

        # Python styles
        self.Editor.StyleSetSpec(wx.stc.STC_P_DEFAULT, 'fore:#000000')
        # Comments
        self.Editor.StyleSetSpec(wx.stc.STC_P_COMMENTLINE,  'fore:#008000,back:#F0FFF0')
        self.Editor.StyleSetSpec(wx.stc.STC_P_COMMENTBLOCK, 'fore:#008000,back:#F0FFF0')
        # Numbers
        self.Editor.StyleSetSpec(wx.stc.STC_P_NUMBER, 'fore:#008080')
        # Strings and characters
        self.Editor.StyleSetSpec(wx.stc.STC_P_STRING, 'fore:#800080')
        self.Editor.StyleSetSpec(wx.stc.STC_P_CHARACTER, 'fore:#800080')
        # Keywords
        self.Editor.StyleSetSpec(wx.stc.STC_P_WORD, 'fore:#000080,bold')
        # Triple quotes
        self.Editor.StyleSetSpec(wx.stc.STC_P_TRIPLE, 'fore:#800080,back:#FFFFEA')
        self.Editor.StyleSetSpec(wx.stc.STC_P_TRIPLEDOUBLE, 'fore:#800080,back:#FFFFEA')
        # Class names
        self.Editor.StyleSetSpec(wx.stc.STC_P_CLASSNAME, 'fore:#0000FF,bold')
        # Function names
        self.Editor.StyleSetSpec(wx.stc.STC_P_DEFNAME, 'fore:#008080,bold')
        # Operators
        self.Editor.StyleSetSpec(wx.stc.STC_P_OPERATOR, 'fore:#800000,bold')
        # Identifiers. I leave this as not bold because everything seems
        # to be an identifier if it doesn't match the above criterae
        self.Editor.StyleSetSpec(wx.stc.STC_P_IDENTIFIER, 'fore:#000000')

        # Caret color
        self.Editor.SetCaretForeground("BLUE")
        # Selection background
        self.Editor.SetSelBackground(1, '#66CCFF')

        self.Editor.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.Editor.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        
        # register some images for use in the AutoComplete box.
        #self.RegisterImage(1, images.getSmilesBitmap())
        self.Editor.RegisterImage(1, 
            wx.ArtProvider.GetBitmap(wx.ART_DELETE, size=(16,16)))
        self.Editor.RegisterImage(2, 
            wx.ArtProvider.GetBitmap(wx.ART_NEW, size=(16,16)))
        self.Editor.RegisterImage(3, 
            wx.ArtProvider.GetBitmap(wx.ART_COPY, size=(16,16)))

        # Indentation and tab stuff
        self.Editor.SetIndent(4)               # Proscribed indent size for wx
        self.Editor.SetIndentationGuides(True) # Show indent guides
        self.Editor.SetBackSpaceUnIndents(True)# Backspace unindents rather than delete 1 space
        self.Editor.SetTabIndents(True)        # Tab key indents
        self.Editor.SetTabWidth(4)             # Proscribed tab size for wx
        self.Editor.SetUseTabs(False)          # Use spaces rather than tabs, or
                                        # TabTimmy will complain!    
        # White space
        self.Editor.SetViewWhiteSpace(False)   # Don't view white space

        # EOL: Since we are loading/saving ourselves, and the
        # strings will always have \n's in them, set the STC to
        # edit them that way.            
        self.Editor.SetEOLMode(wx.stc.STC_EOL_LF)
        self.Editor.SetViewEOL(False)
        
        # No right-edge mode indicator
        self.Editor.SetEdgeMode(stc.STC_EDGE_NONE)
        
        self.Editor.SetModEventMask(wx.stc.STC_MOD_BEFOREINSERT|wx.stc.STC_MOD_BEFOREDELETE)

        self.Editor.Bind(wx.stc.EVT_STC_DO_DROP, self.OnDoDrop, id=ID_PYTHONEDITOR)
        self.Editor.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Editor.Bind(wx.stc.EVT_STC_MODIFIED, self.OnModification, id=ID_PYTHONEDITOR)


    def __init__(self, parent, controler, window):
        EditorPanel.__init__(self, parent, "", window, controler)
        
        self.DisableEvents = False
        self.CurrentAction = None
        
        img = wx.Bitmap(self.Controler.GetIconPath("Cfile.png"), wx.BITMAP_TYPE_PNG).ConvertToImage()
        self.SetIcon(wx.BitmapFromImage(img.Rescale(16, 16)))
    
    def __del__(self):
        self.Controler.OnCloseEditor(self)
    
    def GetTitle(self):
        fullname = self.Controler.PlugFullName()
        if not self.Controler.PythonIsSaved():
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
    
    def HasNoModel(self):
        return False
    
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
        self.ResetBuffer()
        self.DisableEvents = True
        old_cursor_pos = self.Editor.GetCurrentPos()
        old_text = self.Editor.GetText()
        new_text = self.Controler.GetPythonCode()
        self.Editor.SetText(new_text)
        new_cursor_pos = GetCursorPos(old_text, new_text)
        if new_cursor_pos != None:
            self.Editor.GotoPos(new_cursor_pos)
        else:
            self.Editor.GotoPos(old_cursor_pos)
        self.Editor.ScrollToColumn(0)
        self.Editor.EmptyUndoBuffer()
        self.DisableEvents = False
        
        self.Editor.Colourise(0, -1)

    def RefreshModel(self):
        self.Controler.SetPythonCode(self.Editor.GetText())

    def OnKeyPressed(self, event):
        if self.Editor.CallTipActive():
            self.Editor.CallTipCancel()
        key = event.GetKeyCode()

        if key == 32 and event.ControlDown():
            pos = self.Editor.GetCurrentPos()

            # Tips
            if event.ShiftDown():
                pass
##                self.CallTipSetBackground("yellow")
##                self.CallTipShow(pos, 'lots of of text: blah, blah, blah\n\n'
##                                 'show some suff, maybe parameters..\n\n'
##                                 'fubar(param1, param2)')
            # Code completion
            else:
                self.Editor.AutoCompSetIgnoreCase(False)  # so this needs to match

                # Images are specified with a appended "?type"
                self.Editor.AutoCompShow(0, " ".join([word + "?1" for word in keyword.kwlist]))
        else:
            event.Skip()

    def OnKillFocus(self, event):
        self.Editor.AutoCompCancel()
        event.Skip()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.Editor.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.Editor.GetCharAt(caretPos - 1)
            styleBefore = self.Editor.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.Editor.GetCharAt(caretPos)
            styleAfter = self.Editor.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.Editor.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.Editor.BraceBadLight(braceAtCaret)
        else:
            self.Editor.BraceHighlight(braceAtCaret, braceOpposite)
            #pt = self.Editor.PointFromPosition(braceOpposite)
            #self.Editor.Refresh(True, wxRect(pt.x, pt.y, 5,5))
            #print pt
            #self.Editor.Refresh(False)


    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.Editor.LineFromPosition(evt.GetPosition())

                if self.Editor.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.Editor.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.Editor.GetFoldExpanded(lineClicked):
                            self.Editor.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.Editor.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.Editor.ToggleFold(lineClicked)


    def FoldAll(self):
        lineCount = self.Editor.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.Editor.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.Editor.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.Editor.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.Editor.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.Editor.GetLastChild(lineNum, -1)
                    self.Editor.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.Editor.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1



    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.Editor.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.Editor.ShowLines(line, line)
                else:
                    self.Editor.HideLines(line, line)
            else:
                if doExpand:
                    self.Editor.ShowLines(line, line)

            if level == -1:
                level = self.Editor.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.Editor.SetFoldExpanded(line, True)
                    else:
                        self.Editor.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.Editor.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def Cut(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.Editor.CmdKeyExecute(wx.stc.STC_CMD_CUT)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()
    
    def Copy(self):
        self.Editor.CmdKeyExecute(wx.stc.STC_CMD_COPY)
    
    def Paste(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.Editor.CmdKeyExecute(wx.stc.STC_CMD_PASTE)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()
