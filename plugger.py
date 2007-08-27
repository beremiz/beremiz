import os
import plugins
from plugins import PlugTemplate


class PluginsRoot(PlugTemplate):

    # A special PlugChildsTypes
    PlugChildsTypes = [(name,lambda : getattr(__import__("plugins." + name), name).RootClass) for name in plugins.__all__]

    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:simpleType name="Win32Compiler">
        <xsd:restriction base="xsd:string">
          <xsd:enumeration value="Cygwin"/>
          <xsd:enumeration value="MinGW"/>
          <xsd:enumeration value="VC++"/>
        </xsd:restriction>
      </xsd:simpleType>
      <xsd:element name="BeremizRoot">
        <xsd:complexType>
          <xsd:element name="TargetType">
            <xsd:complexType>
              <xsd:choice>
                <xsd:element name="Win32">
                  <xsd:complexType>
                    <xsd:attribute name="ToolChain" type="ppx:Win32Compiler" use="required" default="MinGW"/>
                    <xsd:attribute name="Priority" type="xsd:integer" use="required" default="0"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Linux">
                  <xsd:complexType>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required" default="0"/>
                    <xsd:attribute name="Nice" type="xsd:integer" use="required" default="0"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Xenomai">
                  <xsd:complexType>
                    <xsd:attribute name="xeno-config" type="xsd:string" use="required" default="0"/>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required" default="0"/>
                    <xsd:attribute name="Priority" type="xsd:integer" use="required" default="0"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="RTAI">
                  <xsd:complexType>
                    <xsd:attribute name="xeno-config" type="xsd:string" use="required" default="0"/>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required" default="0"/>
                    <xsd:attribute name="Priority" type="xsd:integer" use="required" default="0"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Library">
                  <xsd:complexType>
                    <xsd:attribute name="Dynamic" type="xsd:boolean" default="true"/>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required" default="0"/>
                  </xsd:complexType>
                </xsd:element>
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def __init__(self, ProjectPath):
        # self is the parent
        self.PlugParent = None
        # Keep track of the plugin type name
        self.PlugType = "Beremiz"
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        # Change XSD into class members
        self._AddParamsMembers()
        self.PluggedChilds = {}
        # No IEC channel, name, etc...
        self.MandatoryParams = []
        # If dir have already be made, and file exist
        if os.path.isdir(_self.PlugPath(PlugName)) and os.path.isfile(_self.PluginXmlFilePath(PlugName)):
            #Load the plugin.xml file into parameters members
            _self.LoadXMLParams()
            #Load and init all the childs
            _self.LoadChilds()

    def PlugPath(self,PlugName=None):
        return self.ProjectPath
        
    def PluginXmlFilePath(self, PlugName=None):
        return os.path.join(self.PlugPath(PlugName), "beremiz.xml")
        
    
