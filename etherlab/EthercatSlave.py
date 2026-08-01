#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
#
# Copyright (C) 2011-2014: Laurent BESSARD, Edouard TISSERANT
#                          RTES Lab : CRKim, JBLee, youcu
#                          Higen Motor : Donggu Kang
#
# See COPYING file for copyrights details.



from plcopen.types_enums import LOCATION_CONFNODE, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY
from ConfigTreeNode import ConfigTreeNode

from etherlab.ConfigEditor import NodeEditor

# ------------------------------------------
from etherlab.CommonEtherCATFunction import _CommonSlave
# ------------------------------------------


TYPECONVERSION = {"BOOL": "X", "SINT": "B", "INT": "W", "DINT": "D", "LINT": "L",
                  "USINT": "B", "UINT": "W", "UDINT": "D", "ULINT": "L",
                  "BYTE": "B", "WORD": "W", "DWORD": "D", "LWORD": "L"}

DATATYPECONVERSION = {"BOOL": "BIT", "SINT": "S8", "INT": "S16", "DINT": "S32", "LINT": "S64",
                      "USINT": "U8", "UINT": "U16", "UDINT": "U32", "ULINT": "U64",
                      "BYTE": "U8", "WORD": "U16", "DWORD": "U32", "LWORD": "U64"}

VARCLASSCONVERSION = {"T": LOCATION_VAR_INPUT, "R": LOCATION_VAR_OUTPUT, "RT": LOCATION_VAR_MEMORY}


def ExtractHexDecValue(value):
    try:
        return int(value)
    except Exception:
        pass
    try:
        return int(value.replace("#", "0"), 16)
    except Exception:
        raise ValueError("Invalid value for HexDecValue \"%s\"" % value)


def GenerateHexDecValue(value, base=10):
    if base == 10:
        return str(value)
    elif base == 16:
        return "#x%.8x" % value
    else:
        raise ValueError("Not supported base")


def ExtractName(names, default=None):
    if len(names) == 1:
        return names[0].getcontent()
    else:
        for name in names:
            if name.getLcId() == 1033:
                return name.getcontent()
    return default

PDO ="""<xsd:attribute name="RxPDO" type="xsd:string" use="optional" default=""/>
<xsd:attribute name="TxPDO" type="xsd:string" use="optional" default=""/>
"""

# --------------------------------------------------
#                    Ethercat Node
# --------------------------------------------------

class _EthercatSlaveCTN(object):
    NODE_PROFILE = None
    EditorType = NodeEditor

    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">

      <xsd:element name="EthercatSlaveParams">
        <xsd:complexType>
          <xsd:sequence/>
          %s
        </xsd:complexType>
      </xsd:element>

    </xsd:schema>
    """ % PDO

    def __init__(self):
        # ----------- call ethercat mng. function --------------
        self.CommonMethod = _CommonSlave(self)
        self.SelectedRxPDOIndex = []
        self.SelectedTxPDOIndex = []

    def GetSlaveParams(self):
        """
        PDO and DC parameters of this slave, whatever the XSD root element is
        called : plain slaves store them in EthercatSlaveParams, CiA402 slaves
        in CIA402SlaveParams.
        @return the confnode parameters object, None when there is none
        """
        return self.CTNParams[1] if self.CTNParams else None

    def GetIconName(self):
        return "Slave"

    def ExtractHexDecValue(self, value):
        return ExtractHexDecValue(value)

    def GetSizeOfType(self, type):
        return TYPECONVERSION.get(self.GetCTRoot().GetBaseType(type), None)

    def GetSlavePos(self):
        return self.BaseParams.getIEC_Channel()

    def GetParamsAttributes(self, path=None):
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
                    'children': [],
                    'doc': [{"documentation": "EtherCAT slave parameters"}]
                })

            slave_type = self.CTNParent.GetSlaveType(self.GetSlavePos())
            params[0]['children'].insert(
                0,
                {
                    'use': 'optional',
                    'type': self.CTNParent.GetSlaveTypesLibrary(self.NODE_PROFILE),
                    'name': 'Type',
                    'value': (slave_type["device_type"], slave_type),
                    'doc': [{"documentation": "EtherCAT slave type"}]
                })
            return params

    def SetParamsAttribute(self, path, value):
        self.GetSlaveInfos()
        position = self.BaseParams.getIEC_Channel()

        # "Type" is shown among the confnode parameters but stored in the
        # master network configuration, so it is handled here rather than by
        # ConfigTreeNode. The parameters editor prefixes it with the XSD root
        # element name, the master calls it by its bare name.
        root = self.CTNParams[0] if self.CTNParams else "SlaveParams"

        if path in ("SlaveParams.Type", "%s.Type" % root):
            self.CTNParent.SetSlaveType(position, value)
            slave_type = self.CTNParent.GetSlaveType(self.GetSlavePos())
            return slave_type["device_type"], True

        value, refresh = ConfigTreeNode.SetParamsAttribute(self, path, value)

        # IEC_Channel is the ring position of the slave, keep the network
        # configuration in sync when it changes
        if path == "BaseParams.IEC_Channel" and value != position:
            self.CTNParent.SetSlavePosition(position, value)

        return value, refresh

    def GetSlaveInfos(self):
        return self.CTNParent.GetSlaveInfos(self.GetSlavePos())

    def GetSlaveVariables(self, limits):
        return self.CTNParent.GetSlaveVariables(self.GetSlavePos(), limits)

    def GetVariableLocationTree(self):
        return {
            "name": self.BaseParams.getName(),
            "type": LOCATION_CONFNODE,
            "location": self.GetFullIEC_Channel(),
            "children": self.CTNParent.GetDeviceLocationTree(self.GetSlavePos(), self.GetCurrentLocation(), self.BaseParams.getName())
        }

    def CTNGenerate_C(self, buildpath, locations):
        return [], "", False
