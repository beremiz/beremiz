#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (c) 2016 Mario de Sousa (msousa@fe.up.pt)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# This code is made available on the understanding that it will not be
# used in safety-critical situations without a full and competent review.


import os

from modbus.modbus_base import (
    _RequestPlugBase, _MemoryAreaPlugBase,
    _ModbusTCPclientPlugBase, _ModbusTCPserverPlugBase,
    _ModbusRTUmasterPlugBase, _ModbusRTUslavePlugBase,
    RootClassBase,
    modbus_function_dict, modbus_memtype_dict,
    GetCTVal, _lt_to_str,
)
from modbus.mb_utils import (
    GetTCPServerNodePrinted, GetTCPServerMemAreaPrinted,
    GetRTUSlaveNodePrinted, GetRTUClientNodePrinted,
    GetTCPClientNodePrinted, GetClientRequestPrinted,
)
import util.paths as paths

ModbusPath = paths.ThirdPartyPath("Modbus")


class _RequestPlug(_RequestPlugBase):
    pass


class _MemoryAreaPlug(_MemoryAreaPlugBase):
    pass


class _ModbusTCPclientPlug(_ModbusTCPclientPlugBase):
    CTNChildrenTypes = [("ModbusRequest", _RequestPlug, "Request")]


class _ModbusTCPserverPlug(_ModbusTCPserverPlugBase):
    CTNChildrenTypes = [("MemoryArea", _MemoryAreaPlug, "Memory Area")]


class _ModbusRTUmasterPlug(_ModbusRTUmasterPlugBase):
    CTNChildrenTypes = [("ModbusRequest", _RequestPlug, "Request")]


class _ModbusRTUslavePlug(_ModbusRTUslavePlugBase):
    CTNChildrenTypes = [("MemoryArea", _MemoryAreaPlug, "Memory Area")]


