#!/usr/bin/env python
# -*- coding: utf-8 -*-


# This file is part of Beremiz
#
# Copyright (C) 2013: Real-Time & Embedded Systems (RTES) Lab. University of Seoul, Korea
#
# See COPYING file for copyrights details.

from __future__ import absolute_import
from __future__ import division
from builtins import str as text
import codecs
import wx
import re

from etherlab.rpc import CallEtherCAT, DecodeBinary, EncodeBinary, EtherCATError

mailbox_protocols = ["AoE", "EoE", "CoE", "FoE", "SoE", "VoE"]


def ExtractHexDecValue(value):
    """
     convert numerical value in string format into decimal or hex format.
     @param value : hex or decimal data
     @return integer data
    """
    try:
        return int(value)
    except Exception:
        pass
    try:
        return int(value.replace("#", "0"), 16)

    except Exception:
        raise ValueError(_("Invalid value for HexDecValue \"%s\"") % value)


def ExtractName(names, default=None):
    """
     Extract "name" field from XML entries.
     @param names : XML entry
     @default : if it fails to extract from the designated XML entry, return the default value ("None").
     @return default or the name extracted
    """
    if len(names) == 1:
        return names[0].getcontent()
    else:
        for name in names:
            if name.getLcId() == 1033:
                return name.getcontent()
    return default

