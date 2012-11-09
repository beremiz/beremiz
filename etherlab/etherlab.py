import os, shutil
import cPickle
from xml.dom import minidom

import wx

from xmlclass import *
from POULibrary import POULibrary
from ConfigTreeNode import ConfigTreeNode
from PLCControler import UndoBuffer, LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY
from ConfigEditor import NodeEditor, CIA402NodeEditor, ETHERCAT_VENDOR, ETHERCAT_GROUP, ETHERCAT_DEVICE

try:
    from MotionLibrary import Headers, AxisXSD
    HAS_MCL = True
except:
    HAS_MCL = False

TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", 
    "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L"}

DATATYPECONVERSION = {"BOOL" : "BIT", "SINT" : "S8", "INT" : "S16", "DINT" : "S32", "LINT" : "S64",
    "USINT" : "U8", "UINT" : "U16", "UDINT" : "U32", "ULINT" : "U64", 
    "BYTE" : "U8", "WORD" : "U16", "DWORD" : "U32", "LWORD" : "U64"}

VARCLASSCONVERSION = {"T": LOCATION_VAR_INPUT, "R": LOCATION_VAR_OUTPUT, "RT": LOCATION_VAR_MEMORY}

#--------------------------------------------------
#         Remote Exec Etherlab Commands
#--------------------------------------------------

SCAN_COMMAND = """
import commands
result = commands.getoutput("ethercat slaves")
slaves = []
for slave_line in result.splitlines():
    chunks = slave_line.split()
    idx, pos, state, flag = chunks[:4]
    name = " ".join(chunks[4:])
    alias, position = pos.split(":")
    slave = {"idx": int(idx),
             "alias": int(alias),
             "position": int(position),
             "name": name}
    details = commands.getoutput("ethercat slaves -p %d -v" % slave["idx"])
    for details_line in details.splitlines():
        details_line = details_line.strip()
        for header, param in [("Vendor Id:", "vendor_id"),
                              ("Product code:", "product_code"),
                              ("Revision number:", "revision_number")]:
            if details_line.startswith(header):
                slave[param] = details_line.split()[-1]
                break
    slaves.append(slave)
returnVal = slaves
"""

#--------------------------------------------------
#      Etherlab Specific Blocks Library
#--------------------------------------------------

def GetLocalPath(filename):
    return os.path.join(os.path.split(__file__)[0], filename)

class EtherlabLibrary(POULibrary):
    def GetLibraryPath(self):
        return GetLocalPath("pous.xml")

    def Generate_C(self, buildpath, varlist, IECCFLAGS):
        etherlab_ext_file = open(GetLocalPath("etherlab_ext.c"), 'r')
        etherlab_ext_code = etherlab_ext_file.read()
        etherlab_ext_file.close()
        
        Gen_etherlabfile_path = os.path.join(buildpath, "etherlab_ext.c")
        ethelabfile = open(Gen_etherlabfile_path,'w')
        ethelabfile.write(etherlab_ext_code)
        ethelabfile.close()
        
        runtimefile_path = os.path.join(os.path.split(__file__)[0], "runtime_etherlab.py")
        return ((["etherlab_ext"], [(Gen_etherlabfile_path, IECCFLAGS)], True), "", 
                ("runtime_etherlab.py", file(GetLocalPath("runtime_etherlab.py"))))

#--------------------------------------------------
#                    Ethercat Node
#--------------------------------------------------

class _EthercatSlaveCTN:
    
    NODE_PROFILE = None
    EditorType = NodeEditor
    
    def GetIconName(self):
        return "Slave"
    
    def ExtractHexDecValue(self, value):
        return ExtractHexDecValue(value)
    
    def GetSizeOfType(self, type):
        return TYPECONVERSION.get(self.GetCTRoot().GetBaseType(type), None)
    
    def GetSlavePos(self):
        return self.BaseParams.getIEC_Channel()
    
    def GetParamsAttributes(self, path = None):
        if path:
            parts = path.split(".", 1)
            if self.MandatoryParams and parts[0] == self.MandatoryParams[0]:
                return self.MandatoryParams[1].getElementInfos(parts[0], parts[1])
            elif self.CTNParams and parts[0] == self.CTNParams[0]:
                return self.CTNParams[1].getElementInfos(parts[0], parts[1])
        else:
            params = []
            if self.CTNParams:
                params.append(self.CTNParams[1].getElementInfos(self.CTNParams[0]))
            else:
                params.append({
                    'use': 'required', 
                    'type': 'element', 
                    'name': 'SlaveParams', 
                    'value': None, 
                    'children': []
                })
            
            slave_type = self.CTNParent.GetSlaveType(self.GetSlavePos())
            params[0]['children'].insert(0,
                   {'use': 'optional', 
                    'type': self.CTNParent.GetSlaveTypesLibrary(self.NODE_PROFILE), 
                    'name': 'Type', 
                    'value': (slave_type["device_type"], slave_type)}) 
            params[0]['children'].insert(1,
                   {'use': 'optional', 
                    'type': 'unsignedLong', 
                    'name': 'Alias', 
                    'value': self.CTNParent.GetSlaveAlias(self.GetSlavePos())})
            return params
        
    def SetParamsAttribute(self, path, value):
        position = self.BaseParams.getIEC_Channel()
        
        if path == "SlaveParams.Type":
            self.CTNParent.SetSlaveType(position, value)
            slave_type = self.CTNParent.GetSlaveType(self.GetSlavePos())
            value = (slave_type["device_type"], slave_type)
            if self._View is not None:
                wx.CallAfter(self._View.RefreshSlaveInfos)
            return value, True
        elif path == "SlaveParams.Alias":
            self.CTNParent.SetSlaveAlias(position, value)
            return value, True
        
        value, refresh = ConfigTreeNode.SetParamsAttribute(self, path, value)
        
        # Filter IEC_Channel, Slave_Type and Alias that have specific behavior
        if path == "BaseParams.IEC_Channel" and value != position:
            self.CTNParent.SetSlavePosition(position, value)
        
        return value, refresh
        
    def GetSlaveInfos(self):
        return self.CTNParent.GetSlaveInfos(self.GetSlavePos())
    
    def GetVariableLocationTree(self):
        return  {"name": self.BaseParams.getName(),
                 "type": LOCATION_CONFNODE,
                 "location": self.GetFullIEC_Channel(),
                 "children": self.CTNParent.GetDeviceLocationTree(self.GetSlavePos(), self.GetCurrentLocation(), self.BaseParams.getName())
        }

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing confnode IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        return [],"",False

#--------------------------------------------------
#                 Ethercat CIA402 Node
#--------------------------------------------------

