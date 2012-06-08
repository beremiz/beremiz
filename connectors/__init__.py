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


_base_path = path.split(__file__)[0]


def _GetLocalConnectorClassFactory(name):
    return lambda:getattr(__import__(name,globals(),locals()), name + "_connector_factory")

connectors = {name:_GetLocalConnectorClassFactory(name) 
                  for name in listdir(_base_path) 
                      if path.isdir(path.join(_base_path, name)) 
                          and not name.startswith("__")}

def ConnectorFactory(uri, confnodesroot):
    """
    Return a connector corresponding to the URI
    or None if cannot connect to URI
    """
    servicetype = uri.split("://")[0]
    if servicetype in connectors:
        # import module according to uri type
        connectorclass = connectors[servicetype]()
    elif servicetype == "LOCAL":
        from PYRO import PYRO_connector_factory as connectorclass
        runtime_port = confnodesroot.AppFrame.StartLocalRuntime(taskbaricon=True)
        uri="PYRO://127.0.0.1:"+str(runtime_port)
    else :
        return None    
    return connectorclass(uri, confnodesroot)

