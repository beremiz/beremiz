# mqtt/client.py

from __future__ import absolute_import

import os
import re
import wx

from editors.ConfTreeNodeEditor import ConfTreeNodeEditor
from PLCControler import LOCATION_CONFNODE, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT
from .mqtt_client_gen import MQTTClientPanel, MQTTClientModel, MQTT_IEC_types, authParams

import util.paths as paths


# assumes that "build" directory was created in paho.mqtt.c source directory,
# and cmake build was invoked from this directory
PahoMqttCLibraryPath = paths.ThirdPartyPath("paho.mqtt.c", "build", "src")

frozen_path = paths.ThirdPartyPath("frozen")

MqttCIncludePaths = [
    paths.ThirdPartyPath("paho.mqtt.c", "build"),  # VersionInfo.h
    paths.ThirdPartyPath("paho.mqtt.c", "src"),
    frozen_path
]

class MQTTClientEditor(ConfTreeNodeEditor):
    CONFNODEEDITOR_TABS = [
        (_("MQTT Client"), "CreateMQTTClient_UI"),
        (_("Info"), "CreateInfo_UI")]

    MQTTClient_UI = None
    Info_UI = None

    def Log(self, msg):
        self.Controler.GetCTRoot().logger.write(msg)

    def CreateMQTTClient_UI(self, parent):
        self.MQTTClient_UI = MQTTClientPanel(
            parent,
            self.Controler.GetModelData(),
            self.Log,
            self.Controler.GetTypes)
        return self.MQTTClient_UI

    def CreateInfo_UI(self, parent):
        location_str = "_".join(map(str, self.Controler.GetCurrentLocation()))
        information=("Connection status GLOBAL VAR is:\n\n\tMQTT_STATUS_"+location_str
                    +", of type INT.\n\t"
                    +"0 is disconnected\n\t"
                    +"1 is connected\n")
        self.Info_UI = wx.StaticText(parent, label = information)
        return self.Info_UI

    def RefreshView(self):
        if(self.MQTTClient_UI):
            self.MQTTClient_UI.RefreshView()
        return ConfTreeNodeEditor.RefreshView(self)


