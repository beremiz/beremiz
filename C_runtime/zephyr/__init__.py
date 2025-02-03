#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zephyr Targets

- Targets are regular python packages (directory with __init__.py), containing:
    - "XSD_name" string: name of the target element in the XSD:choice
    - "XSD" string containing the XSD that defines the target configuration schema
    - "GetBuildOptions" functions transforming the target XML configuration into Zephyr build options

- The target folder also contains:
    - Zephyr configuration files (*.conf)
    - Zephyr device tree overlay files (*.overlay)
    - Target specific source and header files (*.c, *.h)
    - Target specific FB library (pous.xml)
    
- The target folder's name must match Zephyr board name (e.g. "native_sim")
"""

import os
import importlib

def _CollectZephyrTargets():
    collected = []
    for name in os.listdir(__path__[0]):
        if (os.path.isdir(os.path.join(__path__[0], name)) and
            not name.startswith("__")):
            module = importlib.import_module("C_runtime.zephyr."+name)
            collected.append([getattr(module, attr) 
                                for attr in ["XSD_name",
                                            "XSD"]]+
                               [module])
                                
    collected.sort(key=lambda x: x[0])
    choices_names, xsds, modules = zip(*collected)
    return "\n".join(xsds), dict(zip(choices_names, modules))

_xsd_choices, _choices_modules = _CollectZephyrTargets()

def GetZephyrXSDChoices():
    return _xsd_choices

def GetZephyrBuildOptions(choice, target_cfg):
    return _choices_modules[choice].GetBuildOptions(target_cfg)