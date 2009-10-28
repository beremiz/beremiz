import wx
import os
import modules
from plugger import PlugTemplate, opjimg
from PythonEditor import PythonEditorFrame

from xml.dom import minidom
from xmlclass import *
import cPickle

PythonClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "python_xsd.xsd")) 

#-------------------------------------------------------------------------------
#                         Undo Buffer for PythonCode
#-------------------------------------------------------------------------------

# Length of the buffer
UNDO_BUFFER_LENGTH = 20

"""
Class implementing a buffer of changes made on the current editing model
"""
class UndoBuffer:

    # Constructor initialising buffer
    def __init__(self, currentstate, issaved = False):
        self.Buffer = []
        self.CurrentIndex = -1
        self.MinIndex = -1
        self.MaxIndex = -1
        # if current state is defined
        if currentstate:
            self.CurrentIndex = 0
            self.MinIndex = 0
            self.MaxIndex = 0
        # Initialising buffer with currentstate at the first place
        for i in xrange(UNDO_BUFFER_LENGTH):
            if i == 0:
                self.Buffer.append(currentstate)
            else:
                self.Buffer.append(None)
        # Initialising index of state saved
        if issaved:
            self.LastSave = 0
        else:
            self.LastSave = -1
    
    # Add a new state in buffer
    def Buffering(self, currentstate):
        self.CurrentIndex = (self.CurrentIndex + 1) % UNDO_BUFFER_LENGTH
        self.Buffer[self.CurrentIndex] = currentstate
        # Actualising buffer limits
        self.MaxIndex = self.CurrentIndex
        if self.MinIndex == self.CurrentIndex:
            # If the removed state was the state saved, there is no state saved in the buffer
            if self.LastSave == self.MinIndex:
                self.LastSave = -1
            self.MinIndex = (self.MinIndex + 1) % UNDO_BUFFER_LENGTH
        self.MinIndex = max(self.MinIndex, 0)
    
    # Return current state of buffer
    def Current(self):
        return self.Buffer[self.CurrentIndex]
    
    # Change current state to previous in buffer and return new current state
    def Previous(self):
        if self.CurrentIndex != self.MinIndex:
            self.CurrentIndex = (self.CurrentIndex - 1) % UNDO_BUFFER_LENGTH
            return self.Buffer[self.CurrentIndex]
        return None
    
    # Change current state to next in buffer and return new current state
    def Next(self):
        if self.CurrentIndex != self.MaxIndex:
            self.CurrentIndex = (self.CurrentIndex + 1) % UNDO_BUFFER_LENGTH
            return self.Buffer[self.CurrentIndex]
        return None
    
    # Return True if current state is the first in buffer
    def IsFirst(self):
        return self.CurrentIndex == self.MinIndex
    
    # Return True if current state is the last in buffer
    def IsLast(self):
        return self.CurrentIndex == self.MaxIndex

    # Note that current state is saved
    def CurrentSaved(self):
        self.LastSave = self.CurrentIndex
        
    # Return True if current state is saved
    def IsCurrentSaved(self):
        return self.LastSave == self.CurrentIndex

