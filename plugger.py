"""
Base definitions for beremiz plugins
"""

import os
import plugins
import types
import shutil
from xml.dom import minidom
from xmlclass import GenerateClassesFromXSDstring

from PLCControler import PLCControler

_BaseParamsClass = GenerateClassesFromXSDstring("""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="BaseParams">
            <xsd:complexType>
              <xsd:attribute name="Name" type="xsd:string" use="required"/>
              <xsd:attribute name="IEC_Channel" type="xsd:integer" use="required"/>
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
        Classes = [(name, XSDclass) for name, XSDclass in Classes.items() if XSDclass.IsBaseClass]
        if len(Classes) == 1:
            name, XSDclass = Classes[0]
            obj = XSDclass()
            self.PlugParams = (name, obj)
            setattr(self, name, obj)

    def __init__(self):
        # Create BaseParam 
        self.BaseParams = _BaseParamsClass()
        self.MandatoryParams = ("BaseParams", self.BaseParams)
        self._AddParamsMembers()
        self.PluggedChilds = {}

    def PluginBaseXmlFilePath(self, PlugName=None):
        return os.path.join(self.PlugPath(PlugName), "baseplugin.xml")
    
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

    def GetPlugParamsAttributes(self):
        return self.PlugParams[1].getElementAttributes()
    
    def SetPlugParamsAttribute(self, name, value):
        attr = getattr(self.PlugParams[1], name, None)
        if isinstance(attr, types.ClassType):
            attr.SetValue(value)
        else:
            setattr(self.PlugParams[1], name, value)

    def PlugRequestSave(self):
        # If plugin do not have corresponding directory
        plugpath = self.PlugPath()
        if not os.path.isdir(plugpath):
            # Create it
            os.mkdir(plugpath)

        # generate XML for base XML parameters controller of the plugin
        basexmlfilepath = self.PluginBaseXmlFilePath()
        if basexmlfilepath:
            BaseXMLFile = open(basexmlfilepath,'w')
            BaseXMLFile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            BaseXMLFile.write(self.MandatoryParams[1].generateXMLText(self.MandatoryParams[0], 0))
            BaseXMLFile.close()
        
        # generate XML for XML parameters controller of the plugin
        xmlfilepath = self.PluginXmlFilePath()
        if xmlfilepath:
            XMLFile = open(xmlfilepath,'w')
            XMLFile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            XMLFile.write(self.PlugParams[1].generateXMLText(self.PlugParams[0], 0))
            XMLFile.close()
        
        # Call the plugin specific OnPlugSave method
        result = self.OnPlugSave()
        if not result:
            return "Error while saving \"%s\""%self.PlugPath()
        
        # go through all childs and do the same
        for PlugChild in self.IterChilds():
            result = PlugChild.PlugRequestSave()
            if result:
                return result
        return None
    
    def PlugImport(self, src_PlugPath):
        shutil.copytree(src_PlugPath, self.PlugPath)
        return True

    def PlugGenerate_C(self, buildpath, current_location, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [(IEC_loc, IEC_Direction, IEC_Type, Name)]\
            ex: [((0,0,4,5),'I','STRING','__IX_0_0_4_5'),...]
        """
        return [],""
    
    def _Generate_C(self, buildpath, current_location, locations):
        # Generate plugins [(Cfiles, CFLAGS)], LDFLAGS
        PlugCFilesAndCFLAGS, PlugLDFLAGS = self.PlugGenerate_C(buildpath, current_location, locations)
        # recurse through all childs, and stack their results
        for PlugChild in self.IterChilds():
            # Compute chile IEC location
            new_location = current_location + (self.BaseParams.getIEC_Channel())
            # Get childs [(Cfiles, CFLAGS)], LDFLAGS
            CFilesAndCFLAGS, LDFLAGS = \
                PlugChild._Generate_C(
                    #keep the same path
                    buildpath,
                    # but update location (add curent IEC channel at the end)
                    new_location,
                    # filter locations that start with current IEC location
                    [ (l,d,t,n) for l,d,t,n in locations if l[0:len(new_location)] == new_location ])
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
        for PlugInstance in self.IterChilds():
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
    
    def GetPlugInfos(self):
        childs = []
        for child in self.IterChilds():
            childs.append(child.GetPlugInfos())
        return {"name" : self.BaseParams.getName(), "type" : None, "values" : childs}
    
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
        PluggedChildsWithSameClass = self.PluggedChilds.setdefault(PlugType, list())
        # Check count
        if getattr(PlugClass, "PlugMaxCount", None) and len(PluggedChildsWithSameClass) >= PlugClass.PlugMaxCount:
            raise Exception, "Max count (%d) reached for this plugin of type %s "%(PlugClass.PlugMaxCount, PlugType)
        
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
                    _self.LoadXMLParams(PlugName)
                    # Check that IEC_Channel is not already in use.
                    self.FindNewIEC_Channel(self.BaseParams.getIEC_Channel())
                    # Call the plugin real __init__
                    if getattr(PlugClass, "__init__", None):
                        PlugClass.__init__(_self)
                    #Load and init all the childs
                    _self.LoadChilds()
                else:
                    # If plugin do not have corresponding file/dirs - they will be created on Save
                    # Set plugin name
                    _self.BaseParams.setName(PlugName)
                    os.mkdir(_self.PlugPath())
                    # Find an IEC number
                    _self.FindNewIEC_Channel(0)
                    # Call the plugin real __init__
                    if getattr(PlugClass, "__init__", None):
                        PlugClass.__init__(_self)
                    _self.PlugRequestSave()

        # Create the object out of the resulting class
        newPluginOpj = FinalPlugClass()
        # Store it in PluggedChils
        PluggedChildsWithSameClass.append(newPluginOpj)
        
        return newPluginOpj
            

    def LoadXMLParams(self, PlugName = None, test = True):
        # Get the base xml tree
        basexmlfilepath = self.PluginBaseXmlFilePath(PlugName)
        if basexmlfilepath:
            basexmlfile = open(basexmlfilepath, 'r')
            basetree = minidom.parse(basexmlfile)
            self.MandatoryParams[1].loadXMLTree(basetree.childNodes[0])
            basexmlfile.close()
        
        # Get the xml tree
        xmlfilepath = self.PluginXmlFilePath(PlugName)
        if xmlfilepath:
            xmlfile = open(xmlfilepath, 'r')
            tree = minidom.parse(xmlfile)
            self.PlugParams[1].loadXMLTree(tree.childNodes[0])
            xmlfile.close()
        
        if test:
            # Basic check. Better to fail immediately.
            if not PlugName:
                PlugName = os.path.split(self.PlugPath())[1].split(NameTypeSeparator)[0]
            if (self.BaseParams.getName() != PlugName):
                raise Exception, "Project tree layout do not match plugin.xml %s!=%s "%(PlugName, self.BaseParams.getName())
            # Now, self.PlugPath() should be OK

    def LoadChilds(self):
        # Iterate over all PlugName@PlugType in plugin directory, and try to open them
        for PlugDir in os.listdir(self.PlugPath()):
            if os.path.isdir(os.path.join(self.PlugPath(), PlugDir)) and \
               PlugDir.count(NameTypeSeparator) == 1:
                try:
                    self.PlugAddChild(*PlugDir.split(NameTypeSeparator))
                except Exception, e:
                    print e

def _GetClassFunction(name):
    def GetRootClass():
        return getattr(__import__("plugins." + name), name).RootClass
    return GetRootClass

class PluginsRoot(PlugTemplate):

    # For root object, available Childs Types are modules of the plugin packages.
    PlugChildsTypes = [(name, _GetClassFunction(name)) for name in plugins.__all__]

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
                    <xsd:attribute name="Priority" type="xsd:integer" use="required"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Linux">
                  <xsd:complexType>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required" default="gcc"/>
                    <xsd:attribute name="Nice" type="xsd:integer" use="required"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Xenomai">
                  <xsd:complexType>
                    <xsd:attribute name="xeno-config" type="xsd:string" use="required" default="/usr/xenomai/"/>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required"/>
                    <xsd:attribute name="Priority" type="xsd:integer" use="required"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="RTAI">
                  <xsd:complexType>
                    <xsd:attribute name="xeno-config" type="xsd:string" use="required"/>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required"/>
                    <xsd:attribute name="Priority" type="xsd:integer" use="required"/>
                  </xsd:complexType>
                </xsd:element>
                <xsd:element name="Library">
                  <xsd:complexType>
                    <xsd:attribute name="Dynamic" type="xsd:boolean" use="required" default="true"/>
                    <xsd:attribute name="Compiler" type="xsd:string" use="required"/>
                  </xsd:complexType>
                </xsd:element>
              </xsd:choice>
            </xsd:complexType>
          </xsd:element>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def __init__(self):
        PlugTemplate.__init__(self)
        # self is the parent
        self.PlugParent = None
        # Keep track of the plugin type name
        self.PlugType = "Beremiz"
        
        self.ProjectPath = ""
        self.PLCManager = None
    
    def HasProjectOpened(self):
        """
        Return if a project is actually opened
        """
        return self.ProjectPath != ""
    
    def GetProjectPath(self):
        return self.ProjectPath
    
    def GetTargetTypes(self):
        return self.BeremizRoot.TargetType.getChoices().keys()
    
    def ChangeTargetType(self, target_type):
        self.BeremizRoot.TargetType.addContent(target_type)
        
    def GetTargetAttributes(self):
        content = self.BeremizRoot.TargetType.getContent()
        if content:
            return content["value"].getElementAttributes()
        else:
            return []
        
    def SetTargetAttribute(self, name, value):
        content = self.BeremizRoot.TargetType.getContent()
        if content:
            attr = getattr(content["value"], name, None)
            if isinstance(attr, types.ClassType):
                attr.SetValue(value)
            else:
                setattr(content["value"], name, value)
    
    def GetTargetType(self):
        content = self.BeremizRoot.TargetType.getContent()
        if content:
            return content["name"]
        else:
            return ""
    
    def NewProject(self, ProjectPath, PLCParams):
        """
        Create a new project in an empty folder
        @param ProjectPath: path of the folder where project have to be created
        @param PLCParams: properties of the PLCOpen program created
        """
        # Verify that choosen folder is empty
        if not os.path.isdir(ProjectPath) or len(os.listdir(ProjectPath)) > 0:
            return "Folder choosen isn't empty. You can't use it for a new project!"
        # Create Controler for PLCOpen program
        self.PLCManager = PLCControler()
        self.PLCManager.CreateNewProject(PLCParams.pop("projectName"))
        self.PLCManager.SetProjectProperties(properties = PLCParams)
        # Change XSD into class members
        self._AddParamsMembers()
        self.PluggedChilds = {}
        # No IEC channel, name, etc...
        self.MandatoryParams = []
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        self.BaseParams.setName(os.path.split(ProjectPath)[1])
        return None
        
    def LoadProject(self, ProjectPath):
        """
        Load a project contained in a folder
        @param ProjectPath: path of the project folder
        """
        # Verify that project contains a PLCOpen program
        plc_file = os.path.join(ProjectPath, "plc.xml")
        if not os.path.isfile(plc_file):
            return "Folder choosen doesn't contain a program. It's not a valid project!"
        # Create Controler for PLCOpen program
        self.PLCManager = PLCControler()
        # Load PLCOpen file
        result = self.PLCManager.OpenXMLFile(plc_file)
        if result:
            return result
        # Change XSD into class members
        self._AddParamsMembers()
        self.PluggedChilds = {}
        # No IEC channel, name, etc...
        self.MandatoryParams = None
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        # If dir have already be made, and file exist
        if os.path.isdir(self.PlugPath()) and os.path.isfile(self.PluginXmlFilePath()):
            #Load the plugin.xml file into parameters members
            result = self.LoadXMLParams(test = False)
            if result:
                return result
            #Load and init all the childs
            self.LoadChilds()
        self.BaseParams.setName(os.path.split(ProjectPath)[1])
        return None
    
    def SaveProject(self):
        if not self.PLCManager.SaveXMLFile():
            self.PLCManager.SaveXMLFile(os.path.join(self.ProjectPath, 'plc.xml'))
        self.PlugRequestSave()
    
    def PlugPath(self, PlugName=None):
        return self.ProjectPath
    
    def PluginBaseXmlFilePath(self, PlugName=None):
        return None
    
    def PluginXmlFilePath(self, PlugName=None):
        return os.path.join(self.PlugPath(PlugName), "beremiz.xml")
