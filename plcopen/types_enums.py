#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of Beremiz
# See COPYING file for copyrights details.

from __future__ import absolute_import
from util.TranslationCatalogs import NoTranslate
_ = NoTranslate

ITEMS_EDITABLE = [
    ITEM_PROJECT,
    ITEM_POU,
    ITEM_VARIABLE,
    ITEM_TRANSITION,
    ITEM_ACTION,
    ITEM_CONFIGURATION,
    ITEM_RESOURCE,
    ITEM_DATATYPE
] = range(8)

ITEMS_UNEDITABLE = [
    ITEM_DATATYPES,
    ITEM_FUNCTION,
    ITEM_FUNCTIONBLOCK,
    ITEM_PROGRAM,
    ITEM_TRANSITIONS,
    ITEM_ACTIONS,
    ITEM_CONFIGURATIONS,
    ITEM_RESOURCES,
    ITEM_PROPERTIES
] = range(8, 17)

ITEMS_VARIABLE = [
    ITEM_VAR_LOCAL,
    ITEM_VAR_GLOBAL,
    ITEM_VAR_EXTERNAL,
    ITEM_VAR_TEMP,
    ITEM_VAR_INPUT,
    ITEM_VAR_OUTPUT,
    ITEM_VAR_INOUT
] = range(17, 24)

VAR_CLASS_INFOS = {
    "Local":    ("localVars",    ITEM_VAR_LOCAL),
    "Global":   ("globalVars",   ITEM_VAR_GLOBAL),
    "External": ("externalVars", ITEM_VAR_EXTERNAL),
    "Temp":     ("tempVars",     ITEM_VAR_TEMP),
    "Input":    ("inputVars",    ITEM_VAR_INPUT),
    "Output":   ("outputVars",   ITEM_VAR_OUTPUT),
    "InOut":    ("inOutVars",    ITEM_VAR_INOUT)}

POU_TYPES = {
    "program": ITEM_PROGRAM,
    "functionBlock": ITEM_FUNCTIONBLOCK,
    "function": ITEM_FUNCTION,
}

CLASS_TYPES = {
    "configuration": ITEM_CONFIGURATION,
    "resource": ITEM_RESOURCE,
    "action": ITEM_ACTION,
    "transition": ITEM_TRANSITION,
    "program": ITEM_PROGRAM
}

LOCATIONS_ITEMS = [LOCATION_CONFNODE,
                   LOCATION_MODULE,
                   LOCATION_GROUP,
                   LOCATION_VAR_INPUT,
                   LOCATION_VAR_OUTPUT,
                   LOCATION_VAR_MEMORY] = range(6)

UNEDITABLE_NAMES = [_("User-defined POUs"), _("Functions"), _("Function Blocks"),
            _("Programs"), _("Data Types"), _("Transitions"), _("Actions"),
            _("Configurations"), _("Resources"), _("Properties")]

[USER_DEFINED_POUS, FUNCTIONS, FUNCTION_BLOCKS, PROGRAMS,
 DATA_TYPES, TRANSITIONS, ACTIONS, CONFIGURATIONS,
 RESOURCES, PROPERTIES] = UNEDITABLE_NAMES

# remove gettext override
del _
