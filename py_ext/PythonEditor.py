import re
import keyword

import wx
import wx.grid
import wx.stc as stc

from plcopen.plcopen import TestTextElement
from graphics.GraphicCommons import ERROR_HIGHLIGHT, SEARCH_RESULT_HIGHLIGHT, REFRESH_HIGHLIGHT_PERIOD
from editors.ConfTreeNodeEditor import ConfTreeNodeEditor
from editors.TextViewer import GetCursorPos, faces

[STC_PYTHON_ERROR, STC_PYTHON_SEARCH_RESULT] = range(15, 17)

HIGHLIGHT_TYPES = {
    ERROR_HIGHLIGHT: STC_PYTHON_ERROR,
    SEARCH_RESULT_HIGHLIGHT: STC_PYTHON_SEARCH_RESULT,
}

[ID_PYTHONEDITOR,
] = [wx.NewId() for _init_ctrls in range(1)]

class PythonEditor(ConfTreeNodeEditor):

    fold_symbols = 3
    CONFNODEEDITOR_TABS = [
        (_("Python code"), "_create_PythonCodeEditor")]
    
    def _create_PythonCodeEditor(self, prnt):
        self.PythonCodeEditor = stc.StyledTextCtrl(id=ID_PYTHONEDITOR, parent=prnt,
                 name="TextViewer", pos=wx.DefaultPosition, 
                 size=wx.DefaultSize, style=0)
        self.PythonCodeEditor.ParentWindow = self
        
        self.PythonCodeEditor.CmdKeyAssign(ord('B'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMIN)
        self.PythonCodeEditor.CmdKeyAssign(ord('N'), stc.STC_SCMOD_CTRL, stc.STC_CMD_ZOOMOUT)

        self.PythonCodeEditor.SetLexer(stc.STC_LEX_PYTHON)
        self.PythonCodeEditor.SetKeyWords(0, " ".join(keyword.kwlist))

        self.PythonCodeEditor.SetProperty("fold", "1")
        self.PythonCodeEditor.SetProperty("tab.timmy.whinge.level", "1")
        self.PythonCodeEditor.SetMargins(0,0)

        self.PythonCodeEditor.SetViewWhiteSpace(False)
        
        self.PythonCodeEditor.SetEdgeMode(stc.STC_EDGE_BACKGROUND)
        self.PythonCodeEditor.SetEdgeColumn(78)

        # Set up the numbers in the margin for margin #1
        self.PythonCodeEditor.SetMarginType(1, wx.stc.STC_MARGIN_NUMBER)
        # Reasonable value for, say, 4-5 digits using a mono font (40 pix)
        self.PythonCodeEditor.SetMarginWidth(1, 40)

        # Setup a margin to hold fold markers
        self.PythonCodeEditor.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.PythonCodeEditor.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.PythonCodeEditor.SetMarginSensitive(2, True)
        self.PythonCodeEditor.SetMarginWidth(2, 12)

        if self.fold_symbols == 0:
            # Arrow pointing right for contracted folders, arrow pointing down for expanded
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_ARROWDOWN, "black", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_ARROW, "black", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "black", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "black", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY,     "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY,     "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY,     "white", "black")
            
        elif self.fold_symbols == 1:
            # Plus for contracted folders, minus for expanded
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, "white", "black")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, "white", "black")

        elif self.fold_symbols == 2:
            # Like a flattened tree control using circular headers and curved joins
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_CIRCLEMINUS,          "white", "#404040")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_CIRCLEPLUS,           "white", "#404040")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,                "white", "#404040")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNERCURVE,         "white", "#404040")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_CIRCLEPLUSCONNECTED,  "white", "#404040")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_CIRCLEMINUSCONNECTED, "white", "#404040")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNERCURVE,         "white", "#404040")

        elif self.fold_symbols == 3:
            # Like a flattened tree control using square headers
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_BOXMINUS,          "white", "#808080")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_BOXPLUS,           "white", "#808080")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_VLINE,             "white", "#808080")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_LCORNER,           "white", "#808080")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_BOXPLUSCONNECTED,  "white", "#808080")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_BOXMINUSCONNECTED, "white", "#808080")
            self.PythonCodeEditor.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_TCORNER,           "white", "#808080")


        self.PythonCodeEditor.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.PythonCodeEditor.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        self.PythonCodeEditor.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)
        
        # Global default style
        if wx.Platform == '__WXMSW__':
            self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Courier New')
        elif wx.Platform == '__WXMAC__':
            # TODO: if this looks fine on Linux too, remove the Mac-specific case 
            # and use this whenever OS != MSW.
            self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Monaco')
        else:
            defsize = wx.SystemSettings.GetFont(wx.SYS_ANSI_FIXED_FONT).GetPointSize()
            self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_DEFAULT, 'fore:#000000,back:#FFFFFF,face:Courier,size:%d'%defsize)

        # Clear styles and revert to default.
        self.PythonCodeEditor.StyleClearAll()

        # Following style specs only indicate differences from default.
        # The rest remains unchanged.

        # Line numbers in margin
        self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_LINENUMBER,'fore:#000000,back:#99A9C2,size:%(size)d' % faces)    
        # Highlighted brace
        self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,'fore:#00009D,back:#FFFF00,size:%(size)d' % faces)
        # Unmatched brace
        self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_BRACEBAD,'fore:#00009D,back:#FF0000,size:%(size)d' % faces)
        # Indentation guide
        self.PythonCodeEditor.StyleSetSpec(stc.STC_STYLE_INDENTGUIDE, 'fore:#CDCDCD,size:%(size)d' % faces)

        # Python styles
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_DEFAULT, 'fore:#000000,size:%(size)d' % faces)
        # Comments
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_COMMENTLINE,  'fore:#008000,back:#F0FFF0,size:%(size)d' % faces)
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_COMMENTBLOCK, 'fore:#008000,back:#F0FFF0,size:%(size)d' % faces)
        # Numbers
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_NUMBER, 'fore:#008080,size:%(size)d' % faces)
        # Strings and characters
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_STRING, 'fore:#800080,size:%(size)d' % faces)
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_CHARACTER, 'fore:#800080,size:%(size)d' % faces)
        # Keywords
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_WORD, 'fore:#000080,bold,size:%(size)d' % faces)
        # Triple quotes
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_TRIPLE, 'fore:#800080,back:#FFFFEA,size:%(size)d' % faces)
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, 'fore:#800080,back:#FFFFEA,size:%(size)d' % faces)
        # Class names
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_CLASSNAME, 'fore:#0000FF,bold,size:%(size)d' % faces)
        # Function names
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_DEFNAME, 'fore:#008080,bold,size:%(size)d' % faces)
        # Operators
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_OPERATOR, 'fore:#800000,bold,size:%(size)d' % faces)
        # Identifiers. I leave this as not bold because everything seems
        # to be an identifier if it doesn't match the above criterae
        self.PythonCodeEditor.StyleSetSpec(stc.STC_P_IDENTIFIER, 'fore:#000000,size:%(size)d' % faces)
        
        # Highlighting styles
        self.PythonCodeEditor.StyleSetSpec(STC_PYTHON_ERROR, 'fore:#FF0000,back:#FFFF00,size:%(size)d' % faces)
        self.PythonCodeEditor.StyleSetSpec(STC_PYTHON_SEARCH_RESULT, 'fore:#FFFFFF,back:#FFA500,size:%(size)d' % faces)
        
        # Caret color
        self.PythonCodeEditor.SetCaretForeground("BLUE")
        # Selection background
        self.PythonCodeEditor.SetSelBackground(1, '#66CCFF')

        self.PythonCodeEditor.SetSelBackground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHT))
        self.PythonCodeEditor.SetSelForeground(True, wx.SystemSettings_GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT))
        
        # register some images for use in the AutoComplete box.
        #self.RegisterImage(1, images.getSmilesBitmap())
        self.PythonCodeEditor.RegisterImage(1, 
            wx.ArtProvider.GetBitmap(wx.ART_DELETE, size=(16,16)))
        self.PythonCodeEditor.RegisterImage(2, 
            wx.ArtProvider.GetBitmap(wx.ART_NEW, size=(16,16)))
        self.PythonCodeEditor.RegisterImage(3, 
            wx.ArtProvider.GetBitmap(wx.ART_COPY, size=(16,16)))

        # Indentation and tab stuff
        self.PythonCodeEditor.SetIndent(4)               # Proscribed indent size for wx
        self.PythonCodeEditor.SetIndentationGuides(True) # Show indent guides
        self.PythonCodeEditor.SetBackSpaceUnIndents(True)# Backspace unindents rather than delete 1 space
        self.PythonCodeEditor.SetTabIndents(True)        # Tab key indents
        self.PythonCodeEditor.SetTabWidth(4)             # Proscribed tab size for wx
        self.PythonCodeEditor.SetUseTabs(False)          # Use spaces rather than tabs, or
                                        # TabTimmy will complain!    
        # White space
        self.PythonCodeEditor.SetViewWhiteSpace(False)   # Don't view white space

        # EOL: Since we are loading/saving ourselves, and the
        # strings will always have \n's in them, set the STC to
        # edit them that way.            
        self.PythonCodeEditor.SetEOLMode(stc.STC_EOL_LF)
        self.PythonCodeEditor.SetViewEOL(False)
        
        # No right-edge mode indicator
        self.PythonCodeEditor.SetEdgeMode(stc.STC_EDGE_NONE)
        
        self.PythonCodeEditor.SetModEventMask(stc.STC_MOD_BEFOREINSERT|stc.STC_MOD_BEFOREDELETE)

        self.PythonCodeEditor.Bind(wx.stc.EVT_STC_DO_DROP, self.OnDoDrop, id=ID_PYTHONEDITOR)
        self.PythonCodeEditor.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.PythonCodeEditor.Bind(wx.stc.EVT_STC_MODIFIED, self.OnModification, id=ID_PYTHONEDITOR)
        
        return self.PythonCodeEditor

    def __init__(self, parent, controler, window):
        ConfTreeNodeEditor.__init__(self, parent, controler, window)
        
        self.DisableEvents = False
        self.CurrentAction = None
    
        self.Highlights = []
        self.SearchParams = None
        self.SearchResults = None
        self.CurrentFindHighlight = None
        
        self.RefreshHighlightsTimer = wx.Timer(self, -1)
        self.Bind(wx.EVT_TIMER, self.OnRefreshHighlightsTimer, self.RefreshHighlightsTimer)
    
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
        old_cursor_pos = self.PythonCodeEditor.GetCurrentPos()
        line = self.PythonCodeEditor.GetFirstVisibleLine()
        column = self.PythonCodeEditor.GetXOffset()
        old_text = self.PythonCodeEditor.GetText()
        new_text = self.Controler.GetPythonCode()
        if old_text != new_text:
            self.PythonCodeEditor.SetText(new_text)
            new_cursor_pos = GetCursorPos(old_text, new_text)
            self.PythonCodeEditor.LineScroll(column, line)
            if new_cursor_pos != None:
                self.PythonCodeEditor.GotoPos(new_cursor_pos)
            else:
                self.PythonCodeEditor.GotoPos(old_cursor_pos)
            self.PythonCodeEditor.EmptyUndoBuffer()
        self.DisableEvents = False
        
        self.PythonCodeEditor.Colourise(0, -1)
        
        self.ShowHighlights()

    def RefreshModel(self):
        self.Controler.SetPythonCode(self.PythonCodeEditor.GetText())

    def OnKeyPressed(self, event):
        if self.PythonCodeEditor.CallTipActive():
            self.PythonCodeEditor.CallTipCancel()
        key = event.GetKeyCode()

        if key == 32 and event.ControlDown():
            pos = self.PythonCodeEditor.GetCurrentPos()

            # Code completion
            if not event.ShiftDown():
                self.PythonCodeEditor.AutoCompSetIgnoreCase(False)  # so this needs to match

                # Images are specified with a appended "?type"
                self.PythonCodeEditor.AutoCompShow(0, " ".join([word + "?1" for word in keyword.kwlist]))
        else:
            event.Skip()
    
    def OnKillFocus(self, event):
        self.PythonCodeEditor.AutoCompCancel()
        event.Skip()

    def OnUpdateUI(self, evt):
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = self.PythonCodeEditor.GetCurrentPos()

        if caretPos > 0:
            charBefore = self.PythonCodeEditor.GetCharAt(caretPos - 1)
            styleBefore = self.PythonCodeEditor.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.PythonCodeEditor.GetCharAt(caretPos)
            styleAfter = self.PythonCodeEditor.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.PythonCodeEditor.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.PythonCodeEditor.BraceBadLight(braceAtCaret)
        else:
            self.PythonCodeEditor.BraceHighlight(braceAtCaret, braceOpposite)

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.PythonCodeEditor.LineFromPosition(evt.GetPosition())

                if self.PythonCodeEditor.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.PythonCodeEditor.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.PythonCodeEditor.GetFoldExpanded(lineClicked):
                            self.PythonCodeEditor.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.PythonCodeEditor.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.PythonCodeEditor.ToggleFold(lineClicked)


    def FoldAll(self):
        lineCount = self.PythonCodeEditor.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.PythonCodeEditor.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.PythonCodeEditor.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.PythonCodeEditor.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.PythonCodeEditor.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.PythonCodeEditor.GetLastChild(lineNum, -1)
                    self.PythonCodeEditor.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.PythonCodeEditor.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1



    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.PythonCodeEditor.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.PythonCodeEditor.ShowLines(line, line)
                else:
                    self.PythonCodeEditor.HideLines(line, line)
            else:
                if doExpand:
                    self.PythonCodeEditor.ShowLines(line, line)

            if level == -1:
                level = self.PythonCodeEditor.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.PythonCodeEditor.SetFoldExpanded(line, True)
                    else:
                        self.PythonCodeEditor.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.PythonCodeEditor.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

    def Cut(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.PythonCodeEditor.CmdKeyExecute(wx.stc.STC_CMD_CUT)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()
    
    def Copy(self):
        self.PythonCodeEditor.CmdKeyExecute(wx.stc.STC_CMD_COPY)
    
    def Paste(self):
        self.ResetBuffer()
        self.DisableEvents = True
        self.PythonCodeEditor.CmdKeyExecute(wx.stc.STC_CMD_PASTE)
        self.DisableEvents = False
        self.RefreshModel()
        self.RefreshBuffer()

    def Find(self, direction, search_params):
        if self.SearchParams != search_params:
            self.ClearHighlights(SEARCH_RESULT_HIGHLIGHT)
            
            self.SearchParams = search_params
            criteria = {
                "raw_pattern": search_params["find_pattern"], 
                "pattern": re.compile(search_params["find_pattern"]),
                "case_sensitive": search_params["case_sensitive"],
                "regular_expression": search_params["regular_expression"],
                "filter": "all"}
            
            self.SearchResults = [
                (start, end, SEARCH_RESULT_HIGHLIGHT)
                for start, end, text in 
                TestTextElement(self.PythonCodeEditor.GetText(), criteria)]
            self.CurrentFindHighlight = None
        
        if len(self.SearchResults) > 0:
            if self.CurrentFindHighlight is not None:
                old_idx = self.SearchResults.index(self.CurrentFindHighlight)
                if self.SearchParams["wrap"]:
                    idx = (old_idx + direction) % len(self.SearchResults)
                else:
                    idx = max(0, min(old_idx + direction, len(self.SearchResults) - 1))
                if idx != old_idx:
                    self.RemoveHighlight(*self.CurrentFindHighlight)
                    self.CurrentFindHighlight = self.SearchResults[idx]
                    self.AddHighlight(*self.CurrentFindHighlight)
            else:
                self.CurrentFindHighlight = self.SearchResults[0]
                self.AddHighlight(*self.CurrentFindHighlight)
            
        else:
            if self.CurrentFindHighlight is not None:
                self.RemoveHighlight(*self.CurrentFindHighlight)
            self.CurrentFindHighlight = None

#-------------------------------------------------------------------------------
#                        Highlights showing functions
#-------------------------------------------------------------------------------

    def OnRefreshHighlightsTimer(self, event):
        self.RefreshView()
        event.Skip()

    def ClearHighlights(self, highlight_type=None):
        if highlight_type is None:
            self.Highlights = []
        else:
            highlight_type = HIGHLIGHT_TYPES.get(highlight_type, None)
            if highlight_type is not None:
                self.Highlights = [(start, end, highlight) for (start, end, highlight) in self.Highlights if highlight != highlight_type]
        self.RefreshView()

    def AddHighlight(self, start, end, highlight_type):
        highlight_type = HIGHLIGHT_TYPES.get(highlight_type, None)
        if highlight_type is not None:
            self.Highlights.append((start, end, highlight_type))
            self.PythonCodeEditor.GotoPos(self.PythonCodeEditor.PositionFromLine(start[0]) + start[1])
            self.RefreshHighlightsTimer.Start(int(REFRESH_HIGHLIGHT_PERIOD * 1000), oneShot=True)
            self.RefreshView()

    def RemoveHighlight(self, start, end, highlight_type):
        highlight_type = HIGHLIGHT_TYPES.get(highlight_type, None)
        if (highlight_type is not None and 
            (start, end, highlight_type) in self.Highlights):
            self.Highlights.remove((start, end, highlight_type))
            self.RefreshHighlightsTimer.Start(int(REFRESH_HIGHLIGHT_PERIOD * 1000), oneShot=True)
    
    def ShowHighlights(self):
        for start, end, highlight_type in self.Highlights:
            if start[0] == 0:
                highlight_start_pos = start[1]
            else:
                highlight_start_pos = self.PythonCodeEditor.GetLineEndPosition(start[0] - 1) + start[1] + 1
            if end[0] == 0:
                highlight_end_pos = end[1] - indent + 1
            else:
                highlight_end_pos = self.PythonCodeEditor.GetLineEndPosition(end[0] - 1) + end[1] + 2
            self.PythonCodeEditor.StartStyling(highlight_start_pos, 0xff)
            self.PythonCodeEditor.SetStyling(highlight_end_pos - highlight_start_pos, highlight_type)
            self.PythonCodeEditor.StartStyling(highlight_start_pos, 0x00)
            self.PythonCodeEditor.SetStyling(len(self.PythonCodeEditor.GetText()) - highlight_end_pos, stc.STC_STYLE_DEFAULT)
                
