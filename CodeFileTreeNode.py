import os
from xml.dom import minidom
import cPickle

from xmlclass import GenerateClassesFromXSDstring, UpdateXMLClassGlobals

from PLCControler import UndoBuffer

CODEFILE_XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <xsd:element name="%(codefile_name)s">
    <xsd:complexType>
      <xsd:sequence>
        %(includes_section)s
        <xsd:element name="variables">
          <xsd:complexType>
            <xsd:sequence>
              <xsd:element name="variable" minOccurs="0" maxOccurs="unbounded">
                <xsd:complexType>
                  <xsd:attribute name="name" type="xsd:string" use="required"/>
                  <xsd:attribute name="type" type="xsd:string" use="required"/>
                  <xsd:attribute name="class" use="optional">
                    <xsd:simpleType>
                      <xsd:restriction base="xsd:string">
                        <xsd:enumeration value="input"/>
                        <xsd:enumeration value="memory"/>
                        <xsd:enumeration value="output"/>
                      </xsd:restriction>
                    </xsd:simpleType>
                  </xsd:attribute>
                  <xsd:attribute name="initial" type="xsd:string" use="optional" default=""/>
                </xsd:complexType>
              </xsd:element>
            </xsd:sequence>
          </xsd:complexType>
        </xsd:element>
        %(sections)s
      </xsd:sequence>
    </xsd:complexType>
  </xsd:element>
  <xsd:complexType name="CodeText">
    <xsd:annotation>
      <xsd:documentation>Formatted text according to parts of XHTML 1.1</xsd:documentation>
    </xsd:annotation>
    <xsd:sequence>
      <xsd:any namespace="http://www.w3.org/1999/xhtml" processContents="lax"/>
    </xsd:sequence>
  </xsd:complexType>
</xsd:schema>"""

SECTION_TAG_ELEMENT = "<xsd:element name=\"%s\" type=\"CodeText\"/>"

class CodeFile:
    
    CODEFILE_NAME = "CodeFile"
    SECTIONS_NAMES = []
    
    def __init__(self):
        sections_str = {"codefile_name": self.CODEFILE_NAME}
        if "includes" in self.SECTIONS_NAMES:
            sections_str["includes_section"] = SECTION_TAG_ELEMENT % "includes"
        else:
            sections_str["includes_section"] = ""
        sections_str["sections"] = "\n".join(
            [SECTION_TAG_ELEMENT % name
             for name in self.SECTIONS_NAMES if name != "includes"])
        
        self.CodeFileClasses = GenerateClassesFromXSDstring(
            CODEFILE_XSD % sections_str)
        
        filepath = self.CodeFileName()
        
        self.CodeFile = self.CodeFileClasses[self.CODEFILE_NAME]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName in [self.CODEFILE_NAME]:
                    self.CodeFile.loadXMLTree(child, ["xmlns", "xmlns:xsi", "xsi:schemaLocation"])
                    self.CreateCodeFileBuffer(True)
        else:
            self.CreateCodeFileBuffer(False)
            self.OnCTNSave()

    def GetBaseTypes(self):
        return self.GetCTRoot().GetBaseTypes()

    def GetDataTypes(self, basetypes = False):
        return self.GetCTRoot().GetDataTypes(basetypes=basetypes)

    def GenerateNewName(self, format, start_idx):
        return self.GetCTRoot().GenerateNewName(
            None, None, format, start_idx,
            dict([(var.getname(), None) 
                  for var in self.CodeFile.variables.getvariable()]))

    def SetVariables(self, variables):
        self.CodeFile.variables.setvariable([])
        for var in variables:
            variable = self.CodeFileClasses["variables_variable"]()
            variable.setname(var["Name"])
            variable.settype(var["Type"])
            variable.setinitial(var["Initial"])
            self.CodeFile.variables.appendvariable(variable)
    
    def GetVariables(self):
        datas = []
        for var in self.CodeFile.variables.getvariable():
            datas.append({"Name" : var.getname(), 
                          "Type" : var.gettype(), 
                          "Initial" : var.getinitial()})
        return datas

    def SetTextParts(self, parts):
        for section in self.SECTIONS_NAMES:
            section_code = parts.get(section)
            if section_code is not None:
                getattr(self.CodeFile, section).settext(section_code)
    
    def GetTextParts(self):
        return dict([(section, getattr(self.CodeFile, section).gettext())
                     for section in self.SECTIONS_NAMES])
            
    def CTNTestModified(self):
        return self.ChangesToSave or not self.CodeFileIsSaved()    

    def OnCTNSave(self, from_project_path=None):
        filepath = self.CodeFileName()
        
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n"
        text += self.CodeFile.generateXMLText(self.CODEFILE_NAME, 0)

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

    def cPickle_loads(self, str_obj):
        UpdateXMLClassGlobals(self.CodeFileClasses)
        return cPickle.loads(str_obj)

    def cPickle_dumps(self, obj):
        UpdateXMLClassGlobals(self.CodeFileClasses)
        return cPickle.dumps(obj)

    """
    Return a copy of the codefile model
    """
    def Copy(self, model):
        return self.cPickle_loads(self.cPickle_dumps(model))

    def CreateCodeFileBuffer(self, saved):
        self.Buffering = False
        self.CodeFileBuffer = UndoBuffer(self.cPickle_dumps(self.CodeFile), saved)

    def BufferCodeFile(self):
        self.CodeFileBuffer.Buffering(self.cPickle_dumps(self.CodeFile))
    
    def StartBuffering(self):
        self.Buffering = True
        
    def EndBuffering(self):
        if self.Buffering:
            self.CodeFileBuffer.Buffering(self.cPickle_dumps(self.CodeFile))
            self.Buffering = False
    
    def MarkCodeFileAsSaved(self):
        self.EndBuffering()
        self.CodeFileBuffer.CurrentSaved()
    
    def CodeFileIsSaved(self):
        return self.CodeFileBuffer.IsCurrentSaved() and not self.Buffering
        
    def LoadPrevious(self):
        self.EndBuffering()
        self.CodeFile = self.cPickle_loads(self.CodeFileBuffer.Previous())
    
    def LoadNext(self):
        self.CodeFile = self.cPickle_loads(self.CodeFileBuffer.Next())
    
    def GetBufferState(self):
        first = self.CodeFileBuffer.IsFirst() and not self.Buffering
        last = self.CodeFileBuffer.IsLast()
        return not first, not last

