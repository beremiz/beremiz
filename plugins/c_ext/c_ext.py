import wx
import os
from xml.dom import minidom
import cPickle

from xmlclass import *

from plugger import PlugTemplate
from CFileEditor import CFileEditor
from PLCControler import PLCControler, LOCATION_PLUGIN, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY

CFileClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "cext_xsd.xsd")) 

#-------------------------------------------------------------------------------
#                         Undo Buffer for CFile
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


TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", "REAL" : "D", "LREAL" : "L",
    "STRING" : "B", "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L", "WSTRING" : "W"}

class _Cfile:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CExtension">
        <xsd:complexType>
          <xsd:attribute name="CFLAGS" type="xsd:string" use="required"/>
          <xsd:attribute name="LDFLAGS" type="xsd:string" use="required"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    def __init__(self):
        filepath = self.CFileName()
        
        self.Buffering = False
        self.CFile = CFileClasses["CFile"]()
        self.CFileBuffer = UndoBuffer(self.Copy(self.CFile), False)
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "CFile":
                    self.CFile.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.CFileBuffer = UndoBuffer(self.Copy(self.CFile), True)
        else:
            self.OnPlugSave()

    def CFileName(self):
        return os.path.join(self.PlugPath(), "cfile.xml")

    def GetFilename(self):
        if self.CFileBuffer.IsCurrentSaved():
            return "cfile"
        else:
            return "~cfile~"

    def GetBaseTypes(self):
        return self.GetPlugRoot().GetBaseTypes()

    def GetDataTypes(self, basetypes = False):
        return self.GetPlugRoot().GetDataTypes(basetypes = basetypes)

    def GetSizeOfType(self, type):
        return TYPECONVERSION[self.GetPlugRoot().GetBaseType(type)]

    def SetVariables(self, variables):
        self.CFile.variables.setvariable([])
        for var in variables:
            variable = CFileClasses["variables_variable"]()
            variable.setname(var["Name"])
            variable.settype(var["Type"])
            variable.setclass(var["Class"])
            self.CFile.variables.appendvariable(variable)
    
    def GetVariables(self):
        datas = []
        for var in self.CFile.variables.getvariable():
            datas.append({"Name" : var.getname(), "Type" : var.gettype(), "Class" : var.getclass()})
        return datas

    def GetVariableLocationTree(self):
        '''See PlugTemplate.GetVariableLocationTree() for a description.'''

        current_location = ".".join(map(str, self.GetCurrentLocation()))
        
        vars = []
        input = output = 0
        for var in self.CFile.variables.getvariable():
            var_size = self.GetSizeOfType(var.gettype())
            if var.getclass() == "input":
                var_class = LOCATION_VAR_INPUT
                var_location = "%%I%s%s.%d"%(var_size, current_location, input)
                input += 1
            else:
                var_class = LOCATION_VAR_OUTPUT
                var_location = "%%Q%s%s.%d"%(var_size, current_location, output)
                output += 1
            vars.append({"name": var.getname(),
                         "type": var_class,
                         "size": var_size,
                         "IEC_type": var.gettype(),
                         "location": var_location,
                         "description": "",
                         "children": []})
                
        return  {"name": self.BaseParams.getName(),
                "type": LOCATION_PLUGIN,
                "location": self.GetFullIEC_Channel(),
                "children": vars}

    def SetPartText(self, name, text):
        if name == "Includes":
            self.CFile.includes.settext(text)
        elif name == "Globals":
            self.CFile.globals.settext(text)
        elif name == "Init":
            self.CFile.initFunction.settext(text)
        elif name == "CleanUp":
            self.CFile.cleanUpFunction.settext(text)
        elif name == "Retrieve":
            self.CFile.retrieveFunction.settext(text)
        elif name == "Publish":
            self.CFile.publishFunction.settext(text)
        
    def GetPartText(self, name):
        if name == "Includes":
            return self.CFile.includes.gettext()
        elif name == "Globals":
            return self.CFile.globals.gettext()
        elif name == "Init":
            return self.CFile.initFunction.gettext()
        elif name == "CleanUp":
            return self.CFile.cleanUpFunction.gettext()
        elif name == "Retrieve":
            return self.CFile.retrieveFunction.gettext()
        elif name == "Publish":
            return self.CFile.publishFunction.gettext()
        return ""
    
    _View = None
    def _OpenView(self):
        if not self._View:
            def _onclose():
                self._View = None
            def _onsave():
                self.GetPlugRoot().SaveProject()
            self._View = CFileEditor(self.GetPlugRoot().AppFrame, self)
            self._View._onclose = _onclose
            self._View._onsave = _onsave
            self._View.Show()

    PluginMethods = [
        {"bitmap" : os.path.join("images", "EditCfile"),
         "name" : _("Edit C File"), 
         "tooltip" : _("Edit C File"),
         "method" : "_OpenView"},
    ]

    def OnPlugSave(self):
        filepath = self.CFileName()
        
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n"
        extras = {"xmlns":"http://www.w3.org/2001/XMLSchema",
                  "xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
                  "xsi:schemaLocation" : "cext_xsd.xsd"}
        text += self.CFile.generateXMLText("CFile", 0, extras)

        xmlfile = open(filepath,"w")
        xmlfile.write(text)
        xmlfile.close()
        
        self.CFileBuffer.CurrentSaved()
        return True

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
        location_str = "_".join(map(str, current_location))
        
        text = "/* Code generated by Beremiz c_ext plugin */\n\n"
        
        # Adding includes
        text += "/* User includes */\n"
        text += self.CFile.includes.gettext()
        text += "\n"
        
        text += """/* Beremiz c_ext plugin includes */
#ifdef _WINDOWS_H
  #include "iec_types.h"
#else
  #include "iec_std_lib.h"
#endif

"""

        # Adding variables
        vars = []
        inputs = outputs = 0
        for variable in self.CFile.variables.variable:
            var = {"Name" : variable.getname(), "Type" : variable.gettype()}
            if variable.getclass() == "input":
                var["location"] = "__I%s%s_%d"%(self.GetSizeOfType(var["Type"]), location_str, inputs)
                inputs += 1
            else:
                var["location"] = "__Q%s%s_%d"%(self.GetSizeOfType(var["Type"]), location_str, outputs)
                outputs += 1
            vars.append(var)
        text += "/* Beremiz c_ext plugin user variables definition */\n"
        base_types = self.GetPlugRoot().GetBaseTypes()
        for var in vars:
            if var["Type"] in base_types:
                prefix = "IEC_"
            else:
                prefix = ""
            text += "%s%s beremiz%s;\n"%(prefix, var["Type"], var["location"])
            text += "%s%s *%s = &beremiz%s;\n"%(prefix, var["Type"], var["location"], var["location"])
        text += "/* User variables reference */\n"
        for var in vars:
            text += "#define %s beremiz%s\n"%(var["Name"], var["location"])
        text += "\n"
        
        # Adding user global variables and routines
        text += "/* User internal user variables and routines */\n"
        text += self.CFile.globals.gettext()
        
        # Adding Beremiz plugin functions
        text += "/* Beremiz plugin functions */\n"
        text += "int __init_%s(int argc,char **argv)\n{\n"%location_str
        text += self.CFile.initFunction.gettext()
        text += "  return 0;\n"
        text += "\n}\n\n"
        
        text += "void __cleanup_%s()\n{\n"%location_str
        text += self.CFile.cleanUpFunction.gettext()
        text += "\n}\n\n"
        
        text += "void __retrieve_%s()\n{\n"%location_str
        text += self.CFile.retrieveFunction.gettext()
        text += "\n}\n\n"
        
        text += "void __publish_%s()\n{\n"%location_str
        text += self.CFile.publishFunction.gettext()
        text += "\n}\n\n"
        
        Gen_Cfile_path = os.path.join(buildpath, "CFile_%s.c"%location_str)
        cfile = open(Gen_Cfile_path,'w')
        cfile.write(text)
        cfile.close()
        
        if wx.Platform == '__WXMSW__':
            matiec_flags = " -I../../matiec/lib"
        else:
            matiec_flags = " -I../matiec/lib"
        
        return [(Gen_Cfile_path, str(self.CExtension.getCFLAGS() + matiec_flags))],str(self.CExtension.getLDFLAGS()),True
        
#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the project
    """
    def Copy(self, model):
        return cPickle.loads(cPickle.dumps(model))

    def BufferCFile(self):
        self.CFileBuffer.Buffering(self.Copy(self.CFile))
    
    def StartBuffering(self):
        self.CFileBuffer.Buffering(self.CFile)
        self.Buffering = True
        
    def EndBuffering(self):
        if self.Buffering:
            self.CFile = self.Copy(self.CFile)
            self.Buffering = False
    
    def CFileIsSaved(self):
        if self.CFileBuffer:
            return self.CFileBuffer.IsCurrentSaved()
        else:
            return True

    def LoadPrevious(self):
        self.CFile = self.Copy(self.CFileBuffer.Previous())
    
    def LoadNext(self):
        self.CFile = self.Copy(self.CFileBuffer.Next())
    
    def GetBufferState(self):
        first = self.CFileBuffer.IsFirst()
        last = self.CFileBuffer.IsLast()
        return not first, not last

class RootClass:

    PlugChildsTypes = [("C_File",_Cfile, "C file")]
    
    def PlugGenerate_C(self, buildpath, locations):
        return [],"",False


