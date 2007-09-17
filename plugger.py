"""
Base definitions for beremiz plugins
"""

import os,sys
import plugins
import types
import shutil
from xml.dom import minidom
import wx

#Quick hack to be able to find Beremiz IEC tools. Should be config params.
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "plcopeneditor"))

from xmlclass import GenerateClassesFromXSDstring

_BaseParamsClass = GenerateClassesFromXSDstring("""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="BaseParams">
            <xsd:complexType>
              <xsd:attribute name="Name" type="xsd:string" use="required" default="__unnamed__"/>
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
        self.PlugParams = None
        if self.XSD:
            Classes = GenerateClassesFromXSDstring(self.XSD)[0]
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
        #Default, do nothing and return success
        return True

    def GetParamsAttributes(self, path = None):
        if path:
            parts = path.split(".", 1)
            if self.MandatoryParams and parts[0] == self.MandatoryParams[0]:
                return self.MandatoryParams[1].getElementInfos(parts[0], parts[1])
            elif self.PlugParams and parts[0] == self.PlugParams[0]:
                return self.PlugParams[1].getElementInfos(parts[0], parts[1])
        else:
            params = []
            if self.MandatoryParams:
                params.append(self.MandatoryParams[1].getElementInfos(self.MandatoryParams[0]))
            if self.PlugParams:
                params.append(self.PlugParams[1].getElementInfos(self.PlugParams[0]))
            return params
        
    def SetParamsAttribute(self, path, value, logger):
        # Filter IEC_Channel and Name, that have specific behavior
        if path == "BaseParams.IEC_Channel":
            return self.FindNewIEC_Channel(value,logger), True
        elif path == "BaseParams.Name":
            res = self.FindNewName(value,logger)
            self.PlugRequestSave()
            return res, True
        
        parts = path.split(".", 1)
        if self.MandatoryParams and parts[0] == self.MandatoryParams[0]:
            self.MandatoryParams[1].setElementValue(parts[1], value)
        elif self.PlugParams and parts[0] == self.PlugParams[0]:
            self.PlugParams[1].setElementValue(parts[1], value)
        return value, False

    def PlugRequestSave(self):
        # If plugin do not have corresponding directory
        plugpath = self.PlugPath()
        if not os.path.isdir(plugpath):
            # Create it
            os.mkdir(plugpath)

        # generate XML for base XML parameters controller of the plugin
        if self.MandatoryParams:
            BaseXMLFile = open(self.PluginBaseXmlFilePath(),'w')
            BaseXMLFile.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            BaseXMLFile.write(self.MandatoryParams[1].generateXMLText(self.MandatoryParams[0], 0))
            BaseXMLFile.close()
        
        # generate XML for XML parameters controller of the plugin
        if self.PlugParams:
            XMLFile = open(self.PluginXmlFilePath(),'w')
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

    def PlugGenerate_C(self, buildpath, locations, logger):
        """
        Generate C code
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        logger.write_warning(".".join(map(lambda x:str(x), self.GetCurrentLocation())) + " -> Nothing yo do\n")
        return [],""
    
    def _Generate_C(self, buildpath, locations, logger):
        # Generate plugins [(Cfiles, CFLAGS)], LDFLAGS
        PlugCFilesAndCFLAGS, PlugLDFLAGS = self.PlugGenerate_C(buildpath, locations, logger)
        # recurse through all childs, and stack their results
        for PlugChild in self.IterChilds():
            new_location = PlugChild.GetCurrentLocation()
            # How deep are we in the tree ?
            depth=len(new_location)
            CFilesAndCFLAGS, LDFLAGS = \
                PlugChild._Generate_C(
                    #keep the same path
                    buildpath,
                    # filter locations that start with current IEC location
                    [loc for loc in locations if loc["LOC"][0:depth] == new_location ],
                    #propagete logger
                    logger)
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
    
    def GetCurrentLocation(self):
        """
        @return:  Tupple containing plugin IEC location of current plugin : %I0.0.4.5 => (0,0,4,5)
        """
        return self.PlugParent.GetCurrentLocation() + (self.BaseParams.getIEC_Channel(),)

    def GetPlugRoot(self):
        return self.PlugParent.GetPlugRoot()

    def GetPlugInfos(self):
        childs = []
        # reorder childs by IEC_channels
        ordered = [(chld.BaseParams.getIEC_Channel(),chld) for chld in self.IterChilds()]
        if ordered:
            ordered.sort()
            for child in zip(*ordered)[1]:
                childs.append(child.GetPlugInfos())
        return {"name" : "%d-%s"%(self.BaseParams.getIEC_Channel(),self.BaseParams.getName()), "type" : self.BaseParams.getName(), "values" : childs}
    
    
    def FindNewName(self, DesiredName, logger):
        """
        Changes Name to DesiredName if available, Name-N if not.
        @param DesiredName: The desired Name (string)
        """
        # Get Current Name
        CurrentName = self.BaseParams.getName()
        # Do nothing if no change
        #if CurrentName == DesiredName: return CurrentName
        # Build a list of used Name out of parent's PluggedChilds
        AllNames=[]
        for PlugInstance in self.PlugParent.IterChilds():
            if PlugInstance != self:
                AllNames.append(PlugInstance.BaseParams.getName())

        # Find a free name, eventually appending digit
        res = DesiredName
        suffix = 1
        while res in AllNames:
            res = "%s-%d"%(DesiredName, suffix)
            suffix += 1
        
        # Get old path
        oldname = self.PlugPath()
        # Check previous plugin existance
        dontexist = self.BaseParams.getName() == "__unnamed__"
        # Set the new name
        self.BaseParams.setName(res)
        # Rename plugin dir if exist
        if not dontexist:
            shutil.move(oldname, self.PlugPath())
        # warn user he has two left hands
        if DesiredName != res:
            logger.write_warning("A child names \"%s\" already exist -> \"%s\"\n"%(DesiredName,res))
        return res

    def FindNewIEC_Channel(self, DesiredChannel, logger):
        """
        Changes IEC Channel number to DesiredChannel if available, nearest available if not.
        @param DesiredChannel: The desired IEC channel (int)
        """
        # Get Current IEC channel
        CurrentChannel = self.BaseParams.getIEC_Channel()
        # Do nothing if no change
        #if CurrentChannel == DesiredChannel: return CurrentChannel
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
                if res < 0 :
                    if logger :
                        logger.write_warning("Cannot find lower free IEC channel than %d\n"%CurrentChannel)
                    return CurrentChannel # Can't go bellow 0, do nothing
            else : # Want to go up ?
                res +=  1 # Test for n-1
        # Finally set IEC Channel
        self.BaseParams.setIEC_Channel(res)
        if logger and DesiredChannel != res:
            logger.write_warning("A child with IEC channel %d already exist -> %d\n"%(DesiredChannel,res))
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

    def PlugAddChild(self, PlugName, PlugType, logger):
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
                # check name is unique
                NewPlugName = _self.FindNewName(PlugName, logger)
                # If dir have already be made, and file exist
                if os.path.isdir(_self.PlugPath(NewPlugName)): #and os.path.isfile(_self.PluginXmlFilePath(PlugName)):
                    #Load the plugin.xml file into parameters members
                    _self.LoadXMLParams(NewPlugName)
                    # Basic check. Better to fail immediately.
                    if (_self.BaseParams.getName() != NewPlugName):
                        raise Exception, "Project tree layout do not match plugin.xml %s!=%s "%(NewPlugName, _self.BaseParams.getName())

                    # Now, self.PlugPath() should be OK
                    
                    # Check that IEC_Channel is not already in use.
                    _self.FindNewIEC_Channel(_self.BaseParams.getIEC_Channel(),logger)
                    # Call the plugin real __init__
                    if getattr(PlugClass, "__init__", None):
                        PlugClass.__init__(_self)
                    #Load and init all the childs
                    _self.LoadChilds(logger)
                else:
                    # If plugin do not have corresponding file/dirs - they will be created on Save
                    os.mkdir(_self.PlugPath())
                    # Find an IEC number
                    _self.FindNewIEC_Channel(0, None)
                    # Call the plugin real __init__
                    if getattr(PlugClass, "__init__", None):
                        PlugClass.__init__(_self)
                    _self.PlugRequestSave()

        # Create the object out of the resulting class
        newPluginOpj = FinalPlugClass()
        # Store it in PluggedChils
        PluggedChildsWithSameClass.append(newPluginOpj)
        
        return newPluginOpj
            

    def LoadXMLParams(self, PlugName = None):
        # Get the base xml tree
        if self.MandatoryParams:
            basexmlfile = open(self.PluginBaseXmlFilePath(PlugName), 'r')
            basetree = minidom.parse(basexmlfile)
            self.MandatoryParams[1].loadXMLTree(basetree.childNodes[0])
            basexmlfile.close()
        
        # Get the xml tree
        if self.PlugParams:
            xmlfile = open(self.PluginXmlFilePath(PlugName), 'r')
            tree = minidom.parse(xmlfile)
            self.PlugParams[1].loadXMLTree(tree.childNodes[0])
            xmlfile.close()
        
    def LoadChilds(self, logger):
        # Iterate over all PlugName@PlugType in plugin directory, and try to open them
        for PlugDir in os.listdir(self.PlugPath()):
            if os.path.isdir(os.path.join(self.PlugPath(), PlugDir)) and \
               PlugDir.count(NameTypeSeparator) == 1:
                pname, ptype = PlugDir.split(NameTypeSeparator)
                try:
                    self.PlugAddChild(pname, ptype, logger)
                except Exception, e:
                    logger.write_error("Could not add child \"%s\", type %s :\n%s\n"%(pname, ptype, str(e)))

def _GetClassFunction(name):
    def GetRootClass():
        return getattr(__import__("plugins." + name), name).RootClass
    return GetRootClass


####################################################################################
####################################################################################
####################################################################################
###################################   ROOT    ######################################
####################################################################################
####################################################################################
####################################################################################

iec2cc_path = os.path.join(base_folder, "matiec", "iec2cc")
ieclib_path = os.path.join(base_folder, "matiec", "lib")

# import for project creation timestamping
from time import localtime
from datetime import datetime
# import necessary stuff from PLCOpenEditor
from PLCControler import PLCControler
from PLCOpenEditor import PLCOpenEditor, ProjectDialog
from TextViewer import TextViewer
from plcopen.structures import IEC_KEYWORDS
import re

class PluginsRoot(PlugTemplate):
    """
    This class define Root object of the plugin tree. 
    It is responsible of :
    - Managing project directory
    - Building project
    - Handling PLCOpenEditor controler and view
    - Loading user plugins and instanciante them as childs
    - ...
    
    """

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

    def __init__(self, frame):

        self.MandatoryParams = None
        self.AppFrame = frame
        
        """
        This method are not called here... but in NewProject and OpenProject
        self._AddParamsMembers()
        self.PluggedChilds = {}
        """

        # root have no parent
        self.PlugParent = None
        # Keep track of the plugin type name
        self.PlugType = "Beremiz"
        
        # After __init__ root plugin is not valid
        self.ProjectPath = None
        self.PLCManager = None
        self.PLCEditor = None
    
    def HasProjectOpened(self):
        """
        Return if a project is actually opened
        """
        return self.ProjectPath != None

    def GetPlugRoot(self):
        return self

    def GetCurrentLocation(self):
        return ()
    
    def GetProjectPath(self):
        return self.ProjectPath
    
    def GetPlugInfos(self):
        childs = []
        for child in self.IterChilds():
            childs.append(child.GetPlugInfos())
        return {"name" : "PLC (%s)"%os.path.split(self.ProjectPath)[1], "type" : None, "values" : childs}
    
    def NewProject(self, ProjectPath):
        """
        Create a new project in an empty folder
        @param ProjectPath: path of the folder where project have to be created
        @param PLCParams: properties of the PLCOpen program created
        """
        # Verify that choosen folder is empty
        if not os.path.isdir(ProjectPath) or len(os.listdir(ProjectPath)) > 0:
            return "Folder choosen isn't empty. You can't use it for a new project!"
        
        dialog = ProjectDialog(self.AppFrame)
        if dialog.ShowModal() == wx.ID_OK:
            values = dialog.GetValues()
            values["creationDateTime"] = datetime(*localtime()[:6])
            dialog.Destroy()
        else:
            dialog.Destroy()
            return "Project not created"
        
        # Create Controler for PLCOpen program
        self.PLCManager = PLCControler()
        self.PLCManager.CreateNewProject(values.pop("projectName"))
        self.PLCManager.SetProjectProperties(properties = values)
        # Change XSD into class members
        self._AddParamsMembers()
        self.PluggedChilds = {}
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        return None
        
    def LoadProject(self, ProjectPath, logger):
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
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        # If dir have already be made, and file exist
        if os.path.isdir(self.PlugPath()) and os.path.isfile(self.PluginXmlFilePath()):
            #Load the plugin.xml file into parameters members
            result = self.LoadXMLParams()
            if result:
                return result
            #Load and init all the childs
            self.LoadChilds(logger)
        return None
    
    def SaveProject(self):
        if not self.PLCManager.SaveXMLFile():
            self.PLCManager.SaveXMLFile(os.path.join(self.ProjectPath, 'plc.xml'))
        if self.PLCEditor:
            self.PLCEditor.RefreshTitle()
        self.PlugRequestSave()
    
    def PlugPath(self, PlugName=None):
        return self.ProjectPath
    
    def PluginXmlFilePath(self, PlugName=None):
        return os.path.join(self.PlugPath(PlugName), "beremiz.xml")

    def PlugGenerate_C(self, buildpath, locations, logger):
        """
        Generate C code
        @param locations: List of complete variables locations \
            [(IEC_loc, IEC_Direction, IEC_Type, Name)]\
            ex: [((0,0,4,5),'I','STRING','__IX_0_0_4_5'),...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [(C_file_name, "") for C_file_name in self.PLCGeneratedCFiles ] , ""
    
    def _getBuildPath(self):
        return os.path.join(self.ProjectPath, "build")
    
    def _getIECcodepath(self):
        # define name for IEC code file
        return os.path.join(self._getBuildPath(), "plc.st")
    
    def _Generate_SoftPLC(self, logger):
        """
        Generate SoftPLC ST/IL/SFC code out of PLCOpenEditor controller, and compile it with IEC2CC
        @param buildpath: path where files should be created
        @param logger: the log pseudo file
        """

        logger.write("Generating SoftPLC IEC-61131 ST/IL/SFC code...\n")
        buildpath = self._getBuildPath()
        # define name for IEC code file
        plc_file = self._getIECcodepath()
        # ask PLCOpenEditor controller to write ST/IL/SFC code file
        result = self.PLCManager.GenerateProgram(plc_file)
        if not result:
            # Failed !
            logger.write_error("Error : ST/IL/SFC code generator returned %d\n"%result)
            return False
        logger.write("Compiling ST Program in to C Program...\n")
        # Now compile IEC code into many C files
        # files are listed to stdout, and errors to stderr. 
        status, result, err_result = logger.LogCommand("%s %s -I %s %s"%(iec2cc_path, plc_file, ieclib_path, buildpath))
        if status:
            # Failed !
            logger.write_error("Error : IEC to C compiler returned %d\n"%status)
            return False
        # Now extract C files of stdout
        C_files = result.splitlines()
        # remove those that are not to be compiled because included by others
        C_files.remove("POUS.c")
        C_files.remove("LOCATED_VARIABLES.h")
        # transform those base names to full names with path
        C_files = map(lambda filename:os.path.join(buildpath, filename), C_files)
        logger.write("Extracting Located Variables...\n")
        # IEC2CC compiler generate a list of located variables : LOCATED_VARIABLES.h
        location_file = open(os.path.join(buildpath,"LOCATED_VARIABLES.h"))
        locations = []
        # each line of LOCATED_VARIABLES.h declares a located variable
        lines = [line.strip() for line in location_file.readlines()]
        # This regular expression parses the lines genereated by IEC2CC
        LOCATED_MODEL = re.compile("__LOCATED_VAR\((?P<IEC_TYPE>[A-Z]*),(?P<NAME>[_A-Za-z0-9]*),(?P<DIR>[QMI])(?:,(?P<SIZE>[XBWD]))?,(?P<LOC>[,0-9]*)\)")
        for line in lines:
            # If line match RE, 
            result = LOCATED_MODEL.match(line)
            if result:
                # Get the resulting dict
                resdict = result.groupdict()
                # rewrite string for variadic location as a tuple of integers
                resdict['LOC'] = tuple(map(int,resdict['LOC'].split(',')))
                # set located size to 'X' if not given 
                if not resdict['SIZE']:
                    resdict['SIZE'] = 'X'
                # finally store into located variable list
                locations.append(resdict)
        # Keep track of generated C files for later use by self.PlugGenerate_C
        self.PLCGeneratedCFiles = C_files
        # Keep track of generated located variables for later use by self._Generate_C
        self.PLCGeneratedLocatedVars = locations
        return True

    def _build(self, logger):
        """
        Method called by user to (re)build SoftPLC and plugin tree
        """
        buildpath = self._getBuildPath()

        # Eventually create build dir
        if not os.path.exists(buildpath):
            os.mkdir(buildpath)
        
        logger.flush()
        logger.write("Start build in %s\n" % buildpath)
        
        # Generate SoftPLC code
        if not self._Generate_SoftPLC(logger):
            logger.write_error("SoftPLC code generation failed !\n")
            return False

        logger.write("SoftPLC code generation successfull\n")
        
        # Generate C code and compilation params from plugin hierarchy
        try:
            CFilesAndCFLAGS, LDFLAGS = self._Generate_C(
                buildpath, 
                self.PLCGeneratedLocatedVars,
                logger)
        except Exception, msg:
            logger.write_error("Plugins code generation Failed !\n")
            logger.write_error(str(msg))
            return False

        logger.write("Plugins code generation successfull\n")

        # Compile the resulting code into object files.
        for CFile, CFLAG in CFilesAndCFLAGS:
            logger.write(str((CFile,CFLAG)))
        
        # Link object files into something that can be executed on target
        logger.write(LDFLAGS)

    def _showIECcode(self, logger):
        plc_file = self._getIECcodepath()
        new_dialog = wx.Frame(None)
        ST_viewer = TextViewer(new_dialog, None, None)
        #ST_viewer.Enable(False)
        ST_viewer.SetKeywords(IEC_KEYWORDS)
        try:
            text = file(plc_file).read()
        except:
            text = '(* No IEC code have been generated at that time ! *)'
        ST_viewer.SetText(text)
            
        new_dialog.Show()

    def _EditPLC(self, logger):
        if not self.PLCEditor:
            def _onclose():
                self.PLCEditor = None
            def _onsave():
                self.SaveProject()
            self.PLCEditor = PLCOpenEditor(self.AppFrame, self.PLCManager)
            self.PLCEditor.RefreshProjectTree()
            self.PLCEditor.RefreshFileMenu()
            self.PLCEditor.RefreshEditMenu()
            self.PLCEditor.RefreshToolBar()
            self.PLCEditor._onclose = _onclose
            self.PLCEditor._onsave = _onsave
            self.PLCEditor.Show()

    def _Clean(self, logger):
        logger.write_error("Not impl\n")
    
    def _Run(self, logger):
        logger.write_error("Not impl\n")

    PluginMethods = [("EditPLC",_EditPLC), ("Build",_build), ("Clean",_Clean), ("Run",_Run), ("Show IEC code",_showIECcode)]
    
