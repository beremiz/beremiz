from .. import toolchain_gcc

class Linux_target(toolchain_gcc):
    extension = ".so"
    CustomLDFLAGS = ["-shared"]
