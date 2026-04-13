#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (c) 2016 Mario de Sousa (msousa@fe.up.pt)
# Copyright (c) 2025 Edouard Tisserant (edouard@beremiz.fr)
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


from ConfigTreeNode import ConfigTreeNode
from plcopen.types_enums import LOCATION_CONFNODE, LOCATION_VAR_MEMORY


# dictionary implementing:
# key   - string with the description we want in the request plugin GUI
# tuple - (modbus function number, request type, max count value,
#          data_type, bit_size, datazone, datatacc, dataname)
#
# Client perspective: reads are inputs ("I"), writes are outputs ("Q")
modbus_function_dict = {
    "01 - Read Coils":                ('1',  'req_input', 2000, "BOOL",  1, "I", "X", "Coil"),
    "02 - Read Input Discretes":      ('2',  'req_input', 2000, "BOOL",  1, "I", "X", "Input Discrete"),
    "03 - Read Holding Registers":    ('3',  'req_input',  125, "WORD", 16, "I", "W", "Holding Register"),
    "04 - Read Input Registers":      ('4',  'req_input',  125, "WORD", 16, "I", "W", "Input Register"),
    "05 - Write Single coil":         ('5', 'req_output',    1, "BOOL",  1, "Q", "X", "Coil"),
    "06 - Write Single Register":     ('6', 'req_output',    1, "WORD", 16, "Q", "W", "Holding Register"),
    "15 - Write Multiple Coils":     ('15', 'req_output', 1968, "BOOL",  1, "Q", "X", "Coil"),
    "16 - Write Multiple Registers": ('16', 'req_output',  123, "WORD", 16, "Q", "W", "Holding Register"),
}


# dictionary implementing:
# key - string with the description we want in the request plugin GUI
# list - (modbus function number, memory area type, max count value,
#         data_type, bit_size, datazone, datatacc, dataname)
#
# Server perspective
modbus_memtype_dict = {
    "01 - Coils":            ('1', 'rw_bits',  65536, "BOOL",  1, "Q", "X", "Coil"),
    "02 - Input Discretes":  ('2', 'ro_bits',  65536, "BOOL",  1, "I", "X", "Input Discrete"),
    "03 - Holding Registers": ('3', 'rw_words', 65536, "WORD", 16, "Q", "W", "Holding Register"),
    "04 - Input Registers":  ('4', 'ro_words', 65536, "WORD", 16, "I", "W", "Input Register"),
}


modbus_serial_baudrate_list = [
    "110", "300", "600", "1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"]
modbus_serial_stopbits_list = ["1", "2"]
modbus_serial_parity_dict = {"none": 0, "odd": 1, "even": 2}


# Configuration tree value access helper
def GetCTVal(child, index):
    return child.GetParamsAttributes()[0]["children"][index]["value"]


# Configuration tree value access helper, for multiple values
def GetCTVals(child, indexes):
    return [GetCTVal(child, index) for index in indexes]


def _lt_to_str(loctuple):
    return '.'.join(map(str, loctuple))


#
#
# C L I E N T    R E Q U E S T
#
#

