import os, re, operator
from wxPopen import ProcessLogger
import hashlib, shutil
from toolchain_gcc import toolchain_gcc

includes_re =  re.compile('\s*#include\s*["<]([^">]*)[">].*')

class toolchain_makefile(toolchain_gcc):
    """
    This abstract class contains GCC specific code.
    It cannot be used as this and should be inherited in a target specific
    class such as target_linux or target_win32
    """

    def build(self):
        srcfiles= []
        cflags = []
        for Location, CFilesAndCFLAGS, DoCalls in self.PluginsRootInstance.LocationCFilesAndCFLAGS:
            # Get CFiles list to give it to makefile 
            for CFile, CFLAGS in CFilesAndCFLAGS:
                CFileName = os.path.basename(CFile)
                srcfiles.append(CFileName)
                if CFLAGS not in cflags:
                    cflags.append(CFLAGS)
                    
        beremizcommand = {"src": ' '.join(srcfiles),
                          "cflags": ' '.join(cflags)
                         }
        
        target = self.getTarget().getcontent()["value"]
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
