#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.


import os
import hashlib
from os.path import join

class Builder:
    def __init__(self, CTRInstance):
        self.CTRInstance = CTRInstance
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())
        self.md5key = None

    bin_path = None
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
            return True
        return False

    def compute_file_md5(filestocheck):
        hasher = hashlib.md5()
        if type(filestocheck) is str:
            filestocheck = [filestocheck]
        for filetocheck in filestocheck:
            with open(filetocheck, 'rb') as afile:
                while True:
                    buf = afile.read(65536)
                    if len(buf) > 0:
                        hasher.update(buf)
                    else:
                        break
        return hasher.hexdigest()
    compute_file_md5 = staticmethod(compute_file_md5)

    def getDebugEnabled(self):
        target_cfg = self.CTRInstance.GetTarget().getcontent()
        programmable = target_cfg.getProgrammable()
        # only programmable PLCs are debuggable
        return programmable

    def GetReservedIECChannels(self):
        return []