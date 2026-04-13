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

#
# C code generation utilities for the original (non-Zephyr) Modbus backend.
# Generates C struct initializers for flat-array data structures used by libmb.a.
#

from modbus.modbus_base import (
    modbus_function_dict, modbus_serial_parity_dict,
    GetCTVal, GetCTVals,
)


def GetTCPServerNodePrinted(self, child):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
    """
    node_init_template = '''/*node %(locnodestr)s*/
{"%(locnodestr)s", "%(config_name)s", "%(host)s", "%(port)s", %(slaveid)s, {naf_tcp, {.tcp = {NULL, NULL, DEF_CLOSE_ON_SILENCE}}}, -1 /* mb_nd */, 0 /* init_state */}'''

    location = ".".join(map(str, child.GetCurrentLocation()))
    config_name, host, port, slaveid = GetCTVals(child, list(range(4)))
    if host == "#ANY#":
        host = ''

    node_dict = {"locnodestr": location,
                 "config_name": config_name,
                 "host": host,
                 "port": port,
                 "slaveid": slaveid}
    return node_init_template % node_dict


def GetTCPServerMemAreaPrinted(self, child, nodeid):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
            nodeid - on C code, each request has it's own parent node (sequential, 0..NUMBER_OF_NODES)
                     It's this parameter.
    return: None - if any definition error found
            The string that should be added on C code - if everything goes allright
    """
    request_dict = {}

    request_dict["locreqstr"] = "_".join(map(str, child.GetCurrentLocation()))
    request_dict["nodeid"] = str(nodeid)
    request_dict["address"] = GetCTVal(child, 2)
    if int(request_dict["address"]) not in range(65536):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid Start Address in server memory area node %(locreqstr)s (Must be in the range [0..65535])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    request_dict["count"] = GetCTVal(child, 1)
    if int(request_dict["count"]) not in range(1, 65537):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid number of channels in server memory area node %(locreqstr)s (Must be in the range [1..65536-start_address])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    if (int(request_dict["address"]) + int(request_dict["count"])) not in range(1, 65537):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid number of channels in server memory area node %(locreqstr)s (Must be in the range [1..65536-start_address])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None

    return ""


def GetRTUSlaveNodePrinted(self, child):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
    """
    node_init_template = '''/*node %(locnodestr)s*/
{"%(locnodestr)s", "%(config_name)s", "%(device)s", "",%(slaveid)s, {naf_rtu, {.rtu = {NULL, %(baud)s /*baud*/, %(parity)s /*parity*/, 8 /*data bits*/, %(stopbits)s, 0 /* ignore echo */}}}, -1 /* mb_nd */, 0 /* init_state */}'''

    location = ".".join(map(str, child.GetCurrentLocation()))
    config_name, device, baud, parity, stopbits, slaveid = GetCTVals(child, list(range(6)))

    node_dict = {"locnodestr": location,
                 "config_name": config_name,
                 "device": device,
                 "baud": baud,
                 "parity": modbus_serial_parity_dict[parity],
                 "stopbits": stopbits,
                 "slaveid": slaveid}
    return node_init_template % node_dict


def GetRTUClientNodePrinted(self, child):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
    """
    node_init_template = '''/*node %(locnodestr)s*/
{"%(locnodestr)s", "%(config_name)s", "%(device)s", "", {naf_rtu, {.rtu = {NULL, %(baud)s /*baud*/, %(parity)s /*parity*/, 8 /*data bits*/, %(stopbits)s, 0 /* ignore echo */}}}, -1 /* mb_nd */, 0 /* init_state */, %(coms_period)s /* communication period  (ms)*/, %(coms_delay)s /* inter request delay (ms)*/, 0 /* prev_error */}'''

    location = ".".join(map(str, child.GetCurrentLocation()))
    config_name, device, baud, parity, stopbits, coms_period, coms_delay = GetCTVals(child, list(range(7)))

    node_dict = {"locnodestr": location,
                 "config_name": config_name,
                 "device": device,
                 "baud": baud,
                 "parity": modbus_serial_parity_dict[parity],
                 "stopbits": stopbits,
                 "coms_period": coms_period,
                 "coms_delay": coms_delay}
    return node_init_template % node_dict


