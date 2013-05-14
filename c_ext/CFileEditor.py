
import wx.stc as stc

from controls.CustomStyledTextCtrl import faces
from editors.CodeFileEditor import CodeFileEditor, CodeEditor

class CppEditor(CodeEditor):

    KEYWORDS = ["asm", "auto", "bool", "break", "case", "catch", "char", "class", 
        "const", "const_cast", "continue", "default", "delete", "do", "double", 
        "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false", 
        "float", "for", "friend", "goto", "if", "inline", "int", "long", "mutable", 
        "namespace", "new", "operator", "private", "protected", "public", "register", 
        "reinterpret_cast", "return", "short", "signed", "sizeof", "static", 
        "static_cast", "struct", "switch", "template", "this", "throw", "true", "try",
        "typedef", "typeid", "typename", "union", "unsigned", "using", "virtual", 
        "void", "volatile", "wchar_t", "while"]
    COMMENT_HEADER = "/"
    
    def SetCodeLexer(self):
        self.SetLexer(stc.STC_LEX_CPP)
        
        self.StyleSetSpec(stc.STC_C_COMMENT, 'fore:#408060,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_COMMENTLINE, 'fore:#408060,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_COMMENTDOC, 'fore:#408060,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_NUMBER, 'fore:#0076AE,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_WORD, 'bold,fore:#800056,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_STRING, 'fore:#2a00ff,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_PREPROCESSOR, 'bold,fore:#800056,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_OPERATOR, 'bold,size:%(size)d' % faces)
        self.StyleSetSpec(stc.STC_C_STRINGEOL, 'back:#FFD5FF,size:%(size)d' % faces)

#-------------------------------------------------------------------------------
#                          CFileEditor Main Frame Class
#-------------------------------------------------------------------------------

class CFileEditor(CodeFileEditor):
    
    CONFNODEEDITOR_TABS = [
        (_("C code"), "_create_CodePanel")]
    CODE_EDITOR = CppEditor



