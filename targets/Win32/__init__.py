from .. import toolchain_gcc

class Win32_target(toolchain_gcc):
    extension = ".dll"
    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared"]
