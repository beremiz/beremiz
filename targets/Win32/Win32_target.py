#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.

from ..toolchain_gcc import toolchain_gcc


class Win32_target(toolchain_gcc):
    dlopen_prefix = ""
    extension = ".dll"

    def getBuilderCFLAGS(self):
        return toolchain_gcc.getBuilderCFLAGS(self) + \
            ["-Wno-implicit-function-declaration", "-Wno-int-conversion"]

    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared", "-lwinmm"]