if HAS_MCL:
    
    NODE_VARIABLES = [
        ("ControlWord", 0x6040, 0x00, "UINT", "Q"),
        ("TargetPosition", 0x607a, 0x00, "DINT", "Q"),
        ("ModesOfOperation", 0x06060, 0x00, "SINT", "Q"),
        ("StatusWord", 0x6041, 0x00, "UINT", "I"),
        ("ModesOfOperationDisplay", 0x06061, 0x00, "SINT", "I"),
        ("ActualPosition", 0x6064, 0x00, "DINT", "I"),
        ("ActualVelocity", 0x606C, 0x00, "DINT", "I"),
    ]
    
    DEFAULT_RETRIEVE = "    __CIA402Node_%(location)s.axis->%(name)s = *(__CIA402Node_%(location)s.%(name)s);"
    DEFAULT_PUBLISH = "    *(__CIA402Node_%(location)s.%(name)s) = __CIA402Node_%(location)s.axis->%(name)s;"
    
    EXTRA_NODE_VARIABLES = [
        ("DigitalInputs", [
            {"description": ("DigitalInputs", 0x60FD, 0x00, "UDINT", "I"),
             "publish": None}
            ])
    ]
    EXTRA_NODE_VARIABLES_DICT = dict([("Enable" + name, value) for name, value in EXTRA_NODE_VARIABLES])
    
    class _EthercatCIA402SlaveCTN(_EthercatSlaveCTN):
        XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="CIA402SlaveParams">
            <xsd:complexType>
              %s
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
        """ % ("\n".join(['<xsd:attribute name="Enable%s" type="xsd:boolean" use="optional" default="false"/>' % category 
                          for category, variables in EXTRA_NODE_VARIABLES]) + AxisXSD)
        
        NODE_PROFILE = 402
        EditorType = CIA402NodeEditor
        
        ConfNodeMethods = [
            {"bitmap" : "CIA402AxisRef",
             "name" : _("Axis Ref"),
             "tooltip" : _("Initiate Drag'n drop of Axis ref located variable"),
             "method" : "_getCIA402AxisRef",
             "push": True},
        ]
        
        def GetIconName(self):
            return "CIA402Slave"
        
        def SetParamsAttribute(self, path, value):
            if path == "CIA402SlaveParams.Type":
                path = "SlaveParams.Type"
            elif path == "CIA402SlaveParams.Alias":
                path = "SlaveParams.Alias"
            return _EthercatSlaveCTN.SetParamsAttribute(self, path, value)
        
        def GetVariableLocationTree(self):
            axis_name = self.CTNName()
            current_location = self.GetCurrentLocation()
            children = [{"name": "%s Axis Ref" % (axis_name),
                         "type": LOCATION_VAR_INPUT,
                         "size": "W",
                         "IEC_type": "AXIS_REF",
                         "var_name": axis_name,
                         "location": "%%IW%s.0" % (".".join(map(str, current_location))),
                         "description": "",
                         "children": []}]
            children.extend(self.CTNParent.GetDeviceLocationTree(self.GetSlavePos(), current_location, axis_name))
            return  {"name": axis_name,
                     "type": LOCATION_CONFNODE,
                     "location": self.GetFullIEC_Channel(),
                     "children": children,
            }
        
        def _getCIA402AxisRef(self):
            data = wx.TextDataObject(str(("%%IW%s.0" % ".".join(map(str, self.GetCurrentLocation())), 
                                          "location", "AXIS_REF", self.CTNName(), "")))
            dragSource = wx.DropSource(self.GetCTRoot().AppFrame)
            dragSource.SetData(data)
            dragSource.DoDragDrop()
        
        def CTNGenerate_C(self, buildpath, locations):
            """
            Generate C code
            @param current_location: Tupple containing confnode IEC location : %I0.0.4.5 => (0,0,4,5)
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
            
            location_str = "_".join(map(lambda x:str(x), current_location))
            
            plc_cia402node_filepath = os.path.join(os.path.split(__file__)[0], "plc_cia402node.c")
            plc_cia402node_file = open(plc_cia402node_filepath, 'r')
            plc_cia402node_code = plc_cia402node_file.read()
            plc_cia402node_file.close()
            
            str_completion = {
                "slave_pos": self.GetSlavePos(),
                "location": location_str,
                "MCL_headers": Headers,
                "extern_located_variables_declaration": [],
                "entry_variables": [],
                "init_axis_params": [],
                "init_entry_variables": [],
                "extra_variables_retrieve": [],
                "extra_variables_publish": []
            }
            
            variables = NODE_VARIABLES[:]
            
            params = self.CTNParams[1].getElementInfos(self.CTNParams[0])
            for param in params["children"]:
                if param["name"] in EXTRA_NODE_VARIABLES_DICT:
                    if param["value"]:
                        extra_variables = EXTRA_NODE_VARIABLES_DICT.get(param["name"])
                        for variable_infos in extra_variables:
                            var_infos = {
                                "location": location_str,
                                "name": variable_infos["description"][0]
                            }
                            variables.append(variable_infos["description"])
                            retrieve_template = variable_infos.get("retrieve", DEFAULT_RETRIEVE)
                            publish_template = variable_infos.get("publish", DEFAULT_PUBLISH)
                            
                            if retrieve_template is not None:
                                str_completion["extra_variables_retrieve"].append(
                                    retrieve_template % var_infos)
                            if publish_template is not None:
                                str_completion["extra_variables_publish"].append(
                                    publish_template % var_infos)
                elif param["value"] is not None:
                    param_infos = {
                        "location": location_str,
                        "param_name": param["name"],
                    }
                    if param["type"] == "boolean":
                        param_infos["param_value"] = {True: "true", False: "false"}[param["value"]]
                    else:
                        param_infos["param_value"] = str(param["value"])
                    str_completion["init_axis_params"].append(
                        "        __CIA402Node_%(location)s.axis->%(param_name)s = %(param_value)s;" % param_infos)
            
            for variable in variables:
                var_infos = dict(zip(["name", "index", "subindex", "var_type", "dir"], variable))
                var_infos["location"] = location_str
                var_infos["var_size"] = self.GetSizeOfType(var_infos["var_type"])
                var_infos["var_name"] = "__%(dir)s%(var_size)s%(location)s_%(index)d_%(subindex)d" % var_infos
                
                str_completion["extern_located_variables_declaration"].append(
                        "IEC_%(var_type)s *%(var_name)s;" % var_infos)
                str_completion["entry_variables"].append(
                        "    IEC_%(var_type)s *%(name)s;" % var_infos)
                str_completion["init_entry_variables"].append(
                        "    __CIA402Node_%(location)s.%(name)s = %(var_name)s;" % var_infos)
                
                self.CTNParent.FileGenerator.DeclareVariable(
                        self.GetSlavePos(), var_infos["index"], var_infos["subindex"], 
                        var_infos["var_type"], var_infos["dir"], var_infos["var_name"])
            
            for element in ["extern_located_variables_declaration", 
                            "entry_variables", 
                            "init_axis_params", 
                            "init_entry_variables",
                            "extra_variables_retrieve",
                            "extra_variables_publish"]:
                str_completion[element] = "\n".join(str_completion[element])
            
            Gen_CIA402Nodefile_path = os.path.join(buildpath, "cia402node_%s.c"%location_str)
            cia402nodefile = open(Gen_CIA402Nodefile_path, 'w')
            cia402nodefile.write(plc_cia402node_code % str_completion)
            cia402nodefile.close()
            
            return [(Gen_CIA402Nodefile_path, '"-I%s"'%os.path.abspath(self.GetCTRoot().GetIECLibPath()))],"",True

#--------------------------------------------------
#                 Ethercat MASTER
#--------------------------------------------------

EtherCATConfigClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "EtherCATConfig.xsd")) 

def ExtractHexDecValue(value):
    try:
        return int(value)
    except:
        pass
    try:
        return int(value.replace("#", "0"), 16)
    except:
        raise ValueError, "Invalid value for HexDecValue \"%s\"" % value

def GenerateHexDecValue(value, base=10):
    if base == 10:
        return str(value)
    elif base == 16:
        return "#x%.8x" % value
    else:
        raise ValueError, "Not supported base"

cls = EtherCATConfigClasses.get("Config_Slave", None)
if cls:
    
    def getType(self):
        slave_info = self.getInfo()
        return {"device_type": slave_info.getName(),
                "vendor": GenerateHexDecValue(slave_info.getVendorId()),
                "product_code": GenerateHexDecValue(slave_info.getProductCode(), 16),
                "revision_number": GenerateHexDecValue(slave_info.getRevisionNo(), 16)}
    setattr(cls, "getType", getType)

    def setType(self, type_infos):
        slave_info = self.getInfo()
        slave_info.setName(type_infos["device_type"])
        slave_info.setVendorId(ExtractHexDecValue(type_infos["vendor"]))
        slave_info.setProductCode(ExtractHexDecValue(type_infos["product_code"]))
        slave_info.setRevisionNo(ExtractHexDecValue(type_infos["revision_number"]))
    setattr(cls, "setType", setType)

