#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.


from ..toolchain_gcc_XSD import XSD as toolchain_gcc_XSD

XSD=f"""
<xsd:element name="Linux">
    <xsd:complexType>
        <xsd:attribute name="RealTime" type="xsd:boolean" use="optional" default="false"/>
        {toolchain_gcc_XSD}
    </xsd:complexType>
</xsd:element>
"""
