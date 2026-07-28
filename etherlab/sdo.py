class SDOEntry(object):
    def __init__(self, idx="", subIdx="", datatype="", size="", value=""):
        self.idx = idx
        self.subIdx = subIdx
        self.datatype = datatype
        self.size = size
        self.value = value


class SDODataPack(object):
    def __init__(self):
        self.entries = []
        self.slavePos = 0
