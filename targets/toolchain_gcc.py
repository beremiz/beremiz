#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2007: Laurent BESSARD
# Copyright (C) 2017: Paul Beltyukov
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.


import os
import re
import operator
import hashlib
import subprocess
import shlex
from functools import reduce
from util.ProcessLogger import ProcessLogger
from targets.Builder import Builder

includes_re = re.compile(r'\s*#include\s*["<]([^">]*)[">].*')


class toolchain_gcc(Builder):
    """
    This abstract class contains GCC specific code.
    It cannot be used as this and should be inherited in a target specific
    class such as target_linux or target_win32
    """

    def getBuilderCFLAGS(self):
        """
        Returns list of builder specific CFLAGS
        """
        cflags = [self.CTRInstance.GetTarget().getcontent().getCFLAGS()]
        if "CFLAGS" in os.environ:
            cflags.append(os.environ["CFLAGS"])
        if "SYSROOT" in os.environ:
            cflags.append("--sysroot="+os.environ["SYSROOT"])
        return cflags

    def getBuilderLDFLAGS(self):
        """
        Returns list of builder specific LDFLAGS
        """
        ldflags = self.CTRInstance.LDFLAGS + \
            [self.CTRInstance.GetTarget().getcontent().getLDFLAGS()]
        if "LDLAGS" in os.environ:
            ldflags.append(os.environ["LDLAGS"])
        if "SYSROOT" in os.environ:
            ldflags.append("--sysroot="+os.environ["SYSROOT"])
        return ldflags

    def getCompiler(self):
        """
        Returns compiler
        """
        return self.CTRInstance.GetTarget().getcontent().getCompiler()

    def getLinker(self):
        """
        Returns linker
        """
        return self.CTRInstance.GetTarget().getcontent().getLinker()

    def SetBuildPath(self, buildpath):
        if Builder.SetBuildPath(self, buildpath):
            self.srcmd5 = {}

    def append_cfile_deps(self, srcname, deps):
        src = open(os.path.join(self.buildpath, srcname), "r").read()
        for l in src.splitlines():
            res = includes_re.match(l)
            if res is not None:
                depfn = res.groups()[0]
                if os.path.exists(os.path.join(self.buildpath, depfn)):
                    deps.append(depfn)

    def check_and_update_hash_and_deps(self, bn):
        # Get latest computed hash and deps
        oldhash, deps = self.srcmd5.get(bn, (None, []))
        # read source
        src = os.path.join(self.buildpath, bn)
        if not os.path.exists(src):
            return False
        # compute new hash
        newhash = self.compute_file_md5(src)
        # compare
        match = (oldhash == newhash)
        if not match:
            # file have changed
            # update direct dependencies
            deps = []
            self.append_cfile_deps(src, deps)
            # store that hashand deps
            self.srcmd5[bn] = (newhash, deps)
        # recurse through deps
        # TODO detect cicular deps.
        return reduce(operator.and_, list(map(self.check_and_update_hash_and_deps, deps)), match)

    def build(self):
        # Retrieve compiler and linker
        self.compiler = self.getCompiler()
        self.linker = self.getLinker()

        Builder_CFLAGS_str = ' '.join(self.getBuilderCFLAGS())
        Builder_LDFLAGS_str = ' '.join(self.getBuilderLDFLAGS())

        Builder_CFLAGS = shlex.split(Builder_CFLAGS_str)
        Builder_LDFLAGS = shlex.split(Builder_LDFLAGS_str)

        pattern = "{SYSROOT}"
        if pattern in Builder_CFLAGS_str or pattern in Builder_LDFLAGS_str:
            try:
                sysrootb = subprocess.check_output([self.compiler,"-print-sysroot"])
            except subprocess.CalledProcessError:
                self.CTRInstance.logger.write("GCC failed with -print-sysroot\n")
                return False
            except FileNotFoundError:
                self.CTRInstance.logger.write("GCC not found\n")
                return False

            sysroot = sysrootb.decode().strip()

            replace_sysroot = lambda l:list(map(lambda s:s.replace(pattern, sysroot), l))
            Builder_CFLAGS = replace_sysroot(Builder_CFLAGS)
            Builder_LDFLAGS = replace_sysroot(Builder_LDFLAGS)

        # ----------------- GENERATE OBJECT FILES ------------------------
        obns = []
        objs = []
        must_link = not os.path.exists(self.bin_path)
        for Location, CFilesAndCFLAGS, _DoCalls, *_req in self.CTRInstance.LocationCFilesAndCFLAGS:
            if CFilesAndCFLAGS:
                if Location:
                    self.CTRInstance.logger.write(".".join(map(str, Location))+" :\n")
                else:
                    self.CTRInstance.logger.write(_("PLC :\n"))

            for CFile, CFLAGS in CFilesAndCFLAGS:
                if CFile.endswith(".c"):
                    bn = os.path.basename(CFile)
                    obn = os.path.splitext(bn)[0]+".o"
                    objectfilename = os.path.splitext(CFile)[0]+".o"

                    match = self.check_and_update_hash_and_deps(bn)

                    if match:
                        self.CTRInstance.logger.write("   [pass]  "+bn+" -> "+obn+"\n")
                    else:
                        must_link = True

                        self.CTRInstance.logger.write("   [CC]  "+bn+" -> "+obn+"\n")

                        status, _result, _err_result = ProcessLogger(
                            self.CTRInstance.logger,
                            [self.compiler,
                             "-c", CFile,
                             "-o", objectfilename,
                             "-O2"]
                            + Builder_CFLAGS
                            + shlex.split(CFLAGS)
                        ).spin()

                        if status:
                            self.srcmd5.pop(bn)
                            self.CTRInstance.logger.write_error(_("C compilation of %s failed.\n") % bn)
                            return False
                    obns.append(obn)
                    objs.append(objectfilename)
                elif CFile.endswith(".o"):
                    obns.append(os.path.basename(CFile))
                    objs.append(CFile)

        # ---------------- GENERATE OUTPUT FILE --------------------------
        # Link all the object files into one binary file
        self.CTRInstance.logger.write(_("Linking :\n"))
        if must_link:
            if not self.link(objs, obns, Builder_LDFLAGS):
                return False
        else:
            self.CTRInstance.logger.write("   [pass]  " + ' '.join(obns)+" -> " + self.bin + "\n")

        # Calculate md5 key and get data for the new created PLC
        self.md5key = self.compute_file_md5(self.bin_path)

        # Store new PLC filename based on md5 key
        f = open(self._GetMD5FileName(), "w")
        f.write(self.md5key)
        f.close()

        return True

    def link(self, objs, obns, LDFLAGS):
        self.CTRInstance.logger.write("   [CC]  " + ' '.join(obns)+" -> " + self.bin + "\n")

        status, _result, _err_result = ProcessLogger(
            self.CTRInstance.logger,
            [self.linker] + objs
            + ["-o", self.bin_path]
            + LDFLAGS
        ).spin()

        if status:
            self.CTRInstance.logger.write_error(_("Linking failed with %d.\n") % status)
            return False
        return True
