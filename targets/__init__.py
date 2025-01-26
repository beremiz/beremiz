#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2007: Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.

# Package initialisation


"""
Beremiz Targets

- Target are python packages, containing at least one "XSD" file
- Target class may inherit from a toolchain_(toolchainname)
- The target folder's name must match to name define in the XSD for TargetType
"""


from os import listdir, path
import util.paths as paths
import importlib

_base_path = paths.AbsDir(__file__)


# Lazy loading of target classes
def _GetLocalTargetClassFactory(name):
    return lambda: getattr(importlib.import_module(f"targets.{name}.{name}_target"), f"{name}_target")

targets = {}
targetchoices = ""
for name in listdir(_base_path):
    if (path.isdir(path.join(_base_path, name)) and
        not name.startswith("__")):
        targets[name] = {"class": _GetLocalTargetClassFactory(name),
                         "code":  {fname: path.join(_base_path, name, fname)
                                  for fname in listdir(path.join(_base_path, name))
                                  if (fname.startswith("plc_%s_main" % name) and
                                      fname.endswith(".c"))}}
        targetchoices += getattr(importlib.import_module(f"targets.{name}"), f"XSD")


def GetBuilder(targetname):
    return targets[targetname]["class"]()


def GetTargetChoices():
    return targetchoices


def GetTargetCode(targetname):
    codedesc = targets[targetname]["code"]
    code = "\n".join([open(fpath).read() for _fname, fpath in sorted(codedesc.items())])
    return code


def GetHeader():
    filename = paths.AbsNeighbourFile(__file__, "beremiz.h")
    return open(filename).read()


def GetCode(name):
    filename = paths.AbsNeighbourFile(__file__, name)
    return open(filename).read()
