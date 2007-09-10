#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA

from types import *

DicoTypes = {"BOOL":0x01, "SINT":0x02, "INT":0x03,"DINT":0x04,"LINT":0x10,
             "USINT":0x05,"UINT":0x06,"UDINT":0x07,"ULINT":0x1B,"REAL":0x08,
             "LREAL":0x11,"STRING":0x09,"BYTE":0x05,"WORD":0x06,"DWORD":0x07,
             "LWORD":0x1B,"WSTRING":0x0B}

DictLocations = {}
DictCobID = {}
DictLocationsNotMapped = {}
ListCobIDAvailable = []
SlavesPdoNumber = {}

# Constants for PDO types 
RPDO = 1
TPDO = 2
SlavePDOType = {"I" : TPDO, "Q" : RPDO}
InvertPDOType = {RPDO : TPDO, TPDO : RPDO}

DefaultTransmitTypeMaster = 0x01

GenerateMasterMapping = lambda x:[None] + [(loc_infos["type"], name) for name, loc_infos in x]

TrashVariableSizes = {1 : 0x01, 8 : 0x05, 16 : 0x06, 32 : 0x07, 64 : 0x1B}


def GetSlavePDOIndexes(slave, type, parameters = False):
    indexes = []
    if type & RPDO:
        indexes.extend([idx for idx in slave.GetIndexes() if 0x1400 <= idx <= 0x15FF])
    if type & TPDO:
        indexes.extend([idx for idx in slave.GetIndexes() if 0x1800 <= idx <= 0x19FF])
    if not parameters:
        return [idx + 0x200 for idx in indexes]
    else:
        return indexes


def LE_to_BE(value, size): # Convert Little Endian to Big Endian
    data = ("%" + str(size * 2) + "." + str(size * 2) + "X") % value
    list_car = [data[i:i+2] for i in xrange(0, len(data), 2)]
    list_car.reverse()
    return "".join([chr(int(car, 16)) for car in list_car])



def SearchSlavePDOMapping(loc_infos, slave): # Search the TPDO or RPDO mapping where location is defined on the slave
    typeinfos = slave.GetEntryInfos(loc_infos["type"])
    model = (loc_infos["index"] << 16) + (loc_infos["subindex"] << 8) + typeinfos["size"]
    slavePDOidxlist = GetSlavePDOIndexes(slave, loc_infos["pdotype"])
    
    for PDOidx in slavePDOidxlist:
        values = slave.GetEntry(PDOidx)
        if values != None:
            for subindex, mapping in enumerate(values):
                if subindex != 0 and mapping == model:
                    return PDOidx, subindex
    return None

def GenerateMappingDCF(cobid, idx, pdomapping, mapped): # Build concise DCF
    
    # Create entry for RPDO or TPDO parameters and Disable PDO
    dcfdata = LE_to_BE(idx, 2) + LE_to_BE(0x01, 1) + LE_to_BE(0x04, 4) + LE_to_BE((0x80000000 + cobid), 4)
    # Set Transmit type synchrone
    dcfdata += LE_to_BE(idx, 2) + LE_to_BE(0x02, 1) + LE_to_BE(0x01, 4) + LE_to_BE(DefaultTransmitTypeSlave, 1)
    # Re-Enable PDO
    #         ---- INDEX -----   --- SUBINDEX ----   ----- SIZE ------   ------ DATA ------
    dcfdata += LE_to_BE(idx, 2) + LE_to_BE(0x01, 1) + LE_to_BE(0x04, 4) + LE_to_BE(0x00000000 + cobid, 4)
    nbparams = 3
    if mapped == False and pdomapping != None:
    # Map Variables
        for subindex, (name, loc_infos) in enumerate(pdomapping):
            value = (loc_infos["index"] << 16) + (loc_infos["subindex"] << 8) + loc_infos["size"]
            dcfdata += LE_to_BE(idx + 0x200, 2) + LE_to_BE(subindex + 1, 1) + LE_to_BE(0x04, 4) + LE_to_BE(value, 4)
            nbparams += 1
    return dcfdata, nbparams

