#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from LPCBootProto import *
from LPCObject import *

class LPCBootObject(LPCObject):
    def __init__(self, pluginsroot, comportstr):
        LPCObject.__init__(self, pluginsroot, comportstr)
        self.successfully_transfered = False
    
    def connect(self,comport):
        self.SerialConnection = LPCBootProto(comport,#number
                                         115200, #speed
                                         120)      #timeout
        self.PLCStatus = "Stopped"
    
    def NewPLC(self, md5sum, data, extrafiles):
        self.successfully_transfered = self.HandleSerialTransaction(LOADTransaction(data))
        return successfully_transfered

    def MatchMD5(self, MD5):
        return self.successfully_transfered


    def SetTraceVariablesList(self, idxs):
        pass
    
    def GetTraceVariables(self):
        return self.PLCStatus, None, None

