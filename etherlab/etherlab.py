import os, shutil
from xml.dom import minidom

import wx
import csv

from xmlclass import *

from ConfigTreeNode import ConfigTreeNode
from PLCControler import UndoBuffer, LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY

from EthercatSlave import ExtractHexDecValue, ExtractName
from EthercatMaster import _EthercatCTN
from ConfigEditor import LibraryEditor, ETHERCAT_VENDOR, ETHERCAT_GROUP, ETHERCAT_DEVICE

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
            dictionary.load()
            
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

    def GetEntriesList(self, limits=None):
        if self.DataTypes is None:
            self.ExtractDataTypes()
        
        entries = {}
        
        for dictionary in self.GetProfileDictionaries():
            dictionary.load()
            
            for object in dictionary.getObjects().getObject():
                entry_index = object.getIndex().getcontent()
                index = ExtractHexDecValue(entry_index)
                if limits is None or limits[0] <= index <= limits[1]:
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
                                "PDOMapping": subitem_pdomapping}
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
                             "PDOMapping": entry_pdomapping}
        
        for TxPdo in self.getTxPdo():
            ExtractPdoInfos(TxPdo, "Transmit", entries, limits)
        for RxPdo in self.getRxPdo():
            ExtractPdoInfos(RxPdo, "Receive", entries, limits)
        
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

def ExtractPdoInfos(pdo, pdo_type, entries, limits=None):
    pdo_index = pdo.getIndex().getcontent()
    pdo_name = ExtractName(pdo.getName())
    for pdo_entry in pdo.getEntry():
        entry_index = pdo_entry.getIndex().getcontent()
        entry_subindex = pdo_entry.getSubIndex()
        index = ExtractHexDecValue(entry_index)
        subindex = ExtractHexDecValue(entry_subindex)
        
        if limits is None or limits[0] <= index <= limits[1]:
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
                        "PDOMapping": pdomapping}

