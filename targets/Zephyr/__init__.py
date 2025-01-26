#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.


from ..toolchain_gcc_XSD import XSD as toolchain_gcc_XSD

# TODO one deduce boards from directories

XSD=f"""
<xsd:element name="Zephyr">
    <xsd:complexType>
        <xsd:attribute name="BoardName" type="xsd:string" use="optional" default="native_sim/native/64"/>
        <xsd:attribute name="Programmable" type="xsd:boolean" use="optional" default="true"/>
    </xsd:complexType>
</xsd:element>
"""
