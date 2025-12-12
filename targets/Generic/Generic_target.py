#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of Beremiz IDE
#
# Copyright (C) 2007: Laurent BESSARD
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.


import os
import re
import operator
import hashlib
from functools import reduce
from util.ProcessLogger import ProcessLogger
from targets.Builder import Builder


includes_re = re.compile(r'\s*#include\s*["<]([^">]*)[">].*')


class Generic_target(Builder):

    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            self.md5key = None

    def concat_deps(self, bn):
        # read source
        src = open(os.path.join(self.buildpath, bn), "r").read()
        # update direct dependencies
        deps = []
        for l in src.splitlines():
            res = includes_re.match(l)
            if res is not None:
                depfn = res.groups()[0]
                if os.path.exists(os.path.join(self.buildpath, depfn)):
                    # print bn + " depends on "+depfn
                    deps.append(depfn)
        # recurse through deps
        # TODO detect cicular deps.
        return reduce(operator.concat, list(map(self.concat_deps, deps)), src)

    def build(self):
        srcfiles = []
        cflags = []
        wholesrcdata = ""
        for _Location, CFilesAndCFLAGS, _DoCalls, *_req in self.CTRInstance.LocationCFilesAndCFLAGS:
            # Get CFiles list to give it to makefile
            for CFile, CFLAGS in CFilesAndCFLAGS:
                CFileName = os.path.basename(CFile)
                wholesrcdata += self.concat_deps(CFileName)
                srcfiles.append(CFileName)
                if CFLAGS not in cflags:
                    cflags.append(CFLAGS)

        oldmd5 = self.md5key
        self.md5key = hashlib.md5(wholesrcdata).hexdigest()

        # Store new PLC filename based on md5 key
        f = open(self._GetMD5FileName(), "w")
        f.write(self.md5key)
        f.close()

        if oldmd5 != self.md5key:
            target = self.CTRInstance.GetTarget().getcontent()
            beremizcommand = {"src": ' '.join(srcfiles),
                              "cflags": ' '.join(cflags),
                              "md5": self.md5key,
                              "buildpath": self.buildpath}

            # clean sequence of multiple whitespaces
            cmd = re.sub(r"[ ]+", " ", target.getCommand().strip())

            command = [token % beremizcommand for token in cmd.split(' ')]

            # Call Makefile to build PLC code and link it with target specific code
            status, _result, _err_result = ProcessLogger(self.CTRInstance.logger,
                                                         command).spin()
            if status:
                self.md5key = None
                self.CTRInstance.logger.write_error(_("C compilation failed.\n"))
                return False
            return True
        else:
            self.CTRInstance.logger.write(_("Source didn't change, no build.\n"))
            return True
        