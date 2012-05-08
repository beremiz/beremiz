import wx
import os
import modules
from ConfigTree import ConfigTreeNode, opjimg
from PLCControler import UndoBuffer
from PythonEditor import PythonEditor

from xml.dom import minidom
from xmlclass import *
import cPickle

PythonClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "py_ext_xsd.xsd")) 

class PythonCodeTemplate:
    
    EditorType = PythonEditor
    
    def __init__(self):
        
        self.ConfNodeMethods.insert(0, 
                {"bitmap" : opjimg("editPYTHONcode"),
                 "name" : _("Edit Python File"), 
                 "tooltip" : _("Edit Python File"),
                 "method" : "_OpenView"},
        )

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

    def ConfNodePath(self):
        return os.path.join(self.CTNParent.ConfNodePath(), "modules", self.CTNType)

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
    
    def OnCTNSave(self):
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

def _GetClassFunction(name):
    def GetRootClass():
        __import__("py_ext.modules." + name)
        return getattr(modules, name).RootClass
    return GetRootClass

class RootClass(PythonCodeTemplate):

    # For root object, available Children Types are modules of the modules packages.
    CTNChildrenTypes = [(name, _GetClassFunction(name), help) for name, help in zip(modules.__all__,modules.helps)]
    
    def ConfNodePath(self):
        return os.path.join(self.CTNParent.ConfNodePath(), self.CTNType)
    
    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing confnode IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        current_location = self.GetCurrentLocation()
        # define a unique name for the generated C file
        location_str = "_".join(map(lambda x:str(x), current_location))
        
        ctr = self.GetCTRoot()
        ctr.GetIECProgramsAndVariables()
        
        plc_python_filepath = os.path.join(os.path.split(__file__)[0], "plc_python.c")
        plc_python_file = open(plc_python_filepath, 'r')
        plc_python_code = plc_python_file.read()
        plc_python_file.close()
        python_eval_fb_list = []
        for v in ctr._VariablesList:
            if v["vartype"] == "FB" and v["type"] in ["PYTHON_EVAL","PYTHON_POLL"]:
                python_eval_fb_list.append(v)
        python_eval_fb_count = max(1, len(python_eval_fb_list))
        
        # prepare python code
        plc_python_code = plc_python_code % {
           "python_eval_fb_count": python_eval_fb_count,
           "location": location_str}
        
        Gen_Pythonfile_path = os.path.join(buildpath, "python_%s.c"%location_str)
        pythonfile = open(Gen_Pythonfile_path,'w')
        pythonfile.write(plc_python_code)
        pythonfile.close()
        
        runtimefile_path = os.path.join(buildpath, "runtime_%s.py"%location_str)
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write(self.GetPythonCode())
        runtimefile.close()
        
        matiec_flags = '"-I%s"'%os.path.abspath(self.GetCTRoot().GetIECLibPath())
        
        return [(Gen_Pythonfile_path, matiec_flags)], "", True, ("runtime_%s.py"%location_str, file(runtimefile_path,"rb"))
