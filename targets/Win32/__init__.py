from ..toolchain_gcc import toolchain_gcc

class Win32_target(toolchain_gcc):
    dlopen_prefix = ""
    extension = ".dll"
    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared", "-lwinmm"]