# --------------------------------------------------
#    Common Method For EtherCAT Management
# --------------------------------------------------
class _CommonSlave(object):

    # ----- Data Structure for ethercat management ----
    SlaveState = ""

    # SDO base data type for Ethercatmaster
    BaseDataTypes = {
            "bool": ["BOOLEAN", "BOOL", "BIT"],
            "uint8": ["BYTE", "USINT", "BIT1", "BIT2", "BIT3", "BIT4", "BIT5", "BIT6",
                      "BIT7", "BIT8", "BITARR8", "UNSIGNED8"],
            "uint16": ["BITARR16", "UNSIGNED16", "UINT"],
            "uint32": ["BITARR32", "UNSIGNED24", "UINT24", "UNSIGNED32", "UDINT"],
            "uint64": ["UNSINED40", "UINT40", "UNSIGNED48", "UINT48", "UNSIGNED56", 
                       "UINT56", "UNSIGNED64", "ULINT"],
            "int8": ["INTEGER8", "SINT"],
            "int16": ["INTEGER16", "INT"],
            "int32": ["INTEGER24", "INT24", "INTEGER32", "DINT"],
            "int64": ["INTEGER40", "INT40", "INTEGER48", "INT48", "INTEGER56", "INT56",
                      "INTEGER64", "LINT"],
            "float": ["REAL", "REAL32"],
            "double": ["LREAL", "REAL64"],
            "string": ["VISUBLE_STRING", "STRING(n)"],
            "octet_string": ["OCTET_STRING"],
            "unicode_string": ["UNICODE_STRING"]
            }
    
    # category of SDO data
    DatatypeDescription, CommunicationObject, ManufacturerSpecific, \
        ProfileSpecific, Reserved, AllSDOData = range(6)

    # SDO data informations: index, sub-index, type, bit size, category-name 
    SDOVariables = []
    SDOSubEntryData = []
    
    # defalut value of SDO data in XML
    # Not Used
    DefaultValueDic = {}
    
    # Flags for checking "write" permission of OD entries 
    CheckPREOP = False
    CheckSAFEOP = False
    CheckOP = False

    # Save PDO Data
    TxPDOInfo = []
    TxPDOCategory = []
    RxPDOInfo = []
    RxPDOCategory = []

    # Save EEPROM Data
    SiiData = ""

    # Save Register Data
    RegData = ""
    CrtRegSpec = {"ESCType": "",
                  "FMMUNumber": "",
                  "SMNumber": "",
                  "PDIType": ""}

    def __init__(self, controler):
        """
        Constructor
        @param controler: _EthercatSlaveCTN class in EthercatSlave.py
        """
        self.Controler = controler
        self.HexDecode = codecs.getdecoder("hex_codec")
        self.ClearSDODataSet()

    # -------------------------------------------------------------------------------
    #                        Runtime EtherCAT service
    # -------------------------------------------------------------------------------
    def EtherCATCall(self, command, *args, **kwargs):
        """
        Run an EtherCAT command on the runtime, see ETHERCAT_COMMANDS in
        etherlab/runtime_etherlab.py.
        @param command : name of the command to run
        @param args : arguments of the command
        @param default : value returned when the runtime cannot be reached
        @return result of the command
        """
        default = kwargs.pop("default", None)
        try:
            return CallEtherCAT(self.Controler.GetCTRoot()._connector,
                                command, *args)
        except EtherCATError as e:
            self.Controler.GetCTRoot().logger.write_warning(
                _("EtherCAT %s failed: %s\n") % (command, str(e)))
            return default

    # -------------------------------------------------------------------------------
    #                        Used Master State
    # -------------------------------------------------------------------------------
    def GetMasterState(self):
        """
        Execute "ethercat master" command and parse the execution result
        @return MasterState
        """

        # exectute "ethercat master" command
        return_val = self.EtherCATCall("master_state", default="")
        master_state = {}
        # parse the reslut
        for each_line in return_val.splitlines():
            if len(each_line) > 0:
                chunks = each_line.strip().split(':', 1)
                key = chunks[0]
                value = []
                if len(chunks) > 1:
                    value = chunks[1].split()
                if '(attached)' in value:
                    value.remove('(attached)')
                master_state[key] = value

        return master_state

    # -------------------------------------------------------------------------------
    #                        Used Slave State
    # -------------------------------------------------------------------------------
    def AliasToPosition(self, alias):
        """
        Translate an EtherCAT alias into the real ring position, using the
        "ethercat slaves" command.
        @param alias : alias of the slave to look for
        @return position : ring position of the slave, None when not found
        """
        output = self.EtherCATCall("slaves", default="")

        for line in output.splitlines():
            # line format : 0  3:0  PREOP  +  CL3-E57H
            match = re.match(r"(\d+)\s+(\d+):(\d+)", line)
            if match:
                position = int(match.group(1))
                found_alias = int(match.group(2))
                if found_alias == alias:
                    return position

        self.Controler.GetCTRoot().logger.write_warning(
            _("No EtherCAT slave found for alias %d\n") % alias)
        return None

    def RequestSlaveState(self, command):
        """
        Set slave state to the specified one using "ethercat states -p %d %s" command.
        Command example : "ethercat states -p 0 PREOP" (target slave position and target state are given.)
        @param command : target slave state
        @return state : slave list as reported by "ethercat slaves"
        """
        alias = self.Controler.GetSlavePos()
        pos = self.AliasToPosition(alias)
        if pos is None:
            return

        self.EtherCATCall("slave_state", pos, command)
        return self.EtherCATCall("slaves", default="")

    def GetSlaveStateFromSlave(self):
        """
        Get slave information using "ethercat slaves" command and store the information into internal data structure
        (self.SlaveState) for "Slave State"
        return_val example : 0  0:0  PREOP  +  EL9800 (V4.30) (PIC24, SPI, ET1100)
        """
        return_val = self.EtherCATCall("slaves", default="")
        self.SlaveState = return_val
        return return_val

    # -------------------------------------------------------------------------------
    #                        Used SDO Management
    # -------------------------------------------------------------------------------
    def SDODownload(self, data_type, idx, sub_idx, value):
        """
        Set an SDO object value to user-specified value using "ethercat download" command.
        Command example : "ethercat download --type int32 -p 0 0x8020 0x12 0x00000000"
        @param data_type : data type of SDO entry
        @param idx : index of the SDO entry
        @param sub_idx : subindex of the SDO entry
        @param value : value of SDO entry
        """ 
        valid_type = self.GetValidDataType(data_type)
        return self.EtherCATCall("sdo_download", self.Controler.GetSlavePos(),
                                 valid_type, idx, sub_idx, value, default="")
    
    def BackupSDODataSet(self):
        """
        Back-up current SDO entry information to restore the SDO data
        in case that the user cancels SDO update operation.
        """
        self.BackupDatatypeDescription = self.SaveDatatypeDescription
        self.BackupCommunicationObject = self.SaveCommunicationObject
        self.BackupManufacturerSpecific = self.SaveManufacturerSpecific
        self.BackupProfileSpecific = self.SaveProfileSpecific
        self.BackupReserved = self.SaveReserved
        self.BackupAllSDOData = self.SaveAllSDOData

    def ClearSDODataSet(self):
        """
        Clear the specified SDO entry information.
        """
        self.SaveDatatypeDescription = []
        self.SaveCommunicationObject = []
        self.SaveManufacturerSpecific = []
        self.SaveProfileSpecific = []
        self.SaveReserved = []
        self.SaveAllSDOData = []

    def GetAllSDOValuesFromSlave(self):
        """
        Get SDO values of All SDO entries.
        @return return_val: one "ethercat upload" output line per entry
        """
        entry_infos = []
        alldata_idx = len(self.SDOVariables)
        counter = 0
        for category in self.SDOVariables:
            counter +=1
            # for avoid redundant repetition
            if counter == alldata_idx:
                continue

            for entry in category:
                valid_type = self.GetValidDataType(entry["datatype"])
                entry_infos.append(
                    [valid_type, str(entry["idx"]), str(entry["subIdx"])])

        return self.EtherCATCall("sdo_upload", self.Controler.GetSlavePos(),
                                 entry_infos, default=[])

    def GetSDOValuesFromSlave(self, entries_info):
        """
        Get SDO values of some SDO entries.
        @param entries_info: dictionary of SDO entries that is wanted to know the value. 
        @return return_val: one "ethercat upload" output line per entry
        """
        entry_infos = []

        for (idx, subIdx), entry in sorted(entries_info.items()):
            valid_type = self.GetValidDataType(entry["datatype"])
            entry_infos.append([valid_type, str(idx), str(subIdx)])

        return self.EtherCATCall("sdo_upload", self.Controler.GetSlavePos(),
                                 entry_infos, default=[])

    def ExtractObjects(self):
        """
        Extract object type items from imported ESI xml.
        And they are stuctured as dictionary.
        @return objects: dictionary of objects
        """
        objects = {}

        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())
        type_infos = slave.getType()
        device, alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)
         
        if device is None:
            return objects

        # ESI profile dictionaries are not parsed any more, the objects are
        # collected from the PDO entries of the device instead.
        if hasattr(device, "getTxPdo"):

            for pdo in device.getTxPdo():
                for entry in pdo.getEntry():
                    try:
                        idx = ExtractHexDecValue(entry.getIndex().getcontent())
                        objects[idx] = entry
                    except:
                        pass

            for pdo in device.getRxPdo():
                for entry in pdo.getEntry():
                    try:
                        idx = ExtractHexDecValue(entry.getIndex().getcontent())
                        objects[idx] = entry
                    except:
                        pass
        
        return objects

    def ExtractAllDataTypes(self):
        """
        Extract all data types from imported ESI xml.
        @return dataTypes: dictionary of datatypes 
        """
        dataTypes = {}
        
        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())
        type_infos = slave.getType()
        device, alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)

        if device is None:
            return dataTypes

        # take the data types straight from the device, when it declares some
        datatypes_container = getattr(device, "getDataTypes", None)

        if datatypes_container is None:
            return dataTypes

        datatypes = datatypes_container()

        if datatypes is None:
            return dataTypes

        for datatype in datatypes.getDataType():
            dataTypes[datatype.getName()] = datatype
        return dataTypes
    
    def IsBaseDataType(self, datatype):
        """
        Check if the datatype is a base data type.
        @return baseTypeFlag: true if datatype is a base data type, unless false
        """
        baseTypeFlag = False
        for baseDataTypeList in self.BaseDataTypes.values():
            if datatype in baseDataTypeList:
                baseTypeFlag = True
                break
        return baseTypeFlag

    def GetBaseDataType(self, datatype):
        """
        Get a base data type corresponding the datatype.
        @param datatype: Some data type (string format)
        @return base data type
        """
        if self.IsBaseDataType(datatype):
            return datatype
        elif not datatype.find("STRING") == -1:
            return datatype
        else:
            datatypes = self.ExtractAllDataTypes()
            base_datatype = datatypes[datatype].getBaseType()
            return self.GetBaseDataType(base_datatype)

    def GetValidDataType(self, datatype):
        """
        Convert the datatype into a data type that is possible to download/upload 
        in etherlab master stack.
        @param datatype: Some data type (string format)
        @return base_type: vaild data type
        """
        base_type = self.GetBaseDataType(datatype)

        if re.match("STRING\([0-9]*\)", datatype) is not None:
            return "string"
        else:
            for key, value in self.BaseDataTypes.items():
                if base_type in value:
                    return key
        return base_type 

    # Not Used 
    def GetAllEntriesList(self):
        """
        Get All entries information that includes index, sub-index, name,
        type, bit size, PDO mapping, and default value.
        @return self.entries: dictionary of entry
        """
        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())
        type_infos = slave.getType()
        device, alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)
        self.entries = device.GetEntriesList()
        datatypes = self.ExtractAllDataTypes()
        objects = self.ExtractObjects()
        entries_list = sorted(self.entries.items())

        # append sub entries
        for (index, subidx), entry in entries_list:
            # entry_* is string type
            entry_type = entry["Type"]
            entry_index = entry["Index"]
            
            try:
                object_info = objects[index].getInfo()
            except:
                continue
            
            if object_info is not None:
                obj_content = object_info.getcontent()
            
            typeinfo = datatypes.get(entry_type, None)
            bitsize = typeinfo.getBitSize()
            type_content = typeinfo.getcontent()
           
            # ArrayInfo type
            if type_content is not None and type_content["name"] == "ArrayInfo":
                for arrayinfo in type_content["value"]:
                    element_num = arrayinfo.getElements()
                    first_subidx = arrayinfo.getLBound()
                    for offset in range(element_num):
                        new_subidx = int(first_subidx) + offset
                        entry_subidx = hex(new_subidx)
                        if obj_content["value"][new_subidx]["name"] == "SubItem":
                            subitem = obj_content["value"][new_subidx]["value"]
                            subname = subitem[new_subidx].getName()
                        if subname is not None:
                            entry_name = "%s - %s" % \
                                    (ExtractName(objects[index].getName()), subname)
                        else:
                            entry_name = ExtractName(objects[index].getName()) 
                        self.entries[(index, new_subidx)] = {
                                "Index": entry_index,
                                "SubIndex": entry_subidx,
                                "Name": entry_name,
                                "Type": typeinfo.getBaseType(),
                                "BitSize": str(bitsize/element_num),
                                "Access": entry["Access"],
                                "PDOMapping": entry["PDOMapping"]}
                        try:
                            value_info = subitem[new_subidx].getInfo().getcontent()\
                                                            ["value"][0]["value"][0]
                            self.AppendDefaultValue(index, new_subidx, value_info)
                        except:
                            pass

                try:
                    value_info = subitem[subidx].getInfo().getcontent()\
                                                            ["value"][0]["value"][0]
                    self.AppendDefaultValue(index, subidx, value_info)
                except:
                    pass
            
            # EnumInfo type
            elif type_content is not None and type_content["name"] == "EnumInfo":
                self.entries[(index, subidx)]["EnumInfo"] = {}
                
                for enuminfo in type_content["value"]:
                    text = enuminfo.getText()
                    enum = enuminfo.getEnum()
                    self.entries[(index, subidx)]["EnumInfo"][str(enum)] = text

                self.entries[(index, subidx)]["DefaultValue"] = "0x00" 
            
            # another types
            else:
                if subidx == 0x00:
                    tmp_subidx = 0x00

                try:
                    if obj_content["value"][tmp_subidx]["name"] == "SubItem":
                        sub_name = entry["Name"].split(" - ")[1]
                        for num in range(len(obj_content["value"])):
                            if sub_name == \
                                    obj_content["value"][num]["value"][num].getName():
                                subitem_content = obj_content["value"][tmp_subidx]\
                                                             ["value"][tmp_subidx]
                                value_info = subitem_content.getInfo().getcontent()\
                                                             ["value"][0]["value"][0]
                                tmp_subidx += 1
                                break
                            else:
                                value_info = None
                        
                    else:
                        value_info = \
                                obj_content["value"][tmp_subidx]["value"][tmp_subidx]

                    self.AppendDefaultValue(index, subidx, value_info)

                except:
                    pass

        return self.entries
                   
    # Not Used  
    def AppendDefaultValue(self, index, subidx, value_info=None):
        """
        Get the default value from the ESI xml
        @param index: entry index
        @param subidx: entry sub index
        @param value_info: dictionary of infomation about default value

        """
        # there is not default value.
        if value_info == None:
            return

        raw_value = value_info["value"]
        
        # default value is hex binary type.
        if value_info["name"]  == "DefaultData":
            raw_value_bit = list(hex(raw_value).split("0x")[1])
             
            datatype = self.GetValidDataType(self.entries[(index, subidx)]["Type"])
            if datatype == "string" or datatype == "octet_string":

                if "L" in raw_value_bit:
                    raw_value_bit.remove("L")

                default_value = "".join(raw_value_bit).decode("hex")
           
            elif datatype == "unicode_string":
                default_value = "".join(raw_value_bit).decode("hex").\
                                                           decode("utf-8")
            
            else:   
                bit_num = len(raw_value_bit)
                # padding 
                if not bit_num%2 == 0:
                    raw_value_bit.insert(0, "0")

                default_value_bit = []
            
                # little endian -> big endian
                for num in range(bit_num):
                    if num%2 == 0:
                        default_value_bit.insert(0, raw_value_bit[num])
                        default_value_bit.insert(1, raw_value_bit[num+1])
                
                default_value = "0x%s" % "".join(default_value_bit)

        # default value is string type.
        # this case is not tested yet.
        elif value_info["name"] == "DefaultString":
            default_value = raw_value

        # default value is Hex or Dec type.
        elif value_info["name"] == "DefaultValue":
            default_value = "0x" + hex(ExtractHexDecValue(raw_value))

        self.entries[(index, subidx)]["DefaultValue"] = default_value

    # -------------------------------------------------------------------------------
    #                        Used PDO Monitoring
    # -------------------------------------------------------------------------------
    def RequestPDOInfo(self):
        """
        Load slave information from RootClass (XML data) and parse the information 
        (calling SlavePDOData() method).
        """
        # Load slave information from ESI XML file (def EthercatMaster.py)
        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())

        type_infos = slave.getType()
        device, _alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)
        # Initialize PDO data set
        self.ClearDataSet()

        # if 'device' object is valid, call SavePDOData() to parse PDO data
        if device is not None:
            self.SavePDOData(device)

    def SavePDOData(self, device):
        """
        Parse PDO data and store the results in TXPDOCategory and RXPDOCategory
        Tx(Rx)PDOCategory : index, name, entry number
        Tx(Rx)Info : entry index, sub index, name, length, type
        @param device : Slave information extracted from ESI XML file
        """
        # Parsing TXPDO entries
        for pdo, _pdo_info in ([(pdo, "Inputs") for pdo in device.getTxPdo()]):
            # Save pdo_index, entry, and name of each entry
            pdo_index = ExtractHexDecValue(pdo.getIndex().getcontent())
            entries = pdo.getEntry()
            pdo_name = ExtractName(pdo.getName())
            excludes = pdo.getExclude()
            exclude_list = []
            Sm = pdo.getSm()

            if excludes :
                for exclude in excludes:
                    exclude_list.append(ExtractHexDecValue(exclude.getcontent()))

            # Initialize entry number count
            count = 0

            # Parse entries
            for entry in entries:
                # Save index and subindex
                index = ExtractHexDecValue(entry.getIndex().getcontent())
                subindex = ExtractHexDecValue(entry.getSubIndex())
                # if entry name exists, save entry data
                if ExtractName(entry.getName()) is not None:
                    entry_infos = {
                        "entry_index": index,
                        "subindex": subindex,
                        "name": ExtractName(entry.getName()),
                        "bitlen": entry.getBitLen()
                    }
                    if entry.getDataType() is not None:
                        entry_infos["type"] = entry.getDataType().getcontent()
                    self.TxPDOInfo.append(entry_infos)
                    count += 1

            categorys = {"pdo_index" : pdo_index, "name" : pdo_name, "sm" : Sm,
                         "number_of_entry" : count, "exclude_list" : exclude_list}  
            self.TxPDOCategory.append(categorys)

        # Parsing RxPDO entries
        for pdo, _pdo_info in ([(rxpdo, "Outputs") for rxpdo in device.getRxPdo()]):
            # Save pdo_index, entry, and name of each entry
            pdo_index = ExtractHexDecValue(pdo.getIndex().getcontent())
            entries = pdo.getEntry()
            pdo_name = ExtractName(pdo.getName())
            excludes = pdo.getExclude()
            exclude_list = []
            Sm = pdo.getSm()

            if excludes :
                for exclude in excludes:
                    exclude_list.append(ExtractHexDecValue(exclude.getcontent()))

            # Initialize entry number count
            count = 0

            # Parse entries
            for entry in entries:
                # Save index and subindex
                index = ExtractHexDecValue(entry.getIndex().getcontent())
                subindex = ExtractHexDecValue(entry.getSubIndex())
                # if entry name exists, save entry data
                if ExtractName(entry.getName()) is not None:
                    entry_infos = {
                        "entry_index": index,
                        "subindex": subindex,
                        "name": ExtractName(entry.getName()),
                        "bitlen": str(entry.getBitLen())
                    }
                    if entry.getDataType() is not None:
                        entry_infos["type"] = entry.getDataType().getcontent()
                    self.RxPDOInfo.append(entry_infos)
                    count += 1

            categorys = {"pdo_index" : pdo_index, "name" : pdo_name, "sm" : Sm,
                         "number_of_entry" : count, "exclude_list" : exclude_list}
            self.RxPDOCategory.append(categorys) 

    def GetTxPDOCategory(self):
        """
        Get TxPDOCategory data structure (Meta informaton of TxPDO).
        TxPDOCategorys : index, name, number of entries
        @return TxPDOCategorys
        """
        return self.TxPDOCategory

    def GetRxPDOCategory(self):
        """
        Get RxPDOCategory data structure (Meta information of RxPDO).
        RxPDOCategorys : index, name, number of entries
        @return RxPDOCategorys
        """
        return self.RxPDOCategory

    def GetTxPDOInfo(self):
        """
        Get TxPDOInfo data structure (Detailed information on TxPDO entries).
        TxPDOInfos : entry index, sub index, name, length, type
        @return TxPDOInfos
        """
        return self.TxPDOInfo

    def GetRxPDOInfo(self):
        """
        Get RxPDOInfo data structure (Detailed information on RxPDO entries).
        RxPDOInfos : entry index, sub index, name, length, type
        @return RxPDOInfos
        """
        return self.RxPDOInfo

    def ClearDataSet(self):
        """
        Initialize PDO management data structure.
        """
        self.TxPDOInfo = []
        self.TxPDOCategory = []
        self.RxPDOInfo = []
        self.RxPDOCategory = []

    # -------------------------------------------------------------------------------
    #                        Used EEPROM Management
    # -------------------------------------------------------------------------------
    # Base data types in ETG2000; format = {"Name": "BitSize"}
    BaseDataTypeDict = {"BOOL": "01",
                        "SINT": "02",
                        "INT": "03",
                        "DINT": "04",
                        "USINT": "05",
                        "UINT": "06",
                        "UDINT": "07",
                        "REAL": "08",
                        "INT24": "10",
                        "LREAL": "11",
                        "INT40": "12",
                        "INT48": "13",
                        "INT56": "14",
                        "LINT": "15",
                        "UINT24": "16",
                        "UINT40": "18",
                        "UINT48": "19",
                        "UINT56": "1a",
                        "ULINT": "1b",
                        "BITARR8": "2d",
                        "BITARR16": "2e",
                        "BITARR32": "2f",
                        "BIT1": "30",
                        "BIT2": "31",
                        "BIT3": "32",
                        "BIT4": "33",
                        "BIT5": "34",
                        "BIT6": "35",
                        "BIT7": "36",
                        "BIT8": "37"}

    def GetSmartViewInfos(self):
        """
        Parse XML data for "Smart View" of EEPROM contents.
        @return smartview_infos : EEPROM contents dictionary
        """

        smartview_infos = {"eeprom_size": 128,
                           "pdi_type": 0,
                           "device_emulation": "False",
                           "vendor_id": '0x00000000',
                           "product_code": '0x00000000',
                           "revision_no": '0x00000000',
                           "serial_no": '0x00000000',
                           "supported_mailbox": "",
                           "mailbox_bootstrapconf_outstart": '0',
                           "mailbox_bootstrapconf_outlength": '0',
                           "mailbox_bootstrapconf_instart": '0',
                           "mailbox_bootstrapconf_inlength": '0',
                           "mailbox_standardconf_outstart": '0',
                           "mailbox_standardconf_outlength": '0',
                           "mailbox_standardconf_instart": '0',
                           "mailbox_standardconf_inlength": '0'}

        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())
        type_infos = slave.getType()
        device, _alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)

        # 'device' represents current slave device selected by user
        if device is not None:
            for eeprom_element in device.getEeprom().getcontent():
                # get EEPROM size; <Device>-<Eeprom>-<ByteSize>
                if eeprom_element["name"] == "ByteSize":
                    smartview_infos["eeprom_size"] = eeprom_element

                elif eeprom_element["name"] == "ConfigData":
                    configData_data = self.DecimalToHex(eeprom_element)
                    # get PDI type; <Device>-<Eeprom>-<ConfigData> address 0x00
                    smartview_infos["pdi_type"] = int(configData_data[0:2], 16)
                    # get state of device emulation; <Device>-<Eeprom>-<ConfigData> address 0x01
                    if "{:0>8b}".format(int(configData_data[2:4], 16))[7] == '1':
                        smartview_infos["device_emulation"] = "True"

                elif eeprom_element["name"] == "BootStrap":
                    bootstrap_data = "{:0>16x}".format(eeprom_element)
                    # get bootstrap configuration; <Device>-<Eeprom>-<BootStrap>
                    for cfg, iter in [("mailbox_bootstrapconf_outstart", 0),
                                      ("mailbox_bootstrapconf_outlength", 1),
                                      ("mailbox_bootstrapconf_instart", 2),
                                      ("mailbox_bootstrapconf_inlength", 3)]:
                        smartview_infos[cfg] = str(int(bootstrap_data[4*iter+2:4*(iter+1)]+bootstrap_data[4*iter:4*iter+2], 16))

            # get protocol (profile) types supported by mailbox; <Device>-<Mailbox>
            mb = device.getMailbox()
            if mb is not None:
                for mailbox_protocol in mailbox_protocols:
                    if getattr(mb, "get%s" % mailbox_protocol)() is not None:
                        smartview_infos["supported_mailbox"] += "%s,  " % mailbox_protocol
            smartview_infos["supported_mailbox"] = smartview_infos["supported_mailbox"].strip(", ")

            # get standard configuration of mailbox; <Device>-<Sm>
            for sm_element in device.getSm():
                if sm_element.getcontent() == "MBoxOut":
                    smartview_infos["mailbox_standardconf_outstart"] = str(ExtractHexDecValue(sm_element.getStartAddress()))
                    smartview_infos["mailbox_standardconf_outlength"] = str(ExtractHexDecValue(sm_element.getDefaultSize()))
                elif sm_element.getcontent() == "MBoxIn":
                    smartview_infos["mailbox_standardconf_instart"] = str(ExtractHexDecValue(sm_element.getStartAddress()))
                    smartview_infos["mailbox_standardconf_inlength"] = str(ExtractHexDecValue(sm_element.getDefaultSize()))
                else:
                    pass

            # get device identity from <Device>-<Type>
            # vendor ID; by default, pre-defined value in self.ModulesLibrary
            # if device type in 'vendor' item equals to actual slave device type, set 'vendor_id' to vendor ID.
            for vendor_id, vendor in self.Controler.CTNParent.CTNParent.ModulesLibrary.Library.items():
                first_group_key = next(iter(vendor["groups"]))
                for available_device in vendor["groups"][first_group_key]["devices"]:
                    if available_device[0] == type_infos["device_type"]:
                        smartview_infos["vendor_id"] = "0x" + "{:0>8x}".format(vendor_id)

            # product code;
            if device.getType().getProductCode() is not None:
                product_code = device.getType().getProductCode()
                smartview_infos["product_code"] = "0x"+"{:0>8x}".format(ExtractHexDecValue(product_code))

            # revision number;
            if device.getType().getRevisionNo() is not None:
                revision_no = device.getType().getRevisionNo()
                smartview_infos["revision_no"] = "0x"+"{:0>8x}".format(ExtractHexDecValue(revision_no))

            # serial number;
            if device.getType().getSerialNo() is not None:
                serial_no = device.getType().getSerialNo()
                smartview_infos["serial_no"] = "0x"+"{:0>8x}".format(ExtractHexDecValue(serial_no))

            return smartview_infos

        else:
            return None

    def DecimalToHex(self, decnum):
        """
        Convert decimal value into hexadecimal representation.
        @param decnum : decimal value
        @return hex_data : hexadecimal representation of input value in decimal
        """
        value = "%x" % int(decnum, 16)
        value_len = len(value)
        if (value_len % 2) == 0:
            hex_len = value_len
        else:
            hex_len = (value_len // 2) * 2 + 2

        hex_data = ("{:0>"+str(hex_len)+"x}").format(int(decnum, 16))

        return hex_data

    def SiiRead(self):
        """
        Get slave EEPROM contents maintained by master device using "ethercat sii_read -p %d" command.
        Command example : "ethercat sii_read -p 0"
        @return return_val : result of "ethercat sii_read" (binary data)
        """
        alias = self.Controler.GetSlavePos()
        return_val = self.EtherCATCall("sii_read", alias)
        return_val = b"" if return_val is None else DecodeBinary(return_val)
        self.SiiData = return_val
        return return_val

    def SiiWrite(self, binary):
        """
        Overwrite slave EEPROM contents using "ethercat sii_write -p %d" command.
        Command example : "ethercat sii_write -p 0 - (binary contents)"
        @param binary : EEPROM contents in binary data format
        @return return_val : result of "ethercat sii_write" (If it succeeds, the return value is NULL.)
        """
        return self.EtherCATCall("sii_write", self.Controler.GetSlavePos(),
                                 EncodeBinary(binary))

    def LoadData(self):
        """
        Loading data from EEPROM use Sii_Read Method
        @return self.BinaryCode : slave EEPROM data in binary format (zero-padded)
        """
        return_val = self.Controler.CommonMethod.SiiRead()
        self.BinaryCode = return_val
        self.Controler.SiiData = self.BinaryCode

        # append zero-filled padding data up to EEPROM size
        for dummy in range(self.SmartViewInfosFromXML["eeprom_size"] - len(self.BinaryCode)):
            self.BinaryCode = self.BinaryCode + self.HexDecode('ff')[0]

        return self.BinaryCode

    def HexRead(self, binary):
        """
        Convert binary digit representation into hexadecimal representation for "Hex View" menu.
        @param binary : binary digits
        @return hexCode : hexadecimal digits
        @return hexview_table_row, hexview_table_col : Grid size for "Hex View" UI
        """

        if binary is None:
            return [], 0, 17

        # accept both a hex string and a bytes object
        if isinstance(binary, str):
            try:
                binary = bytes.fromhex(binary)
            except ValueError:
                binary = binary.encode(errors="ignore")

        row_code = []
        row_text = ""
        row = 0
        hex_code = []

        hexview_table_col = 17

        for value in binary:

            # normalise each item to an integer
            if not isinstance(value, int):
                try:
                    value = int(value, 16)
                except:
                    try:
                        value = int(value)
                    except:
                        continue  # not a byte value, skip it

            # keep byte range only
            if value < 0 or value > 255:
                continue

            # hexadecimal digits
            tempvar2 = "{:02x}".format(value)
            row_code.append(tempvar2)

            # printable representation
            if 32 <= value <= 126:
                row_text += chr(value)
            else:
                row_text += "."

            # row completed
            if len(row_code) == (hexview_table_col - 1):
                row_code.append(row_text)
                hex_code.append(row_code)
                row_text = ""
                row_code = []
                row += 1

        # append the last, incomplete, row
        if row_code:
            while len(row_code) < (hexview_table_col - 1):
                row_code.append("  ")
            row_code.append(row_text)
            hex_code.append(row_code)
            row += 1

        hexview_table_row = row

        return hex_code, hexview_table_row, hexview_table_col

    def GenerateEEPROMList(self, data, direction, length):
        """
        Generate EEPROM data list by reconstructing 'data' string.
        example : data="12345678", direction=0, length=8 -> eeprom_list=['12', '34', '56', '78']
                  data="12345678", direction=1, length=8 -> eeprom_list=['78', '56', '34', '12']
        @param data : string to be reconstructed
        @param direction : endianness
        @param length : data length
        @return eeprom_list : reconstructed list data structure
        """
        eeprom_list = []

        if direction in (0, 1):
            for dummy in range(length//2):
                if data == "":
                    eeprom_list.append("00")
                else:
                    eeprom_list.append(data[direction*(length-2):direction*(length-2)+2])
                data = data[(1-direction)*2:length-direction*2]
                length -= 2
        return eeprom_list

    def XmlToEeprom(self):
        """
        Extract slave EEPROM contents using slave ESI XML file.
          - Mandatory parts
          - String category : ExtractEEPROMStringCategory()
          - General category : ExtractEEPROMGeneralCategory()
          - FMMU category : ExtractEEPROMFMMUCategory
          - SyncM category : ExtractEEPROMSyncMCategory()
          - Tx/RxPDO category : ExtractEEPROMPDOCategory()
          - DC category : ExtractEEPROMDCCategory()
        @return eeprom_binary
        """
        eeprom = []
        data = ""
        eeprom_size = 0
        eeprom_binary = b""

        # 'device' is the slave device of the current EtherCAT slave plugin
        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())
        type_infos = slave.getType()
        device, _alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)

        if device is not None:
            # get ConfigData for EEPROM offset 0x0000-0x000d; <Device>-<Eeprom>-<ConfigData>
            for eeprom_element in device.getEeprom().getcontent():
                if eeprom_element["name"] == "ConfigData":
                    data = self.DecimalToHex(eeprom_element)
            eeprom += self.GenerateEEPROMList(data, 0, 28)

            # calculate CRC for EEPROM offset 0x000e-0x000f
            crc = 0x48
            for segment in eeprom:
                for i in range(8):
                    bit = crc & 0x80
                    crc = (crc << 1) | ((int(segment, 16) >> (7 - i)) & 0x01)
                    if bit:
                        crc ^= 0x07
            for dummy in range(8):
                bit = crc & 0x80
                crc <<= 1
                if bit:
                    crc ^= 0x07
            eeprom.append(hex(crc)[len(hex(crc))-3:len(hex(crc))-1])
            eeprom.append("00")

            # get VendorID for EEPROM offset 0x0010-0x0013;
            data = ""
            for vendor_id, vendor in self.Controler.CTNParent.CTNParent.ModulesLibrary.Library.items():
                group_key = next(iter(vendor["groups"]))
                for available_device in vendor["groups"][group_key]["devices"]:
                    if available_device[0] == type_infos["device_type"]:
                        data = "{:0>8x}".format(vendor_id)

            eeprom += self.GenerateEEPROMList(data, 1, 8)

            # get Product Code for EEPROM offset 0x0014-0x0017;
            data = ""
            if device.getType().getProductCode() is not None:
                data = "{:0>8x}".format(ExtractHexDecValue(device.getType().getProductCode()))
            eeprom += self.GenerateEEPROMList(data, 1, 8)

            # get Revision Number for EEPROM offset 0x0018-0x001b;
            data = ""
            if device.getType().getRevisionNo() is not None:
                data = "{:0>8x}".format(ExtractHexDecValue(device.getType().getRevisionNo()))
            eeprom += self.GenerateEEPROMList(data, 1, 8)

            # get Serial Number for EEPROM 0x001c-0x001f;
            data = ""
            if device.getType().getSerialNo() is not None:
                data = "{:0>8x}".format(ExtractHexDecValue(device.getType().getSerialNo()))
            eeprom += self.GenerateEEPROMList(data, 1, 8)

            # get Execution Delay for EEPROM 0x0020-0x0021; not analyzed yet
            eeprom.append("00")
            eeprom.append("00")

            # get Port0/1 Delay for EEPROM offset 0x0022-0x0025; not analyzed yet
            eeprom.append("00")
            eeprom.append("00")
            eeprom.append("00")
            eeprom.append("00")

            # reserved for EEPROM offset 0x0026-0x0027;
            eeprom.append("00")
            eeprom.append("00")

            # get BootStrap for EEPROM offset 0x0028-0x002e; <Device>-<Eeprom>-<BootStrap>
            data = ""
            for eeprom_element in device.getEeprom().getcontent():
                if eeprom_element["name"] == "BootStrap":
                    data = "{:0>16x}".format(int(eeprom_element,16))
            eeprom += self.GenerateEEPROMList(data, 0, 16)

            # get Standard Mailbox for EEPROM offset 0x0030-0x0037; <Device>-<sm>
            data = ""
            standard_send_mailbox_offset = None
            standard_send_mailbox_size = None
            standard_receive_mailbox_offset = None
            standard_receive_mailbox_size = None
            for sm_element in device.getSm():
                if sm_element.getcontent() == "MBoxOut":
                    standard_receive_mailbox_offset = "{:0>4x}".format(ExtractHexDecValue(sm_element.getStartAddress()))
                    standard_receive_mailbox_size = "{:0>4x}".format(ExtractHexDecValue(sm_element.getDefaultSize()))
                elif sm_element.getcontent() == "MBoxIn":
                    standard_send_mailbox_offset = "{:0>4x}".format(ExtractHexDecValue(sm_element.getStartAddress()))
                    standard_send_mailbox_size = "{:0>4x}".format(ExtractHexDecValue(sm_element.getDefaultSize()))

            if standard_receive_mailbox_offset is None:
                eeprom.append("00")
                eeprom.append("00")
            else:
                eeprom.append(standard_receive_mailbox_offset[2:4])
                eeprom.append(standard_receive_mailbox_offset[0:2])
            if standard_receive_mailbox_size is None:
                eeprom.append("00")
                eeprom.append("00")
            else:
                eeprom.append(standard_receive_mailbox_size[2:4])
                eeprom.append(standard_receive_mailbox_size[0:2])
            if standard_send_mailbox_offset is None:
                eeprom.append("00")
                eeprom.append("00")
            else:
                eeprom.append(standard_send_mailbox_offset[2:4])
                eeprom.append(standard_send_mailbox_offset[0:2])
            if standard_send_mailbox_size is None:
                eeprom.append("00")
                eeprom.append("00")
            else:
                eeprom.append(standard_send_mailbox_size[2:4])
                eeprom.append(standard_send_mailbox_size[0:2])

            data = 0
            mb = device.getMailbox()
            if mb is not None:
                for bit, mbprot in enumerate(mailbox_protocols):
                    if getattr(mb, "get%s" % mbprot)() is not None:
                        data += 1 << bit

            data = "{:0>4x}".format(data)
            eeprom.append(data[2:4])
            eeprom.append(data[0:2])

            # resereved for EEPROM offset 0x003a-0x007b;
            for i in range(0x007b-0x003a+0x0001):
                eeprom.append("00")

            # get EEPROM size for EEPROM offset 0x007c-0x007d;
            # Modify by jblee because of update IDE module (minidom -> lxml) 
            data = ""
            for eeprom_element in device.getEeprom().getchildren():
                if eeprom_element.tag == "ByteSize":
                    eeprom_size = int(eeprom_element.text)
                    data = "{:0>4x}".format(eeprom_size//1024*8-1)

            if data == "":
                eeprom.append("00")
                eeprom.append("00")
            else:
                eeprom.append(data[2:4])
                eeprom.append(data[0:2])

            # Version for EEPROM 0x007e-0x007f;
            # According to "EtherCAT Slave Device Description(V0.3.0)"
            eeprom.append("01")
            eeprom.append("00")

            # append String Category data
            for data in self.ExtractEEPROMStringCategory(device):
                eeprom.append(data)

            # append General Category data
            for data in self.ExtractEEPROMGeneralCategory(device):
                eeprom.append(data)

            # append FMMU Category data
            for data in self.ExtractEEPROMFMMUCategory(device):
                eeprom.append(data)

            # append SyncM Category data
            for data in self.ExtractEEPROMSyncMCategory(device):
                eeprom.append(data)

            # append TxPDO Category data
            for data in self.ExtractEEPROMPDOCategory(device, "TxPdo"):
                eeprom.append(data)

            # append RxPDO Category data
            for data in self.ExtractEEPROMPDOCategory(device, "RxPdo"):
                eeprom.append(data)

            # append DC Category data
            for data in self.ExtractEEPROMDCCategory(device):
                eeprom.append(data)

            # append padding
            padding = eeprom_size-len(eeprom)
            for i in range(padding):
                eeprom.append("ff")

            # convert binary code
            for index in range(eeprom_size):
                eeprom_binary = eeprom_binary + self.HexDecode(eeprom[index])[0]

            return eeprom_binary

    def ExtractEEPROMStringCategory(self, device):
        """
        Extract "Strings" category data from slave ESI XML and generate EEPROM image data.
        @param device : 'device' object in the slave ESI XML
        @return eeprom : "Strings" category EEPROM image data
        """
        eeprom = []
        self.Strings = []
        data = ""
        count = 0        # string counter
        padflag = False  # padding flag if category length is odd

        # index information for General Category in EEPROM
        self.GroupIdx = 0
        self.ImgIdx = 0
        self.OrderIdx = 0
        self.NameIdx = 0

        # flag for preventing duplicated vendor specific data
        typeflag = False
        grouptypeflag = False
        groupnameflag = False
        devnameflag = False
        imageflag = False

        # vendor specific data
        #   element1; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Type>
        #   vendor_specific_data : vendor specific data (binary type)
        vendor_specific_data = ""
        #   vendor_spec_strings : list of vendor specific "strings" for preventing duplicated strings
        vendor_spec_strings = []
        for element in device.getType().getcontent():
            data += element
        if data != "" and isinstance(data, text):
            for vendor_spec_string in vendor_spec_strings:
                if data == vendor_spec_string:
                    self.OrderIdx = vendor_spec_strings.index(data)+1
                    typeflag = True
                    break
            if typeflag is False:
                count += 1
                self.Strings.append(data)
                vendor_spec_strings.append(data)
                typeflag = True
                self.OrderIdx = count
                vendor_specific_data += "{:0>2x}".format(len(data))
                for character in range(len(data)):
                    vendor_specific_data += "{:0>2x}".format(ord(data[character]))
        data = ""

        # element2-1; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<GroupType>
        data = device.getGroupType()
        if data is not None and isinstance(data, text):
            for vendor_spec_string in vendor_spec_strings:
                if data == vendor_spec_string:
                    self.GroupIdx = vendor_spec_strings.index(data)+1
                    grouptypeflag = True
                    break
            if grouptypeflag is False:
                count += 1
                self.Strings.append(data)
                vendor_spec_strings.append(data)
                grouptypeflag = True
                self.GroupIdx = count
                vendor_specific_data += "{:0>2x}".format(len(data))
                for character in range(len(data)):
                    vendor_specific_data += "{:0>2x}".format(ord(data[character]))

        #  element2-2; <EtherCATInfo>-<Groups>-<Group>-<Type>
        if grouptypeflag is False:
            if self.Controler.CTNParent.CTNParent.ModulesLibrary.Library is not None:
                for _vendor_id, vendor in self.Controler.CTNParent.CTNParent.ModulesLibrary.Library.items():
                    for group_type, group_etc in vendor["groups"].items():
                        for device_item in group_etc["devices"]:
                            if device == device_item[1]:
                                data = group_type
                if data is not None and isinstance(data, text):
                    for vendor_spec_string in vendor_spec_strings:
                        if data == vendor_spec_string:
                            self.GroupIdx = vendor_spec_strings.index(data)+1
                            grouptypeflag = True
                            break
                    if grouptypeflag is False:
                        count += 1
                        self.Strings.append(data)
                        vendor_spec_strings.append(data)
                        grouptypeflag = True
                        self.GroupIdx = count
                        vendor_specific_data += "{:0>2x}".format(len(data))
                        for character in range(len(data)):
                            vendor_specific_data += "{:0>2x}".format(ord(data[character]))
        data = ""

        #  element3; <EtherCATInfo>-<Descriptions>-<Groups>-<Group>-<Name(LcId is "1033")>
        if self.Controler.CTNParent.CTNParent.ModulesLibrary.Library is not None:
            for _vendorId, vendor in self.Controler.CTNParent.CTNParent.ModulesLibrary.Library.items():
                for group_type, group_etc in vendor["groups"].items():
                    for device_item in group_etc["devices"]:
                        if device == device_item[1]:
                            data = group_etc["name"]
        if data != "" and isinstance(data, text):
            for vendor_spec_string in vendor_spec_strings:
                if data == vendor_spec_string:
                    groupnameflag = True
                    break
            if groupnameflag is False:
                count += 1
                self.Strings.append(data)
                vendor_spec_strings.append(data)
                groupnameflag = True
                vendor_specific_data += "{:0>2x}".format(len(data))
                for character in range(len(data)):
                    vendor_specific_data += "{:0>2x}".format(ord(data[character]))

        data = ""

        #  element4; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Name(LcId is "1033" or "1"?)>
        for element in device.getName():
            if element.getLcId() == 1 or element.getLcId() == 1033:
                data = element.getcontent()
        if data != "" and isinstance(data, text):
            for vendor_spec_string in vendor_spec_strings:
                if data == vendor_spec_string:
                    self.NameIdx = vendor_spec_strings.index(data)+1
                    devnameflag = True
                    break
            if devnameflag is False:
                count += 1
                self.Strings.append(data)
                vendor_spec_strings.append(data)
                devnameflag = True
                self.NameIdx = count
                vendor_specific_data += "{:0>2x}".format(len(data))
                for character in range(len(data)):
                    vendor_specific_data += "{:0>2x}".format(ord(data[character]))
        data = ""

        #  element5-1; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Image16x14>
        if device.getcontent() is not None:
            data = device.getcontent()
            if data is not None and isinstance(data, text):
                for vendor_spec_string in vendor_spec_strings:
                    if data == vendor_spec_string:
                        self.ImgIdx = vendor_spec_strings.index(data)+1
                        imageflag = True
                        break
                if imageflag is False:
                    count += 1
                    self.Strings.append(data)
                    vendor_spec_strings.append(data)
                    imageflag = True
                    self.ImgIdx = count
                    vendor_specific_data += "{:0>2x}".format(len(data))
                    for character in range(len(data)):
                        vendor_specific_data += "{:0>2x}".format(ord(data[character]))

        #  element5-2; <EtherCATInfo>-<Descriptions>-<Groups>-<Group>-<Image16x14>
        if imageflag is False:
            if self.Controler.CTNParent.CTNParent.ModulesLibrary.Library is not None:
                for _vendor_id, vendor in self.Controler.CTNParent.CTNParent.ModulesLibrary.Library.items():
                    for group_type, group_etc in vendor["groups"].items():
                        for device_item in group_etc["devices"]:
                            if device == device_item[1]:
                                data = group_etc
                if data is not None and isinstance(data, text):
                    for vendor_spec_string in vendor_spec_strings:
                        if data == vendor_spec_string:
                            self.ImgIdx = vendor_spec_strings.index(data)+1
                            imageflag = True
                            break
                    if imageflag is False:
                        count += 1
                        self.Strings.append(data)
                        vendor_spec_strings.append(data)
                        imageflag = True
                        self.ImgIdx = count
                        vendor_specific_data += "{:0>2x}".format(len(data))
                        for character in range(len(data)):
                            vendor_specific_data += "{:0>2x}".format(ord(data[character]))
        data = ""

        # DC related elements
        #  <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Dc>-<OpMode>-<Name>
        dc_related_elements = ""
        if device is not None:
            dc = getattr(device, "getDc", lambda: None)()
            if dc is not None:
                for element in getattr(dc, "getOpMode", lambda: [])() or []:
                    data = getattr(element, "getName", lambda: "")()
                    if data:
                        count += 1
                        self.Strings.append(data)
                        dc_related_elements += "{:0>2x}".format(len(data))
                        for character in range(len(data)):
                            dc_related_elements += "{:0>2x}".format(ord(data[character]))
                        data = ""

        # Input elements(TxPDO)
        #  <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<TxPdo>; Name
        input_elements = ""
        inputs = []
        for element in device.getTxPdo():
            for name in element.getName():
                data = name.getcontent()
            for input in inputs:
                if data == input:
                    data = ""
            if data != "":
                count += 1
                self.Strings.append(data)
                inputs.append(data)
                input_elements += "{:0>2x}".format(len(data))
                for character in range(len(data)):
                    input_elements += "{:0>2x}".format(ord(data[character]))
                data = ""
            for entry in element.getEntry():
                for name in entry.getName():
                    data = name.getcontent()
                for input in inputs:
                    if data == input:
                        data = ""
                if data != "":
                    count += 1
                    self.Strings.append(data)
                    inputs.append(data)
                    input_elements += "{:0>2x}".format(len(data))
                    for character in range(len(data)):
                        input_elements += "{:0>2x}".format(ord(data[character]))
                    data = ""

        # Output elements(RxPDO)
        #  <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<RxPdo>; Name
        output_elements = ""
        outputs = []
        for element in device.getRxPdo():
            for name in element.getName():
                data = name.getcontent()
            for output in outputs:
                if data == output:
                    data = ""
            if data != "":
                count += 1
                self.Strings.append(data)
                outputs.append(data)
                output_elements += "{:0>2x}".format(len(data))
                for character in range(len(data)):
                    output_elements += "{:0>2x}".format(ord(data[character]))
                data = ""
            for entry in element.getEntry():
                for name in entry.getName():
                    data = name.getcontent()
                for output in outputs:
                    if data == output:
                        data = ""
                if data != "":
                    count += 1
                    self.Strings.append(data)
                    outputs.append(data)
                    output_elements += "{:0>2x}".format(len(data))
                    for character in range(len(data)):
                        output_elements += "{:0>2x}".format(ord(data[character]))
                    data = ""

        # form eeprom data
        #  category header
        eeprom.append("0a")
        eeprom.append("00")
        #  category length (word); 1 word is 4 bytes. "+2" is the length of string's total number
        length = len(vendor_specific_data + dc_related_elements + input_elements + output_elements) + 2
        if length % 4 == 0:
            pass
        else:
            length += length % 4
            padflag = True
        eeprom.append("{:0>4x}".format(length//4)[2:4])
        eeprom.append("{:0>4x}".format(length//4)[0:2])
        #  total numbers of strings
        eeprom.append("{:0>2x}".format(count))
        for element in [vendor_specific_data,
                        dc_related_elements,
                        input_elements,
                        output_elements]:
            for dummy in range(len(element)//2):
                if element == "":
                    eeprom.append("00")
                else:
                    eeprom.append(element[0:2])
                element = element[2:len(element)]
        # padding if length is odd bytes
        if padflag is True:
            eeprom.append("ff")

        return eeprom

    def ExtractEEPROMGeneralCategory(self, device):
        """
        Extract "General" category data from slave ESI XML and generate EEPROM image data.
        @param device : 'device' object in the slave ESI XML
        @return eeprom : "Strings" category EEPROM image data
        """
        eeprom = []

        # category header
        eeprom.append("1e")
        eeprom.append("00")

        # category length
        eeprom.append("10")
        eeprom.append("00")

        # word 1 : Group Type index and Image index in STRINGS Category
        eeprom.append("{:0>2x}".format(self.GroupIdx))
        eeprom.append("{:0>2x}".format(self.ImgIdx))

        # word 2 : Device Type index and Device Name index in STRINGS Category
        eeprom.append("{:0>2x}".format(self.OrderIdx))
        eeprom.append("{:0>2x}".format(self.NameIdx))

        # word 3 : Physical Layer Port info. and CoE Details
        eeprom.append("01")  # Physical Layer Port info - assume 01
        #  CoE Details; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Mailbox>-<CoE>
        coe_details = 1  # sdo enabled
        mb = device.getMailbox()

        if mb is not None:
            coe = mb.getCoE()
            if coe is not None:
                for bit, flag in enumerate(["SdoInfo", "PdoAssign", "PdoConfig",
                                            "PdoUpload", "CompleteAccess"]):
                    if getattr(coe, "get%s" % flag)() is not None:
                        coe_details += 1 << bit

        eeprom.append("{:0>2x}".format(coe_details))

        # word 4 : FoE Details and EoE Details
        #  FoE Details; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Mailbox>-<FoE>
        if mb is not None and mb.getFoE() is not None:
            eeprom.append("01")
        else:
            eeprom.append("00")

        #  EoE Details; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Mailbox>-<EoE>
        if mb is not None and mb.getEoE() is not None:
            eeprom.append("01")
        else:
            eeprom.append("00")

        # word 5 : SoE Channels(reserved) and DS402 Channels
        #  SoE Details; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Mailbox>-<SoE>
        if mb is not None and mb.getSoE() is not None:
            eeprom.append("01")
        else:
            eeprom.append("00")

        #  DS402Channels; <EtherCATInfo>-<Descriptions>-<Devices>-<Device>-<Mailbox>-<CoE>: DS402Channels
        ds402ch = False
        if mb is not None:
            coe = mb.getCoE()
            if coe is not None:
                ds402ch = coe.getDS402Channels()

        eeprom.append("01" if ds402ch in [True, 1] else "00")

        # word 6 : SysmanClass(reserved) and Flags
        eeprom.append("00")  # reserved
        #  Flags
        en_safeop = False
        en_lrw = False
        if device.getType().getTcCfgModeSafeOp() is True \
           or device.getType().getTcCfgModeSafeOp() == 1:
            en_safeop = True
        if device.getType().getUseLrdLwr() is True \
           or device.getType().getUseLrdLwr() == 1:
            en_lrw = True

        flags = "0b"+"000000"+str(int(en_lrw))+str(int(en_safeop))
        eeprom.append("{:0>2x}".format(int(flags, 2)))

        # word 7 : Current On EBus (assume 0x0000)
        eeprom.append("00")
        eeprom.append("00")
        # after word 7; couldn't analyze yet
        eeprom.append("03")
        eeprom.append("00")
        eeprom.append("11")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")
        eeprom.append("00")

        return eeprom

    def ExtractEEPROMFMMUCategory(self, device):
        """
        Extract "FMMU" category data from slave ESI XML and generate EEPROM image data.
        @param device : 'device' object in the slave ESI XML
        @return eeprom : "Strings" category EEPROM image data
        """
        eeprom = []
        data = ""
        count = 0  # number of FMMU
        padflag = False

        for fmmu in device.getFmmu():
            count += 1
            if fmmu.getcontent() == "Outputs":
                data += "01"
            if fmmu.getcontent() == "Inputs":
                data += "02"
            if fmmu.getcontent() == "MBoxState":
                data += "03"

        # construct of EEPROM data
        if data != "":
            #  category header
            eeprom.append("28")
            eeprom.append("00")
            #  category length
            if count % 2 == 1:
                padflag = True
                eeprom.append("{:0>4x}".format((count+1)//2)[2:4])
                eeprom.append("{:0>4x}".format((count+1)//2)[0:2])
            else:
                eeprom.append("{:0>4x}".format((count)//2)[2:4])
                eeprom.append("{:0>4x}".format((count)//2)[0:2])
            for dummy in range(count):
                if data == "":
                    eeprom.append("00")
                else:
                    eeprom.append(data[0:2])
                data = data[2:len(data)]
            #  padding if length is odd bytes
            if padflag is True:
                eeprom.append("ff")

        return eeprom

    def ExtractEEPROMSyncMCategory(self, device):
        """
        Extract "SyncM" category data from slave ESI XML and generate EEPROM image data.
        @param device : 'device' object in the slave ESI XML
        @return eeprom : "Strings" category EEPROM image data
        """
        eeprom = []
        data = ""
        number = {"MBoxOut": "01", "MBoxIn": "02", "Outputs": "03", "Inputs": "04"}

        for sm in device.getSm():
            for attr in [sm.getStartAddress(),
                         sm.getDefaultSize(),
                         sm.getControlByte()]:
                if attr is not None:
                    data += "{:0>4x}".format(ExtractHexDecValue(attr))[2:4]
                    data += "{:0>4x}".format(ExtractHexDecValue(attr))[0:2]
                else:
                    data += "0000"
            if sm.getEnable() == "1" or sm.getEnable() is True:
                data += "01"
            else:
                data += "00"
            data += number[sm.getcontent()]

        if data != "":
            #  category header
            eeprom.append("29")
            eeprom.append("00")
            #  category length
            eeprom.append("{:0>4x}".format(len(data)//4)[2:4])
            eeprom.append("{:0>4x}".format(len(data)//4)[0:2])
            for dummy in range(len(data)//2):
                if data == "":
                    eeprom.append("00")
                else:
                    eeprom.append(data[0:2])
                data = data[2:len(data)]

        return eeprom

    def ExtractEEPROMPDOCategory(self, device, pdotype):
        """
        Extract ""PDO (Tx, Rx)"" category data from slave ESI XML and generate EEPROM image data.
        @param device : 'device' object in the slave ESI XML
        @param pdotype : identifier whether "TxPDO" or "RxPDO".
        @return eeprom : "Strings" category EEPROM image data
        """
        eeprom = []
        data = ""
        count = 0
        en_fixed = False
        en_mandatory = False
        en_virtual = False

        for element in eval("device.get%s()" % pdotype):
            #  PDO Index
            data += "{:0>4x}".format(ExtractHexDecValue(element.getIndex().getcontent()))[2:4]
            data += "{:0>4x}".format(ExtractHexDecValue(element.getIndex().getcontent()))[0:2]
            #  Number of Entries
            data += "{:0>2x}".format(len(element.getEntry()))
            #  About Sync Manager
            if element.getSm() is not None:
                data += "{:0>2x}".format(element.getSm())
            else:
                data += "ff"
            #  Reference to DC Synch (according to ET1100 documentation) - assume 0
            data += "00"
            #  Name Index
            objname = ""
            for name in element.getName():
                objname = name.getcontent()
            for name in self.Strings:
                count += 1
                if objname == name:
                    break
            if len(self.Strings)+1 == count:
                data += "00"
            else:
                data += "{:0>2x}".format(count)
            count = 0
            #  Flags; by Fixed, Mandatory, Virtual attributes ?
            if element.getFixed() is True or element.getFixed() == 1:
                en_fixed = True

            if element.getMandatory() is True or element.getMandatory() == 1:
                en_mandatory = True

            if element.getVirtual() is True or element.getVirtual():
                en_virtual = True
            data += str(int(en_fixed)) + str(int(en_mandatory)) + str(int(en_virtual)) + "0"

            for entry in element.getEntry():
                #   Entry Index
                data += "{:0>4x}".format(ExtractHexDecValue(entry.getIndex().getcontent()))[2:4]
                data += "{:0>4x}".format(ExtractHexDecValue(entry.getIndex().getcontent()))[0:2]
                #   Subindex
                data += "{:0>2x}".format(ExtractHexDecValue(entry.getSubIndex()))
                #   Entry Name Index
                objname = ""
                for name in entry.getName():
                    objname = name.getcontent()
                for name in self.Strings:
                    count += 1
                    if objname == name:
                        break
                if len(self.Strings)+1 == count:
                    data += "00"
                else:
                    data += "{:0>2x}".format(count)
                count = 0
                #   DataType
                if entry.getDataType() is not None:
                    if entry.getDataType().getcontent() in self.BaseDataTypeDict:
                        data += self.BaseDataTypeDict[entry.getDataType().getcontent()]
                    else:
                        data += "00"
                else:
                    data += "00"
                #   BitLen
                if entry.getBitLen() is not None:
                    data += "{:0>2x}".format(int(entry.getBitLen()))
                else:
                    data += "00"
                #   Flags; by Fixed attributes ?
                en_fixed = False
                if entry.getFixed() is True or entry.getFixed() == 1:
                    en_fixed = True
                data += str(int(en_fixed)) + "000"

        if data != "":
            #  category header
            if pdotype == "TxPdo":
                eeprom.append("32")
            elif pdotype == "RxPdo":
                eeprom.append("33")
            else:
                eeprom.append("00")
            eeprom.append("00")
            #  category length
            eeprom.append("{:0>4x}".format(len(data)//4)[2:4])
            eeprom.append("{:0>4x}".format(len(data)//4)[0:2])
            data = str(data.lower())
            for dummy in range(len(data)//2):
                if data == "":
                    eeprom.append("00")
                else:
                    eeprom.append(data[0:2])
                data = data[2:len(data)]

        return eeprom

    def ExtractEEPROMDCCategory(self, device):
        """
        Extract "DC(Distributed Clock)" category data from slave ESI XML and generate EEPROM image data.
        @param device : 'device' object in the slave ESI XML
        @return eeprom : "Strings" category EEPROM image data
        """
        eeprom = []
        data = ""
        count = 0
        namecount = 0

        if device.getDc() is not None:
            for element in device.getDc().getOpMode():
                count += 1
                #  assume that word 1-7 are 0x0000
                data += "0000"
                data += "0000"
                data += "0000"
                data += "0000"
                data += "0000"
                data += "0000"
                data += "0000"
                #  word 8-10
                #  AssignActivate
                if element.getAssignActivate() is not None:
                    data += "{:0>4x}".format(ExtractHexDecValue(element.getAssignActivate()))[2:4]
                    data += "{:0>4x}".format(ExtractHexDecValue(element.getAssignActivate()))[0:2]
                else:
                    data += "0000"
                #  Factor of CycleTimeSync0 ? and default is 1?
                if element.getCycleTimeSync0() is not None:
                    if element.getCycleTimeSync0().getFactor() is not None:
                        data += "{:0>2x}".format(int(element.getCycleTimeSync0().getFactor()))
                        data += "00"
                    else:
                        data += "0100"
                else:
                    data += "0100"
                #  Index of Name in STRINGS Category
                #  Name Index
                objname = ""
                for name in element.getName():
                    objname += name
                for name in self.Strings:
                    namecount += 1
                    if objname == name:
                        break
                if len(self.Strings)+1 == namecount:
                    data += "00"
                else:
                    data += "{:0>2x}".format(namecount)
                namecount = 0
                data += "00"
                #  assume that word 11-12 are 0x0000
                data += "0000"
                data += "0000"

        if data != "":
            #  category header
            eeprom.append("3c")
            eeprom.append("00")
            #  category length
            eeprom.append("{:0>4x}".format(len(data)//4)[2:4])
            eeprom.append("{:0>4x}".format(len(data)//4)[0:2])
            data = str(data.lower())
            for dummy in range(len(data)//2):
                if data == "":
                    eeprom.append("00")
                else:
                    eeprom.append(data[0:2])
                data = data[2:len(data)]

        return eeprom

    # -------------------------------------------------------------------------------
    #                        Used Register Access
    # -------------------------------------------------------------------------------
    def RegRead(self, offset, length):
        """
        Read slave ESC register content using "ethercat reg_read -p %d %s %s" command.
        Command example : "ethercat reg_read -p 0 0x0c00 0x0400"
        @param offset : register address
        @param length : register length
        @return return_val : register data
        """
        return self.EtherCATCall("reg_read", self.Controler.GetSlavePos(),
                                 offset, length, default="")

    def MultiRegRead(self, slave_num, reg_infos):
        """
        Read the same registers on every slave of the network.
        @param slave_num: number of slaves on the network
        @param reg_infos: list of "address,size" registers to read
        @return return_val: one "position,address,content" line per read
        """
        registers = [reg_info.split(",") for reg_info in reg_infos]

        return self.EtherCATCall("multi_reg_read", slave_num, registers,
                                 default=[])


    def RegWrite(self, address, data):
        """
        Write data to slave ESC register using "ethercat reg_write -p %d %s %s" command.
        Command example : "ethercat reg_write -p 0 0x0c04 0x0001"
        @param address : register address
        @param data : data to write
        @return return_val : the execution result of "ethercat reg_write" (for error check)
        """
        return self.EtherCATCall("reg_write", self.Controler.GetSlavePos(),
                                 address, data, default="")

    def Rescan(self):
        """
        Synchronize EEPROM data in master controller with the data in slave device after EEPROM write.
        Command example : "ethercat rescan -p 0"
        """
        self.EtherCATCall("rescan", self.Controler.GetSlavePos())

    # -------------------------------------------------------------------------------
    #                        Used DC Configuration
    #-------------------------------------------------------------------------------
    def LoadESIData(self):
        return_data = []
        slave = self.Controler.CTNParent.GetSlave(self.Controler.GetSlavePos())
        type_infos = slave.getType()
        device, alignment = self.Controler.CTNParent.GetModuleInfos(type_infos)

        if device is not None:
            dc = getattr(device, "getDc", lambda: None)()
            if dc is not None:
                for OpMode in device.getDc().getOpMode():
                    temp_data = {
                        "desc" : OpMode.getDesc() if OpMode.getDesc() is not None else "Unused",
                        "assign_activate" : OpMode.getAssignActivate() \
                            if OpMode.getAssignActivate() is not None else "#x0000",
                        "cycletime_sync0" : OpMode.getCycleTimeSync0().getcontent() \
                            if OpMode.getCycleTimeSync0() is not None else None,
                        "shifttime_sync0" : OpMode.getShiftTimeSync0().getcontent() \
                            if OpMode.getShiftTimeSync0() is not None else None,
                        "cycletime_sync1" : OpMode.getShiftTimeSync1().getcontent() \
                            if OpMode.getShiftTimeSync1() is not None else None,
                        "shifttime_sync1" : OpMode.getShiftTimeSync1().getcontent() \
                            if OpMode.getShiftTimeSync1() is not None else None
                    }

                    if OpMode.getCycleTimeSync0() is not None:
                        temp_data["cycletime_sync0_factor"] = OpMode.getCycleTimeSync0().getFactor()

                    if OpMode.getCycleTimeSync1() is not None:
                        temp_data["cycletime_sync1_factor"] = OpMode.getCycleTimeSync1().getFactor()

                    return_data.append(temp_data)

        return return_data
    
    #-------------------------------------------------------------------------------
    #                        Common Use Methods
    # -------------------------------------------------------------------------------
    def CheckConnect(self, cyclic_flag):
        """
        Check connection status (1) between Beremiz and the master (2) between the master and the slave.
        @param cyclic_flag: 0 - one shot, 1 - periodic
        @return True or False
        """
        if self.Controler.GetCTRoot()._connector is not None:
            # Check connection between the master and the slave.
            # Command example : "ethercat xml -p 0"
            alias = self.Controler.GetSlavePos()
            pos = self.AliasToPosition(alias)

            if pos is None:
                if not cyclic_flag:
                    self.CreateErrorDialog(_('Alias not found'))
                return False

            return_val = self.EtherCATCall("slave_xml", pos, default="")

            number_of_lines = return_val.split("\n")
            if len(number_of_lines) <= 2:  # No slave connected to the master controller
                if not cyclic_flag:
                    self.CreateErrorDialog(_('No connected slaves'))
                return False

            elif len(number_of_lines) > 2:
                return True
        else:
            # The master controller is not connected to Beremiz host
            if not cyclic_flag:
                self.CreateErrorDialog(_('PLC not connected!'))
            return False

    def CreateErrorDialog(self, mention):
        """
        Create a dialog to indicate error or warning.
        @param mention : Error String
        """
        app_frame = self.Controler.GetCTRoot().AppFrame
        dlg = wx.MessageDialog(app_frame, mention,
                               _(' Warning...'),
                               wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()