class _RequestPlugBase(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRequest">
        <xsd:complexType>
          <xsd:attribute name="Function" type="xsd:string" use="optional" default="01 - Read Coils"/>
          <xsd:attribute name="SlaveID" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Nr_of_Channels" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="2000"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Start_Address" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Timeout_in_ms" use="optional" default="10">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="100000"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Write_on_change" type="xsd:boolean" use="optional" default="false"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRequest":
                for child in element["children"]:
                    if child["name"] == "Function":
                        _list = list(modbus_function_dict.keys())
                        _list.sort()
                        child["type"] = _list
        return infos

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        address = self.GetParamsAttributes()[0]["children"][3]["value"]
        count = self.GetParamsAttributes()[0]["children"][2]["value"]
        function = self.GetParamsAttributes()[0]["children"][0]["value"]
        # 'BOOL' or 'WORD'
        datatype = modbus_function_dict[function][3]
        # 1 or 16
        datasize = modbus_function_dict[function][4]
        # 'X' for bits, 'W' for words
        datatacc = modbus_function_dict[function][6]
        # 'Coil', 'Holding Register', 'Input Discrete' or 'Input Register'
        dataname = modbus_function_dict[function][7]
        # start off with utility variable entries:
        # - a boolean flag to control when to execute the Modbus request
        # - a status flag for the result of the last Modbus transaction
        # - an error code flag for Modbus error frames
        #
        # NOTE: If the Modbus request has a 'current_location' of
        #          %QX1.2.3
        #       then the execution control flag will be
        #          %QX1.2.3.0.0
        #       and all the Modbus registers/coils will be
        #          %QX1.2.3.0
        #          %QX1.2.3.1
        #          %QX1.2.3.2
        #            ..
        #          %QX1.2.3.n
        entries = []
        entries.append({
            "name": "Execute request flag",
            "type": LOCATION_VAR_MEMORY,
            "size": 1,           # BOOL flag
            "IEC_type": "BOOL",  # BOOL flag
            "var_name": "var_name",
            "location": "X" + ".".join([str(i) for i in current_location]) + ".0.0",
            "description": "Modbus request execution control flag",
            "children": []})
        entries.append({
            "name": "Modbus Request Status flag",
            "type": LOCATION_VAR_MEMORY,
            "size": 8,           # BYTE flag
            "IEC_type": "BYTE",  # BYTE flag
            "var_name": "var_name",
            "location": "B" + ".".join([str(i) for i in current_location]) + ".0.1",
            "description": "Modbus request status flag (0 -> OK, 1 -> Network error, 2 -> Received invalid frame, 3 -> Timeout, 4 -> Received error frame)",
            "children": []})
        entries.append({
            "name": "Modbus Error Code",
            "type": LOCATION_VAR_MEMORY,
            "size": 8,           # BYTE flag
            "IEC_type": "BYTE",  # BYTE flag
            "var_name": "var_name",
            "location": "B" + ".".join([str(i) for i in current_location]) + ".0.2",
            "description": "Modbus Error Code received in Modbus error frame",
            "children": []})
        for offset in range(address, address + count):
            entries.append({
                "name": dataname + " " + str(offset),
                "type": LOCATION_VAR_MEMORY,
                "size": datasize,
                "IEC_type": datatype,
                "var_name": "MB_" + "".join([w[0] for w in dataname.split()]) + "_" + str(offset),
                "location": datatacc + ".".join([str(i) for i in current_location]) + "." + str(offset),
                "description": "description",
                "children": []})
        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries}

    def CTNGenerate_C(self, buildpath, locations):
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
        return [], "", False


#
#
# S E R V E R    M E M O R Y    A R E A
#
#

