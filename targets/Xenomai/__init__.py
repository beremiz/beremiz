from .. import toolchain_gcc
from wxPopen import ProcessLogger

class Xenomai_target(toolchain_gcc):
    extension = ".so"
    def getXenoConfig(self):
        """ Get xeno-config from target parameters """
        return self.PluginsRootInstance.GetTarget().getcontent()["value"].getXenoConfig()
    
    def getBuilderLDFLAGS(self):
        # get xeno-config from target parameters
        xeno_config = self.getXenoConfig()

        status, result, err_result = ProcessLogger(self.PluginsRootInstance.logger, xeno_config + " --skin=native --ldflags", no_stdout=True).spin()
        if status:
            self.PluginsRootInstance.logger.write_error(_("Unable to get Xenomai's LDFLAGS\n"))
        xeno_ldlags = result.strip()
        
        return toolchain_gcc.getBuilderLDFLAGS(self) + [xeno_ldlags, "-shared", "-lnative"]

    def getBuilderCFLAGS(self):
        # get xeno-config from target parameters
        xeno_config = self.getXenoConfig()

        status, result, err_result = ProcessLogger(self.PluginsRootInstance.logger, xeno_config + " --skin=native --cflags", no_stdout=True).spin()
        if status:
            self.PluginsRootInstance.logger.write_error(_("Unable to get Xenomai's CFLAGS\n"))
        xeno_cflags = result.strip()
        
        return toolchain_gcc.getBuilderCFLAGS(self) + [xeno_cflags]
        
