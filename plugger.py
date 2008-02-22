"""
Base definitions for beremiz plugins
"""

import os,sys
import plugins
import types
import shutil
from xml.dom import minidom
import wx
import subprocess, ctypes, time, shutil

#Quick hack to be able to find Beremiz IEC tools. Should be config params.
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "plcopeneditor"))

from xmlclass import GenerateClassesFromXSDstring

_BaseParamsClass = GenerateClassesFromXSDstring("""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="BaseParams">
            <xsd:complexType>
              <xsd:attribute name="Name" type="xsd:string" use="optional" default="__unnamed__"/>
              <xsd:attribute name="IEC_Channel" type="xsd:integer" use="required"/>
              <xsd:attribute name="Enabled" type="xsd:boolean" use="optional" default="true"/>
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>""")["BaseParams"]

NameTypeSeparator = '@'

class MiniTextControler:
    
    def __init__(self, filepath):
        self.FilePath = filepath
        
    def SetEditedElementText(self, tagname, text):
        file = open(self.FilePath, "w")
        file.write(text)
        file.close()
        
    def GetEditedElementText(self, tagname):
        if os.path.isfile(self.FilePath):
            file = open(self.FilePath, "r")
            text = file.read()
            file.close()
            return text
        return ""
    
    def GetEditedElementInterfaceVars(self, tagname):
        return []
    
    def GetEditedElementType(self, tagname):
        return "program"
    
    def GetBlockTypes(self, tagname = ""):
        return []
    
    def GetEnumeratedDataValues(self):
        return []
    
    def StartBuffering(self):
        pass

    def EndBuffering(self):
        pass

    def BufferProject(self):
        pass

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
            Classes = GenerateClassesFromXSDstring(self.XSD)
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
        # copy PluginMethods so that it can be later customized
        self.PluginMethods = [dic.copy() for dic in self.PluginMethods]

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
            if wx.VERSION < (2, 8, 0) and self.MandatoryParams:
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
            return res, False
        
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
        return [],"",False
    
    def _Generate_C(self, buildpath, locations, logger):
        # Generate plugins [(Cfiles, CFLAGS)], LDFLAGS
        PlugCFilesAndCFLAGS, PlugLDFLAGS, DoCalls = self.PlugGenerate_C(buildpath, locations, logger)
        # if some files heve been generated put them in the list with their location
        if PlugCFilesAndCFLAGS:
            LocationCFilesAndCFLAGS = [(self.GetCurrentLocation(), PlugCFilesAndCFLAGS, DoCalls)]
        else:
            LocationCFilesAndCFLAGS = []

        # plugin asks some some LDFLAGS
        if PlugLDFLAGS:
            # LDFLAGS can be either string
            if type(PlugLDFLAGS)==type(str()):
                LDFLAGS=[PlugLDFLAGS]
            #or list of strings
            elif type(PlugLDFLAGS)==type(list()):
                LDFLAGS=PlugLDFLAGS[:]
        else:
            LDFLAGS=[]
        
        # recurse through all childs, and stack their results
        for PlugChild in self.IECSortedChilds():
            new_location = PlugChild.GetCurrentLocation()
            # How deep are we in the tree ?
            depth=len(new_location)
            _LocationCFilesAndCFLAGS, _LDFLAGS = \
                PlugChild._Generate_C(
                    #keep the same path
                    buildpath,
                    # filter locations that start with current IEC location
                    [loc for loc in locations if loc["LOC"][0:depth] == new_location ],
                    #propagete logger
                    logger)
            # stack the result
            LocationCFilesAndCFLAGS += _LocationCFilesAndCFLAGS
            LDFLAGS += _LDFLAGS
        
        return LocationCFilesAndCFLAGS,LDFLAGS

    def BlockTypesFactory(self):
        return []

    def STLibraryFactory(self):
        return ""

    def IterChilds(self):
        for PlugType, PluggedChilds in self.PluggedChilds.items():
            for PlugInstance in PluggedChilds:
                   yield PlugInstance
    
    def IECSortedChilds(self):
        # reorder childs by IEC_channels
        ordered = [(chld.BaseParams.getIEC_Channel(),chld) for chld in self.IterChilds()]
        if ordered:
            ordered.sort()
            return zip(*ordered)[1]
        else:
            return []
    
    def _GetChildBySomething(self, something, toks):
        for PlugInstance in self.IterChilds():
            # if match component of the name
            if getattr(PlugInstance.BaseParams, something) == toks[0]:
                # if Name have other components
                if len(toks) >= 2:
                    # Recurse in order to find the latest object
                    return PlugInstance._GetChildBySomething( something, toks[1:])
                # No sub name -> found
                return PlugInstance
        # Not found
        return None

    def GetChildByName(self, Name):
        if Name:
            toks = Name.split('.')
            return self._GetChildBySomething("Name", toks)
        else:
            return self

    def GetChildByIECLocation(self, Location):
        if Location:
            return self._GetChildBySomething("IEC_Channel", Location)
        else:
            return self
    
    def GetCurrentLocation(self):
        """
        @return:  Tupple containing plugin IEC location of current plugin : %I0.0.4.5 => (0,0,4,5)
        """
        return self.PlugParent.GetCurrentLocation() + (self.BaseParams.getIEC_Channel(),)

    def GetCurrentName(self):
        """
        @return:  String "ParentParentName.ParentName.Name"
        """
        return  self.PlugParent._GetCurrentName() + self.BaseParams.getName()

    def _GetCurrentName(self):
        """
        @return:  String "ParentParentName.ParentName.Name."
        """
        return  self.PlugParent._GetCurrentName() + self.BaseParams.getName() + "."

    def GetPlugRoot(self):
        return self.PlugParent.GetPlugRoot()

    def GetFullIEC_Channel(self):
        return ".".join([str(i) for i in self.GetCurrentLocation()]) + ".x"

    def GetLocations(self):
        location = self.GetCurrentLocation()
        return [loc for loc in self.PlugParent.GetLocations() if loc["LOC"][0:len(location)] == location]

    def GetPlugInfos(self):
        childs = []
        # reorder childs by IEC_channels
        for child in self.IECSortedChilds():
            childs.append(child.GetPlugInfos())
        if wx.VERSION < (2, 8, 0):
            return {"name" : "%d-%s"%(self.BaseParams.getIEC_Channel(),self.BaseParams.getName()), "type" : self.BaseParams.getName(), "values" : childs}
        else:
            return {"name" : self.BaseParams.getName(), "channel" : self.BaseParams.getIEC_Channel(), "enabled" : self.BaseParams.getEnabled(), "parent" : len(self.PlugChildsTypes) > 0, "type" : self.BaseParams.getName(), "values" : childs}
    
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

    def PlugRemove(self):
        # Fetch the plugin
        #PlugInstance = self.GetChildByName(PlugName)
        # Ask to his parent to remove it
        self.PlugParent._doRemoveChild(self)

    def PlugAddChild(self, PlugName, PlugType, logger):
        """
        Create the plugins that may be added as child to this node self
        @param PlugType: string desining the plugin class name (get name from PlugChildsTypes)
        @param PlugName: string for the name of the plugin instance
        """
        # reorgabize self.PlugChildsTypes tuples from (name, PlugClass, Help)
        # to ( name, (PlugClass, Help)), an make a dict
        transpose = zip(*self.PlugChildsTypes)
        PlugChildsTypes = dict(zip(transpose[0],zip(transpose[1],transpose[2])))
        # Check that adding this plugin is allowed
        try:
            PlugClass, PlugHelp = PlugChildsTypes[PlugType]
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
                # remind the help string, for more fancy display
                _self.PlugHelp = PlugHelp
                # Call the base plugin template init - change XSD into class members
                PlugTemplate.__init__(_self)
                # check name is unique
                NewPlugName = _self.FindNewName(PlugName, logger)
                # If dir have already be made, and file exist
                if os.path.isdir(_self.PlugPath(NewPlugName)): #and os.path.isfile(_self.PluginXmlFilePath(PlugName)):
                    #Load the plugin.xml file into parameters members
                    _self.LoadXMLParams(logger, NewPlugName)
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
            
            def _getBuildPath(_self):
                return self._getBuildPath()
            
        # Create the object out of the resulting class
        newPluginOpj = FinalPlugClass()
        # Store it in PluggedChils
        PluggedChildsWithSameClass.append(newPluginOpj)
        
        return newPluginOpj
            

    def LoadXMLParams(self, logger, PlugName = None):
        methode_name = os.path.join(self.PlugPath(PlugName), "methods.py")
        if os.path.isfile(methode_name):
            logger.write("Info: %s plugin as some special methods in methods.py\n" % (PlugName or "Root"))
            execfile(methode_name)

        # Get the base xml tree
        if self.MandatoryParams:
            #try:
                basexmlfile = open(self.PluginBaseXmlFilePath(PlugName), 'r')
                basetree = minidom.parse(basexmlfile)
                self.MandatoryParams[1].loadXMLTree(basetree.childNodes[0])
                basexmlfile.close()
            #except Exception, e:
            #    logger.write_error("Couldn't load plugin base parameters %s :\n %s" % (PlugName, str(e)))
                
        
        # Get the xml tree
        if self.PlugParams:
            #try:
                xmlfile = open(self.PluginXmlFilePath(PlugName), 'r')
                tree = minidom.parse(xmlfile)
                self.PlugParams[1].loadXMLTree(tree.childNodes[0])
                xmlfile.close()
            #except Exception, e:
            #    logger.write_error("Couldn't load plugin parameters %s :\n %s" % (PlugName, str(e)))
        
    def LoadChilds(self, logger):
        # Iterate over all PlugName@PlugType in plugin directory, and try to open them
        for PlugDir in os.listdir(self.PlugPath()):
            if os.path.isdir(os.path.join(self.PlugPath(), PlugDir)) and \
               PlugDir.count(NameTypeSeparator) == 1:
                pname, ptype = PlugDir.split(NameTypeSeparator)
                #try:
                self.PlugAddChild(pname, ptype, logger)
                #except Exception, e:
                #    logger.write_error("Could not add child \"%s\", type %s :\n%s\n"%(pname, ptype, str(e)))

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

