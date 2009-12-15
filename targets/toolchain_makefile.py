import os, re
from wxPopen import ProcessLogger
import hashlib

import time

includes_re =  re.compile('\s*#include\s*["<]([^">]*)[">].*')

class toolchain_makefile():
    def __init__(self, PluginsRootInstance):
        self.PluginsRootInstance = PluginsRootInstance
        self.md5key = None 
        self.buildpath = None
        self.SetBuildPath(self.PluginsRootInstance._getBuildPath())

    def SetBuildPath(self, buildpath):
        self.buildpath = buildpath
        self.exe_path = os.path.join(self.buildpath, "ArmPLC_rom.bin")
        self.md5_path = os.path.join(self.buildpath, "ArmPLC.md5")

    def GetBinaryCode(self):
        try:
            return open(self.exe_path, "rb").read()
        except Exception, e:
            return None

    def _GetMD5FileName(self):
        return os.path.join(self.buildpath, "lastbuildPLC.md5")

    def GetBinaryCodeMD5(self):
        if self.md5key is not None:
            return self.md5key
        else:
            try:
                return open(self._GetMD5FileName(), "r").read()
            except Exception, e:
                return None

    def build(self):
        srcfiles= []
        cflags = []
        for Location, CFilesAndCFLAGS, DoCalls in self.PluginsRootInstance.LocationCFilesAndCFLAGS:
            wholesrcdata = "" 
            # Get CFiles list to give it to makefile
            for CFile, CFLAGS in CFilesAndCFLAGS:
                CFileName = os.path.basename(CFile)
                wholesrcdata += open(CFile, "r").read()
                srcfiles.append(CFileName)
                if CFLAGS not in cflags:
                    cflags.append(CFLAGS)
                    
            self.md5key = hashlib.md5(wholesrcdata).hexdigest()
            props = self.PluginsRootInstance.GetProjectProperties()
            self.md5key += '|'.join([props[key] for key in ['companyName',
                                                            'projectName',
                                                            'productName']])
            self.md5key += '|'+','.join(map(str,time.localtime()))
            # Store new PLC filename based on md5 key
            f = open(self._GetMD5FileName(), "w")
            f.write(self.md5key)
            f.close()
        beremizcommand = {"src": ' '.join(srcfiles),
                          "cflags": ' '.join(cflags),
                          "md5": self.md5key
                         }
        
        target = self.PluginsRootInstance.GetTarget().getcontent()["value"]
        command = target.getCommand().split(' ') +\
                  [target.getBuildPath()] +\
                  [arg % beremizcommand for arg in target.getArguments().split(' ')] +\
                  target.getRule().split(' ')
        
        # Call Makefile to build PLC code and link it with target specific code
        status, result, err_result = ProcessLogger(self.PluginsRootInstance.logger,
                                                   command).spin()
        if status :
            self.PluginsRootInstance.logger.write_error(_("C compilation of %s failed.\n"))
            return False
        return True
