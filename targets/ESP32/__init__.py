#!/usr/bin/env python
# -*- coding: utf-8 -*-

from .ESP32_target import ESP32_target
from ..toolchain_gcc_XSD import XSD as toolchain_gcc_XSD

XSD = f"""
<xsd:element name="ESP32">
    <xsd:complexType>
        <xsd:attribute name="TargetName" type="xsd:string" use="optional" default="ESP32"/>
        {toolchain_gcc_XSD}
    </xsd:complexType>
</xsd:element>
"""