class RootClass(RootClassBase):
    CTNChildrenTypes = [("ModbusTCPclient", _ModbusTCPclientPlug, "Modbus TCP Client"),
                        ("ModbusTCPserver", _ModbusTCPserverPlug, "Modbus TCP Server"),
                        ("ModbusRTUmaster", _ModbusRTUmasterPlug, "Modbus RTU Client"),
                        ("ModbusRTUslave", _ModbusRTUslavePlug,  "Modbus RTU Slave")]

    def SupportsTarget(self, target):
        return target.GetTargetName() != "Zephyr"

    def CTNGenerate_C(self, buildpath, locations):
        loc_dict = {"locstr": "_".join(map(str, self.GetCurrentLocation()))}

        # Determine the number of (modbus library) nodes ALL instances of the modbus plugin will need
        #   total_node_count: (tcp nodes, rtu nodes, ascii nodes)
        #
        # Also get a list with tuples of (location, IP address, port number) used by all the Modbus/IP server nodes
        #   This list is later used to search for duplicates in port numbers!
        #   IPServer_port_numbers = [(location, IP address, port number), ...]
        #
        # Also get a list with tuples of (location, Configuration_Name) used by all the Modbus nodes
        #   This list is later used to search for duplicates in Configuration Names!
        total_node_count = (0, 0, 0)
        IPServer_port_numbers    = []
        Node_Configuration_Names = []
        for CTNInstance in self.GetCTRoot().IterChildren():
            if CTNInstance.CTNType == "modbus":
                total_node_count = tuple(x1 + x2 for x1, x2 in zip(total_node_count, CTNInstance.GetNodeCount()))
                IPServer_port_numbers.   extend(CTNInstance.GetIPServerPortNumbers())
                Node_Configuration_Names.extend(CTNInstance.GetConfigNames        ())

        # Search for use of duplicate Configuration_Names by Modbus nodes
        for i in range(0, len(Node_Configuration_Names) - 1):
            for j in range(i + 1, len(Node_Configuration_Names)):
                if Node_Configuration_Names[i][1] == Node_Configuration_Names[j][1]:
                    error_message = _("Error: Modbus plugin nodes %{a1}.x and %{a2}.x use the same Configuration_Name \"{a3}\".\n").format(
                                        a1=_lt_to_str(Node_Configuration_Names[i][0]),
                                        a2=_lt_to_str(Node_Configuration_Names[j][0]),
                                        a3=Node_Configuration_Names[j][1])
                    self.FatalError(error_message)

        # Search for use of duplicate port numbers by Modbus/IP servers
        # Note: We only consider duplicate port numbers if using the same network interface!
        i = 0
        for loc1, addr1, port1 in IPServer_port_numbers[:-1]:
            i = i + 1
            for loc2, addr2, port2 in IPServer_port_numbers[i:]:
                if (port1 == port2) and (
                          (addr1 == addr2)   # on the same network interface
                       or (addr1 == "") or (addr1 == "*") or (addr1 == "#ANY#") # or one (or both) of the servers
                       or (addr2 == "") or (addr2 == "*") or (addr2 == "#ANY#") # use all available network interfaces
                   ):
                    error_message = _("Error: Modbus plugin nodes %{a1}.x and %{a2}.x use same port number \"{a3}\" " +
                                      "on the same (or overlapping) network interfaces \"{a4}\" and \"{a5}\".\n").format(
                                        a1=_lt_to_str(loc1), a2=_lt_to_str(loc2), a3=port1, a4=addr1, a5=addr2)
                    self.FatalError(error_message)

        # Determine the current location in Beremiz's project configuration tree
        current_location = self.GetCurrentLocation()

        # define a unique name for the generated C and h files
        prefix = "_".join(map(str, current_location))
        Gen_MB_c_path = os.path.join(buildpath, "MB_%s.c" % prefix)
        Gen_MB_h_path = os.path.join(buildpath, "MB_%s.h" % prefix)
        c_filename = os.path.join(os.path.split(__file__)[0], "mb_runtime.c")
        h_filename = os.path.join(os.path.split(__file__)[0], "mb_runtime.h")

        tcpclient_reqs_count = 0
        rtuclient_reqs_count = 0
        ascclient_reqs_count = 0
        tcpclient_node_count = 0
        rtuclient_node_count = 0
        ascclient_node_count = 0
        tcpserver_node_count = 0
        rtuserver_node_count = 0
        ascserver_node_count = 0
        nodeid = 0
        client_nodeid = 0
        client_requestid = 0
        server_id = 0

        server_node_list = []
        client_node_list = []
        client_request_list = []
        server_memarea_list = []
        loc_vars = []
        loc_vars_list = []  # list of variables already declared in C code!
        for child in self.IECSortedChildren():
            if child.PlugType == "ModbusTCPserver":
                tcpserver_node_count += 1
                new_node = GetTCPServerNodePrinted(self, child)
                if new_node is None:
                    return [], "", False
                server_node_list.append(new_node)
                #        We currently add 4 flags/counters to each Modbus server/slave
                for iecvar in child.GetLocations():
                    if (len(iecvar["LOC"]) == 3) and (str(iecvar["NAME"]) not in loc_vars_list):
                        if iecvar["LOC"][2] == 0:
                            loc_vars.append("u32 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_read_req_counter;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["LOC"][2] == 1:
                            loc_vars.append("u32 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_write_req_counter;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["LOC"][2] == 2:
                            loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_read_req_flag;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["LOC"][2] == 3:
                            loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_write_req_flag;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))

                for subchild in child.IECSortedChildren():
                    new_memarea = GetTCPServerMemAreaPrinted(self, subchild, nodeid)
                    if new_memarea is None:
                        return [], "", False
                    server_memarea_list.append(new_memarea)
                    function = subchild.GetParamsAttributes()[0]["children"][0]["value"]
                    memarea = modbus_memtype_dict[function][1]
                    for iecvar in subchild.GetLocations():
                        if len(iecvar["LOC"]) == 4:
                            absloute_address = iecvar["LOC"][3]
                            start_address = int(GetCTVal(subchild, 2))
                            relative_addr = absloute_address - start_address
                            if relative_addr in range(int(GetCTVal(subchild, 1))):
                                if str(iecvar["NAME"]) not in loc_vars_list:
                                    loc_vars.append("u16 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.%s[%d];" % (
                                        server_id, memarea, absloute_address))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                server_id += 1
            #
            if child.PlugType == "ModbusRTUslave":
                rtuserver_node_count += 1
                new_node = GetRTUSlaveNodePrinted(self, child)
                if new_node is None:
                    return [], "", False
                server_node_list.append(new_node)
                for iecvar in child.GetLocations():
                    if (len(iecvar["LOC"]) == 3) and (str(iecvar["NAME"]) not in loc_vars_list):
                        if iecvar["LOC"][2] == 0:
                            loc_vars.append("u32 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_read_req_counter;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["LOC"][2] == 1:
                            loc_vars.append("u32 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_write_req_counter;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["LOC"][2] == 2:
                            loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_read_req_flag;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))
                        if iecvar["LOC"][2] == 3:
                            loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.flag_write_req_flag;" % (server_id))
                            loc_vars_list.append(str(iecvar["NAME"]))

                for subchild in child.IECSortedChildren():
                    new_memarea = GetTCPServerMemAreaPrinted(
                        self, subchild, nodeid)
                    if new_memarea is None:
                        return [], "", False
                    server_memarea_list.append(new_memarea)
                    function = subchild.GetParamsAttributes()[0]["children"][0]["value"]
                    memarea = modbus_memtype_dict[function][1]
                    for iecvar in subchild.GetLocations():
                        if len(iecvar["LOC"]) == 4:
                            absloute_address = iecvar["LOC"][3]
                            start_address = int(GetCTVal(subchild, 2))
                            relative_addr = absloute_address - start_address
                            if relative_addr in range(int(GetCTVal(subchild, 1))):
                                if str(iecvar["NAME"]) not in loc_vars_list:
                                    loc_vars.append("u16 *" + str(iecvar["NAME"]) + " = &server_nodes[%d].mem_area.%s[%d];" % (
                                        server_id, memarea, absloute_address))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                server_id += 1
            #
            if child.PlugType == "ModbusTCPclient":
                tcpclient_reqs_count += len(child.IECSortedChildren())
                new_node = GetTCPClientNodePrinted(self, child)
                if new_node is None:
                    return [], "", False
                client_node_list.append(new_node)
                for subchild in child.IECSortedChildren():
                    new_req = GetClientRequestPrinted(
                        self, subchild, client_nodeid)
                    if new_req is None:
                        return [], "", False
                    client_request_list.append(new_req)
                    for iecvar in subchild.GetLocations():
                        relative_addr = iecvar["LOC"][3] - int(GetCTVal(subchild, 3))
                        if (        relative_addr in range(int(GetCTVal(subchild, 2)))
                            and len(iecvar["LOC"]) < 5):
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                loc_vars.append("u16 *" + str(iecvar["NAME"]) + " = &client_requests[%d].plcv_buffer[%d];" % (client_requestid, relative_addr))
                                loc_vars_list.append(str(iecvar["NAME"]))
                        if  len(iecvar["LOC"]) >= 5:
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                if iecvar["LOC"][4] == 0:
                                    loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &client_requests[%d].flag_exec_req;" % (client_requestid))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                                if iecvar["LOC"][4] == 1:
                                    loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &client_requests[%d].flag_tn_error_code;" % (client_requestid))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                                if iecvar["LOC"][4] == 2:
                                    loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &client_requests[%d].flag_mb_error_code;" % (client_requestid))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                    client_requestid += 1
                tcpclient_node_count += 1
                client_nodeid += 1
            #
            if child.PlugType == "ModbusRTUmaster":
                rtuclient_reqs_count += len(child.IECSortedChildren())
                new_node = GetRTUClientNodePrinted(self, child)
                if new_node is None:
                    return [], "", False
                client_node_list.append(new_node)
                for subchild in child.IECSortedChildren():
                    new_req = GetClientRequestPrinted(
                        self, subchild, client_nodeid)
                    if new_req is None:
                        return [], "", False
                    client_request_list.append(new_req)
                    for iecvar in subchild.GetLocations():
                        relative_addr = iecvar["LOC"][3] - int(GetCTVal(subchild, 3))
                        if (        relative_addr in range(int(GetCTVal(subchild, 2)))
                            and len(iecvar["LOC"]) < 5):
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                loc_vars.append(
                                    "u16 *" + str(iecvar["NAME"]) + " = &client_requests[%d].plcv_buffer[%d];" % (client_requestid, relative_addr))
                                loc_vars_list.append(str(iecvar["NAME"]))
                        if  len(iecvar["LOC"]) >= 5:
                            if str(iecvar["NAME"]) not in loc_vars_list:
                                if iecvar["LOC"][4] == 0:
                                    loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &client_requests[%d].flag_exec_req;" % (client_requestid))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                                if iecvar["LOC"][4] == 1:
                                    loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &client_requests[%d].flag_tn_error_code;" % (client_requestid))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                                if iecvar["LOC"][4] == 2:
                                    loc_vars.append("u8 *" + str(iecvar["NAME"]) + " = &client_requests[%d].flag_mb_error_code;" % (client_requestid))
                                    loc_vars_list.append(str(iecvar["NAME"]))
                    client_requestid += 1
                rtuclient_node_count += 1
                client_nodeid += 1
            nodeid += 1

        loc_dict["loc_vars"] = "\n".join(loc_vars)
        loc_dict["server_nodes_params"] = ",\n\n".join(server_node_list)
        loc_dict["client_nodes_params"] = ",\n\n".join(client_node_list)
        loc_dict["client_req_params"] = ",\n\n".join(client_request_list)
        loc_dict["tcpclient_reqs_count"] = str(tcpclient_reqs_count)
        loc_dict["tcpclient_node_count"] = str(tcpclient_node_count)
        loc_dict["tcpserver_node_count"] = str(tcpserver_node_count)
        loc_dict["rtuclient_reqs_count"] = str(rtuclient_reqs_count)
        loc_dict["rtuclient_node_count"] = str(rtuclient_node_count)
        loc_dict["rtuserver_node_count"] = str(rtuserver_node_count)
        loc_dict["ascclient_reqs_count"] = str(ascclient_reqs_count)
        loc_dict["ascclient_node_count"] = str(ascclient_node_count)
        loc_dict["ascserver_node_count"] = str(ascserver_node_count)
        loc_dict["total_tcpnode_count"] = str(total_node_count[0])
        loc_dict["total_rtunode_count"] = str(total_node_count[1])
        loc_dict["total_ascnode_count"] = str(total_node_count[2])
        loc_dict["max_remote_tcpclient"] = int(
            self.GetParamsAttributes()[0]["children"][0]["value"])

        # get template file content into a string, format it with dict
        # and write it to proper .h file
        mb_main = open(h_filename).read() % loc_dict
        f = open(Gen_MB_h_path, 'w')
        f.write(mb_main)
        f.close()
        # same thing as above, but now to .c file
        mb_main = open(c_filename).read() % loc_dict
        f = open(Gen_MB_c_path, 'w')
        f.write(mb_main)
        f.close()

        LDFLAGS = []
        LDFLAGS.append(" \"-L" + ModbusPath + "\"")
        LDFLAGS.append(" \"" + os.path.join(ModbusPath, "libmb.a") + "\"")
        LDFLAGS.append(" \"-Wl,-rpath," + ModbusPath + "\"")

        websettingfile = open(paths.AbsNeighbourFile(__file__, "web_settings.py"), 'r')
        websettingcode = websettingfile.read()
        websettingfile.close()

        location_str = "_".join(map(str, self.GetCurrentLocation()))
        websettingcode = websettingcode % locals()

        runtimefile_path = os.path.join(buildpath, "runtime_modbus_websettings.py")
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write(websettingcode)
        runtimefile.close()

        return ([(Gen_MB_c_path, ' -I"' + ModbusPath + '"')], LDFLAGS, True,
                ("runtime_%s_modbus_websettings.py" % location_str, open(runtimefile_path, "rb")),
        )
