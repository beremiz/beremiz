#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Written by Edouard TISSERANT (C) 2025
# This file is part of Beremiz IDE
# See COPYING file for copyrights details.

# Flashing connector dialog - empty

from connectors.SchemeEditor import SchemeEditor

Schemes = ["FLASH"]

model = []


class FLASH_dialog(SchemeEditor):
    def __init__(self, *args, **kwargs):
        self.model = model
        self.EnableIDSelector = False
        SchemeEditor.__init__(self, *args, **kwargs)

    # pylint: disable=unused-variable
    def SetLoc(self, loc):
        pass

    def GetLoc(self):
        return ""
