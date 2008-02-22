from os import listdir, path

_base_path = path.split(__file__)[0]

__all__ = [name for name in listdir(_base_path) if path.isdir(path.join(_base_path, name)) and name.upper() != "CVS" or name.endswith(".py") and not name.startswith("__")]

helps = []
for name in __all__:
    helpfilename = path.join(_base_path, name, "README")
    if path.isfile(helpfilename):
        helps.append(open(helpfilename).readline().strip())
    else:
        helps.append(name)
