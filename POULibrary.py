#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.



from weakref import ref

# Exception type for problems that user has to take action in order to fix
class UserAddressedException(Exception):
    pass


class POULibrary(object):
    def __init__(self, CTR, LibName, TypeStack):
        from PLCControler import PLCControler
        self.CTR = ref(CTR)
        self.LibName = LibName
        libpath = self.GetLibraryPath()
        if libpath is not None:            
            self.LibraryControler = PLCControler()
            self.LibraryControler.OpenXMLFile(libpath)
            self.LibraryControler.ClearConfNodeTypes()
            self.LibraryControler.AddConfNodeTypesList(TypeStack)
        else:
            self.LibraryControler = None
        self.program = None

    def GetSTCode(self):
        if self.program is None:
            if self.LibraryControler is not None:
                self.program = self.LibraryControler.GenerateProgram(noconfig=True)[0]+"\n"
            else:
                self.program = f"(* Library {self.LibName} produced no ST code *)"
        return self.program

    def GetName(self):
        return self.LibName

    def GetCTR(self):
        return self.CTR()

    def GetTypes(self):
        """
        Types of the library, for the IDE and the libraries loaded after it.
        Its POUs appear in the library panel under "<name> POUs". A library
        may sort some of them into categories of their own by adding to the
        returned dictionary:
          "categories": [(category name, [POU name, ...]), ...]

        @return: {"name": library name, "types": project of the library}
        """
        return {"name": self.GetName(),
                "types": self.LibraryControler.Project
                         if self.LibraryControler else None}

    def GetLibraryPath(self):
        raise Exception("Not implemented")

    def GetSDKFiles(self):
        """
        Generated files a plc-sdk has to carry along this library's POUs, so
        that a PLC rebuilt from the SDK still resolves the C symbols they call.
        Only meaningful once Generate_C has run.

        @return: ([(Cfile, CFLAGS), ...], [header, ...])
        """
        return [], []

    def Generate_C(self, buildpath, pous_data, IECCFLAGS):
        """
        Generate C code for Libraries
        
        Generate_C returns a tuple :
          (["library_name"],[(Cfiles, CFLAGS)], DoCalls), LDFLAGS, *extra_files

        The first element may also be a list of such location-entries, when a
        library needs to place C files in more than one target binary (e.g. a
        split hot-swap build where some files go to the IOs .so and others to
        the logic .so, selected by location truthiness in toolchain_gcc):
          [(["name"], [(Cfiles, CFLAGS)], DoCalls), ([], [...], DoCalls)], LDFLAGS, *extra_files

        extra_files is:
          [(fname,fobject), ...]

        DoCalls is either a Boolean, a dictionary, or a string,
        see definitions in ConfigTreeNode.CTNGenerate_C
        """
        # Pure python or IEC libs doesn't produce C code
        return ((""), [], False), ""

    def GlobalInstances(self):
        """
        @return: [varlist_object, ...]
        """
        varlists = []
        if self.LibraryControler:
            for configuration in self.LibraryControler.Project.getconfigurations():
                varlist = configuration.getglobalVars()
                if len(varlist)>0 :
                    varlists += varlist
        return varlists

    def FatalError(self, message):
        """ Raise an exception that will trigger error message intended to 
            the user, but without backtrace since it is not a software error """

        raise UserAddressedException(message)

    def OnModelRefresh(self):
        pass

    def SupportsTarget(self, target):
        return True

def SimplePOULibraryFactory(path):
    class SimplePOULibrary(POULibrary):
        def GetLibraryPath(self):
            return path
    return SimplePOULibrary
