#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# Package initialisation
#import targets

"""
Beremiz Targets

- Target are python packages, containing at least one "XSD" file
- Target class may inherit from a toolchain_(toolchainname)
- The target folder's name must match to name define in the XSD for TargetType
"""

from os import listdir, path

_base_path = path.split(__file__)[0]

targets = [name for name in listdir(_base_path) 
                   if path.isdir(path.join(_base_path, name)) 
                       and not name.startswith("__")]
toolchains = [name for name in listdir(_base_path) 
                       if not path.isdir(path.join(_base_path, name)) 
                            and name.endswith(".py") 
                            and not name.startswith("__") 
                            and not name.endswith(".pyc")]

DictXSD_toolchain = {}
DictXSD_target = {}

targetchoices = ""

# Get all xsd toolchains
for toolchain in toolchains :
     toolchainname = path.splitext(toolchain)[0]
     xsdfilename = path.join(_base_path, "XSD_%s"%(toolchainname))
     if path.isfile(xsdfilename):
         xsd_toolchain_string = ""
         for line in open(xsdfilename).readlines():
             xsd_toolchain_string += line
         DictXSD_toolchain[toolchainname] = xsd_toolchain_string

# Get all xsd targets 
for targetname in targets:
    xsdfilename = path.join(_base_path, targetname, "XSD")
    if path.isfile(xsdfilename):
        xsd_target_string = ""
        for line in open(xsdfilename).readlines():
            xsd_target_string += line
        DictXSD_target[targetname] = xsd_target_string%DictXSD_toolchain

for target in DictXSD_target.keys():
    targetchoices += DictXSD_target[target]

def targetcode(target_name, code_name=None):
    if code_name is None:
        code_name="plc_%s_main.c"%target_name
    filename = path.join(path.split(__file__)[0], target_name, code_name)
    return open(filename).read()

def code(name):
    filename = path.join(path.split(__file__)[0],name + ".c")
    return open(filename).read()

