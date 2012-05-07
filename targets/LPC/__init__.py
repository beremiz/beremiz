import os
from subprocess import Popen,PIPE
from ..toolchain_makefile import toolchain_makefile
import hashlib

class LPC_target(toolchain_makefile):
    #extension = ".ld"
    #DebugEnabled = False
    def __init__(self, ConfigTreeRootInstance):
        self.binmd5key = None
        toolchain_makefile.__init__(self, ConfigTreeRootInstance)

    def _GetBinMD5FileName(self):
        return os.path.join(self.buildpath, "lastbuildPLCbin.md5")

    def _get_md5_header(self):
        """Returns signature header"""
        size = int(Popen(
             ['arm-elf-size','-B',os.path.join(self.buildpath,"ArmPLC_rom.elf")],
             stdout=PIPE).communicate()[0].splitlines()[1].split()[0])
        res = "&" + hashlib.md5(open(os.path.join(self.buildpath, "ArmPLC_rom.bin"), "rb").read(size)).hexdigest() + '\n' +\
              "$" + str(size) + '\n'
        return res

    def GetBinaryCode(self):
        """Returns ready to send signed + sized intel formated hex program"""
        try:
            res = self._get_md5_header() +\
                   open(os.path.join(self.buildpath, "ArmPLC_rom.hex"), "r").read()
            return res
        except Exception, e:
            return None

    def _get_cached_md5_header(self):
        if self.binmd5key is not None:
            return self.binmd5key
        else:
            try:
                return open(self._GetBinMD5FileName(), "r").read()
            except IOError, e:
                return None

    def ResetBinaryCodeMD5(self, mode):
        if mode == "BOOTLOADER":
            self.binmd5key = None
            try:
                os.remove(self._GetBinMD5FileName())
            except Exception, e:
                pass
        else:
            return toolchain_makefile.ResetBinaryCodeMD5(self)

    def GetBinaryCodeMD5(self, mode):
        if mode == "BOOTLOADER":
            return self._get_cached_md5_header()
        else:
            return toolchain_makefile.GetBinaryCodeMD5(self)

    def build(self):
        res = toolchain_makefile.build(self)
        if res:
            self.binmd5key = self._get_md5_header()
            f = open(self._GetBinMD5FileName(), "w")
            f.write(self.binmd5key)
            f.close()
            try:
                self.ConfigTreeRootInstance.logger.write(
                    _("Binary is %s bytes long\n")%
                        str(os.path.getsize(
                            os.path.join(self.buildpath, "ArmPLC_rom.bin"))))
            except Exception, e:
                pass
        return res

