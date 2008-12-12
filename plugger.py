"""
Base definitions for beremiz plugins
"""

import os,sys,traceback
import plugins
import types
import shutil
from xml.dom import minidom
import wx

#Quick hack to be able to find Beremiz IEC tools. Should be config params.
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "plcopeneditor"))
sys.path.append(os.path.join(base_folder, "docutils"))

from docpdf import *
from xmlclass import GenerateClassesFromXSDstring
from wxPopen import ProcessLogger

from PLCControler import PLCControler

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
        
    def GetEditedElementText(self, tagname, debug = False):
        if os.path.isfile(self.FilePath):
            file = open(self.FilePath, "r")
            text = file.read()
            file.close()
            return text
        return ""
    
    def GetEditedElementInterfaceVars(self, tagname, debug = False):
        return []
    
    def GetEditedElementType(self, tagname, debug = False):
        return "program"
    
    def GetBlockTypes(self, tagname = "", debug = False):
        return []
    
    def GetEnumeratedDataValues(self, debug = False):
        return []
    
    def StartBuffering(self):
        pass

    def EndBuffering(self):
        pass

    def BufferProject(self):
        pass

# helper func to get path to images
def opjimg(imgname):
    return os.path.join("images",imgname)

class PlugTemplate:
    """
    This class is the one that define plugins.
    """

    XSD = None
    PlugChildsTypes = []
    PlugMaxCount = None
    PluginMethods = []
    LibraryControler = None

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

    def PluginLibraryFilePath(self, PlugName=None):
        return os.path.join(os.path.join(os.path.split(__file__)[0], "plugins", self.PlugType, "pous.xml"))

    def PlugPath(self,PlugName=None):
        if not PlugName:
            PlugName = self.BaseParams.getName()
        return os.path.join(self.PlugParent.PlugPath(),
                            PlugName + NameTypeSeparator + self.PlugType)
    
    def PlugTestModified(self):
        return self.ChangesToSave

    def ProjectTestModified(self):
        """
        recursively check modified status
        """
        if self.PlugTestModified():
            return True

        for PlugChild in self.IterChilds():
            if PlugChild.ProjectTestModified():
                return True

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
        
    def SetParamsAttribute(self, path, value):
        self.ChangesToSave = True
        # Filter IEC_Channel and Name, that have specific behavior
        if path == "BaseParams.IEC_Channel":
            return self.FindNewIEC_Channel(value), True
        elif path == "BaseParams.Name":
            res = self.FindNewName(value)
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
            return "Error while saving \"%s\"\n"%self.PlugPath()

        # mark plugin as saved
        self.ChangesToSave = False        
        # go through all childs and do the same
        for PlugChild in self.IterChilds():
            result = PlugChild.PlugRequestSave()
            if result:
                return result
        return None
    
    def PlugImport(self, src_PlugPath):
        shutil.copytree(src_PlugPath, self.PlugPath)
        return True

    def PlugGenerate_C(self, buildpath, locations):
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
        self.logger.write_warning(".".join(map(lambda x:str(x), self.GetCurrentLocation())) + " -> Nothing to do\n")
        return [],"",False
    
    def _Generate_C(self, buildpath, locations):
        # Generate plugins [(Cfiles, CFLAGS)], LDFLAGS, DoCalls, extra_files
        # extra_files = [(fname,fobject), ...]
        gen_result = self.PlugGenerate_C(buildpath, locations)
        PlugCFilesAndCFLAGS, PlugLDFLAGS, DoCalls = gen_result[:3]
        extra_files = gen_result[3:]
        # if some files heve been generated put them in the list with their location
        if PlugCFilesAndCFLAGS:
            LocationCFilesAndCFLAGS = [(self.GetCurrentLocation(), PlugCFilesAndCFLAGS, DoCalls)]
        else:
            LocationCFilesAndCFLAGS = []

        # plugin asks for some LDFLAGS
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
            _LocationCFilesAndCFLAGS, _LDFLAGS, _extra_files = \
                PlugChild._Generate_C(
                    #keep the same path
                    buildpath,
                    # filter locations that start with current IEC location
                    [loc for loc in locations if loc["LOC"][0:depth] == new_location ])
            # stack the result
            LocationCFilesAndCFLAGS += _LocationCFilesAndCFLAGS
            LDFLAGS += _LDFLAGS
            extra_files += _extra_files
        
        return LocationCFilesAndCFLAGS, LDFLAGS, extra_files

    def BlockTypesFactory(self):
        if self.LibraryControler is not None:
            return [{"name" : "%s POUs" % self.PlugType, "list": self.LibraryControler.Project.GetCustomBlockTypes()}]
        return []

    def STLibraryFactory(self):
        if self.LibraryControler is not None:
            return self.LibraryControler.GenerateProgram()
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
    
    def FindNewName(self, DesiredName):
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
            self.logger.write_warning("A child names \"%s\" already exist -> \"%s\"\n"%(DesiredName,res))
        return res

    def FindNewIEC_Channel(self, DesiredChannel):
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
                    self.logger.write_warning("Cannot find lower free IEC channel than %d\n"%CurrentChannel)
                    return CurrentChannel # Can't go bellow 0, do nothing
            else : # Want to go up ?
                res +=  1 # Test for n-1
        # Finally set IEC Channel
        self.BaseParams.setIEC_Channel(res)
        if DesiredChannel != res:
            self.logger.write_warning("A child with IEC channel %d already exist -> %d\n"%(DesiredChannel,res))
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

    def PlugAddChild(self, PlugName, PlugType):
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
                # self is the parent
                _self.logger = self.logger
                # Keep track of the plugin type name
                _self.PlugType = PlugType
                # remind the help string, for more fancy display
                _self.PlugHelp = PlugHelp
                # Call the base plugin template init - change XSD into class members
                PlugTemplate.__init__(_self)
                # check name is unique
                NewPlugName = _self.FindNewName(PlugName)
                # If dir have already be made, and file exist
                if os.path.isdir(_self.PlugPath(NewPlugName)): #and os.path.isfile(_self.PluginXmlFilePath(PlugName)):
                    #Load the plugin.xml file into parameters members
                    _self.LoadXMLParams(NewPlugName)
                    # Basic check. Better to fail immediately.
                    if (_self.BaseParams.getName() != NewPlugName):
                        raise Exception, "Project tree layout do not match plugin.xml %s!=%s "%(NewPlugName, _self.BaseParams.getName())

                    # Now, self.PlugPath() should be OK
                    
                    # Check that IEC_Channel is not already in use.
                    _self.FindNewIEC_Channel(_self.BaseParams.getIEC_Channel())
                    # Call the plugin real __init__
                    if getattr(PlugClass, "__init__", None):
                        PlugClass.__init__(_self)
                    #Load and init all the childs
                    _self.LoadChilds()
                    #just loaded, nothing to saved
                    _self.ChangesToSave = False
                else:
                    # If plugin do not have corresponding file/dirs - they will be created on Save
                    os.mkdir(_self.PlugPath())
                    # Find an IEC number
                    _self.FindNewIEC_Channel(0)
                    # Call the plugin real __init__
                    if getattr(PlugClass, "__init__", None):
                        PlugClass.__init__(_self)
                    _self.PlugRequestSave()
                    #just created, must be saved
                    _self.ChangesToSave = True
            
            def _getBuildPath(_self):
                return self._getBuildPath()
            
        # Create the object out of the resulting class
        newPluginOpj = FinalPlugClass()
        # Store it in PluggedChils
        PluggedChildsWithSameClass.append(newPluginOpj)
        
        return newPluginOpj
            

    def LoadXMLParams(self, PlugName = None):
        methode_name = os.path.join(self.PlugPath(PlugName), "methods.py")
        if os.path.isfile(methode_name):
            execfile(methode_name)
        
        # Get library blocks if plcopen library exist
        library_path = self.PluginLibraryFilePath(PlugName)
        if os.path.isfile(library_path):
            self.LibraryControler = PLCControler()
            self.LibraryControler.OpenXMLFile(library_path)
        
        # Get the base xml tree
        if self.MandatoryParams:
            try:
                basexmlfile = open(self.PluginBaseXmlFilePath(PlugName), 'r')
                basetree = minidom.parse(basexmlfile)
                self.MandatoryParams[1].loadXMLTree(basetree.childNodes[0])
                basexmlfile.close()
            except Exception, exc:
                self.logger.write_error("Couldn't load plugin base parameters %s :\n %s" % (PlugName, str(exc)))
                self.logger.write_error(traceback.format_exc())
        
        # Get the xml tree
        if self.PlugParams:
            try:
                xmlfile = open(self.PluginXmlFilePath(PlugName), 'r')
                tree = minidom.parse(xmlfile)
                self.PlugParams[1].loadXMLTree(tree.childNodes[0])
                xmlfile.close()
            except Exception, exc:
                self.logger.write_error("Couldn't load plugin parameters %s :\n %s" % (PlugName, str(exc)))
                self.logger.write_error(traceback.format_exc())
        
    def LoadChilds(self):
        # Iterate over all PlugName@PlugType in plugin directory, and try to open them
        for PlugDir in os.listdir(self.PlugPath()):
            if os.path.isdir(os.path.join(self.PlugPath(), PlugDir)) and \
               PlugDir.count(NameTypeSeparator) == 1:
                pname, ptype = PlugDir.split(NameTypeSeparator)
                try:
                    self.PlugAddChild(pname, ptype)
                except Exception, exc:
                    self.logger.write_error("Could not add child \"%s\", type %s :\n%s\n"%(pname, ptype, str(exc)))
                    self.logger.write_error(traceback.format_exc())

    def EnableMethod(self, method, value):
        for d in self.PluginMethods:
            if d["method"]==method:
                d["enabled"]=value
                return True
        return False

    def ShowMethod(self, method, value):
        for d in self.PluginMethods:
            if d["method"]==method:
                d["shown"]=value
                return True
        return False

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
from threading import Timer, Lock, Thread, Semaphore
from time import localtime
from datetime import datetime
# import necessary stuff from PLCOpenEditor
from PLCOpenEditor import PLCOpenEditor, ProjectDialog
from TextViewer import TextViewer
from plcopen.structures import IEC_KEYWORDS, TypeHierarchy_list