class _EthercatCTN:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="EtherlabNode">
        <xsd:complexType>
          <xsd:attribute name="MasterNumber" type="xsd:integer" use="optional" default="0"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    
    CTNChildrenTypes = [("EthercatSlave", _EthercatSlaveCTN, "Ethercat Slave")]
    if HAS_MCL:
        CTNChildrenTypes.append(("EthercatCIA402Slave", _EthercatCIA402SlaveCTN, "Ethercat CIA402 Slave"))
    
    def __init__(self):
        filepath = self.ConfigFileName()
        
        self.Config = EtherCATConfigClasses["EtherCATConfig"]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "EtherCATConfig":
                    self.Config.loadXMLTree(child)
                    self.CreateConfigBuffer(True)
        else:
            self.CreateConfigBuffer(False)
            self.OnCTNSave()

    def ExtractHexDecValue(self, value):
        return ExtractHexDecValue(value)

    def GetSizeOfType(self, type):
        return TYPECONVERSION.get(self.GetCTRoot().GetBaseType(type), None)

    def ConfigFileName(self):
        return os.path.join(self.CTNPath(), "config.xml")

    def GetSlaves(self):
        slaves = []
        for slave in self.Config.getConfig().getSlave():
            slaves.append(slave.getInfo().getPhysAddr())
        slaves.sort()
        return slaves

    def GetSlave(self, slave_pos):
        for slave in self.Config.getConfig().getSlave():
            slave_info = slave.getInfo()
            if slave_info.getPhysAddr() == slave_pos:
                return slave
        return None

    def _ScanNetwork(self):
        app_frame = self.GetCTRoot().AppFrame
        
        execute = True
        if len(self.Children) > 0:
            dialog = wx.MessageDialog(app_frame, 
                _("The current network configuration will be deleted.\nDo you want to continue?"), 
                _("Scan Network"), 
                wx.YES_NO|wx.ICON_QUESTION)
            execute = dialog.ShowModal() == wx.ID_YES
            dialog.Destroy()
        
        if execute:
            error, returnVal = self.RemoteExec(SCAN_COMMAND, returnVal = None)
            if error != 0:
                dialog = wx.MessageDialog(app_frame, returnVal, "Error", wx.OK|wx.ICON_ERROR)
                dialog.ShowModal()
                dialog.Destroy()
            elif returnVal is not None:
                for child in self.IECSortedChildren():
                    self._doRemoveChild(child)
                
                for slave in returnVal:
                    type_infos = {
                        "vendor": slave["vendor_id"],
                        "product_code": slave["product_code"],
                        "revision_number":slave["revision_number"],
                    }
                    device = self.GetModuleInfos(type_infos)
                    if device is not None:
                        if HAS_MCL and _EthercatCIA402SlaveCTN.NODE_PROFILE in device.GetProfileNumbers():
                            CTNType = "EthercatCIA402Slave"
                        else:
                            CTNType = "EthercatSlave"
                        self.CTNAddChild("slave%s" % slave["idx"], CTNType, slave["idx"])
                        self.SetSlaveAlias(slave["idx"], slave["alias"])
                        type_infos["device_type"] = device.getType().getcontent()
                        self.SetSlaveType(slave["idx"], type_infos)

    def CTNAddChild(self, CTNName, CTNType, IEC_Channel=0):
        """
        Create the confnodes that may be added as child to this node self
        @param CTNType: string desining the confnode class name (get name from CTNChildrenTypes)
        @param CTNName: string for the name of the confnode instance
        """
        newConfNodeOpj = ConfigTreeNode.CTNAddChild(self, CTNName, CTNType, IEC_Channel)
        
        slave = self.GetSlave(newConfNodeOpj.BaseParams.getIEC_Channel())
        if slave is None:
            slave = EtherCATConfigClasses["Config_Slave"]()
            slave_infos = slave.getInfo()
            slave_infos.setName("undefined")
            slave_infos.setPhysAddr(newConfNodeOpj.BaseParams.getIEC_Channel())
            slave_infos.setAutoIncAddr(0)
            self.Config.getConfig().appendSlave(slave)
            self.BufferConfig()
            self.OnCTNSave()
        
        return newConfNodeOpj

    def _doRemoveChild(self, CTNInstance):
        slave_pos = CTNInstance.GetSlavePos()
        config = self.Config.getConfig()
        for idx, slave in enumerate(config.getSlave()):
            slave_infos = slave.getInfo()
            if slave_infos.getPhysAddr() == slave_pos:
                config.removeSlave(idx)
                self.BufferConfig()
                self.OnCTNSave()
        ConfigTreeNode._doRemoveChild(self, CTNInstance)

    def SetSlavePosition(self, slave_pos, new_pos):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            slave_info = slave.getInfo()
            slave_info.setPhysAddr(new_pos)
            self.BufferConfig()
    
    def GetSlaveAlias(self, slave_pos):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            slave_info = slave.getInfo()
            return slave_info.getAutoIncAddr()
        return None
    
    def SetSlaveAlias(self, slave_pos, alias):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            slave_info = slave.getInfo()
            slave_info.setAutoIncAddr(alias)
            self.BufferConfig()
    
    def GetSlaveType(self, slave_pos):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            return slave.getType()
        return None
    
    def SetSlaveType(self, slave_pos, type_infos):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            slave.setType(type_infos)
            self.BufferConfig()
    
    def GetSlaveInfos(self, slave_pos):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            type_infos = slave.getType()
            device = self.GetModuleInfos(type_infos)
            if device is not None:
                infos = type_infos.copy()
                entries = device.GetEntriesList()
                entries_list = entries.items()
                entries_list.sort()
                entries = []
                current_index = None
                current_entry = None
                for (index, subindex), entry in entries_list:
                    entry["children"] = []
                    if index != current_index:
                        current_index = index
                        current_entry = entry
                        entries.append(entry)
                    elif current_entry is not None:
                        current_entry["children"].append(entry)
                    else:
                        entries.append(entry)
                infos.update({"physics": device.getPhysics(),
                              "sync_managers": device.GetSyncManagers(),
                              "entries": entries})
                return infos
        return None
    
    def GetModuleInfos(self, type_infos):
        return self.CTNParent.GetModuleInfos(type_infos)
    
    def GetSlaveTypesLibrary(self, profile_filter=None):
        return self.CTNParent.GetModulesLibrary(profile_filter)
    
    def GetDeviceLocationTree(self, slave_pos, current_location, device_name):
        slave = self.GetSlave(slave_pos)
        vars = []    
        if slave is not None:
            type_infos = slave.getType()
        
            device = self.GetModuleInfos(type_infos)
            if device is not None:
                sync_managers = []
                for sync_manager in device.getSm():
                    sync_manager_control_byte = ExtractHexDecValue(sync_manager.getControlByte())
                    sync_manager_direction = sync_manager_control_byte & 0x0c
                    if sync_manager_direction:
                        sync_managers.append(LOCATION_VAR_OUTPUT)
                    else:
                        sync_managers.append(LOCATION_VAR_INPUT)
                
                entries = device.GetEntriesList().items()
                entries.sort()
                for (index, subindex), entry in entries:
                    var_size = self.GetSizeOfType(entry["Type"])
                    if var_size is not None:
                        var_class = VARCLASSCONVERSION.get(entry["PDOMapping"], None)
                        if var_class is not None:
                            if var_class == LOCATION_VAR_INPUT:
                                var_dir = "%I"
                            else:
                                var_dir = "%Q"    
                        
                            vars.append({"name": "0x%4.4x-0x%2.2x: %s" % (index, subindex, entry["Name"]),
                                         "type": var_class,
                                         "size": var_size,
                                         "IEC_type": entry["Type"],
                                         "var_name": "%s_%4.4x_%2.2x" % ("_".join(device_name.split()), index, subindex),
                                         "location": "%s%s%s"%(var_dir, var_size, ".".join(map(str, current_location + 
                                                                                                    (index, subindex)))),
                                         "description": "",
                                         "children": []})
        
        return vars
    
    def CTNTestModified(self):
        return self.ChangesToSave or not self.ConfigIsSaved()    

    def OnCTNSave(self):
        filepath = self.ConfigFileName()
        
        text = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n"
        extras = {"xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
                  "xsi:noNamespaceSchemaLocation" : "EtherCATInfo.xsd"}
        text += self.Config.generateXMLText("EtherCATConfig", 0, extras)

        xmlfile = open(filepath,"w")
        xmlfile.write(text.encode("utf-8"))
        xmlfile.close()
        
        self.ConfigBuffer.CurrentSaved()
        return True

    def _Generate_C(self, buildpath, locations):
        current_location = self.GetCurrentLocation()
        # define a unique name for the generated C file
        location_str = "_".join(map(lambda x:str(x), current_location))
        
        Gen_Ethercatfile_path = os.path.join(buildpath, "ethercat_%s.c"%location_str)
        
        self.FileGenerator = _EthercatCFileGenerator(self)
        
        LocationCFilesAndCFLAGS, LDFLAGS, extra_files = ConfigTreeNode._Generate_C(self, buildpath, locations)
        
        self.FileGenerator.GenerateCFile(Gen_Ethercatfile_path, location_str, self.EtherlabNode)
        
        LocationCFilesAndCFLAGS.append(
            (current_location, 
             [(Gen_Ethercatfile_path, '"-I%s"'%os.path.abspath(self.GetCTRoot().GetIECLibPath()))], 
             True))
        LDFLAGS.append("-lethercat -lrtdm")
        
        return LocationCFilesAndCFLAGS, LDFLAGS, extra_files

    ConfNodeMethods = [
        {"bitmap" : "ScanNetwork",
         "name" : _("Scan Network"), 
         "tooltip" : _("Scan Network"),
         "method" : "_ScanNetwork"},
    ]

    def CTNGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing confnode IEC location : %I0.0.4.5 => (0,0,4,5)
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
        
        slaves = self.GetSlaves()
        for slave_pos in slaves:
            slave = self.GetSlave(slave_pos)
            if slave is not None:
                self.FileGenerator.DeclareSlave(slave_pos, slave.getInfo().getAutoIncAddr(), slave.getType())
        
        for location in locations:
            loc = location["LOC"][len(current_location):]
            slave_pos = loc[0]
            if slave_pos in slaves and len(loc) == 3:
                self.FileGenerator.DeclareVariable(
                    slave_pos, loc[1], loc[2], location["IEC_TYPE"], location["DIR"], location["NAME"])
        
        return [],"",False
        
