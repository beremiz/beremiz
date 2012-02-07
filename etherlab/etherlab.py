import os, shutil
import cPickle
from xml.dom import minidom

import wx

from xmlclass import *
from PLCControler import UndoBuffer, LOCATION_PLUGIN, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY
from ConfigEditor import ConfigEditor, ETHERCAT_VENDOR, ETHERCAT_GROUP, ETHERCAT_DEVICE

TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", 
    "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L"}

DATATYPECONVERSION = {"BOOL" : "BIT", "SINT" : "S8", "INT" : "S16", "DINT" : "S32", "LINT" : "S64",
    "USINT" : "U8", "UINT" : "U16", "UDINT" : "U32", "ULINT" : "U64", 
    "BYTE" : "U8", "WORD" : "U16", "DWORD" : "U32", "LWORD" : "U64"}

VARCLASSCONVERSION = {"ro": LOCATION_VAR_INPUT, "wo": LOCATION_VAR_OUTPUT, "rw": LOCATION_VAR_MEMORY}

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
    
cls = EtherCATConfigClasses.get("Slave_Info", None)
if cls:

    def getSlavePosition(self):
        return self.getPhysAddr(), self.getAutoIncAddr()
    setattr(cls, "getSlavePosition", getSlavePosition)

    def setSlavePosition(self, alias, pos):
        self.setPhysAddr(alias)
        self.setAutoIncAddr(pos)
    setattr(cls, "setSlavePosition", setSlavePosition)