# Construct debugger natively supported types
DebugTypes = [t for t in zip(*TypeHierarchy_list)[0] if not t.startswith("ANY")] + \
    ["STEP","TRANSITION","ACTION"]

import re
import targets
import connectors
from discovery import DiscoveryDialog
from weakref import WeakKeyDictionary

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
                """+targets.targetchoices+"""
                </xsd:choice>
              </xsd:complexType>
            </xsd:element>
          </xsd:sequence>
          <xsd:attribute name="URI_location" type="xsd:string" use="optional" default=""/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def __init__(self, frame, logger, runtime_port):
        PLCControler.__init__(self)

        self.runtime_port = runtime_port
        self.MandatoryParams = None
        self.AppFrame = frame
        self.logger = logger
        self._builder = None
        self._connector = None
        
        # Setup debug information
        self.IECdebug_datas = {}
        self.IECdebug_lock = Lock()

        self.DebugTimer=None
        self.ResetIECProgramsAndVariables()
        
        #This method are not called here... but in NewProject and OpenProject
        #self._AddParamsMembers()
        #self.PluggedChilds = {}

        # In both new or load scenario, no need to save
        self.ChangesToSave = False        
        # root have no parent
        self.PlugParent = None
        # Keep track of the plugin type name
        self.PlugType = "Beremiz"
        # After __init__ root plugin is not valid
        self.ProjectPath = None
        self.BuildPath = None
        self.PLCEditor = None
        self.PLCDebug = None
        # copy PluginMethods so that it can be later customized
        self.PluginMethods = [dic.copy() for dic in self.PluginMethods]

    def PluginLibraryFilePath(self, PlugName=None):
        return os.path.join(os.path.join(os.path.split(__file__)[0], "pous.xml"))

    def PlugTestModified(self):
         return self.ChangesToSave or not self.ProjectIsSaved()

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
    
    def NewProject(self, ProjectPath, BuildPath=None):
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
        self.CreateNewProject(values)
        # Change XSD into class members
        self._AddParamsMembers()
        self.PluggedChilds = {}
        # Keep track of the root plugin (i.e. project path)
        self.ProjectPath = ProjectPath
        self.BuildPath = BuildPath
        # get plugins bloclist (is that usefull at project creation?)
        self.RefreshPluginsBlockLists()
        # this will create files base XML files
        self.SaveProject()
        return None
        
    def LoadProject(self, ProjectPath, BuildPath=None):
        """
        Load a project contained in a folder
        @param ProjectPath: path of the project folder
        """
        if os.path.basename(ProjectPath) == "":
            ProjectPath = os.path.dirname(ProjectPath)
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
        self.BuildPath = BuildPath
        # If dir have already be made, and file exist
        if os.path.isdir(self.PlugPath()) and os.path.isfile(self.PluginXmlFilePath()):
            #Load the plugin.xml file into parameters members
            result = self.LoadXMLParams()
            if result:
                return result
            #Load and init all the childs
            self.LoadChilds()
        self.RefreshPluginsBlockLists()
        
        if os.path.exists(self._getBuildPath()):
            self.EnableMethod("_Clean", True)

        if os.path.isfile(self._getIECrawcodepath()):
            self.ShowMethod("_showIECcode", True)

        return None
    
    def SaveProject(self):
        if not self.SaveXMLFile():
            self.SaveXMLFile(os.path.join(self.ProjectPath, 'plc.xml'))
        if self.PLCEditor:
            self.PLCEditor.RefreshTitle()
        result = self.PlugRequestSave()
        if result:
            self.logger.write_error(result)
    
    # Update PLCOpenEditor Plugin Block types from loaded plugins
    def RefreshPluginsBlockLists(self):
        if getattr(self, "PluggedChilds", None) is not None:
            self.ClearPluginTypes()
            self.AddPluginBlockList(self.BlockTypesFactory())
            for child in self.IterChilds():
                self.AddPluginBlockList(child.BlockTypesFactory())
        if self.PLCEditor is not None:
            self.PLCEditor.RefreshEditor()
    
    def PlugPath(self, PlugName=None):
        return self.ProjectPath
    
    def PluginXmlFilePath(self, PlugName=None):
        return os.path.join(self.PlugPath(PlugName), "beremiz.xml")

    def _getBuildPath(self):
        if self.BuildPath is None:
            return os.path.join(self.ProjectPath, "build")
        return self.BuildPath
    
    def _getExtraFilesPath(self):
        return os.path.join(self._getBuildPath(), "extra_files")

    def _getIECcodepath(self):
        # define name for IEC code file
        return os.path.join(self._getBuildPath(), "plc.st")
    
    def _getIECgeneratedcodepath(self):
        # define name for IEC generated code file
        return os.path.join(self._getBuildPath(), "generated_plc.st")
    
    def _getIECrawcodepath(self):
        # define name for IEC raw code file
        return os.path.join(self.PlugPath(), "raw_plc.st")
    
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
        
    def _Generate_SoftPLC(self):
        """
        Generate SoftPLC ST/IL/SFC code out of PLCOpenEditor controller, and compile it with IEC2C
        @param buildpath: path where files should be created
        """

        # Update PLCOpenEditor Plugin Block types before generate ST code
        self.RefreshPluginsBlockLists()
        
        self.logger.write("Generating SoftPLC IEC-61131 ST/IL/SFC code...\n")
        buildpath = self._getBuildPath()
        # ask PLCOpenEditor controller to write ST/IL/SFC code file
        result = self.GenerateProgram(self._getIECgeneratedcodepath())
        if result is not None:
            # Failed !
            self.logger.write_error("Error in ST/IL/SFC code generator :\n%s\n"%result)
            return False
        plc_file = open(self._getIECcodepath(), "w")
        if getattr(self, "PluggedChilds", None) is not None:
            # Add ST Library from plugins
            plc_file.write(self.STLibraryFactory())
            plc_file.write("\n")
            for child in self.IterChilds():
                plc_file.write(child.STLibraryFactory())
                plc_file.write("\n")
        if os.path.isfile(self._getIECrawcodepath()):
            plc_file.write(open(self._getIECrawcodepath(), "r").read())
            plc_file.write("\n")
        plc_file.write(open(self._getIECgeneratedcodepath(), "r").read())
        plc_file.close()
        self.logger.write("Compiling IEC Program in to C code...\n")
        # Now compile IEC code into many C files
        # files are listed to stdout, and errors to stderr. 
        status, result, err_result = ProcessLogger(
               self.logger,
               "\"%s\" -f \"%s\" -I \"%s\" \"%s\""%(
                         iec2c_path,
                         self._getIECcodepath(),
                         ieclib_path, buildpath),
               no_stdout=True).spin()
        if status:
            # Failed !
            self.logger.write_error("Error : IEC to C compiler returned %d\n"%status)
            return False
        # Now extract C files of stdout
        C_files = [ fname for fname in result.splitlines() if fname[-2:]==".c" or fname[-2:]==".C" ]
        # remove those that are not to be compiled because included by others
        C_files.remove("POUS.c")
        if not C_files:
            self.logger.write_error("Error : At least one configuration and one ressource must be declared in PLC !\n")
            return False
        # transform those base names to full names with path
        C_files = map(lambda filename:os.path.join(buildpath, filename), C_files)
        self.logger.write("Extracting Located Variables...\n")
        # Keep track of generated located variables for later use by self._Generate_C
        self.PLCGeneratedLocatedVars = self.GetLocations()
        # Keep track of generated C files for later use by self.PlugGenerate_C
        self.PLCGeneratedCFiles = C_files
        # compute CFLAGS for plc
        self.plcCFLAGS = "\"-I"+ieclib_path+"\""
        return True

    def GetBuilder(self):
        """
        Return a Builder (compile C code into machine code)
        """
        # Get target, module and class name
        targetname = self.BeremizRoot.getTargetType().getcontent()["name"]
        modulename = "targets." + targetname
        classname = targetname + "_target"

        # Get module reference
        try :
            targetmodule = getattr(__import__(modulename), targetname)

        except Exception, msg:
            self.logger.write_error("Can't find module for target %s!\n"%targetname)
            self.logger.write_error(str(msg))
            return None
        
        # Get target class
        targetclass = getattr(targetmodule, classname)

        # if target already 
        if self._builder is None or not isinstance(self._builder,targetclass):
            # Get classname instance
            self._builder = targetclass(self)
        return self._builder

    def GetLastBuildMD5(self):
        builder=self.GetBuilder()
        if builder is not None:
            return builder.GetBinaryCodeMD5()
        else:
            return None

    #######################################################################
    #
    #                C CODE GENERATION METHODS
    #
    #######################################################################
    
    def PlugGenerate_C(self, buildpath, locations):
        """
        Return C code generated by iec2c compiler 
        when _generate_softPLC have been called
        @param locations: ignored
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [(C_file_name, self.plcCFLAGS) for C_file_name in self.PLCGeneratedCFiles ] , "", False
    
    def ResetIECProgramsAndVariables(self):
        """
        Reset variable and program list that are parsed from
        CSV file generated by IEC2C compiler.
        """
        self._ProgramList = None
        self._VariablesList = None
        self._IECPathToIdx = None
        self.TracedIECPath = []

    def GetIECProgramsAndVariables(self):
        """
        Parse CSV-like file  VARIABLES.csv resulting from IEC2C compiler.
        Each section is marked with a line staring with '//'
        list of all variables used in various POUs
        """
        if self._ProgramList is None or self._VariablesList is None:
            try:
                csvfile = os.path.join(self._getBuildPath(),"VARIABLES.csv")
                # describes CSV columns
                ProgramsListAttributeName = ["num", "C_path", "type"]
                VariablesListAttributeName = ["num", "vartype", "IEC_path", "C_path", "type"]
                self._ProgramList = []
                self._VariablesList = []
                self._IECPathToIdx = {}
                
                # Separate sections
                ListGroup = []
                for line in open(csvfile,'r').xreadlines():
                    strippedline = line.strip()
                    if strippedline.startswith("//"):
                        # Start new section
                        ListGroup.append([])
                    elif len(strippedline) > 0 and len(ListGroup) > 0:
                        # append to this section
                        ListGroup[-1].append(strippedline)
        
                # first section contains programs
                for line in ListGroup[0]:
                    # Split and Maps each field to dictionnary entries
                    attrs = dict(zip(ProgramsListAttributeName,line.strip().split(';')))
                    # Truncate "C_path" to remove conf an ressources names
                    attrs["C_path"] = '__'.join(attrs["C_path"].split(".",2)[1:])
                    # Push this dictionnary into result.
                    self._ProgramList.append(attrs)
        
                # second section contains all variables
                for line in ListGroup[1]:
                    # Split and Maps each field to dictionnary entries
                    attrs = dict(zip(VariablesListAttributeName,line.strip().split(';')))
                    # Truncate "C_path" to remove conf an ressources names
                    attrs["C_path"] = '__'.join(attrs["C_path"].split(".",2)[1:])
                    # Push this dictionnary into result.
                    self._VariablesList.append(attrs)
                    # Fill in IEC<->C translation dicts
                    IEC_path=attrs["IEC_path"]
                    Idx=int(attrs["num"])
                    self._IECPathToIdx[IEC_path]=Idx
            except Exception,e:
                self.logger.write_error("Cannot open/parse VARIABLES.csv!\n")
                self.logger.write_error(traceback.format_exc())
                self.ResetIECProgramsAndVariables()
                return False

        return True

    def Generate_plc_debugger(self):
        """
        Generate trace/debug code out of PLC variable list
        """
        self.GetIECProgramsAndVariables()

        # prepare debug code
        debug_code = targets.code("plc_debug") % {
           "programs_declarations":
               "\n".join(["extern %(type)s %(C_path)s;"%p for p in self._ProgramList]),
           "extern_variables_declarations":"\n".join([
              {"PT":"extern %(type)s *%(C_path)s;",
               "VAR":"extern %(type)s %(C_path)s;"}[v["vartype"]]%v 
               for v in self._VariablesList if v["vartype"] != "FB" and v["C_path"].find('.')<0]),
           "subscription_table_count":
               len(self._VariablesList),
           "variables_pointer_type_table_count":
               len(self._VariablesList),
           "variables_pointer_type_table_initializer":"\n".join([
               {"PT":"    variable_table[%(num)s].ptrvalue = (void*)(%(C_path)s);\n",
                "VAR":"    variable_table[%(num)s].ptrvalue = (void*)(&%(C_path)s);\n"}[v["vartype"]]%v + 
                "    variable_table[%(num)s].type = %(type)s_ENUM;\n"%v
                for v in self._VariablesList if v["vartype"] != "FB" and v["type"] in DebugTypes ])}
        
        return debug_code
        
    def Generate_plc_common_main(self):
        """
        Use plugins layout given in LocationCFilesAndCFLAGS to
        generate glue code that dispatch calls to all plugins
        """
        # filter location that are related to code that will be called
        # in retreive, publish, init, cleanup
        locstrs = map(lambda x:"_".join(map(str,x)),
           [loc for loc,Cfiles,DoCalls in self.LocationCFilesAndCFLAGS if loc and DoCalls])

        # Generate main, based on template
        plc_main_code = targets.code("plc_common_main") % {
            "calls_prototypes":"\n".join([(
                  "int __init_%(s)s(int argc,char **argv);\n"+
                  "void __cleanup_%(s)s();\n"+
                  "void __retrieve_%(s)s();\n"+
                  "void __publish_%(s)s();")%{'s':locstr} for locstr in locstrs]),
            "retrieve_calls":"\n    ".join([
                  "__retrieve_%s();"%locstr for locstr in locstrs]),
            "publish_calls":"\n    ".join([ #Call publish in reverse order
                  "__publish_%s();"%locstrs[i-1] for i in xrange(len(locstrs), 0, -1)]),
            "init_calls":"\n    ".join([
                  "init_level=%d; "%(i+1)+
                  "if(res = __init_%s(argc,argv)){"%locstr +
                  #"printf(\"%s\"); "%locstr + #for debug
                  "return res;}" for i,locstr in enumerate(locstrs)]),
            "cleanup_calls":"\n    ".join([
                  "if(init_level >= %d) "%i+
                  "__cleanup_%s();"%locstrs[i-1] for i in xrange(len(locstrs), 0, -1)])
            }

        target_name = self.BeremizRoot.getTargetType().getcontent()["name"]
        plc_main_code += targets.targetcode(target_name)
        return plc_main_code

        
    def _build(self):
        """
        Method called by user to (re)build SoftPLC and plugin tree
        """
        if self.PLCEditor is not None:
            self.PLCEditor.ClearErrors()
        
        buildpath = self._getBuildPath()

        # Eventually create build dir
        if not os.path.exists(buildpath):
            os.mkdir(buildpath)
        # There is something to clean
        self.EnableMethod("_Clean", True)

        self.logger.flush()
        self.logger.write("Start build in %s\n" % buildpath)

        # Generate SoftPLC IEC code
        IECGenRes = self._Generate_SoftPLC()
        self.ShowMethod("_showIECcode", True)

        # If IEC code gen fail, bail out.
        if not IECGenRes:
            self.logger.write_error("IEC-61131-3 code generation failed !\n")
            return False

        # Reset variable and program list that are parsed from
        # CSV file generated by IEC2C compiler.
        self.ResetIECProgramsAndVariables()
        
        # Generate C code and compilation params from plugin hierarchy
        self.logger.write("Generating plugins C code\n")
        try:
            self.LocationCFilesAndCFLAGS, self.LDFLAGS, ExtraFiles = self._Generate_C(
                buildpath, 
                self.PLCGeneratedLocatedVars)
        except Exception, exc:
            self.logger.write_error("Plugins code generation failed !\n")
            self.logger.write_error(traceback.format_exc())
            return False

        # Get temprary directory path
        extrafilespath = self._getExtraFilesPath()
        # Remove old directory
        if os.path.exists(extrafilespath):
            shutil.rmtree(extrafilespath)
        # Recreate directory
        os.mkdir(extrafilespath)
        # Then write the files
        for fname,fobject in ExtraFiles:
            fpath = os.path.join(extrafilespath,fname)
            open(fpath, "wb").write(fobject.read())
        # Now we can forget ExtraFiles (will close files object)
        del ExtraFiles

        # Template based part of C code generation
        # files are stacked at the beginning, as files of plugin tree root
        for generator, filename, name in [
           # debugger code
           (self.Generate_plc_debugger, "plc_debugger.c", "Debugger"),
           # init/cleanup/retrieve/publish, run and align code
           (self.Generate_plc_common_main,"plc_common_main.c","Common runtime")]:
            try:
                # Do generate
                code = generator()
                code_path = os.path.join(buildpath,filename)
                open(code_path, "w").write(code)
                # Insert this file as first file to be compiled at root plugin
                self.LocationCFilesAndCFLAGS[0][1].insert(0,(code_path, self.plcCFLAGS))
            except Exception, exc:
                self.logger.write_error(name+" generation failed !\n")
                self.logger.write_error(traceback.format_exc())
                return False

        self.logger.write("C code generated successfully.\n")

        # Get current or fresh builder
        builder = self.GetBuilder()
        if builder is None:
            self.logger.write_error("Fatal : cannot get builder.\n")
            return False

        # Build
        try:
            if not builder.build() :
                self.logger.write_error("C Build failed.\n")
                return False
        except Exception, exc:
            self.logger.write_error("C Build crashed !\n")
            self.logger.write_error(traceback.format_exc())
            return False

        # Update GUI status about need for transfer
        self.CompareLocalAndRemotePLC()
        return True
    
    def ShowError(self, logger, from_location, to_location):
        chunk_infos = self.GetChunkInfos(from_location, to_location)
        self._EditPLC()
        for infos, (start_row, start_col) in chunk_infos:
            start = (from_location[0] - start_row, from_location[1] - start_col)
            end = (to_location[0] - start_row, to_location[1] - start_col)
            self.PLCEditor.ShowError(infos, start, end)

    def _showIECcode(self):
        plc_file = self._getIECcodepath()
        new_dialog = wx.Frame(self.AppFrame)
        ST_viewer = TextViewer(new_dialog, "", None, None)
        #ST_viewer.Enable(False)
        ST_viewer.SetKeywords(IEC_KEYWORDS)
        try:
            text = file(plc_file).read()
        except:
            text = '(* No IEC code have been generated at that time ! *)'
        ST_viewer.SetText(text = text)
            
        new_dialog.Show()

    def _editIECrawcode(self):
        new_dialog = wx.Frame(self.AppFrame)
        
        controler = MiniTextControler(self._getIECrawcodepath())
        ST_viewer = TextViewer(new_dialog, "", None, controler)
        #ST_viewer.Enable(False)
        ST_viewer.SetKeywords(IEC_KEYWORDS)
        ST_viewer.RefreshView()
            
        new_dialog.Show()

    def _EditPLC(self):
        if self.PLCEditor is None:
            self.RefreshPluginsBlockLists()
            def _onclose():
                self.PLCEditor = None
            def _onsave():
                self.SaveProject()
            self.PLCEditor = PLCOpenEditor(self.AppFrame, self)
            self.PLCEditor._onclose = _onclose
            self.PLCEditor._onsave = _onsave
            self.PLCEditor.Show()

    def _Clean(self):
        if os.path.isdir(os.path.join(self._getBuildPath())):
            self.logger.write("Cleaning the build directory\n")
            shutil.rmtree(os.path.join(self._getBuildPath()))
        else:
            self.logger.write_error("Build directory already clean\n")
        self.ShowMethod("_showIECcode", False)
        self.EnableMethod("_Clean", False)
        self.CompareLocalAndRemotePLC()

    ############# Real PLC object access #############
    def UpdateMethodsFromPLCStatus(self):
        # Get PLC state : Running or Stopped
        # TODO : use explicit status instead of boolean
        if self._connector is not None:
            status = self._connector.GetPLCstatus()
            self.logger.write("PLC is %s\n"%status)
        else:
            status = "Disconnected"
        for args in {
               "Started":[("_Run", False),
                          ("_Debug", False),
                          ("_Stop", True)],
               "Stopped":[("_Run", True),
                          ("_Debug", True),
                          ("_Stop", False)],
               "Empty":  [("_Run", False),
                          ("_Debug", False),
                          ("_Stop", False)],
               "Dirty":  [("_Run", True),
                          ("_Debug", True),
                          ("_Stop", False)],
               "Disconnected":  [("_Run", False),
                                 ("_Debug", False),
                                 ("_Stop", False)],
               }.get(status,[]):
            self.ShowMethod(*args)
        
    def _Run(self):
        """
        Start PLC
        """
        if self._connector.StartPLC():
            self.logger.write("Starting PLC\n")
        else:
            self.logger.write_error("Couldn't start PLC !\n")
        self.UpdateMethodsFromPLCStatus()

    def RegisterDebugVarToConnector(self):
        self.DebugTimer=None
        Idxs = []
        self.TracedIECPath = []
        if self._connector is not None:
            self.IECdebug_lock.acquire()
            IECPathsToPop = []
            for IECPath,data_tuple in self.IECdebug_datas.iteritems():
                WeakCallableDict, data_log, status = data_tuple
                if len(WeakCallableDict) == 0:
                    # Callable Dict is empty.
                    # This variable is not needed anymore!
                    #print "Unused : " + IECPath
                    IECPathsToPop.append(IECPath)
                else:
                    # Convert 
                    Idx = self._IECPathToIdx.get(IECPath,None)
                    if Idx is not None:
                        Idxs.append(Idx)
                        self.TracedIECPath.append(IECPath)
                    else:
                        self.logger.write_warning("Debug : Unknown variable %s\n"%IECPath)
            for IECPathToPop in IECPathsToPop:
                self.IECdebug_datas.pop(IECPathToPop)

            self._connector.SetTraceVariablesList(Idxs)
            self.IECdebug_lock.release()
            
            #for IEC_path, IECdebug_data in self.IECdebug_datas.iteritems():
            #    print IEC_path, IECdebug_data[0].keys()

    def ReArmDebugRegisterTimer(self):
        if self.DebugTimer is not None:
            self.DebugTimer.cancel()

        # Timer to prevent rapid-fire when registering many variables
        # use wx.CallAfter use keep using same thread. TODO : use wx.Timer instead
        self.DebugTimer=Timer(0.5,wx.CallAfter,args = [self.RegisterDebugVarToConnector])
        # Rearm anti-rapid-fire timer
        self.DebugTimer.start()

        
    def SubscribeDebugIECVariable(self, IECPath, callableobj, *args, **kwargs):
        """
        Dispatching use a dictionnary linking IEC variable paths
        to a WeakKeyDictionary linking 
        weakly referenced callables to optionnal args
        """
        if self._IECPathToIdx.get(IECPath, None) is None:
            return None
        
        self.IECdebug_lock.acquire()
        # If no entry exist, create a new one with a fresh WeakKeyDictionary
        IECdebug_data = self.IECdebug_datas.get(IECPath, None)
        if IECdebug_data is None:
            IECdebug_data  = [
                    WeakKeyDictionary(), # Callables
                    [],                  # Data storage [(tick, data),...]
                    "Registered"]        # Variable status
            self.IECdebug_datas[IECPath] = IECdebug_data
        
        IECdebug_data[0][callableobj]=(args, kwargs)

        self.IECdebug_lock.release()
        
        self.ReArmDebugRegisterTimer()
        
        return IECdebug_data[1]

    def UnsubscribeDebugIECVariable(self, IECPath, callableobj):
        #print "Unsubscribe", IECPath, callableobj
        self.IECdebug_lock.acquire()
        IECdebug_data = self.IECdebug_datas.get(IECPath, None)
        if IECdebug_data is not None:
            IECdebug_data[0].pop(callableobj,None)
        self.IECdebug_lock.release()

        self.ReArmDebugRegisterTimer()

    def DebugThreadProc(self):
        """
        This thread waid PLC debug data, and dispatch them to subscribers
        """
        # This lock is used to avoid flooding wx event stack calling callafter
        self.DebugThreadSlowDownLock = Semaphore(0)
        _break = False
        while not _break and self._connector is not None:
            debug_tick, debug_vars = self._connector.GetTraceVariables()
            #print debug_tick, debug_vars
            self.IECdebug_lock.acquire()
            if debug_vars is not None and \
               len(debug_vars) == len(self.TracedIECPath):
                for IECPath,value in zip(self.TracedIECPath, debug_vars):
                    data_tuple = self.IECdebug_datas.get(IECPath, None)
                    if data_tuple is not None:
                        WeakCallableDict, data_log, status = data_tuple
                        data_log.append((debug_tick, value))
                        for weakcallable,(args,kwargs) in WeakCallableDict.iteritems():
                            # delegate call to wx event loop
                            #print weakcallable, value, args, kwargs
                            wx.CallAfter(weakcallable.SetValue, value, *args, **kwargs)
                            # This will block thread if more than one call is waiting
            elif debug_vars is not None:
                wx.CallAfter(self.logger.write_warning, 
                             "debug data not coherent %d != %d"%(len(debug_vars), len(self.TracedIECPath)))
            elif debug_tick == -1:
                #wx.CallAfter(self.logger.write, "Debugger unavailable\n")
                pass
            else:
                wx.CallAfter(self.logger.write, "Debugger disabled\n")
                _break = True
            self.IECdebug_lock.release()
            wx.CallAfter(self.DebugThreadSlowDownLock.release)
            self.DebugThreadSlowDownLock.acquire()

    def _Debug(self):
        """
        Start PLC (Debug Mode)
        """
        if self.GetIECProgramsAndVariables() and \
           self._connector.StartPLC(debug=True):
            self.logger.write("Starting PLC (debug mode)\n")
            self.TracedIECPath = []
            if self.PLCDebug is None:
                self.RefreshPluginsBlockLists()
                def _onclose():
                    self.PLCDebug = None
                self.PLCDebug = PLCOpenEditor(self.AppFrame, self, debug=True)
                self.PLCDebug._onclose = _onclose
                self.PLCDebug.Show()
            self.DebugThread = Thread(target=self.DebugThreadProc)
            self.DebugThread.start()
        else:
            self.logger.write_error("Couldn't start PLC debug !\n")
        self.UpdateMethodsFromPLCStatus()

#    def _Do_Test_Debug(self):
#        # debug code
#        self.temporary_non_weak_callable_refs = []
#        for IEC_Path, idx in self._IECPathToIdx.iteritems():
#            class tmpcls:
#                def __init__(_self):
#                    _self.buf = None
#                def setbuf(_self,buf):
#                    _self.buf = buf
#                def SetValue(_self, value, idx, name):
#                    self.logger.write("debug call: %s %d %s\n"%(repr(value), idx, name))
#                    #self.logger.write("debug call: %s %d %s %s\n"%(repr(value), idx, name, repr(self.buf)))
#            a = tmpcls()
#            res = self.SubscribeDebugIECVariable(IEC_Path, a, idx, IEC_Path)
#            a.setbuf(res)
#            self.temporary_non_weak_callable_refs.append(a)
       
    def _Stop(self):
        """
        Stop PLC
        """
        if self._connector.StopPLC():
            self.logger.write("Stopping PLC\n")
        else:
            self.logger.write_error("Couldn't stop PLC !\n")
        self.UpdateMethodsFromPLCStatus()

    def _Connect(self):
        # don't accept re-connetion is already connected
        if self._connector is not None:
            self.logger.write_error("Already connected. Please disconnect\n")
            return
        
        # Get connector uri
        uri = self.\
              BeremizRoot.\
              getURI_location().\
              strip()

        # if uri is empty launch discovery dialog
        if uri == "":
            # Launch Service Discovery dialog
            dia = DiscoveryDialog(self.AppFrame)
            dia.ShowModal()
            uri = dia.GetResult()
            # Nothing choosed or cancel button
            if uri is None:
                return
            else:
                self.\
                BeremizRoot.\
                setURI_location(uri)
       
        # Get connector from uri
        try:
            self._connector = connectors.ConnectorFactory(uri, self)
        except Exception, msg:
            self.logger.write_error("Exception while connecting %s!\n"%uri)
            self.logger.write_error(traceback.format_exc())

        # Did connection success ?
        if self._connector is None:
            # Oups.
            self.logger.write_error("Connection failed to %s!\n"%uri)
        else:
            self.ShowMethod("_Connect", False)
            self.ShowMethod("_Disconnect", True)
            self.ShowMethod("_Transfer", True)

            self.CompareLocalAndRemotePLC()
            self.UpdateMethodsFromPLCStatus()

    def CompareLocalAndRemotePLC(self):
        if self._connector is None:
            return
        # We are now connected. Update button status
        MD5 = self.GetLastBuildMD5()
        # Check remote target PLC correspondance to that md5
        if MD5 is not None:
            if not self._connector.MatchMD5(MD5):
                self.logger.write_warning(
                   "Latest build do not match with target, please transfer.\n")
                self.EnableMethod("_Transfer", True)
            else:
                self.logger.write(
                   "Latest build match target, no transfer needed.\n")
                self.EnableMethod("_Transfer", True)
                #self.EnableMethod("_Transfer", False)
        else:
            self.logger.write_warning(
                "Cannot compare latest build to target. Please build.\n")
            self.EnableMethod("_Transfer", False)


    def _Disconnect(self):
        self._connector = None
        self.ShowMethod("_Transfer", False)
        self.ShowMethod("_Connect", True)
        self.ShowMethod("_Disconnect", False)
        self.UpdateMethodsFromPLCStatus()
        
    def _Transfer(self):
        # Get the last build PLC's 
        MD5 = self.GetLastBuildMD5()
        
        # Check if md5 file is empty : ask user to build PLC 
        if MD5 is None :
            self.logger.write_error("Failed : Must build before transfer.\n")
            return False

        # Compare PLC project with PLC on target
        if self._connector.MatchMD5(MD5):
            self.logger.write(
                "Latest build already match current target. Transfering anyway...\n")

        # Get temprary directory path
        extrafilespath = self._getExtraFilesPath()
        extrafiles = [(name, open(os.path.join(extrafilespath, name), 
                                  'rb').read()) \
                      for name in os.listdir(extrafilespath) \
                      if not name=="CVS"]

        # Send PLC on target
        builder = self.GetBuilder()
        if builder is not None:
            data = builder.GetBinaryCode()
            if data is not None :
                if self._connector.NewPLC(MD5, data, extrafiles):
                    self.ProgramTransferred()
                    self.logger.write("Transfer completed successfully.\n")
                else:
                    self.logger.write_error("Transfer failed\n")
            else:
                self.logger.write_error("No PLC to transfer (did build success ?)\n")
        self.UpdateMethodsFromPLCStatus()

    PluginMethods = [
        {"bitmap" : opjimg("editPLC"),
         "name" : "Edit PLC",
         "tooltip" : "Edit PLC program with PLCOpenEditor",
         "method" : "_EditPLC"},
        {"bitmap" : opjimg("Build"),
         "name" : "Build",
         "tooltip" : "Build project into build folder",
         "method" : "_build"},
        {"bitmap" : opjimg("Clean"),
         "name" : "Clean",
         "enabled" : False,
         "tooltip" : "Clean project build folder",
         "method" : "_Clean"},
        {"bitmap" : opjimg("Run"),
         "name" : "Run",
         "shown" : False,
         "tooltip" : "Start PLC",
         "method" : "_Run"},
        {"bitmap" : opjimg("Debug"),
         "name" : "Debug",
         "shown" : False,
         "tooltip" : "Start PLC (debug mode)",
         "method" : "_Debug"},
#        {"bitmap" : opjimg("Debug"),
#         "name" : "Do_Test_Debug",
#         "tooltip" : "Test debug mode)",
#         "method" : "_Do_Test_Debug"},
        {"bitmap" : opjimg("Stop"),
         "name" : "Stop",
         "shown" : False,
         "tooltip" : "Stop Running PLC",
         "method" : "_Stop"},
        {"bitmap" : opjimg("Connect"),
         "name" : "Connect",
         "tooltip" : "Connect to the target PLC",
         "method" : "_Connect"},
        {"bitmap" : opjimg("Transfer"),
         "name" : "Transfer",
         "shown" : False,
         "tooltip" : "Transfer PLC",
         "method" : "_Transfer"},
        {"bitmap" : opjimg("Disconnect"),
         "name" : "Disconnect",
         "shown" : False,
         "tooltip" : "Disconnect from PLC",
         "method" : "_Disconnect"},
        {"bitmap" : opjimg("ShowIECcode"),
         "name" : "Show code",
         "shown" : False,
         "tooltip" : "Show IEC code generated by PLCGenerator",
         "method" : "_showIECcode"},
        {"bitmap" : opjimg("editIECrawcode"),
         "name" : "Append code",
         "tooltip" : "Edit raw IEC code added to code generated by PLCGenerator",
         "method" : "_editIECrawcode"},
    ]