#-------------------------------------------------------------------------------
#                      Current Buffering Management Functions
#-------------------------------------------------------------------------------

    """
    Return a copy of the config
    """
    def Copy(self, model):
        return cPickle.loads(cPickle.dumps(model))
    
    def CreateConfigBuffer(self, saved):
        self.ConfigBuffer = UndoBuffer(cPickle.dumps(self.Config), saved)
        
    def BufferConfig(self):
        self.ConfigBuffer.Buffering(cPickle.dumps(self.Config))
    
    def ConfigIsSaved(self):
        if self.ConfigBuffer is not None:
            return self.ConfigBuffer.IsCurrentSaved()
        else:
            return True

    def LoadPrevious(self):
        self.Config = cPickle.loads(self.ConfigBuffer.Previous())
    
    def LoadNext(self):
        self.Config = cPickle.loads(self.ConfigBuffer.Next())
    
    def GetBufferState(self):
        first = self.ConfigBuffer.IsFirst()
        last = self.ConfigBuffer.IsLast()
        return not first, not last


SLAVE_PDOS_CONFIGURATION_DECLARATION = """
/* Slave %(slave)d, "%(device_type)s"
 * Vendor ID:       0x%(vendor).8x
 * Product code:    0x%(product_code).8x
 * Revision number: 0x%(revision_number).8x
 */

ec_pdo_entry_info_t slave_%(slave)d_pdo_entries[] = {
%(pdos_entries_infos)s
};

ec_pdo_info_t slave_%(slave)d_pdos[] = {
%(pdos_infos)s
};

ec_sync_info_t slave_%(slave)d_syncs[] = {
%(pdos_sync_infos)s
    {0xff}
};
"""

SLAVE_CONFIGURATION_TEMPLATE = """
    if (!(slave%(slave)d = ecrt_master_slave_config(master, %(alias)d, %(position)d, 0x%(vendor).8x, 0x%(product_code).8x))) {
        fprintf(stderr, "Failed to get slave %(device_type)s configuration at alias %(alias)d and position %(position)d.\\n");
        return -1;
    }

    if (ecrt_slave_config_pdos(slave%(slave)d, EC_END, slave_%(slave)d_syncs)) {
        fprintf(stderr, "Failed to configure PDOs for slave %(device_type)s at alias %(alias)d and position %(position)d.\\n");
        return -1;
    }
"""

SLAVE_INITIALIZATION_TEMPLATE = """
    {
        uint8_t value[%(data_size)d];
        EC_WRITE_%(data_type)s((uint8_t *)value, %(data)s);
        if (ecrt_master_sdo_download(master, %(slave)d, 0x%(index).4x, 0x%(subindex).2x, (uint8_t *)value, %(data_size)d, &abort_code)) {
            fprintf(stderr, "Failed to initialize slave %(device_type)s at alias %(alias)d and position %(position)d.\\nError: %%d\\n", abort_code);
            return -1;
        }
    }
"""

SLAVE_OUTPUT_PDO_DEFAULT_VALUE = """
    {
        uint8_t value[%(data_size)d];
        if (ecrt_master_sdo_upload(master, %(slave)d, 0x%(index).4x, 0x%(subindex).2x, (uint8_t *)value, %(data_size)d, &result_size, &abort_code)) {
            fprintf(stderr, "Failed to get default value for output PDO in slave %(device_type)s at alias %(alias)d and position %(position)d.\\nError: %%d\\n", abort_code);
            return -1;
        }
        %(real_var)s = EC_READ_%(data_type)s((uint8_t *)value);
    }
"""

def ConfigureVariable(entry_infos, str_completion):
    entry_infos["data_type"] = DATATYPECONVERSION.get(entry_infos["var_type"], None)
    if entry_infos["data_type"] is None:
        raise ValueError, _("Type of location \"%s\" not yet supported!") % entry_infos["var_name"]
    
    if entry_infos.has_key("real_var"):
        str_completion["located_variables_declaration"].append(
            "IEC_%(var_type)s %(real_var)s;" % entry_infos)
    else:
        entry_infos["real_var"] = "beremiz" + entry_infos["var_name"]
        str_completion["located_variables_declaration"].extend(
            ["IEC_%(var_type)s %(real_var)s;" % entry_infos,
             "IEC_%(var_type)s *%(var_name)s = &%(real_var)s;" % entry_infos])
    
    str_completion["used_pdo_entry_offset_variables_declaration"].append(
        "unsigned int slave%(slave)d_%(index).4x_%(subindex).2x;" % entry_infos)
    
    if entry_infos["data_type"] == "BIT":
        str_completion["used_pdo_entry_offset_variables_declaration"].append(
            "unsigned int slave%(slave)d_%(index).4x_%(subindex).2x_bit;" % entry_infos)
        
        str_completion["used_pdo_entry_configuration"].append(
             ("    {%(alias)d, %(position)d, 0x%(vendor).8x, 0x%(product_code).8x, " + 
              "0x%(index).4x, %(subindex)d, &slave%(slave)d_%(index).4x_%(subindex).2x, " + 
              "&slave%(slave)d_%(index).4x_%(subindex).2x_bit},") % entry_infos)
        
        if entry_infos["dir"] == "I":
            str_completion["retrieve_variables"].append(
              ("    %(real_var)s = EC_READ_BIT(domain1_pd + slave%(slave)d_%(index).4x_%(subindex).2x, " + 
               "slave%(slave)d_%(index).4x_%(subindex).2x_bit);") % entry_infos)
        elif entry_infos["dir"] == "Q":
            str_completion["publish_variables"].append(
              ("    EC_WRITE_BIT(domain1_pd + slave%(slave)d_%(index).4x_%(subindex).2x, " + 
               "slave%(slave)d_%(index).4x_%(subindex).2x_bit, %(real_var)s);") % entry_infos)
    
    else:
        str_completion["used_pdo_entry_configuration"].append(
            ("    {%(alias)d, %(position)d, 0x%(vendor).8x, 0x%(product_code).8x, 0x%(index).4x, " + 
             "%(subindex)d, &slave%(slave)d_%(index).4x_%(subindex).2x},") % entry_infos)
        
        if entry_infos["dir"] == "I":
            str_completion["retrieve_variables"].append(
                ("    %(real_var)s = EC_READ_%(data_type)s(domain1_pd + " + 
                 "slave%(slave)d_%(index).4x_%(subindex).2x);") % entry_infos)
        elif entry_infos["dir"] == "Q":
            str_completion["publish_variables"].append(
                ("    EC_WRITE_%(data_type)s(domain1_pd + slave%(slave)d_%(index).4x_%(subindex).2x, " + 
                 "%(real_var)s);") % entry_infos)