def GetNewCobID(nodeid, type): # Return a cobid not used
    global ListCobIDAvailable, SlavesPdoNumber
    
    if len(ListCobIDAvailable) == 0:
        return None
    
    nbSlavePDO = SlavesPdoNumber[nodeid][type]
    if type == RPDO:
        if nbSlavePDO < 4:
            # For the fourth PDO -> cobid = 0x200 + ( numPdo parameters * 0x100) + nodeid
            newcobid = (0x200 + nbSlavePDO * 0x100 + nodeid)
            if newcobid in ListCobIDAvailable:
                ListCobIDAvailable.remove(newcobid)
                return newcobid, 0x1400 + nbSlavePDO
        return ListCobIDAvailable.pop(0), 0x1400 + nbSlavePDO

    elif type == TPDO:
        if nbSlavePDO < 4:
            # For the fourth PDO -> cobid = 0x180 + (numPdo parameters * 0x100) + nodeid
            newcobid = (0x180 + nbSlavePDO * 0x100 + nodeid)
            if newcobid in ListCobIDAvailable:
                ListCobIDAvailable.remove(newcobid)
                return newcobid, 0x1800 + nbSlavePDO
        return ListCobIDAvailable.pop(0), 0x1800 + nbSlavePDO
    
    for number in xrange(4):
        if type == RPDO:
            # For the fourth PDO -> cobid = 0x200 + ( numPdo * 0x100) + nodeid
            newcobid = (0x200 + number * 0x100 + nodeid)
        elif type == TPDO:
            # For the fourth PDO -> cobid = 0x180 + (numPdo * 0x100) + nodeid
            newcobid = (0x180 + number * 0x100 + nodeid)
        else:
            return None
        if newcobid in ListCobIDAvailable:
            ListCobIDAvailable.remove(newcobid)
            return newcobid
    return ListCobIDAvailable.pop(0)
        
        