class ModulesLibrary:

    MODULES_EXTRA_PARAMS = [
        ("pdo_alignment", {
            "column_label": _("PDO alignment"), 
            "column_size": 150,
            "default": 8,
            "description": _(
"Minimal size in bits between 2 pdo entries")}),
        ("max_pdo_size", {
            "column_label": _("Max entries by PDO"),
            "column_size": 150,
            "default": 255,
            "description": _(
"""Maximal number of entries mapped in a PDO
including empty entries used for PDO alignment""")}),
        ("add_pdo", {
            "column_label": _("Creating new PDO"), 
            "column_size": 150,
            "default": 0,
            "description": _(
"""Adding a PDO not defined in default configuration
for mapping needed location variables
(1 if possible)""")})
    ]
    
    def __init__(self, path, parent_library=None):
        self.Path = path
        if not os.path.exists(self.Path):
            os.makedirs(self.Path)
        self.ParentLibrary = parent_library
        
        if parent_library is not None:
            self.LoadModules()
        else:
            self.Library = None
        self.LoadModulesExtraParams()
    
    def GetPath(self):
        return self.Path
    
    def GetModulesExtraParamsFilePath(self):
        return os.path.join(self.Path, "modules_extra_params.cfg")
    
    def LoadModules(self):
        self.Library = {}
        
        files = os.listdir(self.Path)
        for file in files:
            filepath = os.path.join(self.Path, file)
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
                    
                    vendor_category = self.Library.setdefault(ExtractHexDecValue(vendor.getId()), 
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
        if self.Library is None:
            self.LoadModules()
        library = []
        for vendor_id, vendor in self.Library.iteritems():
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
                        product_code = device.getType().getProductCode()
                        revision_number = device.getType().getRevisionNo()
                        module_infos = {"device_type": device_type,
                                        "vendor": vendor_id,
                                        "product_code": product_code,
                                        "revision_number": revision_number}
                        module_infos.update(self.GetModuleExtraParams(vendor_id, product_code, revision_number))
                        device_infos = {"name": ExtractName(device.getName()),
                                        "type": ETHERCAT_DEVICE,
                                        "infos": module_infos,
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

    def GetVendors(self):
        return [(vendor_id, vendor["name"]) for vendor_id, vendor in self.Library.items()]
    
    def GetModuleInfos(self, module_infos):
        vendor = ExtractHexDecValue(module_infos["vendor"])
        vendor_infos = self.Library.get(vendor)
        if vendor_infos is not None:
            for group_name, group_infos in vendor_infos["groups"].iteritems():
                for device_type, device_infos in group_infos["devices"]:
                    product_code = ExtractHexDecValue(device_infos.getType().getProductCode())
                    revision_number = ExtractHexDecValue(device_infos.getType().getRevisionNo())
                    if (product_code == ExtractHexDecValue(module_infos["product_code"]) and
                        revision_number == ExtractHexDecValue(module_infos["revision_number"])):
                        return device_infos, self.GetModuleExtraParams(vendor, product_code, revision_number)
        return None, None
    
    def ImportModuleLibrary(self, filepath):
        if os.path.isfile(filepath):
            shutil.copy(filepath, self.Path)
            self.LoadModules()
            return True
        return False
    
    def LoadModulesExtraParams(self):
        self.ModulesExtraParams = {}
        
        csvfile_path = self.GetModulesExtraParamsFilePath()
        if os.path.exists(csvfile_path):
            csvfile = open(csvfile_path, "rb")
            sample = csvfile.read(1024)
            csvfile.seek(0)
            dialect = csv.Sniffer().sniff(sample)
            has_header = csv.Sniffer().has_header(sample)
            reader = csv.reader(csvfile, dialect)
            for row in reader:
                if has_header:
                    has_header = False
                else:
                    params_values = {}
                    for (param, param_infos), value in zip(
                        self.MODULES_EXTRA_PARAMS, row[3:]):
                        if value != "":
                            params_values[param] = int(value)
                    self.ModulesExtraParams[
                        tuple(map(int, row[:3]))] = params_values
            csvfile.close()
    
    def SaveModulesExtraParams(self):
        csvfile = open(self.GetModulesExtraParamsFilePath(), "wb")
        extra_params = [param for param, params_infos in self.MODULES_EXTRA_PARAMS]
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['Vendor', 'product_code', 'revision_number'] + extra_params)
        for (vendor, product_code, revision_number), module_extra_params in self.ModulesExtraParams.iteritems():
            writer.writerow([vendor, product_code, revision_number] + 
                            [module_extra_params.get(param, '') 
                             for param in extra_params])
        csvfile.close()
    
    def SetModuleExtraParam(self, vendor, product_code, revision_number, param, value):
        vendor = ExtractHexDecValue(vendor)
        product_code = ExtractHexDecValue(product_code)
        revision_number = ExtractHexDecValue(revision_number)
        
        module_infos = (vendor, product_code, revision_number)
        self.ModulesExtraParams.setdefault(module_infos, {})
        self.ModulesExtraParams[module_infos][param] = value
        
        self.SaveModulesExtraParams()
    
    def GetModuleExtraParams(self, vendor, product_code, revision_number):
        vendor = ExtractHexDecValue(vendor)
        product_code = ExtractHexDecValue(product_code)
        revision_number = ExtractHexDecValue(revision_number)
        
        if self.ParentLibrary is not None:
            extra_params = self.ParentLibrary.GetModuleExtraParams(vendor, product_code, revision_number)
        else:
            extra_params = {}
        
        extra_params.update(self.ModulesExtraParams.get((vendor, product_code, revision_number), {}))
        
        for param, param_infos in self.MODULES_EXTRA_PARAMS:
            extra_params.setdefault(param, param_infos["default"])
        
        return extra_params

USERDATA_DIR = wx.StandardPaths.Get().GetUserDataDir()
if wx.Platform != '__WXMSW__':
    USERDATA_DIR += '_files'

ModulesDatabase = ModulesLibrary(
    os.path.join(USERDATA_DIR, "ethercat_modules"))

class RootClass:
    
    CTNChildrenTypes = [("EthercatNode",_EthercatCTN,"Ethercat Master")]
    EditorType = LibraryEditor
    
    def __init__(self):
        self.ModulesLibrary = None
        self.LoadModulesLibrary()
    
    def GetModulesLibraryPath(self, project_path=None):
        if project_path is None:
            project_path = self.CTNPath()
        return os.path.join(project_path, "modules") 
    
    def OnCTNSave(self, from_project_path=None):
        if from_project_path is not None:
            shutil.copytree(self.GetModulesLibraryPath(from_project_path),
                            self.GetModulesLibraryPath())
        return True
    
    def CTNGenerate_C(self, buildpath, locations):
        return [],"",False
    
    def LoadModulesLibrary(self):
        if self.ModulesLibrary is None:
            self.ModulesLibrary = ModulesLibrary(self.GetModulesLibraryPath(), ModulesDatabase)
        else:
            self.ModulesLibrary.LoadModulesLibrary()
    
    def GetModulesDatabaseInstance(self):
        return ModulesDatabase
    
    def GetModulesLibraryInstance(self):
        return self.ModulesLibrary
    
    def GetModulesLibrary(self, profile_filter=None):
        return self.ModulesLibrary.GetModulesLibrary(profile_filter)
    
    def GetVendors(self):
        return self.ModulesLibrary.GetVendors()
    
    def GetModuleInfos(self, module_infos):
        return self.ModulesLibrary.GetModuleInfos(module_infos)

            
