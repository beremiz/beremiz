from os import listdir, path

base_path = path.split(__file__)[0]

__all__ = [name for name in listdir(base_path) if path.isdir(path.join(base_path, name)) and name != "CVS" or name.endswith(".py") and not name.startswith("__")]

for name in __all__:
    __import__(name, globals(), locals(), [])
