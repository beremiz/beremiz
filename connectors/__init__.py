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

from os import listdir, path

import PYRO

_base_path = path.split(__file__)[0]

connector_types = [name for name in listdir(_base_path)
                        if path.isdir(path.join(_base_path, name))
                            and name.lower() != ".hg"
                            and not name.startswith("__")]

# a dict from a URI scheme (connector name) to connector module
connector_modules = {}

# a dict from a DNS-SD service type to a connector module that support it
dnssd_connectors = {}

for t in connector_types:
    new_module = getattr(__import__("connectors." + t), t)
    connector_modules[t] = new_module
    
    if hasattr(new_module, "supported_dnssd_services"):
        for st in new_module.supported_dnssd_services:
            dnssd_connectors[st] = new_module

def ConnectorFactory(uri, pluginsroot):
    """
    Return a connector corresponding to the URI
    or None if cannot connect to URI
    """
    servicetype = uri.split("://")[0]
    if servicetype in connector_types:
        # import module according to uri type
        connectormodule = connector_modules[servicetype]
        factoryname = servicetype + "_connector_factory"
        return getattr(connectormodule, factoryname)(uri, pluginsroot)
    elif servicetype == "LOCAL":
        runtime_port = pluginsroot.AppFrame.StartLocalRuntime(taskbaricon=True)
        return PYRO.PYRO_connector_factory(
                       "PYRO://127.0.0.1:"+str(runtime_port), 
                       pluginsroot)
    else :
        return None    