class _EthercatPlug:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="EtherlabNode">
        <xsd:complexType>
          <xsd:attribute name="MasterNumber" type="xsd:integer" use="optional" default="0"/>
          <xsd:attribute name="ConfigurePDOs" type="xsd:boolean" use="optional" default="true"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    EditorType = ConfigEditor
    
    def __init__(self):
        filepath = self.ConfigFileName()
        
        self.Config = EtherCATConfigClasses["EtherCATConfig"]()
        if os.path.isfile(filepath):
            xmlfile = open(filepath, 'r')
            tree = minidom.parse(xmlfile)
            xmlfile.close()
            
            for child in tree.childNodes:
                if child.nodeType == tree.ELEMENT_NODE and child.nodeName == "EtherCATConfig":
                    self.Config.loadXMLTree(child, ["xmlns:xsi", "xsi:noNamespaceSchemaLocation"])
                    self.CreateConfigBuffer(True)
        else:
            self.CreateConfigBuffer(False)
            self.OnPlugSave()

    def ExtractHexDecValue(self, value):
        return ExtractHexDecValue(value)

    def GetSizeOfType(self, type):
        return TYPECONVERSION.get(self.GetPlugRoot().GetBaseType(type), None)

    def ConfigFileName(self):
        return os.path.join(self.PlugPath(), "config.xml")

    def GetSlaves(self):
        slaves = []
        for slave in self.Config.getConfig().getSlave():
            slaves.append(slave.getInfo().getSlavePosition())
        slaves.sort()
        return slaves

    def GetSlave(self, slave_pos):
        for slave in self.Config.getConfig().getSlave():
            slave_info = slave.getInfo()
            if slave_info.getSlavePosition() == slave_pos:
                return slave
        return None

    def AddSlave(self):
        slaves = self.GetSlaves()
        if len(slaves) > 0:
            new_pos = (slaves[-1][0] + 1, 0)
        else:
            new_pos = (0, 0)
        slave = EtherCATConfigClasses["Config_Slave"]()
        slave_infos = slave.getInfo()
        slave_infos.setName("undefined")
        slave_infos.setSlavePosition(new_pos[0], new_pos[1])
        self.Config.getConfig().appendSlave(slave)
        self.BufferConfig()
        return new_pos
    
    def RemoveSlave(self, slave_pos):
        config = self.Config.getConfig()
        for idx, slave in enumerate(config.getSlave()):
            slave_infos = slave.getInfo()
            if slave_infos.getSlavePosition() == slave_pos:
                config.removeSlave(idx)
                self.BufferConfig()
                return True
        return False
    
    def SetSlavePos(self, slave_pos, alias=None, position=None):
        slave = self.GetSlave(slave_pos)
        if slave is not None:
            slave_info = slave.getInfo()
            new_pos = slave_pos
            if alias is not None:
                new_pos = (alias, new_pos[1])
            if position is not None:
                new_pos = (new_pos[0], position)
            if self.GetSlave(new_pos) is not None:
                return _("Slave with position \"%d:%d\" already exists!" % new_pos)
            slave_info.setSlavePosition(*new_pos)
            self.BufferConfig()
        return None
    
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
        return None
    
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
                infos.update({"physics": device.getPhysics(),
                              "sync_managers": device.GetSyncManagers(),
                              "entries": [entry[1] for entry in entries_list]})
                return infos
        return None
    
    def GetModuleInfos(self, type_infos):
        return self.PlugParent.GetModuleInfos(type_infos)
    
    def GetSlaveTypesLibrary(self):
        return self.PlugParent.GetModulesLibrary()
    
    def GetVariableLocationTree(self):
        '''See PlugTemplate.GetVariableLocationTree() for a description.'''

        current_location = self.GetCurrentLocation()
        
        groups = []
        for slave_pos in self.GetSlaves():
            
            slave = self.GetSlave(slave_pos)
            if slave is not None:
                type_infos = slave.getType()
                
                device = self.GetModuleInfos(type_infos)
                if device is not None:
                    vars = []
                    
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
                            var_class = VARCLASSCONVERSION.get(entry["Access"], LOCATION_VAR_MEMORY)
                            if var_class == LOCATION_VAR_INPUT:
                                var_dir = "%I"
                            else:
                                var_dir = "%Q"    
                            
                            vars.append({"name": "0x%4.4x-0x%2.2x: %s" % (index, subindex, entry["Name"]),
                                         "type": var_class,
                                         "size": var_size,
                                         "IEC_type": entry["Type"],
                                         "var_name": "%s_%4.4x_%2.2x" % (type_infos["device_type"], index, subindex),
                                         "location": "%s%s%s"%(var_dir, var_size, ".".join(map(str, current_location + 
                                                                                                    slave_pos + 
                                                                                                    (index, subindex)))),
                                         "description": "",
                                         "children": []})
                    
                    groups.append({"name": "%s (%d,%d)" % ((type_infos["device_type"],) + slave_pos),
                                   "type": LOCATION_GROUP,
                                   "location": ".".join(map(str, current_location + slave_pos)) + ".x",
                                   "children": vars})
                
        return  {"name": self.BaseParams.getName(),
                 "type": LOCATION_PLUGIN,
                 "location": self.GetFullIEC_Channel(),
                 "children": groups}
    
    PluginMethods = [
        {"bitmap" : os.path.join("images", "EditCfile"),
         "name" : _("Edit Config"), 
         "tooltip" : _("Edit Config"),
         "method" : "_OpenView"},
    ]

    def PlugTestModified(self):
        return self.ChangesToSave or not self.ConfigIsSaved()    

    def OnPlugSave(self):
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

    def PlugGenerate_C(self, buildpath, locations):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
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
        # define a unique name for the generated C file
        location_str = "_".join(map(lambda x:str(x), current_location))
        
        Gen_Ethercatfile_path = os.path.join(buildpath, "ethercat_%s.c"%location_str)
        
        file_generator = _EthercatCFileGenerator(self, Gen_Ethercatfile_path)
        
        for location in locations:
            loc = location["LOC"][len(current_location):]
            file_generator.DeclareVariable(loc[:2], loc[2], loc[3], location["IEC_TYPE"], location["DIR"], location["NAME"])
        
        file_generator.GenerateCFile()
        
        return [(Gen_Ethercatfile_path, '"-I%s"'%os.path.abspath(self.GetPlugRoot().GetIECLibPath()))], "-lethercat -lrtdm", True

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