class MQTTClient(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="MQTTClient">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="AuthType" minOccurs="0">
              <xsd:complexType>
                <xsd:choice minOccurs="0">
                  <xsd:element name="x509">
                    <xsd:complexType>
                      <xsd:attribute name="Client_certificate" type="xsd:string" use="optional" default="KeyStore.pem"/>
                      <xsd:attribute name="Broker_certificate" type="xsd:string" use="optional" default="TrustStore.pem"/>
                      <xsd:attribute name="Verify_hostname" type="xsd:boolean" use="optional" default="true"/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="PSK">
                    <xsd:complexType>
                      <xsd:attribute name="Secret" type="xsd:string" use="optional" default=""/>
                      <xsd:attribute name="ID" type="xsd:string" use="optional" default=""/>
                    </xsd:complexType>
                  </xsd:element>
                  <xsd:element name="UserPassword">
                    <xsd:complexType>
                      <xsd:attribute name="User" type="xsd:string" use="optional"/>
                      <xsd:attribute name="Password" type="xsd:string" use="optional"/>
                    </xsd:complexType>
                  </xsd:element>
                </xsd:choice>
              </xsd:complexType>
            </xsd:element>
          </xsd:sequence>
          <xsd:attribute name="Use_MQTT_5" type="xsd:boolean" use="optional" default="true"/>
          <xsd:attribute name="Broker_URI" type="xsd:string" use="optional" default="ws://localhost:1883"/>
          <xsd:attribute name="Client_ID" type="xsd:string" use="optional" default=""/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    EditorType = MQTTClientEditor

    def __init__(self):
        self.modeldata = MQTTClientModel(self.Log, self.CTNMarkModified)

        filepath = self.GetFileName()
        if os.path.isfile(filepath):
            self.modeldata.LoadCSV(filepath)

    def Log(self, msg):
        self.GetCTRoot().logger.write(msg)

    def GetModelData(self):
        return self.modeldata

    def GetTypes(self):
        datatype_candidates = self.GetCTRoot().GetDataTypes(basetypes=False, only_locatables=True)
        return datatype_candidates

    def GetDataTypeInfos(self, typename):
        tagname = "D::"+typename
        return self.GetCTRoot().GetDataTypeInfos(tagname)

    def GetConfig(self):
        def cfg(path): 
            try:
                attr=self.GetParamsAttributes("MQTTClient."+path)
            except ValueError:
                return None
            return attr["value"]

        AuthType = cfg("AuthType")
        res = dict(
            URI=cfg("Broker_URI"),
            AuthType=AuthType,
            clientID=cfg("Client_ID"),
            UseMQTT5=cfg("Use_MQTT_5"))

        paramList = authParams.get(AuthType, None)
        if paramList:
            for name,default in paramList:

                # Translate internal config naming into user config naming
                displayed_name = {"KeyStore"   : "Client_certificate",
                                  "TrustStore" : "Broker_certificate", 
                                  "Verify"     : "Verify_hostname"}.get(name, name)

                value = cfg("AuthType." + displayed_name)
                if value == "" or value is None:
                    value = default

                if value is not None:
                    # cryptomaterial is expected to be in project's user provided file directory

                    # User input may contain char incompatible with C string literal escaping
                    if name in ["User","Password","TrustStore","KeyStore","Broker_URI","Client_ID"]:
                        value = re.sub(r'([\"\\])',  r'\\\1', value)

                res[name] = value

        return res

    def GetFileName(self):
        return os.path.join(self.CTNPath(), 'selected.csv')

    def OnCTNSave(self, from_project_path=None):
        self.modeldata.SaveCSV(self.GetFileName())
        return True

    def CTNGenerate_C(self, buildpath, locations):
        current_location = self.GetCurrentLocation()
        locstr = "_".join(map(str, current_location))
        c_path = os.path.join(buildpath, "mqtt_client__%s.c" % locstr)

        c_code = """
#include "iec_types_all.h"
#include "beremiz.h"
"""
        config = self.GetConfig()
        c_code += self.modeldata.GenerateC(c_path, locstr, config, self.GetDataTypeInfos)

        with open(c_path, 'w') as c_file:
            c_file.write(c_code)

        if config["AuthType"] == "x509":
            static_lib = "libpaho-mqtt3cs.a"
            libs = ['-lssl', '-lcrypto']
        else:
            static_lib = "libpaho-mqtt3c.a"
            libs = []

        LDFLAGS = [' "' + os.path.join(PahoMqttCLibraryPath, static_lib) + '"'] + libs

        CFLAGS = ' '.join(['-I"' + path + '"' for path in MqttCIncludePaths])

        # TODO: add frozen only if using JSON
        frozen_c_path = os.path.join(frozen_path, "frozen.c")

        return [(c_path, CFLAGS), (frozen_c_path, CFLAGS)], LDFLAGS, True

    def GetVariableLocationTree(self):
        current_location = self.GetCurrentLocation()
        locstr = "_".join(map(str, current_location))
        name = self.BaseParams.getName()

        entries = []
        children = []

        for row in self.modeldata["output"]:
            Topic, QoS, _Retained, iec_type, iec_number = row
            entries.append((Topic, QoS, iec_type, iec_number, "Q", LOCATION_VAR_OUTPUT))

        for row in self.modeldata["input"]:
            Topic, QoS, iec_type, iec_number = row
            entries.append((Topic, QoS, iec_type, iec_number, "I", LOCATION_VAR_INPUT))

        for Topic, QoS, iec_type, iec_number, iec_dir_prefix, loc_type in entries:
            _C_type, iec_size_prefix = MQTT_IEC_types.get(iec_type,(None,""))
            c_loc_name = "__" + iec_dir_prefix + iec_size_prefix + locstr + "_" + str(iec_number)
            children.append({
                "name": Topic,
                "type": loc_type,
                "size": {"X":1, "B":8, "W":16, "D":32, "L":64, "":None}[iec_size_prefix],
                "IEC_type": iec_type,
                "var_name": c_loc_name,
                "location": "%" + iec_dir_prefix + iec_size_prefix + ".".join([str(i) for i in current_location]) + "." + str(iec_number),
                "description": "",
                "children": []})

        return {"name": name,
                "type": LOCATION_CONFNODE,
                "location": ".".join([str(i) for i in current_location]) + ".x",
                "children": children}


    def CTNGlobalInstances(self):
        location_str = "_".join(map(str, self.GetCurrentLocation()))
        return [("MQTT_STATUS_"+location_str, "INT", ""),
               ]


