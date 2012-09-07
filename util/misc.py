"""
Misc definitions
"""

import os,sys

# helper func to check path write permission
def CheckPathPerm(path):
    if path is None or not os.path.isdir(path):
        return False
    for root, dirs, files in os.walk(path):
         for name in files:
             if os.access(root, os.W_OK) is not True or os.access(os.path.join(root, name), os.W_OK) is not True:
                 return False
    return True

def GetClassImporter(classpath):
    if type(classpath)==str:
        def fac():
            mod=__import__(classpath.rsplit('.',1)[0])
            return reduce(getattr, classpath.split('.')[1:], mod)
        return fac
    else:
        return classpath