def GenerateConciseDCF(locations, current_location, nodelist):
    """
    Fills a CanFestival network editor model, with DCF with requested PDO mappings.
    @param locations: List of complete variables locations \
        [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
        "NAME" : name of the variable (generally "__IW0_1_2" style)
        "DIR" : direction "Q","I" or "M"
        "SIZE" : size "X", "B", "W", "D", "L"
        "LOC" : tuple of interger for IEC location (0,1,2,...)
        }, ...]
    @param nodelist: CanFestival network editor model
    @return: a modified copy of the given CanFestival network editor model
    """
    
    global DictLocations, DictCobID, DictLocationsNotMapped, ListCobIDAvailable, SlavesPdoNumber, DefaultTransmitTypeSlave

    DictLocations = {}
    DictCobID = {}
    DictLocationsNotMapped = {}
    DictSDOparams = {}
    ListCobIDAvailable = range(0x180, 0x580)
    SlavesPdoNumber = {}
    DictNameVariable = { "" : 1, "X": 2, "B": 3, "W": 4, "D": 5, "L": 6, "increment": 0x100, 1:("__I", 0x2000), 2:("__Q", 0x4000)}
    DefaultTransmitTypeSlave = 0xFF
    # Master Node initialisation
    
    manager = nodelist.Manager
    masternode = manager.GetCurrentNodeCopy()
    if not masternode.IsEntry(0x1F22):
        masternode.AddEntry(0x1F22, 1, "")
    manager.AddSubentriesToCurrent(0x1F22, 127, masternode)
    # Adding trash mappable variables for unused mapped datas
    idxTrashVariables = 0x2000 + masternode.GetNodeID()
    TrashVariableValue = {}
    manager.AddMapVariableToCurrent(idxTrashVariables, "trashvariables", 3, len(TrashVariableSizes), masternode)
    for subidx, (size, typeidx) in enumerate(TrashVariableSizes.items()):
        manager.SetCurrentEntry(idxTrashVariables, subidx + 1, "TRASH%d" % size, "name", None, masternode)
        manager.SetCurrentEntry(idxTrashVariables, subidx + 1, typeidx, "type", None, masternode)
        TrashVariableValue[size] = (idxTrashVariables << 16) + ((subidx + 1) << 8) + size
    
    
    # Extract Master Node current empty mapping index
    CurrentPDOParamsIdx = {RPDO : 0x1400 + len(GetSlavePDOIndexes(masternode, RPDO)),
                           TPDO : 0x1800 + len(GetSlavePDOIndexes(masternode, TPDO))}

    # Get list of all Slave's CobID and Slave's default SDO server parameters
    for nodeid, nodeinfos in nodelist.SlaveNodes.items():
        node = nodeinfos["Node"]
        node.SetNodeID(nodeid)
        DictSDOparams[nodeid] = {"RSDO" : node.GetEntry(0x1200,0x01), "TSDO" : node.GetEntry(0x1200,0x02)}
        slaveRpdoIndexes = GetSlavePDOIndexes(node, RPDO, True)
        slaveTpdoIndexes = GetSlavePDOIndexes(node, TPDO, True)
        SlavesPdoNumber[nodeid] = {RPDO : len(slaveRpdoIndexes), TPDO : len(slaveTpdoIndexes)}
        for PdoIdx in slaveRpdoIndexes + slaveTpdoIndexes:
            pdo_cobid = node.GetEntry(PdoIdx, 0x01)
            if pdo_cobid > 0x600 :
                pdo_cobid -= 0x80000000
            if pdo_cobid in ListCobIDAvailable:
                ListCobIDAvailable.remove(pdo_cobid)
    
    # Get list of locations check if exists and mappables -> put them in DictLocations
    for location in locations:
        locationtype = location["IEC_TYPE"]
        name = location["NAME"]
        if name in DictLocations:
            if DictLocations[name]["type"] != DicoTypes[locationtype]:
                raise ValueError, "Conflict type for location \"%s\"" % name 
        else:
            #get only the part of the location that concern this node
            loc = location["LOC"][len(current_location):]
            # loc correspond to (ID, INDEX, SUBINDEX [,BIT])
            if len(loc) not in (3, 4):
                raise ValueError, "Bad location size : %s"%str(loc)
            
            direction = location["DIR"]
            
            sizelocation = location["SIZE"]
            
            # Extract and check nodeid
            nodeid, index, subindex = loc[:3]
            
            # Check Id is in slave node list
            if nodeid not in nodelist.SlaveNodes.keys():
                raise ValueError, "Non existing node ID : %d (variable %s)" % (nodeid,name)
            
            # Get the model for this node (made from EDS)
            node = nodelist.SlaveNodes[nodeid]["Node"]
            
            # Extract and check index and subindex
            if not node.IsEntry(index, subindex):
                raise ValueError, "No such index/subindex (%x,%x) in ID : %d (variable %s)" % (index,subindex,nodeid,name)
            
            #Get the entry info
            subentry_infos = node.GetSubentryInfos(index, subindex)
            
            # If a PDO mappable
            if subentry_infos and subentry_infos["pdo"]:
                if sizelocation == "X" and len(loc) > 3:
                    numbit = loc[4]
                elif sizelocation != "X" and len(loc) > 3:
                    raise ValueError, "Cannot set bit offset for non bool '%s' variable (ID:%d,Idx:%x,sIdx:%x))" % (name,nodeid,index,subindex)
                else:
                    numbit = None
                
                COlocationtype = DicoTypes[locationtype]
                entryinfos = node.GetSubentryInfos(index, subindex)
                if entryinfos["type"] != COlocationtype:
                    raise ValueError, "Invalid type \"%s\"-> %d != %d  for location\"%s\"" % (locationtype,COlocationtype, entryinfos["type"] , name)
                
                typeinfos = node.GetEntryInfos(COlocationtype)
                DictLocations[name] = {"type":COlocationtype, "pdotype":SlavePDOType[direction],
                                       "nodeid": nodeid, "index": index,"subindex": subindex,
                                       "bit": numbit, "size": typeinfos["size"], "sizelocation": sizelocation}
            else:
                raise ValueError, "Not PDO mappable variable : '%s' (ID:%d,Idx:%x,sIdx:%x))" % (name,nodeid,index,subindex)
                
    # Create DictCobID with variables already mapped and add them in DictValidLocations
    for name, locationinfos in DictLocations.items():
        node = nodelist.SlaveNodes[locationinfos["nodeid"]]["Node"]
        result = SearchSlavePDOMapping(locationinfos, node)
        if result != None:
            index, subindex = result
            cobid = nodelist.GetSlaveNodeEntry(locationinfos["nodeid"], index - 0x200, 1)
            if cobid not in DictCobID.keys():
                mapping = [None]
                values = node.GetEntry(index)
                for value in values[1:]:
                    mapping.append(value % 0x100)
                DictCobID[cobid] = {"type" : InvertPDOType[locationinfos["pdotype"]], "mapping" : mapping}
        
            DictCobID[cobid]["mapping"][subindex] = (locationinfos["type"], name)
            
        else:
            if locationinfos["nodeid"] not in DictLocationsNotMapped.keys():
                DictLocationsNotMapped[locationinfos["nodeid"]] = {TPDO : [], RPDO : []}
            DictLocationsNotMapped[locationinfos["nodeid"]][locationinfos["pdotype"]].append((name, locationinfos))

    # Check Master Pdo parameters for cobid already used and remove it in ListCobIDAvailable
    ListPdoParams = [idx for idx in masternode.GetIndexes() if 0x1400 <= idx <= 0x15FF or  0x1800 <= idx <= 0x19FF]
    for idx in ListPdoParams:
        cobid = masternode.GetEntry(idx, 0x01)
        if cobid not in DictCobID.keys():
            ListCobIDAvailable.pop(cobid)
    
    #-------------------------------------------------------------------------------
    #                         Build concise DCF for the others locations
    #-------------------------------------------------------------------------------
    
    for nodeid, locations in DictLocationsNotMapped.items():
        # Get current concise DCF
        node = nodelist.SlaveNodes[nodeid]["Node"]
        nodeDCF = masternode.GetEntry(0x1F22, nodeid)
        
        if nodeDCF != None and nodeDCF != '':
            tmpnbparams = [i for i in nodeDCF[:4]]
            tmpnbparams.reverse()
            nbparams = int(''.join(["%2.2x"%ord(i) for i in tmpnbparams]), 16)
            dataparams = nodeDCF[4:]
        else:
            nbparams = 0
            dataparams = ""
        
        for pdotype in (TPDO, RPDO):
            pdosize = 0
            pdomapping = []
            for name, loc_infos in locations[pdotype]:
                pdosize += loc_infos["size"]
                # If pdo's size > 64 bits
                if pdosize > 64:
                    result = GetNewCobID(nodeid, pdotype)
                    if result:
                        SlavesPdoNumber[nodeid][pdotype] += 1
                        new_cobid, new_idx = result
                        data, nbaddedparams = GenerateMappingDCF(new_cobid, new_idx, pdomapping, False)
                        dataparams += data
                        nbparams += nbaddedparams
                        DictCobID[new_cobid] = {"type" : InvertPDOType[pdotype], "mapping" : GenerateMasterMapping(pdomapping)}
                    pdosize = loc_infos["size"]
                    pdomapping = [(name, loc_infos)]
                else:
                    pdomapping.append((name, loc_infos))
            if len(pdomapping) > 0:
                result = GetNewCobID(nodeid, pdotype)
                if result:
                    SlavesPdoNumber[nodeid][pdotype] += 1
                    new_cobid, new_idx = result
                    data, nbaddedparams = GenerateMappingDCF(new_cobid, new_idx, pdomapping, False)
                    dataparams += data
                    nbparams += nbaddedparams
                    DictCobID[new_cobid] = {"type" : InvertPDOType[pdotype], "mapping" : GenerateMasterMapping(pdomapping)}
        
        dcf = LE_to_BE(nbparams, 0x04) + dataparams
        masternode.SetEntry(0x1F22, nodeid, dcf)

        
    #-------------------------------------------------------------------------------
    #                         Master Node Configuration
    #-------------------------------------------------------------------------------
    
    # Configure Master's SDO parameters entries
    for nodeid, SDOparams in DictSDOparams.items():
        SdoClient_index = [0x1280 + nodeid]
        manager.ManageEntriesOfCurrent(SdoClient_index,[], masternode)
        if SDOparams["RSDO"] != None:
            RSDO_cobid = SDOparams["RSDO"]
        else:
            RSDO_cobid = 0x600 + nodeid 
            
        if SDOparams["TSDO"] != None:
            TSDO_cobid = SDOparams["TSDO"]
        else:
            TSDO_cobid = 0x580 + nodeid
            
        masternode.SetEntry(SdoClient_index[0], 0x01, RSDO_cobid)
        masternode.SetEntry(SdoClient_index[0], 0x02, TSDO_cobid)
        masternode.SetEntry(SdoClient_index[0], 0x03, nodeid)
    
    # Configure Master's PDO parameters entries and set cobid, transmit type
    for cobid, pdo_infos in DictCobID.items():
        current_idx = CurrentPDOParamsIdx[pdo_infos["type"]]
        addinglist = [current_idx, current_idx + 0x200]
        manager.ManageEntriesOfCurrent(addinglist, [], masternode)
        masternode.SetEntry(current_idx, 0x01, cobid)
        masternode.SetEntry(current_idx, 0x02, DefaultTransmitTypeMaster)
        if len(pdo_infos["mapping"]) > 2:
            manager.AddSubentriesToCurrent(current_idx + 0x200, len(pdo_infos["mapping"]) - 2, masternode)
        
        # Create Master's PDO mapping
        for subindex, variable in enumerate(pdo_infos["mapping"]):
            if subindex == 0:
                continue
            new_index = False
            
            if type(variable) != IntType:
                
                typeidx, varname = variable
                indexname = \
                    DictNameVariable[DictLocations[variable[1]]["pdotype"]][0] + \
                    DictLocations[variable[1]]["sizelocation"] + \
                    '_'.join(map(str,current_location)) + \
                    "_" + \
                    str(DictLocations[variable[1]]["nodeid"])
                mapvariableidx = DictNameVariable[DictLocations[variable[1]]["pdotype"]][1] +  DictNameVariable[DictLocations[variable[1]]["sizelocation"]] * DictNameVariable["increment"]

                #indexname = DictNameVariable[DictLocations[variable[1]]["pdotype"]][0] + DictLocations[variable[1]]["sizelocation"] + str(DictLocations[variable[1]]["prefix"]) + "_" + str(DictLocations[variable[1]]["nodeid"])
                #mapvariableidx = DictNameVariable[DictLocations[variable[1]]["pdotype"]][1] +  DictNameVariable[DictLocations[variable[1]]["sizelocation"]] * DictNameVariable["increment"]
                
                if not masternode.IsEntry(mapvariableidx):
                    manager.AddMapVariableToCurrent(mapvariableidx, indexname, 3, 1, masternode)
                    new_index = True
                    nbsubentries = masternode.GetEntry(mapvariableidx, 0x00)
                else:
                    nbsubentries = masternode.GetEntry(mapvariableidx, 0x00)
                    mapvariableidxbase = mapvariableidx 
                    while mapvariableidx < (mapvariableidxbase + 0x1FF) and nbsubentries == 0xFF:
                        mapvariableidx += 0x800
                        if not manager.IsCurrentEntry(mapvariableidx):
                            manager.AddMapVariableToCurrent(mapvariableidx, indexname, 3, 1, masternode)
                            new_index = True
                        nbsubentries = masternode.GetEntry(mapvariableidx, 0x00)
                
                if mapvariableidx < 0x6000:
                    if DictLocations[variable[1]]["bit"] != None:
                        subindexname = "_" + str(DictLocations[variable[1]]["index"]) + "_" + str(DictLocations[variable[1]]["subindex"]) + "_" + str(DictLocations[variable[1]]["bit"])
                    else:
                        subindexname = "_" + str(DictLocations[variable[1]]["index"]) + "_" + str(DictLocations[variable[1]]["subindex"])
                    if not new_index:
                        manager.AddSubentriesToCurrent(mapvariableidx, 1, masternode)
                        nbsubentries += 1
                    masternode.SetMappingEntry(mapvariableidx, nbsubentries, values = {"name" : subindexname})
                    masternode.SetMappingEntry(mapvariableidx, nbsubentries, values = {"type" : typeidx})
                    
                    # Map Variable
                    typeinfos = manager.GetEntryInfos(typeidx)
                    if typeinfos != None:
                        value = (mapvariableidx << 16) + ((nbsubentries) << 8) + typeinfos["size"]
                        masternode.SetEntry(current_idx + 0x200, subindex, value)
            else:
                masternode.SetEntry(current_idx + 0x200, subindex, TrashVariableValue[variable])
        
        CurrentPDOParamsIdx[pdo_infos["type"]] += 1
    #masternode.Print()
    return masternode

if __name__ == "__main__":
    from nodemanager import *
    from nodelist import *
    import sys
    
    manager = NodeManager(sys.path[0])
    nodelist = NodeList(manager)
    result = nodelist.LoadProject("/home/deobox/Desktop/TestMapping")
   
##    if result != None:
##        print result
##    else:
##        print "MasterNode :"
##        manager.CurrentNode.Print()
##        for nodeid, node in nodelist.SlaveNodes.items():
##            print "SlaveNode name=%s id=0x%2.2X :"%(node["Name"], nodeid)
##            node["Node"].Print()
            
    #filepath = "/home/deobox/beremiz/test_nodelist/listlocations.txt"
    filepath = "/home/deobox/Desktop/TestMapping/listlocations.txt"
    
    file = open(filepath,'r')
    locations = [location.split(' ') for location in [line.strip() for line in file.readlines() if len(line) > 0]] 
    file.close()
    GenerateConciseDCF(locations, 32, nodelist)
    print "MasterNode :"
    manager.CurrentNode.Print()
    #masternode.Print()