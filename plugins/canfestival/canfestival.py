from nodelist import NodeList
from nodemanager import NodeManager
import config_utils, gen_cfile

class _Beremiz_CanFestival_Controller(NodeList):
    def __init__(self, buspath, bus_id):
        self.bus_id = bus_id
        manager = NodeManager()
        NodeList.__init__(self, manager)
        self.LoadProject(buspath)

    def SaveBus(self):
        self.SaveProject()

    def Generate_C(self, filepath, locations):
        """
        return C code for network dictionnary
        """
        master = config_utils.GenerateConciseDCF(locations, self)
        res = gen_cfile.GenerateFile(filepath, master)
        if not res:
             s = str(self.bus_id)+"_IN(){}\n"
             f = file(filepath, 'a')
             f.write(s)
        else:
             pass # error

def BlockListFactory(bmz_inst):
    return []

def ControllerFactory():
  return _Beremiz_CanFestival_Controller()