#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

_developer_mode = False
_sdk_path = None

def GetDeveloperMode():
    global _developer_mode
    return _developer_mode

def SetDeveloperMode():
    global _developer_mode
    _developer_mode = True
    
def GetSDKPath():
    global _sdk_path
    return _sdk_path

def SetSDKPath(path):
    global _sdk_path
    _sdk_path = path
    # add path to sys.path
    if path not in sys.path:
        sys.path.insert(0, path)