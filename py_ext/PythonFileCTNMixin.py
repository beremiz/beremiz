import os
from PLCControler import UndoBuffer
from PythonEditor import PythonEditor

from xml.dom import minidom
from xmlclass import GenerateClassesFromXSD
import cPickle

from CodeFileTreeNode import CodeFile

PythonClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "py_ext_xsd.xsd")) 

class PythonFileCTNMixin(CodeFile):
    
    CODEFILE_NAME = "PyFile"
    SECTIONS_NAMES = [
        "globals",
        "init",
        "cleanup",
        "start",
        "stop"]
    EditorType = PythonEditor
    
    def __init__(self):
        CodeFile.__init__(self)
        
        filepath = self.PythonFileName()
        
        python_code = PythonClasses["Python"]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "Python":
                    python_code.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.CodeFile.globals.settext(python_code.gettext())
                    os.remove(filepath)
                    self.CreateCodeFileBuffer(False)
                    self.OnCTNSave()
    
    def CodeFileName(self):
        return os.path.join(self.CTNPath(), "pyfile.xml")
    
    def PythonFileName(self):
        return os.path.join(self.CTNPath(), "py_ext.xml")

    def GetSectionsCode(self):
        
        # Generate Beremiz python runtime variables code
        config = self.GetCTRoot().GetProjectConfigNames()[0]
        variables_str = ""
        for variable in self.CodeFile.variables.variable:
            global_name = "%s_%s" % (config.upper(), variable.getname().upper())
            variables_str += "# global_var:%s python_var:%s type:%s initial:%s\n" % (
                global_name,
                variable.getname(),
                variable.gettype(),
                str(variable.getinitial()))
        
        sections_code = {
            "variables": variables_str,
            "globals": self.CodeFile.globals.gettext().strip()
        }
        
        # Generate Beremiz python runtime functions code
        for section in self.SECTIONS_NAMES:
            if section != "globals":
                code_object = getattr(self.CodeFile, section)
                section_str = ""
                lines = code_object.gettext().strip().splitlines()
                if len(lines) > 0:
                    for line in lines:
                        section_str += "    " + line + "\n"
                    section_str += "\n"
                sections_code[section] = section_str
            
        return sections_code

