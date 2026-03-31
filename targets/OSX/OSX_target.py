#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.

from ..toolchain_gcc import toolchain_gcc
import platform


class OSX_target(toolchain_gcc):
    dlopen_prefix = "./"
    extension = ".dynlib"

    def getBuilderCFLAGS(self):
        return toolchain_gcc.getBuilderCFLAGS(self) + \
            ["-fPIC", "-Wno-deprecated-declarations",
             "-Wno-implicit-function-declaration", "-Wno-int-conversion",
             "-Wno-parentheses-equality", "-Wno-varargs", "-arch", platform.machine()]

    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared", "-arch", platform.machine()]