class _MemoryAreaPlugBase(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="MemoryArea">
        <xsd:complexType>
          <xsd:attribute name="MemoryAreaType" type="xsd:string" use="optional" default="01 - Coils"/>
          <xsd:attribute name="Nr_of_Channels" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="65536"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Start_Address" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "MemoryArea":
                for child in element["children"]:
                    if child["name"] == "MemoryAreaType":
                        _list = list(modbus_memtype_dict.keys())
                        _list.sort()
                        child["type"] = _list
        return infos

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        name = self.BaseParams.getName()
        address = self.GetParamsAttributes()[0]["children"][2]["value"]
        count = self.GetParamsAttributes()[0]["children"][1]["value"]
        function = self.GetParamsAttributes()[0]["children"][0]["value"]
        # 'BOOL' or 'WORD'
        datatype = modbus_memtype_dict[function][3]
        # 1 or 16
        datasize = modbus_memtype_dict[function][4]
        # 'X' for bits, 'W' for words
        datatacc = modbus_memtype_dict[function][6]
        # 'Coil', 'Holding Register', 'Input Discrete' or 'Input Register'
        dataname = modbus_memtype_dict[function][7]
        entries = []
        for offset in range(address, address + count):
            entries.append({
                "name": dataname + " " + str(offset),
                "type": LOCATION_VAR_MEMORY,
                "size": datasize,
                "IEC_type": datatype,
                "var_name": "MB_" + "".join([w[0] for w in dataname.split()]) + "_" + str(offset),
                "location": datatacc + ".".join([str(i) for i in current_location]) + "." + str(offset),
                "description": "description",
                "children": []})
        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": entries}

    def CTNGenerate_C(self, buildpath, locations):
        return [], "", False


#
#
# T C P    C L I E N T
#
#

class _ModbusTCPclientPlugBase(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusTCPclient">
        <xsd:complexType>
          <xsd:attribute name="Configuration_Name" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Remote_IP_Address" type="xsd:string" use="optional" default="localhost"/>
          <xsd:attribute name="Remote_Port_Number" type="xsd:string" use="optional" default="502"/>
          <xsd:attribute name="Invocation_Rate_in_ms" use="optional" default="100">
            <xsd:simpleType>
                <xsd:restriction base="xsd:unsignedLong">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Request_Delay_in_ms" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    # NOTE: Max value of 2147483647 (i32_max) for Invocation_Rate_in_ms and Request_Delay_in_ms
    # corresponds to aprox 25 days.

    # CTNChildrenTypes must be set by subclass to reference local _RequestPlug
    # PlugType must be set by subclass
    PlugType = "ModbusTCPclient"

    def __init__(self):
        loc_str = ".".join(map(str, self.GetCurrentLocation()))
        self.ModbusTCPclient.setConfiguration_Name("Modbus TCP Client " + loc_str)

    def GetNodeCount(self):
        return (1, 0, 0)

    def GetConfigName(self):
        return self.ModbusTCPclient.getConfiguration_Name()

    def CTNGenerate_C(self, buildpath, locations):
        return [], "", False


#
#
# T C P    S E R V E R
#
#

def _GetServerVariableLocationTree(self):
    """Shared GetVariableLocationTree for TCP server and RTU slave nodes."""
    current_location = self.GetCurrentLocation()
    name = self.BaseParams.getName()
    # Utility flags/counters for monitoring Modbus server activity.
    #
    # NOTE: If the Modbus slave has a 'current_location' of
    #          %QX1.2
    #       then the "Modbus Read Request Counter"  will be %MD1.2.0
    #       then the "Modbus Write Request Counter" will be %MD1.2.1
    #       then the "Modbus Read Request Flag"     will be %MD1.2.2
    #       then the "Modbus Write Request Flag"    will be %MD1.2.3
    #
    # Note that any MemoryArea contained under this server/slave
    # will ocupy the locations of type
    #          %MX or %MW
    # which will never clash with the %MD used here.
    # Additionaly, any MemoryArea contained under this server/slave
    # will ocupy locations with
    #           %M1.2.a.b (with a and b being numbers in range 0, 1, ...)
    # and therefore never ocupy the locations
    #           %M1.2.0
    #           %M1.2.1
    #           %M1.2.2
    #           %M1.2.3
    # used by the following flags/counters.
    entries = []
    entries.append({
        "name": "Modbus Read Request Counter",
        "type": LOCATION_VAR_MEMORY,
        "size": 32,           # UDINT flag
        "IEC_type": "UDINT",  # UDINT flag
        "var_name": "var_name",
        "location": "D" + ".".join([str(i) for i in current_location]) + ".0",
        "description": "Modbus read request counter",
        "children": []})
    entries.append({
        "name": "Modbus Write Request Counter",
        "type": LOCATION_VAR_MEMORY,
        "size": 32,           # UDINT flag
        "IEC_type": "UDINT",  # UDINT flag
        "var_name": "var_name",
        "location": "D" + ".".join([str(i) for i in current_location]) + ".1",
        "description": "Modbus write request counter",
        "children": []})
    entries.append({
        "name": "Modbus Read Request Flag",
        "type": LOCATION_VAR_MEMORY,
        "size": 1,            # BOOL flag
        "IEC_type": "BOOL",   # BOOL flag
        "var_name": "var_name",
        "location": "X" + ".".join([str(i) for i in current_location]) + ".2",
        "description": "Modbus read request flag",
        "children": []})
    entries.append({
        "name": "Modbus write Request Flag",
        "type": LOCATION_VAR_MEMORY,
        "size": 1,            # BOOL flag
        "IEC_type": "BOOL",   # BOOL flag
        "var_name": "var_name",
        "location": "X" + ".".join([str(i) for i in current_location]) + ".3",
        "description": "Modbus write request flag",
        "children": []})
    # recursively call all the Memory Areas under this Modbus server/slave
    for child in self.IECSortedChildren():
        entries.append(child.GetVariableLocationTree())

    return {"name": name,
            "type": LOCATION_CONFNODE,
            "location": ".".join([str(i) for i in current_location]) + ".x",
            "children": entries}


class _ModbusTCPserverPlugBase(object):
    # NOTE: the Port number is a 'string' and not an 'integer'!
    # This is because the underlying modbus library accepts strings
    # (e.g.: well known port names!)
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusServerNode">
        <xsd:complexType>
          <xsd:attribute name="Configuration_Name" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Local_IP_Address" type="xsd:string" use="optional"  default="#ANY#"/>
          <xsd:attribute name="Local_Port_Number" type="xsd:string" use="optional" default="502"/>
          <xsd:attribute name="SlaveID" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    # CTNChildrenTypes must be set by subclass to reference local _MemoryAreaPlug
    PlugType = "ModbusTCPserver"

    def __init__(self):
        loc_str = ".".join(map(str, self.GetCurrentLocation()))
        self.ModbusServerNode.setConfiguration_Name("Modbus TCP Server " + loc_str)

    def GetNodeCount(self):
        return (1, 0, 0)

    def GetIPServerPortNumbers(self):
        port = self.ModbusServerNode.getLocal_Port_Number()
        addr = self.ModbusServerNode.getLocal_IP_Address()
        return [(self.GetCurrentLocation(), addr, port)]

    def GetConfigName(self):
        return self.ModbusServerNode.getConfiguration_Name()

    def GetVariableLocationTree(self):
        return _GetServerVariableLocationTree(self)

    def CTNGenerate_C(self, buildpath, locations):
        return [], "", False


#
#
# R T U    C L I E N T
#
#

class _ModbusRTUclientPlugBase(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRTUclient">
        <xsd:complexType>
          <xsd:attribute name="Configuration_Name" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Serial_Port" type="xsd:string"  use="optional" default="/dev/ttyS0"/>
          <xsd:attribute name="Baud_Rate"   type="xsd:string"  use="optional" default="9600"/>
          <xsd:attribute name="Parity"      type="xsd:string"  use="optional" default="even"/>
          <xsd:attribute name="Stop_Bits"   type="xsd:string"  use="optional" default="1"/>
          <xsd:attribute name="Invocation_Rate_in_ms" use="optional" default="100">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="Request_Delay_in_ms" use="optional" default="0">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="2147483647"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    # CTNChildrenTypes must be set by subclass to reference local _RequestPlug
    PlugType = "ModbusRTUclient"

    def __init__(self):
        loc_str = ".".join(map(str, self.GetCurrentLocation()))
        self.ModbusRTUclient.setConfiguration_Name("Modbus RTU Client " + loc_str)

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRTUclient":
                for child in element["children"]:
                    if child["name"] == "Baud_Rate":
                        child["type"] = modbus_serial_baudrate_list
                    if child["name"] == "Stop_Bits":
                        child["type"] = modbus_serial_stopbits_list
                    if child["name"] == "Parity":
                        child["type"] = list(modbus_serial_parity_dict.keys())
        return infos

    def GetNodeCount(self):
        return (0, 1, 0)

    def GetConfigName(self):
        return self.ModbusRTUclient.getConfiguration_Name()

    def CTNGenerate_C(self, buildpath, locations):
        return [], "", False


#
#
# R T U    S L A V E
#
#

class _ModbusRTUslavePlugBase(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRTUslave">
        <xsd:complexType>
          <xsd:attribute name="Configuration_Name" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Serial_Port" type="xsd:string"  use="optional" default="/dev/ttyS0"/>
          <xsd:attribute name="Baud_Rate"   type="xsd:string"  use="optional" default="9600"/>
          <xsd:attribute name="Parity"      type="xsd:string"  use="optional" default="even"/>
          <xsd:attribute name="Stop_Bits"   type="xsd:string"  use="optional" default="1"/>
          <xsd:attribute name="SlaveID" use="optional" default="1">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="1"/>
                    <xsd:maxInclusive value="255"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    # CTNChildrenTypes must be set by subclass to reference local _MemoryAreaPlug
    PlugType = "ModbusRTUslave"

    def __init__(self):
        loc_str = ".".join(map(str, self.GetCurrentLocation()))
        self.ModbusRTUslave.setConfiguration_Name("Modbus RTU Slave " + loc_str)

    def GetParamsAttributes(self, path=None):
        infos = ConfigTreeNode.GetParamsAttributes(self, path=path)
        for element in infos:
            if element["name"] == "ModbusRTUslave":
                for child in element["children"]:
                    if child["name"] == "Baud_Rate":
                        child["type"] = modbus_serial_baudrate_list
                    if child["name"] == "Stop_Bits":
                        child["type"] = modbus_serial_stopbits_list
                    if child["name"] == "Parity":
                        child["type"] = list(modbus_serial_parity_dict.keys())
        return infos

    def GetNodeCount(self):
        return (0, 1, 0)

    def GetConfigName(self):
        return self.ModbusRTUslave.getConfiguration_Name()

    def GetVariableLocationTree(self):
        return _GetServerVariableLocationTree(self)

    def CTNGenerate_C(self, buildpath, locations):
        return [], "", False


#
#
# R O O T    C L A S S
#
#

class RootClassBase(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="ModbusRoot">
        <xsd:complexType>
          <xsd:attribute name="MaxRemoteTCPclients" use="optional" default="10">
            <xsd:simpleType>
                <xsd:restriction base="xsd:integer">
                    <xsd:minInclusive value="0"/>
                    <xsd:maxInclusive value="65535"/>
                </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    # CTNChildrenTypes must be set by subclass

    def GetNodeCount(self):
        max_remote_tcpclient = self.GetParamsAttributes()[
            0]["children"][0]["value"]
        total_node_count = (max_remote_tcpclient, 0, 0)
        for child in self.IECSortedChildren():
            total_node_count = tuple(
                x1 + x2 for x1, x2 in zip(total_node_count, child.GetNodeCount()))
        return total_node_count

    def GetIPServerPortNumbers(self):
        IPServer_port_numbers = []
        for child in self.IECSortedChildren():
            if child.CTNType == "ModbusTCPserver":
                IPServer_port_numbers.extend(child.GetIPServerPortNumbers())
        return IPServer_port_numbers

    def GetConfigNames(self):
        Node_Configuration_Names = []
        for child in self.IECSortedChildren():
            Node_Configuration_Names.extend([(child.GetCurrentLocation(), child.GetConfigName())])
        return Node_Configuration_Names

    def SupportsTarget(self, target):
        raise NotImplementedError("Subclass must implement SupportsTarget")
