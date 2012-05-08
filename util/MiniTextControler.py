"""
Minimal tab controller for a simple text editor
"""

import os

class MiniTextControler:
    
    def __init__(self, filepath):
        self.FilePath = filepath
    
    def CTNFullName(self):
        return ""
    
    def SetEditedElementText(self, tagname, text):
        file = open(self.FilePath, "w")
        file.write(text)
        file.close()
        
    def GetEditedElementText(self, tagname, debug = False):
        if os.path.isfile(self.FilePath):
            file = open(self.FilePath, "r")
            text = file.read()
            file.close()
            return text
        return ""
    
    def GetEditedElementInterfaceVars(self, tagname, debug = False):
        return []
    
    def GetEditedElementType(self, tagname, debug = False):
        return "program"
    
    def GetBlockTypes(self, tagname = "", debug = False):
        return []
    
    def GetDataTypes(self, tagname = "", basetypes = True, only_locatables = False, debug = False):
        return []
    
    def GetEnumeratedDataValues(self, debug = False):
        return []
    
    def StartBuffering(self):
        pass

    def EndBuffering(self):
        pass

    def BufferProject(self):
        pass

