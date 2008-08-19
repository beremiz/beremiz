from .. import toolchain_gcc

class Win32_target(toolchain_gcc):
    extension = ".dll"
    CustomLDFLAGS = ["-shared",
                     "-Wl,--export-all-symbols",
                     "-Wl,--enable-auto-import",
                     "-Wl,--whole-archive",
                     "-Wl,--no-whole-archive",
                     "-Wl,--exclude-libs,All"]
