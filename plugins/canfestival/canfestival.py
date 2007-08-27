import os
from nodelist import NodeList
from nodemanager import NodeManager
import config_utils, gen_cfile
from networkedit import networkedit

class _NetworkEdit(networkedit):
    " Overload some of CanFestival Network Editor methods "
    def OnCloseFrame(self, event):
        " Do reset _NodeListPlug.View when closed"
        self._onclose()
        event.Skip()

class _NodeListPlug(NodeList):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CanFestivalNode">
        <xsd:complexType>
          <xsd:attribute name="CAN_Device" type="xsd:string" use="required" />
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def __init__(self, buspath):
        manager = NodeManager()
        NodeList.__init__(self, manager)
        self.LoadProject(buspath)

    _View = None
    def _OpenView(self):
        if not self._View:
            def _onclose():
                self.View = None
            self._View = _NetworkEdit()
            self._View._onclose = _onclose
        return self.View
    PluginMethods = [("NetworkEdit",_OpenView)]

    def OnPlugClose(self):
        if self._View:
            self._View.Close()

    def PlugTestModified(self):
        return self.HasChanged()
        
    def PlugRequestSave(self):
        self.SaveProject()
        return True

    def Generate_C(self, dirpath, locations):
        """
        return C code for network dictionnary
        """
        filepath = os.path.join(dirpath, "master.c")
        master = config_utils.GenerateConciseDCF(locations, self)
        res = gen_cfile.GenerateFile(filepath, master)
        if not res:
             s = str(self.BaseParams.BusId)+"_IN(){}\n"
             s += "CanOpen(\""+self.CanFestivalNode.CAN_Device+"\")"
             f = file(filepath, 'a')
             f.write(s)
        else:
             pass # error
        return {"headers":["master.h"],"sources":["master.c"]}
    
class RootClass:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CanFestivalInstance">
        <xsd:complexType>
          <xsd:attribute name="CAN_Driver" type="xsd:string" use="required" />
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    PlugChildsTypes = [("CanOpenNode",_NodeListPlug)]

    def Generate_C(self, filepath, locations):
        """
        return C code for network dictionnary
        """
        master = config_utils.GenerateConciseDCF(locations, self)
        res = gen_cfile.GenerateFile(filepath, master)
        if not res:
             s = str(self.BaseParams.BusId)+"_IN(){}\n"
             s += "CanOpen(str(\""+self.CanFestivalNode.CAN_Device+"\")"
             f = file(filepath, 'a')
             f.write(s)
        else:
             pass # error

