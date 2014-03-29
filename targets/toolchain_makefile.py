import os, re, operator
from util.ProcessLogger import ProcessLogger
import hashlib

import time

includes_re =  re.compile('\s*#include\s*["<]([^">]*)[">].*')


if os.name == 'nt':
    # on windows, desktop shortcut launches Beremiz.py
    # with working dir set to mingw/bin.
    # then we prefix CWD to PATH in order to ensure that
    # commands invoked from Makefiles will first resolve
    # to here.
    os.environ["PATH"] = os.getcwd()+';'+os.environ["PATH"]

class toolchain_makefile():
    def __init__(self, CTRInstance):
        self.CTRInstance = CTRInstance
        self.md5key = None 
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())

    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            self.md5key = None

    def GetBinaryCode(self):
        return None

    def _GetMD5FileName(self):
        return os.path.join(self.buildpath, "lastbuildPLC.md5")

    def ResetBinaryCodeMD5(self):
        self.md5key = None
        try:
            os.remove(self._GetMD5FileName())
        except Exception, e:
            pass

    def GetBinaryCodeMD5(self):
        if self.md5key is not None:
            return self.md5key
        else:
            try:
                return open(self._GetMD5FileName(), "r").read()
            except IOError, e:
                return None

    def concat_deps(self, bn):
        # read source
        src = open(os.path.join(self.buildpath, bn),"r").read()
        # update direct dependencies
        deps = []
        for l in src.splitlines():
            res = includes_re.match(l)
            if res is not None:
                depfn = res.groups()[0]
                if os.path.exists(os.path.join(self.buildpath, depfn)):
                    #print bn + " depends on "+depfn
                    deps.append(depfn)
        # recurse through deps
        # TODO detect cicular deps.
        return reduce(operator.concat, map(self.concat_deps, deps), src)

    def build(self):
        srcfiles= []
        cflags = []
        wholesrcdata = "" 
        for Location, CFilesAndCFLAGS, DoCalls in self.CTRInstance.LocationCFilesAndCFLAGS:
            # Get CFiles list to give it to makefile
            for CFile, CFLAGS in CFilesAndCFLAGS:
                CFileName = os.path.basename(CFile)
                wholesrcdata += self.concat_deps(CFileName)
                srcfiles.append(CFileName)
                if CFLAGS not in cflags:
                    cflags.append(CFLAGS)
                        
        oldmd5 = self.md5key
        self.md5key = hashlib.md5(wholesrcdata).hexdigest()
        props = self.CTRInstance.GetProjectProperties()
        self.md5key += '#'.join([props[key] for key in ['companyName',
                                                        'projectName',
                                                        'productName']])
        self.md5key += '#' #+','.join(map(str,time.localtime()))
        # Store new PLC filename based on md5 key
        f = open(self._GetMD5FileName(), "w")
        f.write(self.md5key)
        f.close()

        if oldmd5 != self.md5key :
            target = self.CTRInstance.GetTarget().getcontent()
            beremizcommand = {"src": ' '.join(srcfiles),
                              "cflags": ' '.join(cflags),
                              "md5": self.md5key,
                              "buildpath": self.buildpath
                             }
            
            command = [ token % beremizcommand for token in target.getCommand().split(' ')]

            # Call Makefile to build PLC code and link it with target specific code
            status, result, err_result = ProcessLogger(self.CTRInstance.logger,
                                                       command).spin()
            if status :
                self.md5key = None
                self.CTRInstance.logger.write_error(_("C compilation failed.\n"))
                return False
            return True
        else :
            self.CTRInstance.logger.write(_("Source didn't change, no build.\n"))
            return True

