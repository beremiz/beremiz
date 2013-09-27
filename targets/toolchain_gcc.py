import os, re, operator
from util.ProcessLogger import ProcessLogger
import hashlib

includes_re =  re.compile('\s*#include\s*["<]([^">]*)[">].*')

class toolchain_gcc():
    """
    This abstract class contains GCC specific code.
    It cannot be used as this and should be inherited in a target specific
    class such as target_linux or target_win32
    """
    def __init__(self, CTRInstance):
        self.CTRInstance = CTRInstance
        self.buildpath = None
        self.SetBuildPath(self.CTRInstance._getBuildPath())
    
    def getBuilderCFLAGS(self):
        """
        Returns list of builder specific CFLAGS
        """
        return [self.CTRInstance.GetTarget().getcontent().getCFLAGS()]

    def getBuilderLDFLAGS(self):
        """
        Returns list of builder specific LDFLAGS
        """
        return self.CTRInstance.LDFLAGS + \
               [self.CTRInstance.GetTarget().getcontent().getLDFLAGS()]

    def GetBinaryCode(self):
        try:
            return open(self.exe_path, "rb").read()
        except Exception, e:
            return None
        
    def _GetMD5FileName(self):
        return os.path.join(self.buildpath, "lastbuildPLC.md5")

    def ResetBinaryCodeMD5(self):
        self.md5key = None
        try:
            os.remove(self._GetMD5FileName())
        except Exception, e:
            pass
    
    def GetBinaryCodeMD5(self):
        if self.md5key is not None:
            return self.md5key
        else:
            try:
                return open(self._GetMD5FileName(), "r").read()
            except Exception, e:
                return None
    
    def SetBuildPath(self, buildpath):
        if self.buildpath != buildpath:
            self.buildpath = buildpath
            self.exe = self.CTRInstance.GetProjectName() + self.extension
            self.exe_path = os.path.join(self.buildpath, self.exe)
            self.md5key = None
            self.srcmd5 = {}
    
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
        toolchain_params = self.CTRInstance.GetTarget().getcontent()
        self.compiler = toolchain_params.getCompiler()
        self.linker = toolchain_params.getLinker()

        Builder_CFLAGS = ' '.join(self.getBuilderCFLAGS())

        ######### GENERATE OBJECT FILES ########################################
        obns = []
        objs = []
        relink = self.GetBinaryCode() is None
        for Location, CFilesAndCFLAGS, DoCalls in self.CTRInstance.LocationCFilesAndCFLAGS:
            if CFilesAndCFLAGS:
                if Location :
                    self.CTRInstance.logger.write(".".join(map(str,Location))+" :\n")
                else:
                    self.CTRInstance.logger.write(_("PLC :\n"))
                
            for CFile, CFLAGS in CFilesAndCFLAGS:
                if CFile.endswith(".c"):
                    bn = os.path.basename(CFile)
                    obn = os.path.splitext(bn)[0]+".o"
                    objectfilename = os.path.splitext(CFile)[0]+".o"

                    match = self.check_and_update_hash_and_deps(bn)
                    
                    if match:
                        self.CTRInstance.logger.write("   [pass]  "+bn+" -> "+obn+"\n")
                    else:
                        relink = True

                        self.CTRInstance.logger.write("   [CC]  "+bn+" -> "+obn+"\n")
                        
                        status, result, err_result = ProcessLogger(
                               self.CTRInstance.logger,
                               "\"%s\" -c \"%s\" -o \"%s\" %s %s"%
                                   (self.compiler, CFile, objectfilename, Builder_CFLAGS, CFLAGS)
                               ).spin()

                        if status :
                            self.srcmd5.pop(bn)
                            self.CTRInstance.logger.write_error(_("C compilation of %s failed.\n")%bn)
                            return False
                    obns.append(obn)
                    objs.append(objectfilename)
                elif CFile.endswith(".o"):
                    obns.append(os.path.basename(CFile))
                    objs.append(CFile)

        ######### GENERATE library FILE ########################################
        # Link all the object files into one binary file
        self.CTRInstance.logger.write(_("Linking :\n"))
        if relink:
            objstring = []
    
            # Generate list .o files
            listobjstring = '"' + '"  "'.join(objs) + '"'
    
            ALLldflags = ' '.join(self.getBuilderLDFLAGS())
    
            self.CTRInstance.logger.write("   [CC]  " + ' '.join(obns)+" -> " + self.exe + "\n")
    
            status, result, err_result = ProcessLogger(
                   self.CTRInstance.logger,
                   "\"%s\" %s -o \"%s\" %s"%
                       (self.linker,
                        listobjstring,
                        self.exe_path,
                        ALLldflags)
                   ).spin()
            
            if status :
                return False
                
        else:
            self.CTRInstance.logger.write("   [pass]  " + ' '.join(obns)+" -> " + self.exe + "\n")
        
        # Calculate md5 key and get data for the new created PLC
        data=self.GetBinaryCode()
        self.md5key = hashlib.md5(data).hexdigest()

        # Store new PLC filename based on md5 key
        f = open(self._GetMD5FileName(), "w")
        f.write(self.md5key)
        f.close()
        
        return True

