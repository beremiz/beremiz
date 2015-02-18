import os, re, traceback

from copy import deepcopy
from lxml import etree
from xmlclass import GenerateParserFromXSDstring

from PLCControler import UndoBuffer
from ConfigTreeNode import XSDSchemaErrorMessage

CODEFILE_XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
<xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema"
            xmlns:xhtml="http://www.w3.org/1999/xhtml">
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
                  <xsd:attribute name="desc" type="xsd:string" use="optional" default=""/>
                  <xsd:attribute name="onchange" type="xsd:string" use="optional" default=""/>
                  <xsd:attribute name="opts" type="xsd:string" use="optional" default=""/>
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
        
        self.CodeFileParser = GenerateParserFromXSDstring(
            CODEFILE_XSD % sections_str)
        self.CodeFileVariables = etree.XPath("variables/variable")
        
        filepath = self.CodeFileName()
        
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            codefile_xml = xmlfile.read()
            xmlfile.close()
            
            codefile_xml = codefile_xml.replace(
                '<%s>' % self.CODEFILE_NAME, 
                '<%s xmlns:xhtml="http://www.w3.org/1999/xhtml">' % self.CODEFILE_NAME)
            for cre, repl in [
                (re.compile("(?<!<xhtml:p>)(?:<!\[CDATA\[)"), "<xhtml:p><![CDATA["),
                (re.compile("(?:]]>)(?!</xhtml:p>)"), "]]></xhtml:p>")]:
                codefile_xml = cre.sub(repl, codefile_xml)
            
            try:
                self.CodeFile, error = self.CodeFileParser.LoadXMLString(codefile_xml)
                if error is not None:
                    self.GetCTRoot().logger.write_warning(
                        XSDSchemaErrorMessage % ((self.CODEFILE_NAME,) + error))
                self.CreateCodeFileBuffer(True)
            except Exception, exc:
                self.GetCTRoot().logger.write_error(_("Couldn't load confnode parameters %s :\n %s") % (CTNName, unicode(exc)))
                self.GetCTRoot().logger.write_error(traceback.format_exc())
        else:
            self.CodeFile = self.CodeFileParser.CreateRoot()
            self.CreateCodeFileBuffer(False)
            self.OnCTNSave()

    def GetBaseTypes(self):
        return self.GetCTRoot().GetBaseTypes()

    def GetDataTypes(self, basetypes = False):
        return self.GetCTRoot().GetDataTypes(basetypes=basetypes)

    def GenerateNewName(self, format, start_idx):
        return self.GetCTRoot().GenerateNewName(
            None, None, format, start_idx,
            dict([(var.getname().upper(), True) 
                  for var in self.CodeFile.variables.getvariable()]))

    def SetVariables(self, variables):
        self.CodeFile.variables.setvariable([])
        for var in variables:
            variable = self.CodeFileParser.CreateElement("variable", "variables")
            variable.setname(var["Name"])
            variable.settype(var["Type"])
            variable.setinitial(var["Initial"])
            variable.setdesc(var["Description"])
            variable.setonchange(var["OnChange"])
            variable.setopts(var["Options"])
            self.CodeFile.variables.appendvariable(variable)
    
    def GetVariables(self):
        datas = []
        for var in self.CodeFileVariables(self.CodeFile):
            datas.append({"Name" : var.getname(), 
                          "Type" : var.gettype(), 
                          "Initial" : var.getinitial(),
                          "Description" : var.getdesc(),
                          "OnChange"    : var.getonchange(),
                          "Options"     : var.getopts(),
                         })
        return datas

    def SetTextParts(self, parts):
        for section in self.SECTIONS_NAMES:
            section_code = parts.get(section)
            if section_code is not None:
                getattr(self.CodeFile, section).setanyText(section_code)
    
    def GetTextParts(self):
        return dict([(section, getattr(self.CodeFile, section).getanyText())
                     for section in self.SECTIONS_NAMES])
            
    def CTNTestModified(self):
        return self.ChangesToSave or not self.CodeFileIsSaved()    

    def OnCTNSave(self, from_project_path=None):
        filepath = self.CodeFileName()
        
        xmlfile = open(filepath,"w")
        xmlfile.write(etree.tostring(
            self.CodeFile, 
            pretty_print=True, 
            xml_declaration=True, 
            encoding='utf-8'))
        xmlfile.close()
        
        self.MarkCodeFileAsSaved()
        return True

    def CTNGlobalInstances(self):
        variables = self.CodeFileVariables(self.CodeFile)
        ret =  [(variable.getname(),
                 variable.gettype(),
                 variable.getinitial()) 
                for variable in variables]
        ret.extend([("On"+variable.getname()+"Change", "python_poll", "")
                for variable in variables
                if variable.getonchange()])
        return ret

#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the codefile model
    """
    def Copy(self, model):
        return deepcopy(model)

    def CreateCodeFileBuffer(self, saved):
        self.Buffering = False
        self.CodeFileBuffer = UndoBuffer(self.CodeFileParser.Dumps(self.CodeFile), saved)

    def BufferCodeFile(self):
        self.CodeFileBuffer.Buffering(self.CodeFileParser.Dumps(self.CodeFile))
    
    def StartBuffering(self):
        self.Buffering = True
        
    def EndBuffering(self):
        if self.Buffering:
            self.CodeFileBuffer.Buffering(self.CodeFileParser.Dumps(self.CodeFile))
            self.Buffering = False
    
    def MarkCodeFileAsSaved(self):
        self.EndBuffering()
        self.CodeFileBuffer.CurrentSaved()
    
    def CodeFileIsSaved(self):
        return self.CodeFileBuffer.IsCurrentSaved() and not self.Buffering
        
    def LoadPrevious(self):
        self.EndBuffering()
        self.CodeFile = self.CodeFileParser.Loads(self.CodeFileBuffer.Previous())
    
    def LoadNext(self):
        self.CodeFile = self.CodeFileParser.Loads(self.CodeFileBuffer.Next())
    
    def GetBufferState(self):
        first = self.CodeFileBuffer.IsFirst() and not self.Buffering
        last = self.CodeFileBuffer.IsLast()
        return not first, not last

