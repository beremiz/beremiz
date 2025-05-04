#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.

from C_runtime.zephyr import GetZephyrXSDChoices
  
XSD=f"""
<xsd:element name="Zephyr">
    <xsd:complexType>
        <xsd:sequence>
            <xsd:element name="Board">
                <xsd:complexType>
                    <xsd:choice minOccurs="1">
                    """ + GetZephyrXSDChoices() + """
                    </xsd:choice>
                </xsd:complexType>
            </xsd:element>    
        </xsd:sequence>
        <xsd:attribute name="VersionString" type="xsd:string" use="optional" default="">
            <xsd:annotation><xsd:documentation>
                Arbitrary user given version string, available from PLC programs as PLC_VERSION_STRING.
            </xsd:documentation></xsd:annotation>
        </xsd:attribute>
        <xsd:attribute name="DebugBuild" type="xsd:boolean" use="optional" default="false">
            <xsd:annotation><xsd:documentation>
                <![CDATA[GCC debug build (-g).
This option is used to enable debug information in the generated binary.
Usefull for low level debugging with tools such as GDB.]]>
            </xsd:documentation></xsd:annotation>
        </xsd:attribute>
        <xsd:attribute name="VerboseBuild" type="xsd:boolean" use="optional" default="false">
            <xsd:annotation><xsd:documentation>
                Produce verbose output when building.
            </xsd:documentation></xsd:annotation>
        </xsd:attribute>
    </xsd:complexType>
</xsd:element>
"""
