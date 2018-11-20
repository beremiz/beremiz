#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
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


from __future__ import absolute_import
from os import listdir, path
import util.paths as paths

connectors_packages = ["PYRO","WAMP"]


def _GetLocalConnectorClassFactory(name):
    return lambda: getattr(__import__(name, globals(), locals()), name + "_connector_factory")


connectors = {name: _GetLocalConnectorClassFactory(name)
              for name in connectors_packages}

_dialogs_imported = False
per_URI_connectors = None
schemes = None 

# lazy import of connectors dialogs, only if used
def _Import_Dialogs():
    global per_URI_connectors, schemes, _dialogs_imported
    if not _dialogs_imported: 
        _dialogs_imported = True
        per_URI_connectors = {}
        schemes = []
        for con_name in connectors_packages:
            module =  __import__(con_name + '_dialog', globals(), locals())

            for scheme in module.Schemes:
                per_URI_connectors[scheme] = getattr(module, con_name + '_dialog')
                schemes += [scheme]


def ConnectorFactory(uri, confnodesroot):
    """
    Return a connector corresponding to the URI
    or None if cannot connect to URI
    """
    scheme = uri.split("://")[0].upper()
    if scheme == "LOCAL":
        # Local is special case
        # pyro connection to local runtime
        # started on demand, listening on random port
        scheme = "PYRO"
        runtime_port = confnodesroot.AppFrame.StartLocalRuntime(
            taskbaricon=True)
        uri = "PYROLOC://127.0.0.1:" + str(runtime_port)
    elif scheme in connectors:
        pass
    elif scheme[-1] == 'S' and scheme[:-1] in connectors:
        scheme = scheme[:-1]
    else:
        return None

    # import module according to uri type
    connectorclass = connectors[scheme]()
    return connectorclass(uri, confnodesroot)


def EditorClassFromScheme(scheme):
    _Import_Dialogs()
    return per_URI_connectors.get(scheme, None) 

def ConnectorSchemes():
    _Import_Dialogs()
    return schemes
