import os
from wxPopen import ProcessLogger
import hashlib

class toolchain_gcc():
    """
    This abstract class contains GCC specific code.
    It cannot be used as this and should be inherited in a target specific
    class such as target_linux or target_win32
    """
    def __init__(self, PuginsRootInstance):
        self.PuginsRootInstance = PuginsRootInstance
        self.logger = PuginsRootInstance.logger
        self.exe = PuginsRootInstance.GetProjectName() + self.extension
        self.buildpath = PuginsRootInstance._getBuildPath()
        self.exe_path = os.path.join(self.buildpath, self.exe)
        self.md5key = None

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
                
    
    def build(self):
        # Retrieve toolchain user parameters
        toolchain_params = self.PuginsRootInstance.BeremizRoot.getTargetType().getcontent()["value"]
        self.compiler = toolchain_params.getCompiler()
        self._CFLAGS = toolchain_params.getCFLAGS()
        self.linker = toolchain_params.getLinker()
        self._LDFLAGS = toolchain_params.getLDFLAGS()

        ######### GENERATE OBJECT FILES ########################################
        obns = []
        objs = []
        for Location, CFilesAndCFLAGS, DoCalls in self.PuginsRootInstance.LocationCFilesAndCFLAGS:
            if Location:
                self.logger.write("Plugin : " + self.PuginsRootInstance.GetChildByIECLocation(Location).GetCurrentName() + " " + str(Location)+"\n")
            else:
                self.logger.write("PLC :\n")
                
            for CFile, CFLAGS in CFilesAndCFLAGS:
                bn = os.path.basename(CFile)
                obn = os.path.splitext(bn)[0]+".o"
                obns.append(obn)
                self.logger.write("   [CC]  "+bn+" -> "+obn+"\n")
                objectfilename = os.path.splitext(CFile)[0]+".o"
                
                status, result, err_result = ProcessLogger(
                       self.logger,
                       "\"%s\" -c \"%s\" -o \"%s\" %s %s"%
                           (self.compiler, CFile, objectfilename, self._CFLAGS, CFLAGS)
                       ).spin()

                if status :
                    self.logger.write_error("C compilation of "+ bn +" failed.\n")
                    return False
                objs.append(objectfilename)

        ######### GENERATE library FILE ########################################
        # Link all the object files into one binary file
        self.logger.write("Linking :\n")
        objstring = []

        # Generate list .o files
        listobjstring = '"' + '"  "'.join(objs) + '"'

        ALLldflags = ' '.join(self.CustomLDFLAGS+self.PuginsRootInstance.LDFLAGS+[self._LDFLAGS])

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
            file = open(self._GetMD5FileName(), "w")
            file.write(self.md5key)
            file.close()
        
        return True

