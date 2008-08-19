# module which import C files as strings

import os

def code(name):
    filename = os.path.join(os.path.split(__file__)[0],name + ".c")
    if os.path.exists(filename):
        return open(filename).read()
    else:
        return "#error %s target not implemented !!!\n"%name

from PLCObject import PLCObject
import ServicePublisher
