#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# Package initialisation

from os import listdir, path


_base_path = path.split(__file__)[0]


def _GetLocalConnectorClassFactory(name):
    return lambda: getattr(__import__(name, globals(), locals()), name + "_connector_factory")

connectors = {name:_GetLocalConnectorClassFactory(name)
                  for name in listdir(_base_path)
                      if path.isdir(path.join(_base_path, name))
                          and not name.startswith("__")}


def ConnectorFactory(uri, confnodesroot):
    """
    Return a connector corresponding to the URI
    or None if cannot connect to URI
    """
    servicetype = uri.split("://")[0].upper()
    if servicetype == "LOCAL":
        # Local is special case
        # pyro connection to local runtime
        # started on demand, listening on random port
        servicetype = "PYRO"
        runtime_port = confnodesroot.AppFrame.StartLocalRuntime(
            taskbaricon=True)
        uri = "PYROLOC://127.0.0.1:" + str(runtime_port)
    elif servicetype in connectors:
        pass
    elif servicetype[-1] == 'S' and servicetype[:-1] in connectors:
        servicetype = servicetype[:-1]
    else:
        return None

    # import module according to uri type
    connectorclass = connectors[servicetype]()
    return connectorclass(uri, confnodesroot)
