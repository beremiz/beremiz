import os
from nodelist import NodeList
from nodemanager import NodeManager
import config_utils, gen_cfile
from networkedit import networkedit

class _NetworkEditPlugg(networkedit):
    def OnCloseFrame(self, event):
        self.OnPluggClose()
        event.Skip()

class BusController(NodeList):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CanFestivalNode">
        <xsd:complexType>
          <xsd:attribute name="CAN_Device" type="xsd:string" use="required" />
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    ViewClass = _NetworkEditPlugg
    
    def __init__(self, buspath):
        manager = NodeManager()
        NodeList.__init__(self, manager)
        self.LoadProject(buspath)

    def TestModified(self):
        return self.HasChanged()
        
    def ReqSave(self):
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
             s += "CanOpen(str(\""+self.CanFestivalNode.CAN_Device)+"\")"
             f = file(filepath, 'a')
             f.write(s)
        else:
             pass # error
        return {"headers":["master.h"],"sources":["master.c"]}
    
class PluginController:
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CanFestivalInstance">
        <xsd:complexType>
          <xsd:attribute name="CAN_Driver" type="xsd:string" use="required" />
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def Generate_C(self, filepath, locations):
        """
        return C code for network dictionnary
        """
        master = config_utils.GenerateConciseDCF(locations, self)
        res = gen_cfile.GenerateFile(filepath, master)
        if not res:
             s = str(self.BaseParams.BusId)+"_IN(){}\n"
             s += "CanOpen(str(\""+self.CanFestivalNode.CAN_Device)+"\")"
             f = file(filepath, 'a')
             f.write(s)
        else:
             pass # error

