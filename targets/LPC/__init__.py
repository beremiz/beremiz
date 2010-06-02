import os
from subprocess import Popen,PIPE
from .. import toolchain_makefile
import hashlib

class LPC_target(toolchain_makefile):
    extension = ".ld"
    DebugEnabled = False

    def GetBinaryCode(self):
        """Returns ready to send signed + sized intel formated hex program"""
        try:
            size = int(Popen(
                 ['arm-elf-size','-B',os.path.join(self.buildpath,"ArmPLC_rom.elf")],
                 stdout=PIPE).communicate()[0].splitlines()[1].split()[0])
            res = "&" + hashlib.md5(open(os.path.join(self.buildpath, "ArmPLC_rom.bin"), "rb").read(size)).hexdigest() + '\n' +\
                   "$" + str(size) + '\n' +\
                   open(os.path.join(self.buildpath, "ArmPLC_rom.hex"), "r").read()
            return res
        except Exception, e:
            return None

