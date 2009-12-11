from .. import toolchain_makefile

class LPC_target(toolchain_makefile):
    extension = ".ld"
    DebugEnabled = False