def ConfigureVariable(entry_infos, str_completion):
    data_type = DATATYPECONVERSION.get(entry_infos["var_type"], None)
    if data_type is None:
        raise ValueError, _("Type of location \"%s\" not yet supported!") % entry_infos["var_name"]
    
    str_completion["located_variables_declaration"].extend(
        ["IEC_%(var_type)s beremiz%(var_name)s;" % entry_infos,
         "IEC_%(var_type)s *%(var_name)s = &beremiz%(var_name)s;" % entry_infos])
    
    if data_type == "BIT":
        str_completion["used_pdo_entry_offset_variables_declaration"].extend(
            ["static unsigned int slave%(slave)d_%(index).4x_%(subindex).2x;" % entry_infos,
             "static unsigned int slave%(slave)d_%(index).4x_%(subindex).2x_bit;" % entry_infos])
        
        str_completion["used_pdo_entry_configuration"].append(
             ("    {%(alias)d, %(position)d, 0x%(vendor).8x, 0x%(product_code).8x, " + 
              "0x%(index).4x, %(subindex)d, &slave%(slave)d_%(index).4x_%(subindex).2x, " + 
              "&slave%(slave)d_%(index).4x_%(subindex).2x_bit},") % entry_infos)
        
        if entry_infos["dir"] == "I":
            str_completion["retrieve_variables"].append(
              ("    beremiz%(name)s = EC_READ_BIT(domain1_pd + slave%(slave)d_%(index).4x_%(subindex).2x, " + 
               "slave%(slave)d_%(index).4x_%(subindex).2x_bit);") % entry_infos)
        elif entry_infos["dir"] == "Q":
            str_completion["publish_variables"].append(
              ("    EC_WRITE_BIT(domain1_pd + slave%(slave)d_%(index).4x_%(subindex).2x, " + 
               "slave%(slave)d_%(index).4x_%(subindex).2x_bit, beremiz%(var_name)s);") % entry_infos)
    
    else:
        entry_infos["data_type"] = data_type
        
        str_completion["used_pdo_entry_offset_variables_declaration"].append(
            "static unsigned int slave%(slave)d_%(index).4x_%(subindex).2x;" % entry_infos)
        
        str_completion["used_pdo_entry_configuration"].append(
            ("    {%(alias)d, %(position)d, 0x%(vendor).8x, 0x%(product_code).8x, 0x%(index).4x, " + 
             "%(subindex)d, &slave%(slave)d_%(index).4x_%(subindex).2x},") % entry_infos)
        
        if entry_infos["dir"] == "I":
            str_completion["retrieve_variables"].append(
                ("    beremiz%(var_name)s = EC_READ_%(data_type)s(domain1_pd + " + 
                 "slave%(slave)d_%(index).4x_%(subindex).2x);") % entry_infos)
        elif entry_infos["dir"] == "Q":
            str_completion["publish_variables"].append(
                ("    EC_WRITE_%(data_type)s(domain1_pd + slave%(slave)d_%(index).4x_%(subindex).2x, " + 
                 "beremiz%(var_name)s);") % entry_infos)
        

