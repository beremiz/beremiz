#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2024: Edouard TISSERANT
# See COPYING file for copyrights details.

import os
import shlex

from os.path import join
from ..toolchain_gcc import compute_file_md5
from .ZephyrBuildBase import ZephyrBuildException

if os.name == 'nt':
    from .ZephyrWindowsBuild import ZephyrWindowsBuild as ZephyrBuild
else:
    from .ZephyrLinuxBuild import ZephyrLinuxBuild as ZephyrBuild


class Zephyr_target():
    dlopen_prefix = "./"
    extension = ".dlext"

    def __init__(self, CTRInstance):
        self.CTRInstance = CTRInstance
        self.md5key = None
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())

    def GetBinaryPath(self):
        return self.bin_path

    def _GetMD5FileName(self):
        return join(self.buildpath, "lastbuildPLC.md5")

    def ResetBinaryMD5(self):
        self.md5key = None
        try:
            os.remove(self._GetMD5FileName())
        except Exception:
            pass

    def GetBinaryMD5(self):
        if self.md5key is not None:
            return self.md5key
        else:
            try:
                return open(self._GetMD5FileName(), "r").read()
            except Exception:
                return None

    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            self.bin = self.CTRInstance.GetProjectName() + self.extension
            self.bin_path = join(self.buildpath, self.bin)
            self.md5key = None

    def build(self):
        log = self.CTRInstance.logger
        
        options = []

        target_cfg = self.CTRInstance.GetTarget().getcontent()
        
        board_name = target_cfg.getBoardName()
        options.append(f"board_{board_name.split("/")[0]}")
        
        programmable = target_cfg.getProgrammable()
        options.append("programmable" if programmable else "builtin")

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
        
        self.md5key = compute_file_md5(self.bin_path)
        
        # Store new PLC filename based on md5 key
        f = open(self._GetMD5FileName(), "w")
        f.write(self.md5key)
        f.close()

        return True
