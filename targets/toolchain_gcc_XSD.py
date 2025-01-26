#!/usr/bin/env python
# -*- coding: utf-8 -*-

# separated XSD for toolchain gcc, to be included in other targets' XSD
# not in toolchain_gcc.py to avoid circular dependencies, and heavy imports at startup

XSD="""
<xsd:attribute name="Compiler" type="xsd:string" use="optional" default="gcc"/>
<xsd:attribute name="CFLAGS" type="xsd:string" use="optional" default=""/>
<xsd:attribute name="Linker" type="xsd:string" use="optional" default="gcc"/>
<xsd:attribute name="LDFLAGS" type="xsd:string" use="optional" default=""/>
"""