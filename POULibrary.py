from PLCControler import PLCControler

class POULibrary:
    def __init__(self, LibName, TypeStack):
        self.LibName = LibName
        self.LibraryControler = PLCControler()
        self.LibraryControler.OpenXMLFile(self.GetLibraryPath())
        self.LibraryControler.ClearConfNodeTypes()
        self.LibraryControler.AddConfNodeTypesList(TypeStack)
        self.program = None;

    def GetSTCode(self):
        if not self.program:
            self.program = self.LibraryControler.GenerateProgram()[0]+"\n"
        return self.program 

    def GetName(self):
        return self.LibName
        
    def GetTypes(self):
        return {"name" : self.GetName(), "types": self.LibraryControler.Project}

    def GetLibraryPath(self):
        raise Exception("Not implemented")

    def Generate_C(self, buildpath, varlist, IECCFLAGS):
        # Pure python or IEC libs doesn't produce C code
        return ((""), [], False), ""