if wx.Platform == '__WXMSW__':
    exe_ext=".exe"
else:
    exe_ext=""

iec2c_path = os.path.join(base_folder, "matiec", "iec2c"+exe_ext)
ieclib_path = os.path.join(base_folder, "matiec", "lib")

# import for project creation timestamping
from time import localtime
from datetime import datetime
# import necessary stuff from PLCOpenEditor
from PLCControler import PLCControler
from PLCOpenEditor import PLCOpenEditor, ProjectDialog
from TextViewer import TextViewer
from plcopen.structures import IEC_KEYWORDS, AddPluginBlockList, ClearPluginTypes, PluginTypes
import runtime
import re

class PluginsRoot(PlugTemplate, PLCControler):
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
    PlugChildsTypes = [(name, _GetClassFunction(name), help) for name, help in zip(plugins.__all__,plugins.helps)]

    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="BeremizRoot">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="TargetType">
              <xsd:complexType>
                <xsd:choice>
                  <xsd:element name="Win32">
                    <xsd:complexType>
                      <xsd:attribute name="Priority" type="xsd:integer" use="required"/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="Linux">
                    <xsd:complexType>
                      <xsd:attribute name="Nice" type="xsd:integer" use="required"/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="Xenomai">
                    <xsd:complexType>
                      <xsd:attribute name="xeno_config" type="xsd:string" use="optional" default="/usr/xenomai/"/>
                      <xsd:attribute name="Priority" type="xsd:integer" use="required"/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="RTAI">
                    <xsd:complexType>
                      <xsd:attribute name="rtai_config" type="xsd:string" use="required"/>
                      <xsd:attribute name="Priority" type="xsd:integer" use="required"/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="Library">
                    <xsd:complexType>
                      <xsd:attribute name="Dynamic" type="xsd:boolean" use="optional" default="true"/>
                    </xsd:complexType>
                  </xsd:element>
                </xsd:choice>
              </xsd:complexType>
            </xsd:element>
            <xsd:element name="Connection">
              <xsd:complexType>
                <xsd:choice>
                  <xsd:element name="Local"/>
                  <xsd:element name="TCP_IP">
                    <xsd:complexType>
                      <xsd:attribute name="Host" type="xsd:string" use="required"/>
                    </xsd:complexType>
                  </xsd:element>
                </xsd:choice>
              </xsd:complexType>
            </xsd:element>
          </xsd:sequence>
          <xsd:attribute name="Compiler" type="xsd:string" use="optional" default="gcc"/>
          <xsd:attribute name="CFLAGS" type="xsd:string" use="required"/>
          <xsd:attribute name="Linker" type="xsd:string" use="optional" default="ld"/>
          <xsd:attribute name="LDFLAGS" type="xsd:string" use="required"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def __init__(self, frame):
        PLCControler.__init__(self)
        
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
        self.PLCEditor = None
        
        # copy PluginMethods so that it can be later customized
        self.PluginMethods = [dic.copy() for dic in self.PluginMethods]
    
    def HasProjectOpened(self):
        """
        Return if a project is actually opened
        """
        return self.ProjectPath != None

    def GetPlugRoot(self):
        return self

    def GetCurrentLocation(self):
        return ()

    def GetCurrentName(self):
        return ""
    
    def _GetCurrentName(self):
        return ""

    def GetProjectPath(self):
        return self.ProjectPath

    def GetProjectName(self):
        return os.path.split(self.ProjectPath)[1]
    
    def GetPlugInfos(self):
        childs = []
        for child in self.IterChilds():
            childs.append(child.GetPlugInfos())
        return {"name" : "PLC (%s)"%self.GetProjectName(), "type" : None, "values" : childs}
    
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
        
        # Create PLCOpen program
        self.CreateNewProject(values.pop("projectName"))
        self.SetProjectProperties(properties = values)
        # Change XSD into class members
        self._AddParamsMembers()
        self.PluggedChilds = {}
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        self.RefreshPluginsBlockLists()
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
        # Load PLCOpen file
        result = self.OpenXMLFile(plc_file)
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
            result = self.LoadXMLParams(logger)
            if result:
                return result
            #Load and init all the childs
            self.LoadChilds(logger)
        self.RefreshPluginsBlockLists()
        return None
    
    def SaveProject(self):
        if not self.SaveXMLFile():
            self.SaveXMLFile(os.path.join(self.ProjectPath, 'plc.xml'))
        if self.PLCEditor:
            self.PLCEditor.RefreshTitle()
        self.PlugRequestSave()
    
    # Update PLCOpenEditor Plugin Block types from loaded plugins
    def RefreshPluginsBlockLists(self):
        if getattr(self, "PluggedChilds", None) is not None:
            ClearPluginTypes()
            AddPluginBlockList(self.BlockTypesFactory())
            for child in self.IterChilds():
                AddPluginBlockList(child.BlockTypesFactory())
        if self.PLCEditor is not None:
            self.PLCEditor.RefreshEditor()
    
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
        return [(C_file_name, self.CFLAGS) for C_file_name in self.PLCGeneratedCFiles ] , "", False
    
    def _getBuildPath(self):
        return os.path.join(self.ProjectPath, "build")
    
    def _getIECcodepath(self):
        # define name for IEC code file
        return os.path.join(self._getBuildPath(), "plc.st")
    
    def _getIECgeneratedcodepath(self):
        # define name for IEC generated code file
        return os.path.join(self._getBuildPath(), "generated_plc.st")
    
    def _getIECrawcodepath(self):
        # define name for IEC raw code file
        return os.path.join(self._getBuildPath(), "raw_plc.st")
    
    def GetLocations(self):
        locations = []
        filepath = os.path.join(self._getBuildPath(),"LOCATED_VARIABLES.h")
        if os.path.isfile(filepath):
            # IEC2C compiler generate a list of located variables : LOCATED_VARIABLES.h
            location_file = open(os.path.join(self._getBuildPath(),"LOCATED_VARIABLES.h"))
            # each line of LOCATED_VARIABLES.h declares a located variable
            lines = [line.strip() for line in location_file.readlines()]
            # This regular expression parses the lines genereated by IEC2C
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
        return locations
        
    def _Generate_SoftPLC(self, logger):
        """
        Generate SoftPLC ST/IL/SFC code out of PLCOpenEditor controller, and compile it with IEC2C
        @param buildpath: path where files should be created
        @param logger: the log pseudo file
        """

        # Update PLCOpenEditor Plugin Block types before generate ST code
        self.RefreshPluginsBlockLists()
        
        logger.write("Generating SoftPLC IEC-61131 ST/IL/SFC code...\n")
        buildpath = self._getBuildPath()
        # ask PLCOpenEditor controller to write ST/IL/SFC code file
        result = self.GenerateProgram(self._getIECgeneratedcodepath())
        if not result:
            # Failed !
            logger.write_error("Error : ST/IL/SFC code generator returned %d\n"%result)
            return False
        plc_file = open(self._getIECcodepath(), "w")
        if os.path.isfile(self._getIECrawcodepath()):
            plc_file.write(open(self._getIECrawcodepath(), "r").read())
            plc_file.write("\n")
        plc_file.write(open(self._getIECgeneratedcodepath(), "r").read())
        plc_file.close()
        logger.write("Compiling IEC Program in to C code...\n")
        # Now compile IEC code into many C files
        # files are listed to stdout, and errors to stderr. 
        status, result, err_result = logger.LogCommand("%s \"%s\" -I \"%s\" \"%s\""%(iec2c_path, self._getIECcodepath(), ieclib_path, buildpath), no_stdout=True)
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
        # Keep track of generated located variables for later use by self._Generate_C
        self.PLCGeneratedLocatedVars = self.GetLocations()
        # Keep track of generated C files for later use by self.PlugGenerate_C
        self.PLCGeneratedCFiles = C_files
        # compute CFLAGS for plc
        self.CFLAGS = "\"-I"+ieclib_path+"\""
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

        #logger.write("SoftPLC code generation successfull\n")

        logger.write("Generating plugins code ...\n")
        
        # Generate C code and compilation params from plugin hierarchy
        try:
            LocationCFilesAndCFLAGS,LDFLAGS = self._Generate_C(
                buildpath, 
                self.PLCGeneratedLocatedVars,
                logger)
        except Exception, msg:
            logger.write_error("Plugins code generation Failed !\n")
            logger.write_error(str(msg))
            return False


        #debug
        #import pprint
        #pp = pprint.PrettyPrinter(indent=4)
        #logger.write("LocationCFilesAndCFLAGS :\n"+pp.pformat(LocationCFilesAndCFLAGS)+"\n")
        #logger.write("LDFLAGS :\n"+pp.pformat(LDFLAGS)+"\n")
        
        # Generate main
        locstrs = map(lambda x:"_".join(map(str,x)), [loc for loc,Cfiles,DoCalls in LocationCFilesAndCFLAGS if loc and DoCalls])
        plc_main = runtime.code("plc_common_main") % {
            "calls_prototypes":"\n".join(
               ["int __init_%(s)s(int argc,char **argv);\nvoid __cleanup_%(s)s();\nvoid __retrive_%(s)s();\nvoid __publish_%(s)s();"%
                {'s':locstr} for locstr in locstrs]),
            "retrive_calls":"    \n".join(["__retrive_%(s)s();"%{'s':locstr} for locstr in locstrs]),
            "publish_calls":"    \n".join(["__publish_%(s)s();"%{'s':locstr} for locstr in locstrs]),
            "init_calls":"    \n".join(["init_level++; if(res = __init_%(s)s(argc,argv)) return res;"%{'s':locstr} for locstr in locstrs]),
            "cleanup_calls":"    \n".join(["if(init_level-- > 0) __cleanup_%(s)s();"%{'s':locstr} for locstr in locstrs])}
        target_name = self.BeremizRoot.TargetType.content["name"]
        plc_main += runtime.code("plc_%s_main"%target_name)

        main_path = os.path.join(buildpath, "main.c" )
        f = open(main_path,'w')
        f.write(plc_main)
        f.close()
        # First element is necessarely root
        LocationCFilesAndCFLAGS[0][1].insert(0,(main_path, self.CFLAGS))
        
        # Compile the resulting code into object files.
        compiler = self.BeremizRoot.getCompiler()
        _CFLAGS = self.BeremizRoot.getCFLAGS()
        linker = self.BeremizRoot.getLinker()
        _LDFLAGS = self.BeremizRoot.getLDFLAGS()
        obns = []
        objs = []
        for Location, CFilesAndCFLAGS, DoCalls in LocationCFilesAndCFLAGS:
            if Location:
                logger.write("Plugin : " + self.GetChildByIECLocation(Location).GetCurrentName() + " " + str(Location)+"\n")
            else:
                logger.write("PLC :\n")
                
            for CFile, CFLAGS in CFilesAndCFLAGS:
                bn = os.path.basename(CFile)
                obn = os.path.splitext(bn)[0]+".o"
                obns.append(obn)
                logger.write("   [CC]  "+bn+" -> "+obn+"\n")
                objectfilename = os.path.splitext(CFile)[0]+".o"
                status, result, err_result = logger.LogCommand("\"%s\" -c \"%s\" -o \"%s\" %s %s"%(compiler, CFile, objectfilename, _CFLAGS, CFLAGS))
                if status != 0:
                    logger.write_error("Build failed\n")
                    return False
                objs.append(objectfilename)
        # Link all the object files into one executable
        logger.write("Linking :\n")
        exe = self.GetProjectName()
        if target_name == "Win32":
            exe += ".exe"
        exe_path = os.path.join(buildpath, exe)
        logger.write("   [CC]  " + ' '.join(obns)+" -> " + exe + "\n")
        status, result, err_result = logger.LogCommand("\"%s\" \"%s\" -o \"%s\" %s"%(linker, '" "'.join(objs), exe_path, ' '.join(LDFLAGS+[_LDFLAGS])))
        if status != 0:
            logger.write_error("Build failed\n")
            return False
        
        
        return True
        

    def _showIECcode(self, logger):
        plc_file = self._getIECcodepath()
        new_dialog = wx.Frame(None)
        ST_viewer = TextViewer(new_dialog, "", None, None)
        #ST_viewer.Enable(False)
        ST_viewer.SetKeywords(IEC_KEYWORDS)
        try:
            text = file(plc_file).read()
        except:
            text = '(* No IEC code have been generated at that time ! *)'
        ST_viewer.SetText(text = text)
            
        new_dialog.Show()

    def _editIECrawcode(self, logger):
        new_dialog = wx.Frame(None)
        
        buildpath = self._getBuildPath()
        # Eventually create build dir
        if not os.path.exists(buildpath):
            os.mkdir(buildpath)
        
        controler = MiniTextControler(self._getIECrawcodepath())
        ST_viewer = TextViewer(new_dialog, "", None, controler)
        #ST_viewer.Enable(False)
        ST_viewer.SetKeywords(IEC_KEYWORDS)
        ST_viewer.RefreshView()
            
        new_dialog.Show()

    def _EditPLC(self, logger):
        if self.PLCEditor is None:
            self.RefreshPluginsBlockLists()
            def _onclose():
                self.PLCEditor = None
            def _onsave():
                self.SaveProject()
            self.PLCEditor = PLCOpenEditor(self.AppFrame, self)
            self.PLCEditor.RefreshProjectTree()
            self.PLCEditor.RefreshFileMenu()
            self.PLCEditor.RefreshEditMenu()
            self.PLCEditor.RefreshToolBar()
            self.PLCEditor._onclose = _onclose
            self.PLCEditor._onsave = _onsave
            self.PLCEditor.Show()

    def _Clean(self, logger):
        if os.path.isdir(os.path.join(self._getBuildPath())):
            logger.write("Cleaning the build directory\n")
            shutil.rmtree(os.path.join(self._getBuildPath()))
        else:
            logger.write_error("Build directory already clean\n")
    
    def _Run(self, logger):
        logger.write("\n")
        self.pid_plc = 0
        command_start_plc = os.path.join(self._getBuildPath(),self.GetProjectName() + exe_ext)
        if os.path.isfile(command_start_plc):
            logger.write("\nStarting PLC\n")
            self.pid_plc = subprocess.Popen(command_start_plc).pid
        else:
            logger.write_error("%s doesn't exist\n" %command_start_plc)

    def _Stop(self, logger):
        PROCESS_TERMINATE = 1
        if self.pid_plc != 0:
            logger.write("Stopping PLC\n")
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, self.pid_plc)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)

    PluginMethods = [
        {"bitmap" : os.path.join("images", "editPLC"),
         "name" : "Edit PLC",
         "tooltip" : "Edit PLC program with PLCOpenEditor",
         "method" : "_EditPLC"},
        {"bitmap" : os.path.join("images", "Build"),
         "name" : "Build",
         "tooltip" : "Build project into build folder",
         "method" : "_build"},
        {"bitmap" : os.path.join("images", "Clean"),
         "name" : "Clean",
         "tooltip" : "Clean project build folder",
         "method" : "_Clean"},
        {"bitmap" : os.path.join("images", "Run"),
         "name" : "Run",
         "tooltip" : "Run PLC from build folder",
         "method" : "_Run"},
        {"bitmap" : os.path.join("images", "Stop"),
         "name" : "Stop",
         "tooltip" : "Stop Running PLC",
         "method" : "_Stop"},
        {"bitmap" : os.path.join("images", "ShowIECcode"),
         "name" : "Show IEC code",
         "tooltip" : "Show IEC code generated by PLCGenerator",
         "method" : "_showIECcode"},
        {"name" : "Edit raw IEC code",
         "tooltip" : "Edit raw IEC code added to code generated by PLCGenerator",
         "method" : "_editIECrawcode"}
    ]

