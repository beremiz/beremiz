import features

def GetEtherLabLibClass():
    from EthercatMaster import EtherlabLibrary
    return EtherlabLibrary

features.libraries.append(
    ('Etherlab', GetEtherLabLibClass))

def GetEtherLabClass():
    from etherlab import RootClass
    return RootClass

features.catalog.append(
    ('etherlab', _('EtherCat Master'), _('Map located variables over EtherCat'), GetEtherLabClass))

