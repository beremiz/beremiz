#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
import traceback

from runtime.Worker import worker
MainWorker = worker()

from runtime.PLCObject import PLCObject

_PLCObjectSingleton = None

def GetPLCObjectSingleton():
    global _PLCObjectSingleton
    assert(_PLCObjectSingleton is not None)
    return _PLCObjectSingleton


def LogMessageAndException(msg, exp=None):
    global _PLCObjectSingleton
    if exp is None:
        exp = sys.exc_info()
    if _PLCObjectSingleton is not None:
        _PLCObjectSingleton.LogMessage(0, msg + '\n'.join(traceback.format_exception(*exp)))
    else:
        print(msg)
        traceback.print_exception(*exp)

def CreatePLCObjectSingleton(*args):
    global _PLCObjectSingleton
    _PLCObjectSingleton = PLCObject(*args)
