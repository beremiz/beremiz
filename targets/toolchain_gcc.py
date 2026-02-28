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
import subprocess
import shlex
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

    def _collect_includes(self, bn, files, visited, buildpath_real):
        if bn in visited:
            return
        visited.add(bn)

        filepath = os.path.join(self.buildpath, bn)
        if not os.path.realpath(filepath).startswith(buildpath_real):
            return
        if not os.path.isfile(filepath):
            return

        files.append(bn)

        with open(filepath, "r") as f:
            for line in f:
                res = includes_re.match(line)
                if res is not None:
                    self._collect_includes(res.group(1), files, visited, buildpath_real)

    def check_and_update_hash_and_deps(self, bn):
        # Collect source and all transitive includes within build directory
        files = []
        self._collect_includes(bn, files, set(),
                               os.path.realpath(self.buildpath) + os.sep)

        if not files:
            return False

        # Compute combined hash of all collected files
        newhash = self.compute_file_md5(
            [os.path.join(self.buildpath, f) for f in sorted(files)])

        # Compare with cached hash
        oldhash = self.srcmd5.get(bn)
        if oldhash == newhash:
            return True

        self.srcmd5[bn] = newhash
        return False

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

                    if match and os.path.exists(objectfilename):
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
