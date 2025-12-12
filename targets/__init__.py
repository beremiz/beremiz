#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2013: Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.

# Package initialisation


"""
Beremiz Targets

- Targets are python packages, containing "XSD" string and a target module containing a class inheriting from Builder
- The target folder's name must match to name define in the XSD for TargetType
"""


import importlib
import util.paths as paths
from os import listdir, path
import features


targets = {}
targetchoices = []
for name in sorted(listdir(__path__[0])):
    if (path.isdir(path.join(__path__[0], name)) and not name.startswith("__")):
        if not features.targets or name in features.targets:
            module = importlib.import_module(f"targets.{name}")
            targets[name] = module
            targetchoices.append(getattr(module, f"XSD"))


def GetBuilder(targename):
    assert(targename in targets)
    kls = getattr(importlib.import_module(f"targets.{targename}.{targename}_target"), f"{targename}_target")
    kls.GetTargetName = classmethod(lambda cls: targename) # Add target name to class intependently of class name
    return kls


def GetTargetChoices():
    return targetchoices


def GetTargetCode(name):
    targetdir = targets[name].__path__[0]
    return "\n".join([open(path.join(targetdir, fname)).read()
                      for fname in sorted(listdir(targetdir))
                      if (fname.startswith("plc_%s_main" % name)
                          and fname.endswith(".c"))])


def GetHeader():
    filename = paths.AbsNeighbourFile(__file__, "beremiz.h")
    return open(filename).read()


def GetCode(name):
    filename = paths.AbsNeighbourFile(__file__, name)
    return open(filename).read()