def ExclusionSortFunction(x, y):
    if x["matching"] == y["matching"]:
        if x["assigned"] and not y["assigned"]:
            return -1
        elif not x["assigned"] and y["assigned"]:
            return 1
        return cmp(x["count"], y["count"])
    return -cmp(x["matching"], y["matching"])

class _EthercatCFileGenerator:
    
    def __init__(self, controler):
        self.Controler = controler
        
        self.Slaves = []
        self.UsedVariables = {}

    def __del__(self):
        self.Controler = None            
    
    def DeclareSlave(self, slave_index, slave_alias, slave):
        self.Slaves.append((slave_index, slave_alias, slave))

    def DeclareVariable(self, slave_index, index, subindex, iec_type, dir, name):
        slave_variables = self.UsedVariables.setdefault(slave_index, {})
        
        entry_infos = slave_variables.get((index, subindex), None)
        if entry_infos is None:
            slave_variables[(index, subindex)] = {
                "infos": (iec_type, dir, name),
                "mapped": False}
        elif entry_infos["infos"] != (iec_type, dir, name):
            raise ValueError, _("Definition conflict for location \"%s\"") % name 
        
    def GenerateCFile(self, filepath, location_str, etherlab_node_infos):
        
        # Extract etherlab master code template
        plc_etherlab_filepath = os.path.join(os.path.split(__file__)[0], "plc_etherlab.c")
        plc_etherlab_file = open(plc_etherlab_filepath, 'r')
        plc_etherlab_code = plc_etherlab_file.read()
        plc_etherlab_file.close()
        
        # Initialize strings for formatting master code template
        str_completion = {
            "location": location_str,
            "master_number": etherlab_node_infos.getMasterNumber(),
            "located_variables_declaration": [],
            "used_pdo_entry_offset_variables_declaration": [],
            "used_pdo_entry_configuration": [],
            "pdos_configuration_declaration": "",
            "slaves_declaration": "",
            "slaves_configuration": "",
            "slaves_output_pdos_default_values_extraction": "",
            "slaves_initialization": "",
            "retrieve_variables": [],
            "publish_variables": [],
        }
        
        # Initialize variable storing variable mapping state
        for slave_entries in self.UsedVariables.itervalues():
            for entry_infos in slave_entries.itervalues():
                entry_infos["mapped"] = False
        
        # Sort slaves by position (IEC_Channel)
        self.Slaves.sort()
        # Initialize dictionary storing alias auto-increment position values
        alias = {}
        
        # Generating code for each slave
        for (slave_idx, slave_alias, type_infos) in self.Slaves:
            
            # Defining slave alias and auto-increment position
            if alias.get(slave_alias) is not None:
                alias[slave_alias] += 1
            else:
                alias[slave_alias] = 0
            slave_pos = (slave_alias, alias[slave_alias])
            
            # Extract slave device informations
            device = self.Controler.GetModuleInfos(type_infos)
            if device is not None:
                
                # Extract slaves variables to be mapped
                slave_variables = self.UsedVariables.get(slave_idx, {})
                
                # Extract slave device object dictionary entries
                device_entries = device.GetEntriesList()
                
                # Adding code for declaring slave in master code template strings
                for element in ["vendor", "product_code", "revision_number"]:
                    type_infos[element] = ExtractHexDecValue(type_infos[element])
                type_infos.update(dict(zip(["slave", "alias", "position"], (slave_idx,) + slave_pos)))
                
                # Extract slave device CoE informations
                device_coe = device.getCoE()
                if device_coe is not None:
                    
                    # If device support CanOpen over Ethernet, adding code for calling 
                    # init commands when initializing slave in master code template strings
                    for initCmd in device_coe.getInitCmd():
                        index = ExtractHexDecValue(initCmd.getIndex())
                        subindex = ExtractHexDecValue(initCmd.getSubIndex())
                        entry = device_entries.get((index, subindex), None)
                        if entry is not None:
                            data_size = entry["BitSize"] / 8
                            data_str = ("0x%%.%dx" % (data_size * 2)) % initCmd.getData().getcontent()
                            init_cmd_infos = {
                                "index": index,
                                "subindex": subindex,
                                "data": data_str,
                                "data_type": DATATYPECONVERSION.get(entry["Type"]),
                                "data_size": data_size
                            }
                            init_cmd_infos.update(type_infos)
                            str_completion["slaves_initialization"] += SLAVE_INITIALIZATION_TEMPLATE % init_cmd_infos
                
                    # Extract slave device PDO configuration capabilities
                    PdoAssign = device_coe.getPdoAssign()
                    PdoConfig = device_coe.getPdoConfig()
                else:
                    PdoAssign = PdoConfig = False
                
                # Test if slave has a configuration or need one
                if len(device.getTxPdo() + device.getRxPdo()) > 0 or len(slave_variables) > 0 and PdoConfig and PdoAssign:
                    
                    str_completion["slaves_declaration"] += "static ec_slave_config_t *slave%(slave)d = NULL;\n" % type_infos
                    str_completion["slaves_configuration"] += SLAVE_CONFIGURATION_TEMPLATE % type_infos
                    
                    # Initializing 
                    pdos_infos = {
                        "pdos_entries_infos": [],
                        "pdos_infos": [],
                        "pdos_sync_infos": [], 
                    }
                    pdos_infos.update(type_infos)
                    
                    sync_managers = []
                    for sync_manager_idx, sync_manager in enumerate(device.getSm()):
                        sync_manager_infos = {
                            "index": sync_manager_idx, 
                            "name": sync_manager.getcontent(),
                            "slave": slave_idx,
                            "pdos": [], 
                            "pdos_number": 0,
                        }
                        
                        sync_manager_control_byte = ExtractHexDecValue(sync_manager.getControlByte())
                        sync_manager_direction = sync_manager_control_byte & 0x0c
                        sync_manager_watchdog = sync_manager_control_byte & 0x40
                        if sync_manager_direction:
                            sync_manager_infos["sync_manager_type"] = "EC_DIR_OUTPUT"
                        else:
                            sync_manager_infos["sync_manager_type"] = "EC_DIR_INPUT"
                        if sync_manager_watchdog:
                            sync_manager_infos["watchdog"] = "EC_WD_ENABLE"
                        else:
                            sync_manager_infos["watchdog"] = "EC_WD_DISABLE"
                        
                        sync_managers.append(sync_manager_infos)
                    
                    pdos_index = []
                    exclusive_pdos = {}
                    selected_pdos = []
                    for pdo, pdo_type in ([(pdo, "Inputs") for pdo in device.getTxPdo()] +
                                          [(pdo, "Outputs") for pdo in device.getRxPdo()]):
                        
                        pdo_index = ExtractHexDecValue(pdo.getIndex().getcontent())
                        pdos_index.append(pdo_index)
                        
                        excluded_list = pdo.getExclude()
                        if len(excluded_list) > 0:
                            exclusion_list = [pdo_index]
                            for excluded in excluded_list:
                                exclusion_list.append(ExtractHexDecValue(excluded.getcontent()))
                            exclusion_list.sort()
                            
                            exclusion_scope = exclusive_pdos.setdefault(tuple(exclusion_list), [])
                            
                            entries = pdo.getEntry()
                            pdo_mapping_match = {
                                "index": pdo_index, 
                                "matching": 0, 
                                "count": len(entries), 
                                "assigned": pdo.getSm() is not None
                            }
                            exclusion_scope.append(pdo_mapping_match)
                            
                            for entry in entries:
                                index = ExtractHexDecValue(entry.getIndex().getcontent())
                                subindex = ExtractHexDecValue(entry.getSubIndex())
                                if slave_variables.get((index, subindex), None) is not None:
                                    pdo_mapping_match["matching"] += 1
                        
                        elif pdo.getMandatory():
                            selected_pdos.append(pdo_index)
                    
                    excluded_pdos = []
                    for exclusion_scope in exclusive_pdos.itervalues():
                        exclusion_scope.sort(ExclusionSortFunction)
                        start_excluding_index = 0
                        if exclusion_scope[0]["matching"] > 0:
                            selected_pdos.append(exclusion_scope[0]["index"])
                            start_excluding_index = 1
                        excluded_pdos.extend([pdo["index"] for pdo in exclusion_scope[start_excluding_index:] if PdoAssign or not pdo["assigned"]])
                    
                    for pdo, pdo_type in ([(pdo, "Inputs") for pdo in device.getTxPdo()] +
                                          [(pdo, "Outputs") for pdo in device.getRxPdo()]):
                        entries = pdo.getEntry()
                        
                        pdo_index = ExtractHexDecValue(pdo.getIndex().getcontent())
                        if pdo_index in excluded_pdos:
                            continue
                        
                        pdo_needed = pdo_index in selected_pdos
                        
                        entries_infos = []
                        
                        for entry in entries:
                            index = ExtractHexDecValue(entry.getIndex().getcontent())
                            subindex = ExtractHexDecValue(entry.getSubIndex())
                            entry_infos = {
                                "index": index,
                                "subindex": subindex,
                                "name": ExtractName(entry.getName()),
                                "bitlen": entry.getBitLen(),
                            }
                            entry_infos.update(type_infos)
                            entries_infos.append("    {0x%(index).4x, 0x%(subindex).2x, %(bitlen)d}, /* %(name)s */" % entry_infos)
                            
                            entry_declaration = slave_variables.get((index, subindex), None)
                            if entry_declaration is not None and not entry_declaration["mapped"]:
                                pdo_needed = True
                                
                                entry_infos.update(dict(zip(["var_type", "dir", "var_name"], entry_declaration["infos"])))
                                entry_declaration["mapped"] = True
                                
                                entry_type = entry.getDataType().getcontent()
                                if entry_infos["var_type"] != entry_type:
                                    message = _("Wrong type for location \"%s\"!") % entry_infos["var_name"]
                                    if (self.Controler.GetSizeOfType(entry_infos["var_type"]) != 
                                        self.Controler.GetSizeOfType(entry_type)):
                                        raise ValueError, message
                                    else:
                                        self.Controler.GetCTRoot().logger.write_warning(_("Warning: ") + message + "\n")
                                
                                if (entry_infos["dir"] == "I" and pdo_type != "Inputs" or 
                                    entry_infos["dir"] == "Q" and pdo_type != "Outputs"):
                                    raise ValueError, _("Wrong direction for location \"%s\"!") % entry_infos["var_name"]
                                
                                ConfigureVariable(entry_infos, str_completion)
                            
                            elif pdo_type == "Outputs" and entry.getDataType() is not None and device_coe is not None:
                                data_type = entry.getDataType().getcontent()
                                entry_infos["dir"] = "Q"
                                entry_infos["data_size"] = max(1, entry_infos["bitlen"] / 8)
                                entry_infos["data_type"] = DATATYPECONVERSION.get(data_type)
                                entry_infos["var_type"] = data_type
                                entry_infos["real_var"] = "slave%(slave)d_%(index).4x_%(subindex).2x_default" % entry_infos
                                
                                ConfigureVariable(entry_infos, str_completion)
                                
                                str_completion["slaves_output_pdos_default_values_extraction"] += \
                                    SLAVE_OUTPUT_PDO_DEFAULT_VALUE % entry_infos
                                
                        if pdo_needed:
                            for excluded in pdo.getExclude():
                                excluded_index = ExtractHexDecValue(excluded.getcontent())
                                if excluded_index not in excluded_pdos:
                                    excluded_pdos.append(excluded_index)
                            
                            sm = pdo.getSm()
                            if sm is None:
                                for sm_idx, sync_manager in enumerate(sync_managers):
                                    if sync_manager["name"] == pdo_type:
                                        sm = sm_idx
                            if sm is None:
                                raise ValueError, _("No sync manager available for %s pdo!") % pdo_type
                                
                            sync_managers[sm]["pdos_number"] += 1
                            sync_managers[sm]["pdos"].append(
                                {"slave": slave_idx,
                                 "index": pdo_index,
                                 "name": ExtractName(pdo.getName()),
                                 "type": pdo_type, 
                                 "entries": entries_infos,
                                 "entries_number": len(entries_infos),
                                 "fixed": pdo.getFixed() == True})
                
                    if PdoConfig and PdoAssign:
                        dynamic_pdos = {}
                        dynamic_pdos_number = 0
                        for category, min_index, max_index in [("Inputs", 0x1600, 0x1800), 
                                                               ("Outputs", 0x1a00, 0x1C00)]:
                            for sync_manager in sync_managers:
                                if sync_manager["name"] == category:
                                    category_infos = dynamic_pdos.setdefault(category, {})
                                    category_infos["sync_manager"] = sync_manager
                                    category_infos["pdos"] = [pdo for pdo in category_infos["sync_manager"]["pdos"] 
                                                              if not pdo["fixed"] and pdo["type"] == category]
                                    category_infos["current_index"] = min_index
                                    category_infos["max_index"] = max_index
                                    break
                        
                        for (index, subindex), entry_declaration in slave_variables.iteritems():
                            
                            if not entry_declaration["mapped"]:
                                entry = device_entries.get((index, subindex), None)
                                if entry is None:
                                    raise ValueError, _("Unknown entry index 0x%4.4x, subindex 0x%2.2x for device %s") % \
                                                     (index, subindex, type_infos["device_type"])
                                
                                entry_infos = {
                                    "index": index,
                                    "subindex": subindex,
                                    "name": entry["Name"],
                                    "bitlen": entry["BitSize"],
                                }
                                entry_infos.update(type_infos)
                                
                                entry_infos.update(dict(zip(["var_type", "dir", "var_name", "real_var"], entry_declaration["infos"])))
                                entry_declaration["mapped"] = True
                                
                                if entry_infos["var_type"] != entry["Type"]:
                                    message = _("Wrong type for location \"%s\"!") % entry_infos["var_name"]
                                    if (self.Controler.GetSizeOfType(entry_infos["var_type"]) != 
                                        self.Controler.GetSizeOfType(entry["Type"])):
                                        raise ValueError, message
                                    else:
                                        self.Controler.GetCTRoot().logger.write_warning(message + "\n")
                                
                                if entry_infos["dir"] == "I" and entry["PDOMapping"] in ["T", "RT"]:
                                    pdo_type = "Inputs"
                                elif entry_infos["dir"] == "Q" and entry["PDOMapping"] in ["R", "RT"]:
                                    pdo_type = "Outputs"
                                else:
                                    raise ValueError, _("Wrong direction for location \"%s\"!") % entry_infos["var_name"]
                                
                                if not dynamic_pdos.has_key(pdo_type):
                                    raise ValueError, _("No Sync manager defined for %s!") % pdo_type
                                
                                ConfigureVariable(entry_infos, str_completion)
                                
                                if len(dynamic_pdos[pdo_type]["pdos"]) > 0:
                                    pdo = dynamic_pdos[pdo_type]["pdos"][0]
                                else:
                                    while dynamic_pdos[pdo_type]["current_index"] in pdos_index:
                                        dynamic_pdos[pdo_type]["current_index"] += 1
                                    if dynamic_pdos[pdo_type]["current_index"] >= dynamic_pdos[pdo_type]["max_index"]:
                                        raise ValueError, _("No more free PDO index available for %s!") % pdo_type
                                    pdos_index.append(dynamic_pdos[pdo_type]["current_index"])
                                    
                                    dynamic_pdos_number += 1
                                    pdo = {"slave": slave_idx,
                                           "index": dynamic_pdos[pdo_type]["current_index"],
                                           "name": "Dynamic PDO %d" % dynamic_pdos_number,
                                           "type": pdo_type, 
                                           "entries": [],
                                           "entries_number": 0,
                                           "fixed": False}
                                    dynamic_pdos[pdo_type]["sync_manager"]["pdos_number"] += 1
                                    dynamic_pdos[pdo_type]["sync_manager"]["pdos"].append(pdo)
                                    dynamic_pdos[pdo_type]["pdos"].append(pdo)
                                
                                pdo["entries"].append("    {0x%(index).4x, 0x%(subindex).2x, %(bitlen)d}, /* %(name)s */" % entry_infos)
                                pdo["entries_number"] += 1
                                
                                if pdo["entries_number"] == 255:
                                    dynamic_pdos[pdo_type]["pdos"].pop(0)
                    
                    pdo_offset = 0
                    entry_offset = 0
                    for sync_manager_infos in sync_managers:
                    
                        for pdo_infos in sync_manager_infos["pdos"]:
                            pdo_infos["offset"] = entry_offset
                            pdo_entries = pdo_infos["entries"]
                            pdos_infos["pdos_infos"].append(
                                ("    {0x%(index).4x, %(entries_number)d, " + 
                                 "slave_%(slave)d_pdo_entries + %(offset)d}, /* %(name)s */") % pdo_infos)
                            entry_offset += len(pdo_entries)
                            pdos_infos["pdos_entries_infos"].extend(pdo_entries)
                        
                        sync_manager_infos["offset"] = pdo_offset
                        pdo_offset_shift = sync_manager_infos["pdos_number"]
                        pdos_infos["pdos_sync_infos"].append(
                            ("    {%(index)d, %(sync_manager_type)s, %(pdos_number)d, " + 
                             ("slave_%(slave)d_pdos + %(offset)d" if pdo_offset_shift else "NULL") +
                             ", %(watchdog)s},") % sync_manager_infos)
                        pdo_offset += pdo_offset_shift  
                    
                    for element in ["pdos_entries_infos", "pdos_infos", "pdos_sync_infos"]:
                        pdos_infos[element] = "\n".join(pdos_infos[element])
                    
                    str_completion["pdos_configuration_declaration"] += SLAVE_PDOS_CONFIGURATION_DECLARATION % pdos_infos
                
                for (index, subindex), entry_declaration in slave_variables.iteritems():
                    if not entry_declaration["mapped"]:
                        message = _("Entry index 0x%4.4x, subindex 0x%2.2x not mapped for device %s") % \
                                        (index, subindex, type_infos["device_type"])
                        self.Controler.GetCTRoot().logger.write_warning(_("Warning: ") + message + "\n")
                    
        for element in ["used_pdo_entry_offset_variables_declaration", 
                        "used_pdo_entry_configuration", 
                        "located_variables_declaration", 
                        "retrieve_variables", 
                        "publish_variables"]:
            str_completion[element] = "\n".join(str_completion[element])
        
        etherlabfile = open(filepath, 'w')
        etherlabfile.write(plc_etherlab_code % str_completion)
        etherlabfile.close()

