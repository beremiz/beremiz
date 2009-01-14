from .. import toolchain_gcc

class Win32_target(toolchain_gcc):
    extension = ".dll"
    def getBuilderLDFLAGS(self):
        return toolchain_gcc.getBuilderLDFLAGS(self) + ["-shared",
                     "-Wl,--export-all-symbols",
                     "-Wl,--enable-auto-import",
                     "-Wl,--whole-archive",
                     "-Wl,--no-whole-archive",
                     "-Wl,--exclude-libs,All"]
