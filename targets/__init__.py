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
def _GetLocalTargetClassFactory(name):
    return lambda:getattr(__import__(name,globals(),locals()), name+"_target")

targets = dict([(name, {"xsd":path.join(_base_path, name, "XSD"), 
                        "class":_GetLocalTargetClassFactory(name),
                        "code": path.join(path.split(__file__)[0],name,"plc_%s_main.c"%name)})
                for name in listdir(_base_path) 
                    if path.isdir(path.join(_base_path, name)) 
                       and not name.startswith("__")])

toolchains = {"gcc":  path.join(_base_path, "XSD_toolchain_gcc")}

def GetBuilder(targetname):
    return targets[targetname]["class"]()

def GetTargetChoices():
    DictXSD_toolchain = {}
    targetchoices = ""

    # Get all xsd toolchains
    for toolchainname,xsdfilename in toolchains.iteritems() :
         if path.isfile(xsdfilename):
             xsd_toolchain_string = ""
             for line in open(xsdfilename).readlines():
                 xsd_toolchain_string += line
             DictXSD_toolchain["toolchain_"+toolchainname] = xsd_toolchain_string

    # Get all xsd targets 
    for targetname,nfo in targets.iteritems():
        xsd_string = open(nfo["xsd"]).read()
        targetchoices +=  xsd_string%DictXSD_toolchain

    return targetchoices

def GetTargetCode(targetname):
    return open(targets[targetname]["code"]).read()

def GetHeader():
    filename = path.join(path.split(__file__)[0],"beremiz.h")
    return open(filename).read()

def GetCode(name):
    filename = path.join(path.split(__file__)[0],name + ".c")
    return open(filename).read()