#--------------------------------------------------
#                 Ethercat ConfNode
#--------------------------------------------------

EtherCATInfoClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "EtherCATInfo.xsd")) 

cls = EtherCATInfoClasses["EtherCATBase.xsd"].get("DictionaryType", None)
if cls:
    cls.loadXMLTreeArgs = None
    
    setattr(cls, "_loadXMLTree", getattr(cls, "loadXMLTree"))
    
    def loadXMLTree(self, *args):
        self.loadXMLTreeArgs = args
    setattr(cls, "loadXMLTree", loadXMLTree)

    def load(self):
        if self.loadXMLTreeArgs is not None:
            self._loadXMLTree(*self.loadXMLTreeArgs)
            self.loadXMLTreeArgs = None
    setattr(cls, "load", load)

cls = EtherCATInfoClasses["EtherCATInfo.xsd"].get("DeviceType", None)
if cls:
    cls.DataTypes = None
    
    def GetProfileNumbers(self):
        profiles = []
        
        for profile in self.getProfile():
            profile_content = profile.getcontent()
            if profile_content is None:
                continue
            
            for content_element in profile_content["value"]:
                if content_element["name"] == "ProfileNo":
                    profiles.append(content_element["value"])
        
        return profiles
    setattr(cls, "GetProfileNumbers", GetProfileNumbers)
    
    def GetProfileDictionaries(self):
        dictionaries = []
        
        for profile in self.getProfile():
        
            profile_content = profile.getcontent()
            if profile_content is None:
                continue
            
            for content_element in profile_content["value"]:
                if content_element["name"] == "Dictionary":
                    dictionaries.append(content_element["value"])
                elif content_element["name"] == "DictionaryFile":
                    raise ValueError, "DictionaryFile for defining Device Profile is not yet supported!"
                
        return dictionaries
    setattr(cls, "GetProfileDictionaries", GetProfileDictionaries)
    
    def ExtractDataTypes(self):
        self.DataTypes = {}
        
        for dictionary in self.GetProfileDictionaries():
            
            datatypes = dictionary.getDataTypes()
            if datatypes is not None:
                
                for datatype in datatypes.getDataType():
                    content = datatype.getcontent()
                    if content is not None and content["name"] == "SubItem":
                        self.DataTypes[datatype.getName()] = datatype
    
    setattr(cls, "ExtractDataTypes", ExtractDataTypes)
    
    def getCoE(self):
        mailbox = self.getMailbox()
        if mailbox is not None:
            return mailbox.getCoE()
        return None
    setattr(cls, "getCoE", getCoE)

    def GetEntriesList(self):
        if self.DataTypes is None:
            self.ExtractDataTypes()
        
        entries = {}
        
        for dictionary in self.GetProfileDictionaries():
            dictionary.load()
            
            for object in dictionary.getObjects().getObject():
                entry_index = object.getIndex().getcontent()
                index = ExtractHexDecValue(entry_index)
                entry_type = object.getType()
                entry_name = ExtractName(object.getName())
                
                entry_type_infos = self.DataTypes.get(entry_type, None)
                if entry_type_infos is not None:
                    content = entry_type_infos.getcontent()
                    for subitem in content["value"]:
                        entry_subidx = subitem.getSubIdx()
                        if entry_subidx is None:
                            entry_subidx = "0"
                        subidx = ExtractHexDecValue(entry_subidx)
                        subitem_access = ""
                        subitem_pdomapping = ""
                        subitem_flags = subitem.getFlags()
                        if subitem_flags is not None:
                            access = subitem_flags.getAccess()
                            if access is not None:
                                subitem_access = access.getcontent()
                            pdomapping = subitem_flags.getPdoMapping()
                            if pdomapping is not None:
                                subitem_pdomapping = pdomapping.upper()
                        entries[(index, subidx)] = {
                            "Index": entry_index,
                            "SubIndex": entry_subidx,
                            "Name": "%s - %s" % 
                                    (entry_name.decode("utf-8"),
                                     ExtractName(subitem.getDisplayName(), 
                                                 subitem.getName()).decode("utf-8")),
                            "Type": subitem.getType(),
                            "BitSize": subitem.getBitSize(),
                            "Access": subitem_access, 
                            "PDOMapping": subitem_pdomapping, 
                            "PDO index": "", 
                            "PDO name": "", 
                            "PDO type": ""}
                else:
                    entry_access = ""
                    entry_pdomapping = ""
                    entry_flags = object.getFlags()
                    if entry_flags is not None:
                        access = entry_flags.getAccess()
                        if access is not None:
                            entry_access = access.getcontent()
                        pdomapping = entry_flags.getPdoMapping()
                        if pdomapping is not None:
                            entry_pdomapping = pdomapping.upper()
                    entries[(index, 0)] = {
                         "Index": entry_index,
                         "SubIndex": "0",
                         "Name": entry_name,
                         "Type": entry_type,
                         "BitSize": object.getBitSize(),
                         "Access": entry_access,
                         "PDOMapping": entry_pdomapping, 
                         "PDO index": "", 
                         "PDO name": "", 
                         "PDO type": ""}
        
        for TxPdo in self.getTxPdo():
            ExtractPdoInfos(TxPdo, "Transmit", entries)
        for RxPdo in self.getRxPdo():
            ExtractPdoInfos(RxPdo, "Receive", entries)
        
        return entries
    setattr(cls, "GetEntriesList", GetEntriesList)

    def GetSyncManagers(self):
        sync_managers = []
        for sync_manager in self.getSm():
            sync_manager_infos = {}
            for name, value in [("Name", sync_manager.getcontent()),
                                ("Start Address", sync_manager.getStartAddress()),
                                ("Default Size", sync_manager.getDefaultSize()),
                                ("Control Byte", sync_manager.getControlByte()),
                                ("Enable", sync_manager.getEnable())]:
                if value is None:
                    value =""
                sync_manager_infos[name] = value
            sync_managers.append(sync_manager_infos)
        return sync_managers
    setattr(cls, "GetSyncManagers", GetSyncManagers)

