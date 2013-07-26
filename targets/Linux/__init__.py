from ..toolchain_gcc import toolchain_gcc

class Linux_target(toolchain_gcc):
    dlopen_prefix = "./"
    extension = ".so"
    def getBuilderCFLAGS(self):
        return toolchain_gcc.getBuilderCFLAGS(self) + ["-fPIC"]
    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared", "-lrt"]
