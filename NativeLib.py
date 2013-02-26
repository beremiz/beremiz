import os
from POULibrary import POULibrary

class NativeLibrary(POULibrary):
    def GetLibraryPath(self):
        return os.path.join(os.path.split(__file__)[0], "NativeLib.xml") 

