import os
from PLCControler import UndoBuffer
from PythonEditor import PythonEditor

from xml.dom import minidom
from xmlclass import *
import cPickle

PythonClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "py_ext_xsd.xsd")) 

class PythonFileCTNMixin:
    
    EditorType = PythonEditor
    
    def __init__(self):
        
        filepath = self.PythonFileName()
        
        self.PythonCode = PythonClasses["Python"]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "Python":
                    self.PythonCode.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.CreatePythonBuffer(True)
        else:
            self.CreatePythonBuffer(False)
            self.OnCTNSave()

    def PythonFileName(self):
        return os.path.join(self.CTNPath(), "py_ext.xml")

    def GetFilename(self):
        if self.PythonBuffer.IsCurrentSaved():
            return "py_ext"
        else:
            return "~py_ext~"

    def SetPythonCode(self, text):
        self.PythonCode.settext(text)
        
    def GetPythonCode(self):
        return self.PythonCode.gettext()
    
    def CTNTestModified(self):
        return self.ChangesToSave or not self.PythonIsSaved()
    
    def OnCTNSave(self, from_project_path=None):
        filepath = self.PythonFileName()
        
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n"
        extras = {"xmlns":"http://www.w3.org/2001/XMLSchema",
                  "xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
                  "xsi:schemaLocation" : "py_ext_xsd.xsd"}
        text += self.PythonCode.generateXMLText("Python", 0, extras)

        xmlfile = open(filepath,"w")
        xmlfile.write(text.encode("utf-8"))
        xmlfile.close()
        
        self.MarkPythonAsSaved()
        return True
        
#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the project
    """
    def Copy(self, model):
        return cPickle.loads(cPickle.dumps(model))

    def CreatePythonBuffer(self, saved):
        self.Buffering = False
        self.PythonBuffer = UndoBuffer(cPickle.dumps(self.PythonCode), saved)

    def BufferPython(self):
        self.PythonBuffer.Buffering(cPickle.dumps(self.PythonCode))
    
    def StartBuffering(self):
        self.Buffering = True
        
    def EndBuffering(self):
        if self.Buffering:
            self.PythonBuffer.Buffering(cPickle.dumps(self.PythonCode))
            self.Buffering = False
    
    def MarkPythonAsSaved(self):
        self.EndBuffering()
        self.PythonBuffer.CurrentSaved()
    
    def PythonIsSaved(self):
        return self.PythonBuffer.IsCurrentSaved() and not self.Buffering
        
    def LoadPrevious(self):
        self.EndBuffering()
        self.PythonCode = cPickle.loads(self.PythonBuffer.Previous())
    
    def LoadNext(self):
        self.PythonCode = cPickle.loads(self.PythonBuffer.Next())
    
    def GetBufferState(self):
        first = self.PythonBuffer.IsFirst() and not self.Buffering
        last = self.PythonBuffer.IsLast()
        return not first, not last

