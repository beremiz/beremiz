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

from LPCProto import *



class LPCObject():
    def __init__(self, pluginsroot, comportstr):
        self.PLCStatus = "Disconnected"
        self.pluginsroot = pluginsroot
        self.PLCprint = pluginsroot.logger.writeyield
        self._Idxs = []
        comport = int(comportstr[3:]) - 1
        try:
            self.connect(comportstr)
        except Exception,e:
            self.pluginsroot.logger.write_error(str(e)+"\n")
            self.SerialConnection = None
            self.PLCStatus = "Disconnected"

    def HandleSerialTransaction(self, transaction):
        if self.SerialConnection is not None:
            try:
                self.PLCStatus, res = self.SerialConnection.HandleTransaction(transaction)
                return res
            except Exception,e:
                self.pluginsroot.logger.write_warning(str(e)+"\n")
                self.SerialConnection.close()
                self.SerialConnection = None
                self.PLCStatus = "Disconnected"
                return None
        
    def StartPLC(self, debug=False):
        raise LPCProtoError("Not implemented")
            
    def StopPLC(self):
        raise LPCProtoError("Not implemented")

    def GetPLCstatus(self):
        raise LPCProtoError("Not implemented")
    
    def NewPLC(self, md5sum, data, extrafiles):
        raise LPCProtoError("Not implemented")

    def MatchMD5(self, MD5):
        raise LPCProtoError("Not implemented")

    def SetTraceVariablesList(self, idxs):
        raise LPCProtoError("Not implemented")

    def GetTraceVariables(self):
        raise LPCProtoError("Not implemented")