class _EthercatCFileGenerator:
    
    def __init__(self, controler, filepath):
        self.Controler = controler
        self.FilePath = filepath
        
        self.UsedVariables = {}
        
    def __del__(self):
        self.Controler = None

    def DeclareVariable(self, slave_identifier, index, subindex, iec_type, dir, name):
        slave_variables = self.UsedVariables.setdefault(slave_identifier, {})
        
        entry_infos = slave_variables.get((index, subindex), None)
        if entry_infos is None:
            slave_variables[(index, subindex)] = {
                "infos": (iec_type, dir, name),
                "mapped": False}
        elif entry_infos["infos"] != (iec_type, dir, name):
            raise ValueError, _("Definition conflict for location \"%s\"") % name 
        
    def GenerateCFile(self):
        
        current_location = self.Controler.GetCurrentLocation()
        # define a unique name for the generated C file
        location_str = "_".join(map(lambda x:str(x), current_location))
        
        plc_etherlab_filepath = os.path.join(os.path.split(__file__)[0], "plc_etherlab.c")
        plc_etherlab_file = open(plc_etherlab_filepath, 'r')
        plc_etherlab_code = plc_etherlab_file.read()
        plc_etherlab_file.close()
        
        str_completion = {
            "location": location_str,
            "configure_pdos": int(self.Controler.EtherlabNode.getConfigurePDOs()),
            "master_number": self.Controler.EtherlabNode.getMasterNumber(),
            "located_variables_declaration": [],
            "used_pdo_entry_offset_variables_declaration": [],
            "used_pdo_entry_configuration": [],
            "pdos_configuration_declaration": "",
            "slaves_declaration": "",
            "slaves_configuration": "",
            "retrieve_variables": [],
            "publish_variables": [],
        }
        
        for slave_entries in self.UsedVariables.itervalues():
            for entry_infos in slave_entries.itervalues():
                entry_infos["mapped"] = False
        
        for slave_idx, slave_pos in enumerate(self.Controler.GetSlaves()):
            
            slave = self.Controler.GetSlave(slave_pos)
            if slave is not None:
                type_infos = slave.getType()
                
                device = self.Controler.GetModuleInfos(type_infos)
                if device is not None:
                    slave_variables = self.UsedVariables.get(slave_pos, {})
                    device_entries = device.GetEntriesList()
                    
                    if len(device.getTxPdo() + device.getRxPdo()) > 0 or len(slave_variables) > 0:
                        
                        for element in ["vendor", "product_code", "revision_number"]:
                            type_infos[element] = ExtractHexDecValue(type_infos[element])
                        type_infos.update(dict(zip(["slave", "alias", "position"], (slave_idx,) + slave_pos)))
                    
                        str_completion["slaves_declaration"] += "static ec_slave_config_t *slave%(slave)d = NULL;\n" % type_infos
                        str_completion["slaves_configuration"] += SLAVE_CONFIGURATION_TEMPLATE % type_infos
    
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
                        for only_mandatory in [True, False]:
                            for pdo, pdo_type in ([(pdo, "Inputs") for pdo in device.getTxPdo()] +
                                                  [(pdo, "Outputs") for pdo in device.getRxPdo()]):
                                entries = pdo.getEntry()
                                
                                pdo_needed = pdo.getMandatory()
                                if only_mandatory != pdo_needed:
                                    continue
                                
                                pdo_index = ExtractHexDecValue(pdo.getIndex().getcontent())
                                pdos_index.append(pdo_index)
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
                                        
                                        if entry_infos["var_type"] != entry.getDataType().getcontent():
                                            raise ValueError, _("Wrong type for location \"%s\"!") % entry_infos["var_name"]
                                        
                                        if (entry_infos["dir"] == "I" and pdo_type != "Inputs" or 
                                            entry_infos["dir"] == "Q" and pdo_type != "Outputs"):
                                            raise ValueError, _("Wrong direction for location \"%s\"!") % entry_infos["var_name"]
                                        
                                        ConfigureVariable(entry_infos, str_completion)
                                
                                if pdo_needed:
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
                                
                                entry_infos.update(dict(zip(["var_type", "dir", "var_name"], entry_declaration["infos"])))
                                entry_declaration["mapped"] = True
                                
                                if entry_infos["var_type"] != entry["Type"]:
                                    raise ValueError, _("Wrong type for location \"%s\"!") % entry_infos["var_name"]
                                
                                if entry_infos["dir"] == "I" and entry["Access"] in ["ro", "rw"]:
                                    pdo_type = "Inputs"
                                elif entry_infos["dir"] == "Q" and entry["Access"] in ["wo", "rw"]:
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
                            pdos_infos["pdos_sync_infos"].append(
                                ("    {%(index)d, %(sync_manager_type)s, %(pdos_number)d, " + 
                                 "slave_%(slave)d_pdos + %(offset)d, %(watchdog)s},") % sync_manager_infos)
                            pdo_offset += sync_manager_infos["pdos_number"]
                        
                        for element in ["pdos_entries_infos", "pdos_infos", "pdos_sync_infos"]:
                            pdos_infos[element] = "\n".join(pdos_infos[element])
                        
                        str_completion["pdos_configuration_declaration"] += SLAVE_PDOS_CONFIGURATION_DECLARATION % pdos_infos
        
        for element in ["used_pdo_entry_offset_variables_declaration", 
                        "used_pdo_entry_configuration", 
                        "located_variables_declaration", 
                        "retrieve_variables", 
                        "publish_variables"]:
            str_completion[element] = "\n".join(str_completion[element])
        
        etherlabfile = open(self.FilePath,'w')
        etherlabfile.write(plc_etherlab_code % str_completion)
        etherlabfile.close()

#--------------------------------------------------
#                 Ethercat Plugin
#--------------------------------------------------

EtherCATInfoClasses = GenerateClassesFromXSD(os.path.join(os.path.dirname(__file__), "EtherCATInfo.xsd")) 