def GroupItemCompare(x, y):
    if x["type"] == y["type"]:
        if x["type"] == ETHERCAT_GROUP:
            return cmp(x["order"], y["order"])
        else:
            return cmp(x["name"], y["name"])
    elif x["type"] == ETHERCAT_GROUP:
        return -1
    return 1

def SortGroupItems(group):
    for item in group["children"]:
        if item["type"] == ETHERCAT_GROUP:
            SortGroupItems(item)
    group["children"].sort(GroupItemCompare)

def ExtractName(names, default=None):
    if len(names) == 1:
        return names[0].getcontent()
    else:
        for name in names:
            if name.getLcId() == 1033:
                return name.getcontent()
    return default

def ExtractPdoInfos(pdo, pdo_type, entries):
    pdo_index = pdo.getIndex().getcontent()
    pdo_name = ExtractName(pdo.getName())
    for pdo_entry in pdo.getEntry():
        entry_index = pdo_entry.getIndex().getcontent()
        entry_subindex = pdo_entry.getSubIndex()
        index = ExtractHexDecValue(entry_index)
        subindex = ExtractHexDecValue(entry_subindex)
        
        entry = entries.get((index, subindex), None)
        if entry is not None:
            entry["PDO index"] = pdo_index
            entry["PDO name"] = pdo_name
            entry["PDO type"] = pdo_type
        else:
            entry_type = pdo_entry.getDataType()
            if entry_type is not None:
                if pdo_type == "Transmit":
                    access = "ro"
                    pdomapping = "T"
                else:
                    access = "wo"
                    pdomapping = "R"
                entries[(index, subindex)] = {
                    "Index": entry_index,
                    "SubIndex": entry_subindex,
                    "Name": ExtractName(pdo_entry.getName()),
                    "Type": entry_type.getcontent(),
                    "Access": access,
                    "PDOMapping": pdomapping,
                    "PDO index": pdo_index, 
                    "PDO name": pdo_name, 
                    "PDO type": pdo_type}

