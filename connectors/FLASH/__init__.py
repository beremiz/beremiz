#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Written by Edouard TISSERANT (C) 2025
# This file is part of Beremiz IDE
# See COPYING file for copyrights details.

# Flashing connector - delegate transfer to builder, connects to nothing

import os.path
import re
import traceback
from inspect import getmembers, isfunction

from runtime import PlcStatus
from runtime.loglevels import LogLevelsCount

# Re-use ERPC interface definition to make a conforming PLCObject ersatz
from erpc_interface.erpc_PLCObject.interface import IBeremizPLCObjectService
from connectors.ConnectorBase import ConnectorBase

NOP_PLCObject = type(
    "NOP_PLCObject",
    (ConnectorBase,),
    {name: lambda self, *args: self.PLCObjDefaults.get(name, None)
        for name,_func in getmembers(IBeremizPLCObjectService, isfunction)})


class FlashingPLCObject(NOP_PLCObject):
    def __init__(self, uri):
        self.uri = uri

    def GetPLCstatus(self):
        return (PlcStatus.Empty, [0]*LogLevelsCount)

    def DelegateTransferToBuilder(self):
        # the only purpose of that connector is returning True here.
        return True


def FLASH_connector_factory(uri, confnodesroot):
    """
    Expected URI format:

    FLASH://target/dependent#parameters
    """

    return FlashingPLCObject(uri)