class PythonCodeTemplate:
    
    def __init__(self):
        
        self.PluginMethods.insert(0, 
                {"bitmap" : opjimg("editPYTHONcode"),
                 "name" : _("Edit Python File"), 
                 "tooltip" : _("Edit Python File"),
                 "method" : "_OpenView"},
        )

        filepath = self.PythonFileName()
        
        self.Buffering = False
        self.PythonCode = PythonClasses["Python"]()
        self.PythonBuffer = UndoBuffer(self.Copy(self.PythonCode), False)
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "Python":
                    self.PythonCode.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.PythonBuffer = UndoBuffer(self.Copy(self.PythonCode), True)
        else:
            self.OnPlugSave()

    def PluginPath(self):
        return os.path.join(self.PlugParent.PluginPath(), "modules", self.PlugType)

    def PythonFileName(self):
        return os.path.join(self.PlugPath(), "python.xml")

    def GetFilename(self):
        if self.PythonBuffer.IsCurrentSaved():
            return "python"
        else:
            return "~python~"

    def SetPythonCode(self, text):
        self.PythonCode.settext(text)
        
    def GetPythonCode(self):
        return self.PythonCode.gettext()
    
    _View = None
    def _OpenView(self):
        if not self._View:
            open_pyeditor = True
            has_permissions = self.GetPlugRoot().CheckProjectPathPerm()
            if not has_permissions:
                dialog = wx.MessageDialog(self.GetPlugRoot().AppFrame,
                                          _("You don't have write permissions.\nOpen PythonEditor anyway ?"),
                                          _("Open PythonEditor"),
                                          wx.YES_NO|wx.ICON_QUESTION)
                open_pyeditor = dialog.ShowModal() == wx.ID_YES
                dialog.Destroy()
            if open_pyeditor:
                def _onclose():
                    self._View = None
                if has_permissions:
                    def _onsave():
                        self.GetPlugRoot().SaveProject()
                else:
                    def _onsave():
                        pass
                self._View = PythonEditorFrame(self.GetPlugRoot().AppFrame, self)
                self._View._onclose = _onclose
                self._View._onsave = _onsave
                self._View.Show()
    
    def OnPlugSave(self):
        filepath = self.PythonFileName()
        
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n"
        extras = {"xmlns":"http://www.w3.org/2001/XMLSchema",
                  "xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
                  "xsi:schemaLocation" : "python_xsd.xsd"}
        text += self.PythonCode.generateXMLText("Python", 0, extras)

        xmlfile = open(filepath,"w")
        xmlfile.write(text.encode("utf-8"))
        xmlfile.close()
        
        self.PythonBuffer.CurrentSaved()
        return True
        
#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the project
    """
    def Copy(self, model):
        return cPickle.loads(cPickle.dumps(model))

    def BufferPython(self):
        self.PythonBuffer.Buffering(self.Copy(self.PythonCode))
    
    def StartBuffering(self):
        self.PythonBuffer.Buffering(self.PythonCode)
        self.Buffering = True
        
    def EndBuffering(self):
        if self.Buffering:
            self.PythonCode = self.Copy(self.PythonCode)
            self.Buffering = False
    
    def PythonCodeIsSaved(self):
        if self.PythonBuffer:
            return self.PythonBuffer.IsCurrentSaved()
        else:
            return True

    def LoadPrevious(self):
        self.PythonCode = self.Copy(self.PythonBuffer.Previous())
    
    def LoadNext(self):
        self.PythonCode = self.Copy(self.PythonBuffer.Next())
    
    def GetBufferState(self):
        first = self.PythonBuffer.IsFirst()
        last = self.PythonBuffer.IsLast()
        return not first, not last

def _GetClassFunction(name):
    def GetRootClass():
        __import__("plugins.python.modules." + name)
        return getattr(modules, name).RootClass
    return GetRootClass

class RootClass(PythonCodeTemplate):

    # For root object, available Childs Types are modules of the modules packages.
    PlugChildsTypes = [(name, _GetClassFunction(name), help) for name, help in zip(modules.__all__,modules.helps)]
    
    def PluginPath(self):
        return os.path.join(self.PlugParent.PluginPath(), self.PlugType)
    
    def PlugGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
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
        
        plugin_root = self.GetPlugRoot()
        plugin_root.GetIECProgramsAndVariables()
        
        plc_python_filepath = os.path.join(os.path.split(__file__)[0], "plc_python.c")
        plc_python_file = open(plc_python_filepath, 'r')
        plc_python_code = plc_python_file.read()
        plc_python_file.close()
        python_eval_fb_list = []
        for v in plugin_root._VariablesList:
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
        
        matiec_flags = '"-I%s"'%os.path.abspath(self.GetPlugRoot().GetIECLibPath())
        
        return [(Gen_Pythonfile_path, matiec_flags)], "", True, ("runtime_%s.py"%location_str, file(runtimefile_path,"rb"))