class RootClass:
    
    CTNChildrenTypes = [("EthercatNode",_EthercatCTN,"Ethercat Master")]
    
    def __init__(self):
        self.LoadModulesLibrary()
    
    def GetModulesLibraryPath(self):
        library_path = os.path.join(self.CTNPath(), "modules")
        if not os.path.exists(library_path):
            os.mkdir(library_path)
        return library_path
    
    def _ImportModuleLibrary(self):
        dialog = wx.FileDialog(self.GetCTRoot().AppFrame, _("Choose an XML file"), os.getcwd(), "",  _("XML files (*.xml)|*.xml|All files|*.*"), wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            if os.path.isfile(filepath):
                shutil.copy(filepath, self.GetModulesLibraryPath())
                self.LoadModulesLibrary()
            else:
                self.GetCTRoot().logger.write_error(_("No such XML file: %s\n") % filepath)
        dialog.Destroy()  
    
    ConfNodeMethods = [
        {"bitmap" : "ImportESI",
         "name" : _("Import module library"), 
         "tooltip" : _("Import module library"),
         "method" : "_ImportModuleLibrary"},
    ]
    
    def CTNGenerate_C(self, buildpath, locations):
        return [],"",False
    
    def LoadModulesLibrary(self):
        self.ModulesLibrary = {}
        
        library_path = self.GetModulesLibraryPath()
        
        files = os.listdir(library_path)
        for file in files:
            filepath = os.path.join(library_path, file)
            if os.path.isfile(filepath) and os.path.splitext(filepath)[-1] == ".xml":
                xmlfile = open(filepath, 'r')
                xml_tree = minidom.parse(xmlfile)
                xmlfile.close()
                
                modules_infos = None
                for child in xml_tree.childNodes:
                    if child.nodeType == xml_tree.ELEMENT_NODE and child.nodeName == "EtherCATInfo":
                        modules_infos = EtherCATInfoClasses["EtherCATInfo.xsd"]["EtherCATInfo"]()
                        modules_infos.loadXMLTree(child)
                
                if modules_infos is not None:
                    vendor = modules_infos.getVendor()
                    
                    vendor_category = self.ModulesLibrary.setdefault(ExtractHexDecValue(vendor.getId()), 
                                                                     {"name": ExtractName(vendor.getName(), _("Miscellaneous")), 
                                                                      "groups": {}})
                    
                    for group in modules_infos.getDescriptions().getGroups().getGroup():
                        group_type = group.getType()
                        
                        vendor_category["groups"].setdefault(group_type, {"name": ExtractName(group.getName(), group_type), 
                                                                          "parent": group.getParentGroup(),
                                                                          "order": group.getSortOrder(), 
                                                                          "devices": []})
                    
                    for device in modules_infos.getDescriptions().getDevices().getDevice():
                        device_group = device.getGroupType()
                        if not vendor_category["groups"].has_key(device_group):
                            raise ValueError, "Not such group \"%\"" % device_group
                        vendor_category["groups"][device_group]["devices"].append((device.getType().getcontent(), device))
    
    def GetModulesLibrary(self, profile_filter=None):
        library = []
        for vendor_id, vendor in self.ModulesLibrary.iteritems():
            groups = []
            children_dict = {}
            for group_type, group in vendor["groups"].iteritems():
                group_infos = {"name": group["name"],
                               "order": group["order"],
                               "type": ETHERCAT_GROUP,
                               "infos": None,
                               "children": children_dict.setdefault(group_type, [])}
                device_dict = {}
                for device_type, device in group["devices"]:
                    if profile_filter is None or profile_filter in device.GetProfileNumbers():
                        device_infos = {"name": ExtractName(device.getName()),
                                        "type": ETHERCAT_DEVICE,
                                        "infos": {"device_type": device_type,
                                                  "vendor": vendor_id,
                                                  "product_code": device.getType().getProductCode(),
                                                  "revision_number": device.getType().getRevisionNo()},
                                        "children": []}
                        group_infos["children"].append(device_infos)
                        device_type_occurrences = device_dict.setdefault(device_type, [])
                        device_type_occurrences.append(device_infos)
                for device_type_occurrences in device_dict.itervalues():
                    if len(device_type_occurrences) > 1:
                        for occurrence in device_type_occurrences:
                            occurrence["name"] += _(" (rev. %s)") % occurrence["infos"]["revision_number"]
                if len(group_infos["children"]) > 0:
                    if group["parent"] is not None:
                        parent_children = children_dict.setdefault(group["parent"], [])
                        parent_children.append(group_infos)
                    else:
                        groups.append(group_infos)
            if len(groups) > 0:
                library.append({"name": vendor["name"],
                                "type": ETHERCAT_VENDOR,
                                "infos": None,
                                "children": groups})
        library.sort(lambda x, y: cmp(x["name"], y["name"]))
        return library
    
    def GetModuleInfos(self, type_infos):
        vendor = self.ModulesLibrary.get(ExtractHexDecValue(type_infos["vendor"]), None)
        if vendor is not None:
            for group_name, group in vendor["groups"].iteritems():
                for device_type, device in group["devices"]:
                    product_code = ExtractHexDecValue(device.getType().getProductCode())
                    revision_number = ExtractHexDecValue(device.getType().getRevisionNo())
                    if (product_code == ExtractHexDecValue(type_infos["product_code"]) and
                        revision_number == ExtractHexDecValue(type_infos["revision_number"])):
                        return device
        return None

            
