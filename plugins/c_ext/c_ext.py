import wx
import wx.stc as stc
import os, sys, shutil
from CppSTC import CppSTC
from plugger import PlugTemplate
import tempfile

class _Cfile:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="C_Extension">
        <xsd:complexType>
          <xsd:attribute name="C_Files" type="xsd:string" use="optional" default="myfile.c"/>
          <xsd:attribute name="CFLAGS" type="xsd:string" use="required"/>
          <xsd:attribute name="LDFLAGS" type="xsd:string" use="required"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """
    def __init__(self):
        self.CheckCFilesExist()
        
    def CheckCFilesExist(self):
        for CFile in self.CFileNames():
            if not os.path.isfile(CFile):
                f = open(CFile, 'w')
                f.write("/*Empty*/")
                f.close()

    def CFileBaseNames(self):
        """
        Returns list of C files base names, out of C_Extension.C_Files, coma separated list
        """
        return map(str.strip,str(self.C_Extension.getC_Files()).split(','))

    def CFileName(self, fn):
        return os.path.join(self.PlugPath(),fn)

    def CFileNames(self):
        """
        Returns list of full C files paths, out of C_Extension.C_Files, coma separated list
        """
        return map(self.CFileName, self.CFileBaseNames())

    def SetParamsAttribute(self, path, value, logger):
        """
        Take actions if C_Files changed
        """
        # Get a C files list before changes
        oldnames = self.CFileNames()
        # Apply changes
        res = PlugTemplate.SetParamsAttribute(self, path, value, logger)
        # If changes was about C files,
        if path == "C_Extension.C_Files":
            # Create files if did not exist
            self.CheckCFilesExist()
            # Get new list
            newnames = self.CFileNames()
            # Move unused files into trash (temporary directory)
            for oldfile in oldnames:
                if oldfile not in newnames:
                    # define new "trash" name
                    trashname = os.path.join(tempfile.gettempdir(),os.path.basename(oldfile))
                    # move the file
                    shutil.move(oldfile, trashname)
                    # warn user
                    logger.write_warning("\"%s\" moved to \"%s\"\n"%(oldfile, trashname))
            return value, False
        return res

    _Views = {}
    def _OpenView(self, logger):
        lst = self.CFileBaseNames()

        dlg = wx.MultiChoiceDialog( self.GetPlugRoot().AppFrame, 
                                   "Choose C files to Edit :",
                                   "Edit", lst)

        if (dlg.ShowModal() == wx.ID_OK):
            selections = dlg.GetSelections()
            for selected in [lst[x] for x in selections]:
                if selected not in self._Views:
                    # keep track of selected name as static for later close
                    def _onclose(evt, sel = selected):
                        self.SaveCView(sel)
                        self._Views.pop(sel)
                        evt.Skip()
                    New_View = wx.Frame(self.GetPlugRoot().AppFrame,-1,selected)
                    New_View.Bind(wx.EVT_CLOSE, _onclose)
                    ed = CppSTC(New_View, wx.NewId())
                    ed.SetText(open(self.CFileName(selected)).read())
                    ed.EmptyUndoBuffer()
                    ed.Colourise(0, -1)
                    ed.SetMarginType(1, stc.STC_MARGIN_NUMBER)
                    ed.SetMarginWidth(1, 25)
                    New_View.ed = ed
                    New_View.Show()
                    self._Views[selected] = New_View

        dlg.Destroy()
        

    PluginMethods = [
        {"name" : "Edit C File", 
         "tooltip" : "Edit C File",
         "method" : "_OpenView"},
        {"name" : "Import C File", 
         "tooltip" : "Import C File",
         "method" : "_OpenView"}
    ]

    def SaveCView(self, name):
        f = open(self.CFileName(name),'w')
        f.write(self._Views[name].ed.GetText())
        f.close()
        
    def OnPlugSave(self):
        for name in self._Views:
            self.SaveCView(name)
        return True

    def PlugGenerate_C(self, buildpath, locations, logger):
        """
        Generate C code
        @param current_location: Tupple containing plugin IEC location : %I0.0.4.5 => (0,0,4,5)
        @param locations: List of complete variables locations \
            [{"IEC_TYPE" : the IEC type (i.e. "INT", "STRING", ...)
            "NAME" : name of the variable (generally "__IW0_1_2" style)
            "DIR" : direction "Q","I" or "M"
            "SIZE" : size "X", "B", "W", "D", "L"
            "LOC" : tuple of interger for IEC location (0,1,2,...)
            }, ...]
        @return: [(C_file_name, CFLAGS),...] , LDFLAGS_TO_APPEND
        """
        current_location = self.GetCurrentLocation()
        # define a unique name for the generated C file
        location_str = "_".join(map(lambda x:str(x), current_location))
        res = []
        for CFile in self.CFileBaseNames():
            Gen_Cfile_path = os.path.join(buildpath, "CFile_%s_%s.c"%(location_str, os.path.splitext(CFile)[0]))
            f = open(Gen_Cfile_path,'w')
            f.write("/* Header generated by Beremiz c_ext plugin */\n")
            f.write("#include \"iec_std_lib.h\"\n")
            f.write("#define EXT_C_INIT __init_%s\n"%location_str)
            f.write("#define EXT_C_CLEANUP __init_%s\n"%location_str)
            f.write("#define EXT_C_PUBLISH __init_%s\n"%location_str)
            f.write("#define EXT_C_RETRIVE __init_%s\n"%location_str)
            for loc in locations:
                f.write(loc["IEC_TYPE"]+" "+loc["NAME"]+";\n")
            f.write("/* End of header generated by Beremiz c_ext plugin */\n\n")
            src_file = open(self.CFileName(CFile),'r')
            f.write(src_file.read())
            src_file.close()
            f.close()
            res.append((Gen_Cfile_path,str(self.C_Extension.getCFLAGS())))
        return res,str(self.C_Extension.getLDFLAGS()),True
    
class RootClass:

    PlugChildsTypes = [("C_File",_Cfile)]
    
    def PlugGenerate_C(self, buildpath, locations, logger):
        return [],"",False


