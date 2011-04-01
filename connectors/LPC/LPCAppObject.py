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

import ctypes
from LPCAppProto import *
from LPCObject import *
from targets.typemapping import SameEndianessTypeTranslator as TypeTranslator

class LPCAppObject(LPCObject):
    def connect(self,comport):
        self.SerialConnection = LPCAppProto(comport,#number
                                         115200, #speed
                                         2)      #timeout

    def StartPLC(self, debug=False):
        self.HandleSerialTransaction(STARTTransaction())
            
    def StopPLC(self):
        self.HandleSerialTransaction(STOPTransaction())
        return True

    def ResetPLC(self):
        self.HandleSerialTransaction(RESETTransaction())
        return self.PLCStatus

    def GetPLCstatus(self):
        self.HandleSerialTransaction(GET_PLCIDTransaction())
        return self.PLCStatus

    def MatchMD5(self, MD5):
        data = self.HandleSerialTransaction(GET_PLCIDTransaction())
        if data is not None:
            return data[:32] == MD5[:32]
        return False

    def SetTraceVariablesList(self, idxs):
        """
        Call ctype imported function to append 
        these indexes to registred variables in PLC debugger
        """
        if idxs:
            buff = ""
            # keep a copy of requested idx
            self._Idxs = idxs[:]
            for idx,iectype,force in idxs:
                idxstr = ctypes.string_at(
                          ctypes.pointer(
                           ctypes.c_uint32(idx)),4)
                if force !=None:
                    c_type,unpack_func, pack_func = TypeTranslator.get(iectype, (None,None,None))
                    forced_type_size = ctypes.sizeof(c_type)
                    forced_type_size_str = chr(forced_type_size)
                    forcestr = ctypes.string_at(
                                ctypes.pointer(
                                 pack_func(c_type,force)),
                                 forced_type_size)
                    buff += idxstr + forced_type_size_str + forcestr
                else:
                    buff += idxstr + chr(0)
        else:
            buff = ""
            self._Idxs =  []

        self.HandleSerialTransaction(SET_TRACE_VARIABLETransaction(buff))

    def GetTraceVariables(self):
        """
        Return a list of variables, corresponding to the list of required idx
        """
        offset = 0
        strbuf = self.HandleSerialTransaction(
                                     GET_TRACE_VARIABLETransaction())
        if strbuf is not None and len(strbuf) > 4 and self.PLCStatus == "Started":
            res=[]
            size = len(strbuf) - 4
            tick = ctypes.cast(
                    ctypes.c_char_p(strbuf[:4]),
                    ctypes.POINTER(ctypes.c_int)).contents
            buff = ctypes.cast(
                      ctypes.c_char_p(strbuf[4:]),
                      ctypes.c_void_p)
            for idx, iectype, forced in self._Idxs:
                cursor = ctypes.c_void_p(buff.value + offset)
                c_type,unpack_func, pack_func = TypeTranslator.get(iectype, (None,None,None))
                if c_type is not None and offset < size:
                    res.append(unpack_func(ctypes.cast(cursor,
                                                       ctypes.POINTER(c_type)).contents))
                    offset += ctypes.sizeof(c_type)
                else:
                    #if c_type is None:
                        #PLCprint("Debug error - " + iectype + " not supported !")
                    #if offset >= size:
                        #PLCprint("Debug error - buffer too small !")
                    break
            if offset and offset == size:
                return self.PLCStatus, tick.value, res
            #PLCprint("Debug error - wrong buffer unpack !")
        return self.PLCStatus, None, [] 

