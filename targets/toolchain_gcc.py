import os, re, operator
from wxPopen import ProcessLogger
import hashlib

includes_re =  re.compile('\s*#include\s*["<]([^">]*)[">].*')

class toolchain_gcc():
    """
    This abstract class contains GCC specific code.
    It cannot be used as this and should be inherited in a target specific
    class such as target_linux or target_win32
    """
    def __init__(self, PluginsRootInstance):
        self.PluginsRootInstance = PluginsRootInstance
        self.logger = PluginsRootInstance.logger
        self.exe = PluginsRootInstance.GetProjectName() + self.extension
        self.buildpath = PluginsRootInstance._getBuildPath()
        self.exe_path = os.path.join(self.buildpath, self.exe)
        self.md5key = None
        self.srcmd5 = {}

    def getTarget(self):
        target = self.PluginsRootInstance.BeremizRoot.getTargetType()
        if target.getcontent() is None:
            target = self.PluginsRootInstance.GetDefaultTarget()
        return target

    def getBuilderCFLAGS(self):
        """
        Returns list of builder specific CFLAGS
        """
        return [self.getTarget().getcontent()["value"].getCFLAGS()]

    def getBuilderLDFLAGS(self):
        """
        Returns list of builder specific LDFLAGS
        """
        return self.PluginsRootInstance.LDFLAGS + \
               [self.getTarget().getcontent()["value"].getLDFLAGS()]

    def GetBinaryCode(self):
        try:
            return open(self.exe_path, "rb").read()
        except Exception, e:
            return None
        
    def _GetMD5FileName(self):
        return os.path.join(self.buildpath, "lastbuildPLC.md5")

    def GetBinaryCodeMD5(self):
        if self.md5key is not None:
            return self.md5key
        else:
            try:
                return open(self._GetMD5FileName(), "r").read()
            except Exception, e:
                return None

    def check_and_update_hash_and_deps(self, bn):
        # Get latest computed hash and deps
        oldhash, deps = self.srcmd5.get(bn,(None,[]))
        # read source
        src = open(os.path.join(self.buildpath, bn)).read()
        # compute new hash
        newhash = hashlib.md5(src).hexdigest()
        # compare
        match = (oldhash == newhash)
        if not match:
            # file have changed
            # update direct dependencies
            deps = []
            for l in src.splitlines():
                res = includes_re.match(l)
                if res is not None:
                    depfn = res.groups()[0]
                    if os.path.exists(os.path.join(self.buildpath, depfn)):
                        #print bn + " depends on "+depfn
                        deps.append(depfn)
            # store that hashand deps
            self.srcmd5[bn] = (newhash, deps)
        # recurse through deps
        # TODO detect cicular deps.
        return reduce(operator.and_, map(self.check_and_update_hash_and_deps, deps), match)
                
    def build(self):
        # Retrieve toolchain user parameters
        toolchain_params = self.getTarget().getcontent()["value"]
        self.compiler = toolchain_params.getCompiler()
        self.linker = toolchain_params.getLinker()

        Builder_CFLAGS = ' '.join(self.getBuilderCFLAGS())

        ######### GENERATE OBJECT FILES ########################################
        obns = []
        objs = []
        relink = False
        for Location, CFilesAndCFLAGS, DoCalls in self.PluginsRootInstance.LocationCFilesAndCFLAGS:
            if Location:
                self.logger.write(_("Plugin : ") + self.PluginsRootInstance.GetChildByIECLocation(Location).GetCurrentName() + " " + str(Location)+"\n")
            else:
                self.logger.write(_("PLC :\n"))
                
            for CFile, CFLAGS in CFilesAndCFLAGS:
                bn = os.path.basename(CFile)
                obn = os.path.splitext(bn)[0]+".o"
                objectfilename = os.path.splitext(CFile)[0]+".o"

                match = self.check_and_update_hash_and_deps(bn)
                
                if match:
                    self.logger.write("   [pass]  "+bn+" -> "+obn+"\n")
                else:
                    relink = True

                    self.logger.write("   [CC]  "+bn+" -> "+obn+"\n")
                    
                    status, result, err_result = ProcessLogger(
                           self.logger,
                           "\"%s\" -c \"%s\" -o \"%s\" %s %s"%
                               (self.compiler, CFile, objectfilename, Builder_CFLAGS, CFLAGS)
                           ).spin()

                    if status :
                        self.srcmd5.pop(bn)
                        self.logger.write_error(_("C compilation of %s failed.\n")%bn)
                        return False

                obns.append(obn)
                objs.append(objectfilename)

        ######### GENERATE library FILE ########################################
        # Link all the object files into one binary file
        self.logger.write(_("Linking :\n"))
        if relink:
            objstring = []
    
            # Generate list .o files
            listobjstring = '"' + '"  "'.join(objs) + '"'
    
            ALLldflags = ' '.join(self.getBuilderLDFLAGS())
    
            self.logger.write("   [CC]  " + ' '.join(obns)+" -> " + self.exe + "\n")
    
            status, result, err_result = ProcessLogger(
                   self.logger,
                   "\"%s\" %s -o \"%s\" %s"%
                       (self.linker,
                        listobjstring,
                        self.exe_path,
                        ALLldflags)
                   ).spin()
            
            if status :
                return False
            else :
                # Calculate md5 key and get data for the new created PLC
                data=self.GetBinaryCode()
                self.md5key = hashlib.md5(data).hexdigest()
    
                # Store new PLC filename based on md5 key
                f = open(self._GetMD5FileName(), "w")
                f.write(self.md5key)
                f.close()
        else:
            self.logger.write("   [pass]  " + ' '.join(obns)+" -> " + self.exe + "\n")
            
        
        return True

