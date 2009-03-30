from .. import toolchain_gcc
from wxPopen import ProcessLogger

class Xenomai_target(toolchain_gcc):
    extension = ".so"
    def getXenoConfig(self):
        """ Get xeno-config from target parameters """
        return self.PluginsRootInstance.BeremizRoot.getTargetType().getcontent()["value"].getXenoConfig()
    
    def getBuilderLDFLAGS(self):
        # get xeno-config from target parameters
        xeno_config = self.getXenoConfig()

        status, result, err_result = ProcessLogger(self.logger, xeno_config + " --xeno-ldflags", no_stdout=True).spin()
        if status:
            self.logger.write_error("Unable to get Xenomai's LDFLAGS\n")
        xeno_ldlags = result.strip()
        
        return toolchain_gcc.getBuilderLDFLAGS(self) + [xeno_ldlags, "-shared", "-lnative"]

    def getBuilderCFLAGS(self):
        # get xeno-config from target parameters
        xeno_config = self.getXenoConfig()

        status, result, err_result = ProcessLogger(self.logger, xeno_config + " --xeno-cflags", no_stdout=True).spin()
        if status:
            self.logger.write_error("Unable to get Xenomai's CFLAGS\n")
        xeno_cflags = result.strip()
        
        return toolchain_gcc.getBuilderCFLAGS(self) + [xeno_cflags]
        