def GetTCPClientNodePrinted(self, child):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
    """
    node_init_template = '''/*node %(locnodestr)s*/
{"%(locnodestr)s", "%(config_name)s", "%(host)s", "%(port)s", {naf_tcp, {.tcp = {NULL, NULL, DEF_CLOSE_ON_SILENCE}}}, -1 /* mb_nd */, 0 /* init_state */, %(coms_period)s /* communication period (ms)*/, %(coms_delay)s /* inter request delay (ms)*/, 0 /* prev_error */}'''

    location = ".".join(map(str, child.GetCurrentLocation()))
    config_name, host, port, coms_period, coms_delay = GetCTVals(child, list(range(5)))

    node_dict = {"locnodestr": location,
                 "config_name": config_name,
                 "host": host,
                 "port": port,
                 "coms_period": coms_period,
                 "coms_delay": coms_delay}
    return node_init_template % node_dict


def GetClientRequestPrinted(self, child, nodeid):
    """
    Outputs a string to be used on C files
    params: child - the correspondent subplugin in Beremiz
            nodeid - on C code, each request has it's own parent node (sequential, 0..NUMBER_OF_NODES)
                     It's this parameter.
    return: None - if any definition error found
            The string that should be added on C code - if everything goes allright
    """

    req_init_template = '''/*request %(locreqstr)s*/
{"%(locreqstr)s", %(nodeid)s, %(slaveid)s, %(iotype)s, %(func_nr)s, %(address)s , %(count)s,
DEF_REQ_SEND_RETRIES, 0 /* mb_error_code */, 0 /* tn_error_code */, 0 /* prev_code */, {%(timeout_s)d, %(timeout_ns)d} /* timeout */, %(write_on_change)d /* write_on_change */,
{%(buffer)s}, {%(buffer)s}}'''

    timeout = int(GetCTVal(child, 4))
    timeout_s = timeout // 1000
    timeout_ms = timeout - (timeout_s * 1000)
    timeout_ns = timeout_ms * 1000000

    request_dict = {
        "locreqstr": "_".join(map(str, child.GetCurrentLocation())),
        "nodeid": str(nodeid),
        "slaveid": GetCTVal(child, 1),
        "address": GetCTVal(child, 3),
        "count": GetCTVal(child, 2),
        "write_on_change": GetCTVal(child, 5),
        "timeout": timeout,
        "timeout_s": timeout_s,
        "timeout_ns": timeout_ns,
        "buffer": ",".join(['0'] * int(GetCTVal(child, 2))),
        "func_nr": modbus_function_dict[GetCTVal(child, 0)][0],
        "iotype": modbus_function_dict[GetCTVal(child, 0)][1],
        "maxcount": modbus_function_dict[GetCTVal(child, 0)][2]}

    if int(request_dict["slaveid"]) not in range(256):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid slaveID in TCP client request node %(locreqstr)s (Must be in the range [0..255])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    if int(request_dict["address"]) not in range(65536):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid Start Address in TCP client request node %(locreqstr)s (Must be in the range [0..65535])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    if int(request_dict["count"]) not in range(1, 1 + int(request_dict["maxcount"])):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid number of channels in TCP client request node %(locreqstr)s (Must be in the range [1..%(maxcount)s])\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    if (int(request_dict["address"]) + int(request_dict["count"])) not in range(1, 65537):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: Invalid number of channels in TCP client request node %(locreqstr)s (start_address + nr_channels must be less than 65536)\nModbus plugin: Aborting C code generation for this node\n" % request_dict)
        return None
    if (request_dict["write_on_change"] and (request_dict["iotype"] == 'req_input')):
        self.GetCTRoot().logger.write_error(
            "Modbus plugin: (warning) MB client request node %(locreqstr)s has option 'write_on_change' enabled.\nModbus plugin: This option will be ignored by the Modbus read function.\n" % request_dict)

    return req_init_template % request_dict
