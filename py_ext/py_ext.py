#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2013: Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
# Copyright (C) 2025: Edouard TISSERANT
#
# See COPYING file for copyrights details.

import os
from POULibrary import POULibrary
from py_ext.PythonFileCTNMixin import PythonFileCTNMixin
import util.paths as paths


pyext_python_lib_code = open(paths.AbsNeighbourFile(__file__, "py_ext_rt.py"), "r").read()


class PythonLibrary(POULibrary):
    def GetLibraryPath(self):
        return paths.AbsNeighbourFile(__file__, "pous.xml")

    def Generate_C(self, buildpath, varlist, IECCFLAGS):

        plc_python_filepath = paths.AbsNeighbourFile(__file__, "plc_python.c")
        plc_python_file = open(plc_python_filepath, 'r')
        plc_python_code = plc_python_file.read()
        plc_python_file.close()
        python_eval_fb_list = []
        for v in varlist:
            if v["vartype"] == "FB" and v["type"] in ["PYTHON_EVAL",
                                                      "PYTHON_POLL"]:
                python_eval_fb_list.append(v)
        python_eval_fb_count = max(1, len(python_eval_fb_list))

        # prepare python code
        plc_python_code = plc_python_code % {
            "python_eval_fb_count": python_eval_fb_count}

        Gen_Pythonfile_path = os.path.join(buildpath, "py_ext.c")
        pythonfile = open(Gen_Pythonfile_path, 'w')
        pythonfile.write(plc_python_code)
        pythonfile.close()

        runtimefile_path = os.path.join(buildpath, "runtime_00_pyext.py")
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write(pyext_python_lib_code)
        runtimefile.close()
        return ((["py_ext"], [(Gen_Pythonfile_path, IECCFLAGS)], True), "",
                ("runtime_00_pyext.py", open(runtimefile_path, "rb")))


class PythonFile(PythonFileCTNMixin):

    def GetIconName(self):
        return "Pyfile"
