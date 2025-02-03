#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2024: Edouard TISSERANT
#
# See COPYING file for copyrights details.

import os
import shlex

from .ZephyrBuildBase import ZephyrBuildException
from targets.Builder import Builder
from C_runtime.zephyr import GetZephyrBuildOptions

if os.name == 'nt':
    from .ZephyrWindowsBuild import ZephyrWindowsBuild as ZephyrBuild
else:
    from .ZephyrLinuxBuild import ZephyrLinuxBuild as ZephyrBuild


class Zephyr_target(Builder):
    dlopen_prefix = "./"
    extension = ".dlext"

    def getDebugEnabled(self):
        target_cfg = self.CTRInstance.GetTarget().getcontent()
        programmable = target_cfg.getProgrammable()
        # only programmable PLCs are debuggable
        return programmable

    def GetReservedIECChannels(self):
        # TODO: get reserved IEC channels from selected board
        return [0]
              
    def build(self):
        log = self.CTRInstance.logger
        
        target_cfg = self.CTRInstance.GetTarget().getcontent()
        
        board_cfg = target_cfg.getBoard().getcontent()
        
        board_name, options, cflags, user_dts = GetZephyrBuildOptions(board_cfg)
        
        programmable = "programmable" in options
        if programmable:
            assert("builtin" not in options)
            options.append("builtin")

        log.write(f"Building Zephyr dependencies for board name: {board_name}\n")

        # Create Zephyr build instance
        zb = ZephyrBuild(log, board_name, self.buildpath, options)
            
        try:        
            # Setup Zephyr build environment
            need_rebuild = zb.EnsureZephyrBuildEnvironment()

        except ZephyrBuildException as e:
            log.write_error(f"Error building Zephyr dependencies: {e}\n")
            return False

        PLC_CFLAGS = ["-Wno-double-promotion", "-Wno-unused-variable"] #TODO: Make this unnecessary
        PLC_CFILES = []
        for _Location, CFilesAndCFLAGS, _DoCalls in self.CTRInstance.LocationCFilesAndCFLAGS:
            for CFile, CFLAGS in CFilesAndCFLAGS:
                PLC_CFILES.append(CFile)
                # Zephyr doesn't support per C file CFLAGS
                # -> Collect unique per C file CFLAGS into a single string
                # -> This is not perfect, ideally per C file CFLAGS should 
                #    be abandoned in favor of per target CFLAGS in Beremiz
                c_flags = shlex.split(CFLAGS)
                for c_flag in c_flags:
                    if c_flag not in PLC_CFLAGS:
                        PLC_CFLAGS.append(c_flag)

        try:        
            # Build runtime and PLC
            binaries = zb.BuildPLC(PLC_CFILES, PLC_CFLAGS,
                        force = need_rebuild)

        except ZephyrBuildException as e:
            log.write_error(f"Error building Zephyr PLC: {e}\n")
            return False

        log.write(f"Zephyr PLC built successfully\n")
        
        self.bin_path = binaries[0]
        
        self.md5key = self.compute_file_md5(self.bin_path)
        
        # Store new PLC filename based on md5 key
        f = open(self._GetMD5FileName(), "w")
        f.write(self.md5key)
        f.close()

        return True
