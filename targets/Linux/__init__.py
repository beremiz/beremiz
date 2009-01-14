from .. import toolchain_gcc

class Linux_target(toolchain_gcc):
    extension = ".so"
    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared", "-lrt"]
