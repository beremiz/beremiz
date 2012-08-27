"""
Minimal tab controller for a simple text editor
"""

import os

class MiniTextControler:
    
    def __init__(self, filepath, controller):
        self.FilePath = filepath
        self.BaseController = controller
    
    def __del__(self):
        self.BaseController = None
    
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
    
    def GetBlockType(self, type, inputs = None, debug = False):
        return self.BaseController.GetBlockType(type, inputs, debug)
    
    def GetBlockTypes(self, tagname = "", debug = False):
        return self.BaseController.GetBlockTypes(tagname, debug)
    
    def GetDataTypes(self, tagname = "", basetypes = True, only_locatables = False, debug = False):
        return self.BaseController.GetDataTypes(tagname, basetypes, only_locatables, debug)
    
    def GetEnumeratedDataValues(self, debug = False):
        return self.BaseController.GetEnumeratedDataValues(debug)
    
    def StartBuffering(self):
        pass

    def EndBuffering(self):
        pass

    def BufferProject(self):
        pass

