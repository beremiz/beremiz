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


import os
import importlib
from os import listdir, path
from connectors.ConnectorBase import ConnectorBase

connectors_packages = ["ERPC", "WAMP"]


def _GetLocalConnectorClassFactory(name):
    return lambda: getattr(importlib.import_module(f"connectors.{name}"),
                           f"{name}_connector_factory")


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
            module = importlib.import_module(f"connectors.{con_name}_dialog")

            for scheme in module.Schemes:
                per_URI_connectors[scheme] = getattr(module, con_name + '_dialog')
                schemes += [scheme]


LocalHost = os.environ.get("BEREMIZ_LOCAL_HOST", "127.0.0.1")

def ConnectorFactory(uri, confnodesroot):
    """
    Return a connector corresponding to the URI
    or None if cannot connect to URI
    """
    _scheme = uri.split("://")[0].upper()

    if _scheme == "LOCAL":
        # Local is special case
        # ERPC connection to local runtime
        # started on demand, listening on random port
        scheme = "ERPC"
        runtime_port = confnodesroot.StartLocalRuntime()
        uri = f"ERPC://{LocalHost}:{runtime_port}"

    elif _scheme in connectors:
        scheme = _scheme
    elif _scheme[-1] == 'S' and _scheme[:-1] in connectors:
        scheme = _scheme[:-1]
    else:
        return None

    return (connectors[scheme]
            ()  # triggers import
            (uri, confnodesroot))  # creates object

def EditorClassFromScheme(scheme):
    _Import_Dialogs()
    return per_URI_connectors.get(scheme, None)


def ConnectorSchemes():
    _Import_Dialogs()
    return schemes
