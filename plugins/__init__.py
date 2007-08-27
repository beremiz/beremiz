from os import listdir, path
from __templates import PlugTemplate

_base_path = path.split(__file__)[0]

__all__ = [name for name in listdir(_base_path) if path.isdir(path.join(_base_path, name)) and name != "CVS" or name.endswith(".py") and not name.startswith("__")]

#for name in __all__:
#    __import__(name, globals(), locals(), [])

