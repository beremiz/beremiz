"""Lets wxPython start on GTK Broadway backend.

wxPython 4.2.1 (Ubuntu noble) checks for an X11 display before creating wx.App,
and refuses to start otherwise. This directory is added to PYTHONPATH of IDE
under test, so that IDE and runtime it spawns both get patched wx.
"""

import sys
import importlib.util
from importlib.abc import MetaPathFinder


class PatchWxDisplayCheck(MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name != "wx.core":
            return None
        sys.meta_path.remove(self)
        spec = importlib.util.find_spec(name)
        exec_module = spec.loader.exec_module

        def patched_exec_module(module):
            exec_module(module)
            module.App.IsDisplayAvailable = staticmethod(lambda: True)

        spec.loader.exec_module = patched_exec_module
        return spec


sys.meta_path.insert(0, PatchWxDisplayCheck())
