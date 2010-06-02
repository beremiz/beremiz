from .. import toolchain_makefile

class LPC_target(toolchain_makefile):
    extension = ".ld"
    DebugEnabled = False

    def GetBinaryCode(self):
        try:
            return open(os.path.join(self.buildpath, "ArmPLC_rom.bin"), "rb").read()
        except Exception, e:
            return None
