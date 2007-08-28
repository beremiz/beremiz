"""
Base definitions for beremiz plugins
"""

import os
import types
import shutil
from xml.dom import minidom
import plugins
from xmlclass import GenerateClassesFromXSDstring

_BaseParamsClass = GenerateClassesFromXSDstring("""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="BaseParams">
            <xsd:complexType>
              <xsd:attribute name="Name" type="xsd:string" use="required"/>
              <xsd:attribute name="IEC_Channel" type="xsd:integer" use="required"  default="-1"/>
              <xsd:attribute name="Enabled" type="xsd:boolean" use="required" default="true"/>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>""")[0]["BaseParams"]

NameTypeSeparator = '@'

class PlugTemplate:
    """
    This class is the one that define plugins.
    """

    XSD = None
    PlugChildsTypes = []
    PlugMaxCount = None
    PluginMethods = []

    def _AddParamsMembers(self):
        Classes = GenerateClassesFromXSDstring(self.XSD)[0]
        self.PlugParams = []
        for name, XSDclass in Classes.items():
            if XSDclass.IsBaseClass:
                obj = XSDclass()
                self.PlugParams.append( (name, obj) )
                setattr(self, name, obj)

    def __init__(self, PlugPath):
        # Create BaseParam 
        self.BaseParams = _BaseParamsClass()
        self.MandatoryParams = [("BaseParams", self.BaseParams)]
        self._AddParamsMembers()
        self.PluggedChilds = {}
    
    def PluginXmlFilePath(self, PlugName=None):
        return os.path.join(self.PlugPath(PlugName), "plugin.xml")

    def PlugPath(self,PlugName=None):
        if not PlugName:
            PlugName = self.BaseParams.getName()
        return os.path.join(self.PlugParent.PlugPath(), PlugName + NameTypeSeparator + self.PlugType)
    
    def PlugTestModified(self):
        return False
        
    def OnPlugSave(self):
        return True

    def PlugRequestSave(self):
        # If plugin do not have corresponding directory
        if not os.path.isdir(self.PlugPath(PlugName)):
            # Create it
            os.mkdir(self.PlugPath(PlugName))

        # generate XML for all XML parameters controllers of the plugin
        XMLString = '<?xml version="1.0" encoding="UTF-8"?>'
        for nodeName, XMLController in self.PlugParams + self.MandatoryParams:
            XMLString += XMLController.generateXMLTextMethod(self, nodeName, 0)
        XMLFile = open(self.PluginXmlFilePath(PlugName),'w')
        XMLFile.write(XMLString)
        XMLFile.close()
        
        # Call the plugin specific OnPlugSave method
        self.OnPlugSave()
        
        # go through all childs and do the same
        for PlugChild in self.IterChilds():
            PlugChild.PlugRequestSave()
    
    def PlugImport(self, src_PlugPath):
        shutil.copytree(src_PlugPath, self.PlugPath)
        return True

    def PlugGenerate_C(self, buildpath, current_location, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [(IEC_loc, IEC_Direction IEC_Type, Name)]\
            ex: [((0,0,4,5),'I','X','__IX_0_0_4_5'),...]
        """
        return [],""
    
    def _Generate_C(self, buildpath, current_location, locations):
        # Generate plugins [(Cfiles, CFLAGS)], LDFLAGS
        PlugCFilesAndCFLAGS, PlugLDFLAGS = self._Generate_C(buildpath, current_location, locations)
        # recurse through all childs, and stack their results
        for PlugChild in self.IterChilds():
            # Get childs [(Cfiles, CFLAGS)], LDFLAGS
            CFilesAndCFLAGS, LDFLAGS = \
                PlugChild._Generate_C(
                    #keep the same path
                    buildpath,
                    # but update location (add curent IEC channel at the end)
                    current_location + (self.BaseParams.getIEC_Channel()),
                    # filter locations that start with current IEC location
                    [ (l,d,t,n) for l,d,t,n in locations if l[0:len(current_location)] == current_location ])
            # stack the result
            PlugCFilesAndCFLAGS += CFilesAndCFLAGS
            PlugLDFLAGS += LDFLAGS
        
        return PlugCFilesAndCFLAGS,PlugLDFLAGS

    def BlockTypesFactory(self):
        return []

    def STLibraryFactory(self):
        return ""

    def IterChilds(self):
        for PlugType, PluggedChilds in self.PluggedChilds.items():
            for PlugInstance in PluggedChilds:
                   yield PlugInstance
    
    def _GetChildBySomething(self, sep, something, matching):
        toks = matching.split(sep,1)
        for PlugInstance in self.IterChilds:
            # if match component of the name
            if getattr(PlugInstance.BaseParams, something) == toks[0]:
                # if Name have other components
                if len(toks) == 2:
                    # Recurse in order to find the latest object
                    return PlugInstance._GetChildBySomething( sep, something, toks[1])
                # No sub name -> found
                return PlugInstance
        # Not found
        return None

    def GetChildByName(self, Name):
        return self._GetChildBySomething('.',"Name", Name)

    def GetChildByIECLocation(self, Location):
        return self._GetChildBySomething('_',"IEC_Channel", Name)
    
    def FindNewIEC_Channel(self, DesiredChannel):
        """
        Changes IEC Channel number to DesiredChannel if available, nearest available if not.
        @param DesiredChannel: The desired IEC channel (int)
        """
        # Get Current IEC channel
        CurrentChannel = self.BaseParams.getIEC_Channel()
        # Do nothing if no change
        if CurrentChannel == DesiredChannel: return CurrentChannel
        # Build a list of used Channels out of parent's PluggedChilds
        AllChannels=[]
        for PlugInstance in self.PlugParent.IterChilds():
            if PlugInstance != self:
                AllChannels.append(PlugInstance.BaseParams.getIEC_Channel())
        AllChannels.sort()

        # Now, try to guess the nearest available channel
        res = DesiredChannel
        while res in AllChannels: # While channel not free
            if res < CurrentChannel: # Want to go down ?
                res -=  1 # Test for n-1
                if res < 0 : return CurrentChannel # Can't go bellow 0, do nothing
            else : # Want to go up ?
                res +=  1 # Test for n-1
        # Finally set IEC Channel
        self.BaseParams.setIEC_Channel(res)
        return res

    def OnPlugClose(self):
        return True

    def _doRemoveChild(self, PlugInstance):
        # Remove all childs of child
        for SubPlugInstance in PlugInstance.IterChilds():
            PlugInstance._doRemoveChild(SubPlugInstance)
        # Call the OnCloseMethod
        PlugInstance.OnPlugClose()
        # Delete plugin dir
        shutil.rmtree(PlugInstance.PlugPath())
        # Remove child of PluggedChilds
        self.PluggedChilds[PlugInstance.PlugType].remove(PlugInstance)
        # Forget it... (View have to refresh)

    def PlugRemoveChild(self, PlugName):
        # Fetch the plugin
        PlugInstance = self.GetChildByName(PlugName)
        # Ask to his parent to remove it
        PlugInstance.PlugParent._doRemoveChild(PlugInstance)

    def PlugAddChild(self, PlugName, PlugType):
        """
        Create the plugins that may be added as child to this node self
        @param PlugType: string desining the plugin class name (get name from PlugChildsTypes)
        @param PlugName: string for the name of the plugin instance
        """
        PlugChildsTypes = dict(self.PlugChildsTypes)
        # Check that adding this plugin is allowed
        try:
            PlugClass = PlugChildsTypes[PlugType]
        except KeyError:
            raise Exception, "Cannot create child %s of type %s "%(PlugName, PlugType)
        
        # if PlugClass is a class factory, call it. (prevent unneeded imports)
        if type(PlugClass) == types.FunctionType:
            PlugClass = PlugClass()
        
        # Eventualy Initialize child instance list for this class of plugin
        PluggedChildsWithSameClass = self.PluggedChilds.setdefault(PlugType,list())
        # Check count
        if PlugClass.MaxCount and len(PluggedChildsWithSameClass) >= PlugClass.MaxCount:
            raise Exception, "Max count (%d) reached for this plugin of type %s "%(PlugClass.MaxCount, PlugType)
        
        # create the final class, derived of provided plugin and template
        class FinalPlugClass(PlugClass, PlugTemplate):
            """
            Plugin class is derivated into FinalPlugClass before being instanciated
            This way __init__ is overloaded to ensure PlugTemplate.__init__ is called 
            before PlugClass.__init__, and to do the file related stuff.
            """
            def __init__(_self):
                # self is the parent
                _self.PlugParent = self
                # Keep track of the plugin type name
                _self.PlugType = PlugType
                # Call the base plugin template init - change XSD into class members
                PlugTemplate.__init__(_self)
                # If dir have already be made, and file exist
                if os.path.isdir(_self.PlugPath(PlugName)) and os.path.isfile(_self.PluginXmlFilePath(PlugName)):
                    #Load the plugin.xml file into parameters members
                    _self.LoadXMLParams()
                    # Check that IEC_Channel is not already in use.
                    self.FindNewIEC_Channel(self.BaseParams.getIEC_Channel())
                    # Call the plugin real __init__
                    PlugClass.__init__(_self)
                    #Load and init all the childs
                    _self.LoadChilds()
                else:
                    # If plugin do not have corresponding file/dirs - they will be created on Save
                    # Set plugin name
                    _self.BaseParams.setName(PlugName)
                    # Find an IEC number
                    _self.FindNewIEC_Channel(0)
                    # Call the plugin real __init__
                    PlugClass.__init__(_self)

        # Create the object out of the resulting class
        newPluginOpj = FinalPlugClass()
        # Store it in PluggedChils
        PluggedChildsWithSameClass.append(newPluginOpj)
        
        return newPluginOpj
            

    def LoadXMLParams(self):
        # PlugParams have been filled, make a local dict to work with
        PlugParams = dict(self.PlugParams + self.MandatoryParams)
        # Get the xml tree
        xmlfile = open(self.PluginXmlFilePath(PlugName), 'r')
        tree = minidom.parse(xmlfile)
        xmlfile.close()
        # for each root elements
        for subtree in tree.childNodes:
            # if a plugin specific parameter set
            if subtree.nodeName in PlugParams:
                #Load into associated xmlclass.
                PlugParams[subtree.nodeName].loadXMLTree(subtree)
        
        # Basic check. Better to fail immediately.
        if(self.BaseParams.getName() != PlugName):
            raise Exception, "Project tree layout do not match plugin.xml %s!=%s "%(PlugName,self.BaseParams.getName())
        # Now, self.PlugPath() should be OK

    def LoadChilds(self):
        # Iterate over all PlugName@PlugType in plugin directory, and try to open them
        for PlugDir in os.listdir(self.PlugPath()):
            if os.path.isdir(os.path.join(self.PlugPath(),PlugDir)) and \
               PlugDir.count(NameTypeSeparator) == 1:
                try:
                    self.PlugAddChild(*PlugDir.split[NameTypeSeparator])
                except Exception, e:
                    print e


class PluginsRoot(PlugTemplate):

    # For root object, available Childs Types are modules of the plugin packages.
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
                    <xsd:attribute name="Compiler" type="xsd:string" use="required" default="gcc"/>
                    <xsd:attribute name="Nice" type="xsd:integer" use="required" default="0"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Xenomai">
                  <xsd:complexType>
                    <xsd:attribute name="xeno-config" type="xsd:string" use="required" default="/usr/xenomai/"/>
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
        
    
