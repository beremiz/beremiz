#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.


XSD="""
<xsd:element name="Generic">
    <xsd:complexType>                    
        <xsd:attribute name="Command" type="xsd:string" use="optional" default="make -C %(buildpath)s -f ../project_files/Makefile all BEREMIZSRC=%(src)s BEREMIZCFLAGS=%(cflags)s MD5=%(md5)s USE_BEREMIZ=1 FROM_BEREMIZ=1"/>
    </xsd:complexType>
</xsd:element>
"""