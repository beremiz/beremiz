from os import listdir, path

l = listdir(path.split(__file__)[0])

__all__ = [name[0:-3] for name in l if name.endswith(".py") and not name.startswith("__")]

