import os
from xml.dom import minidom
import cPickle

from xmlclass import *

from PLCControler import UndoBuffer
from editors.CodeFileEditor import SECTIONS_NAMES

CodeFileClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "code_file.xsd"))

class CodeFile:
    
    def __init__(self):
        filepath = self.CodeFileName()
        
        self.CodeFile = CodeFileClasses["CodeFile"]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName in ["CodeFile", "CFile"]:
                    self.CodeFile.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.CreateCodeFileBuffer(True)
        else:
            self.CreateCodeFileBuffer(False)
            self.OnCTNSave()

    def GetBaseTypes(self):
        return self.GetCTRoot().GetBaseTypes()

    def GetDataTypes(self, basetypes = False):
        return self.GetCTRoot().GetDataTypes(basetypes=basetypes)

    def SetVariables(self, variables):
        self.CodeFile.variables.setvariable([])
        for var in variables:
            variable = CodeFileClasses["variables_variable"]()
            variable.setname(var["Name"])
            variable.settype(var["Type"])
            variable.setinitial(var["Initial"])
            self.CodeFile.variables.appendvariable(variable)
    
    def GetVariables(self):
        datas = []
        for var in self.CodeFile.variables.getvariable():
            datas.append({"Name" : var.getname(), "Type" : var.gettype(), "Initial" : var.getinitial()})
        return datas

    def SetTextParts(self, parts):
        for section, code_object in zip(
            SECTIONS_NAMES,
            [self.CodeFile.includes,
             self.CodeFile.globals,
             self.CodeFile.initFunction,
             self.CodeFile.cleanUpFunction,
             self.CodeFile.retrieveFunction,
             self.CodeFile.publishFunction]):
            code_object.settext(parts[section])
        
    def GetTextParts(self):
        parts = {}
        for section, code_object in zip(
            SECTIONS_NAMES,
            [self.CodeFile.includes,
             self.CodeFile.globals,
             self.CodeFile.initFunction,
             self.CodeFile.cleanUpFunction,
             self.CodeFile.retrieveFunction,
             self.CodeFile.publishFunction]):
            parts[section] = code_object.gettext()
        return parts
                
    def CTNTestModified(self):
        return self.ChangesToSave or not self.CodeFileIsSaved()    

    def OnCTNSave(self, from_project_path=None):
        filepath = self.CodeFileName()
        
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n"
        extras = {"xmlns":"http://www.w3.org/2001/XMLSchema",
                  "xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
                  "xsi:schemaLocation" : "code_file.xsd"}
        text += self.CodeFile.generateXMLText("CodeFile", 0, extras)

        xmlfile = open(filepath,"w")
        xmlfile.write(text.encode("utf-8"))
        xmlfile.close()
        
        self.MarkCodeFileAsSaved()
        return True

    def CTNGlobalInstances(self):
        current_location = self.GetCurrentLocation()
        return [(variable.getname(),
                 variable.gettype(),
                 variable.getinitial())
                for variable in self.CodeFile.variables.variable]

#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the codefile model
    """
    def Copy(self, model):
        return cPickle.loads(cPickle.dumps(model))

    def CreateCodeFileBuffer(self, saved):
        self.Buffering = False
        self.CodeFileBuffer = UndoBuffer(cPickle.dumps(self.CodeFile), saved)

    def BufferCodeFile(self):
        self.CodeFileBuffer.Buffering(cPickle.dumps(self.CodeFile))
    
    def StartBuffering(self):
        self.Buffering = True
        
    def EndBuffering(self):
        if self.Buffering:
            self.CodeFileBuffer.Buffering(cPickle.dumps(self.CodeFile))
            self.Buffering = False
    
    def MarkCodeFileAsSaved(self):
        self.EndBuffering()
        self.CodeFileBuffer.CurrentSaved()
    
    def CodeFileIsSaved(self):
        return self.CodeFileBuffer.IsCurrentSaved() and not self.Buffering
        
    def LoadPrevious(self):
        self.EndBuffering()
        self.CodeFile = cPickle.loads(self.CodeFileBuffer.Previous())
    
    def LoadNext(self):
        self.CodeFile = cPickle.loads(self.CodeFileBuffer.Next())
    
    def GetBufferState(self):
        first = self.CodeFileBuffer.IsFirst() and not self.Buffering
        last = self.CodeFileBuffer.IsLast()
        return not first, not last