cls = EtherCATInfoClasses["EtherCATInfo.xsd"].get("DeviceType", None)
if cls:
    cls.DataTypes = None
    
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
    
    def GetEntriesList(self):
        if self.DataTypes is None:
            self.ExtractDataTypes()
        
        entries = {}
        
        for dictionary in self.GetProfileDictionaries():
            
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
                        subitem_flags = subitem.getFlags()
                        if subitem_flags is not None:
                            access = subitem_flags.getAccess()
                            if access is not None:
                                subitem_access = access.getcontent()
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
                            "PDO index": "", 
                            "PDO name": "", 
                            "PDO type": ""}
                else:
                    entry_access = ""
                    entry_flags = object.getFlags()
                    if entry_flags is not None:
                        access = entry_flags.getAccess()
                        if access is not None:
                            entry_access = access.getcontent()
                    entries[(index, 0)] = {
                         "Index": entry_index,
                         "SubIndex": "0",
                         "Name": entry_name,
                         "Type": entry_type,
                         "BitSize": object.getBitSize(),
                         "Access": entry_access,
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
                else:
                    access = "wo"
                entries[(index, subindex)] = {
                    "Index": entry_index,
                    "SubIndex": entry_subindex,
                    "Name": ExtractName(pdo_entry.getName()),
                    "Type": entry_type.getcontent(),
                    "Access": access,
                    "PDO index": pdo_index, 
                    "PDO name": pdo_name, 
                    "PDO type": pdo_type}

class RootClass:
    
    PlugChildsTypes = [("EthercatNode",_EthercatPlug,"Ethercat Master")]
    
    def __init__(self):
        self.LoadModulesLibrary()
    
    def GetModulesLibraryPath(self):
        library_path = os.path.join(self.PlugPath(), "modules")
        if not os.path.exists(library_path):
            os.mkdir(library_path)
        return library_path
    
    def _ImportModuleLibrary(self):
        dialog = wx.FileDialog(self.GetPlugRoot().AppFrame, _("Choose an XML file"), os.getcwd(), "",  _("XML files (*.xml)|*.xml|All files|*.*"), wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            filepath = dialog.GetPath()
            if os.path.isfile(filepath):
                shutil.copy(filepath, self.GetModulesLibraryPath())
                self.LoadModulesLibrary()
            else:
                self.GetPlugRoot().logger.write_error(_("No such XML file: %s\n") % filepath)
        dialog.Destroy()  
    
    PluginMethods = [
        {"bitmap" : os.path.join("images", "ImportDEF"),
         "name" : _("Import module library"), 
         "tooltip" : _("Import module library"),
         "method" : "_ImportModuleLibrary"},
    ]
    
    def PlugGenerate_C(self, buildpath, locations):
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
                        modules_infos.loadXMLTree(child, ["xmlns:xsi", "xsi:noNamespaceSchemaLocation"])
                
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
    
    def GetModulesLibrary(self):
        library = []
        children_dict = {}
        for vendor_id, vendor in self.ModulesLibrary.iteritems():
            groups = []
            library.append({"name": vendor["name"],
                            "type": ETHERCAT_VENDOR,
                            "children": groups})
            for group_type, group in vendor["groups"].iteritems():
                group_infos = {"name": group["name"],
                               "order": group["order"],
                               "type": ETHERCAT_GROUP,
                               "children": children_dict.setdefault(group_type, [])}
                if group["parent"] is not None:
                    parent_children = children_dict.setdefault(group["parent"], [])
                    parent_children.append(group_infos)
                else:
                    groups.append(group_infos)
                device_dict = {}
                for device_type, device in group["devices"]:
                    device_infos = {"name": ExtractName(device.getName()),
                                    "type": ETHERCAT_DEVICE,
                                    "infos": {"device_type": device_type,
                                              "vendor": vendor_id,
                                              "product_code": device.getType().getProductCode(),
                                              "revision_number": device.getType().getRevisionNo()}}
                    group_infos["children"].append(device_infos)
                    device_type_occurrences = device_dict.setdefault(device_type, [])
                    device_type_occurrences.append(device_infos)
                for device_type_occurrences in device_dict.itervalues():
                    if len(device_type_occurrences) > 1:
                        for occurrence in device_type_occurrences:
                            occurrence["name"] += _(" (rev. %s)") % occurrence["infos"]["revision_number"]
        library.sort(lambda x, y: cmp(x["name"], y["name"]))
        return library
    
    def GetModuleInfos(self, type_infos):
        vendor = self.ModulesLibrary.get(ExtractHexDecValue(type_infos["vendor"]), None)
        if vendor is not None:
            for group_name, group in vendor["groups"].iteritems():
                for device_type, device in group["devices"]:
                    product_code = ExtractHexDecValue(device.getType().getProductCode())
                    revision_number = ExtractHexDecValue(device.getType().getRevisionNo())
                    if (device_type == type_infos["device_type"] and
                        product_code == ExtractHexDecValue(type_infos["product_code"]) and
                        revision_number == ExtractHexDecValue(type_infos["revision_number"])):
                        return device
        return None
    
