#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.


from ..toolchain_gcc import toolchain_gcc


class Linux_target(toolchain_gcc):
    dlopen_prefix = "./"
    extension = ".so"

    def getBuilderCFLAGS(self):
        additional_cflags = ["-fPIC", "-Wno-implicit-function-declaration", "-Wno-int-conversion"]
        build_for_realtime = self.CTRInstance.GetTarget().getcontent().getRealTime()
        if build_for_realtime:
            additional_cflags.append("-DREALTIME_LINUX")
        return toolchain_gcc.getBuilderCFLAGS(self) + additional_cflags

    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared", "-lrt"]
