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

from threading import Timer, Thread, Lock
import ctypes, os, commands, types, sys
import traceback
from LPCProto import *

class LPCObject():
    def __init__(self,pluginsroot):
        self.PLCStatus = "Stopped"
        self.pluginsroot = pluginsroot
        self.PLCprint = pluginsroot.logger.write
        self.SerialConnection = None
        self._Idxs = []
        
    def HandleSerialTransaction(self, transaction):
        if self.SerialConnection is None:
            try:
                self.SerialConnection = LPCProto(6,115200,2)
            except Exception,e:
                self.pluginsroot.logger.write_error(str(e)+"\n")
                self.SerialConnection = None
                return "Disconnected", res
        try:
            return self.SerialConnection.HandleTransaction(transaction)
        except LPCError,e:
            #pluginsroot.logger.write_error(traceback.format_exc())
            self.pluginsroot.logger.write_error(str(e)+"\n")
            self.SerialConnection = None
            return "Disconnected", res

    def StartPLC(self, debug=False):
        PLCprint("StartPLC")
        self.HandleSerialTransaction(STARTTransaction())
            
    def StopPLC(self):
        PLCprint("StopPLC")
        self.HandleSerialTransaction(STOPTransaction())

    def ForceReload(self):
        pass

    def GetPLCstatus(self):
        status,data = self.HandleSerialTransaction(IDLETransaction())
        return status
    
    def NewPLC(self, md5sum, data, extrafiles):
        pass

    def MatchMD5(self, MD5):
        status,data = self.HandleSerialTransaction(PLCIDTransaction())
        return data == MD5
    
    def SetTraceVariablesList(self, idxs):
        self._Idxs = idxs[]
        status,data = self.HandleSerialTransaction(
               SET_TRACE_VARIABLETransaction(
                     ''.join(map(chr,idx))))

    class IEC_STRING(ctypes.Structure):
        """
        Must be changed according to changes in iec_types.h
        """
        _fields_ = [("len", ctypes.c_uint8),
                    ("body", ctypes.c_char * 127)] 
    
    TypeTranslator = {"BOOL" :       (ctypes.c_uint8, lambda x:x.value!=0),
                      "STEP" :       (ctypes.c_uint8, lambda x:x.value),
                      "TRANSITION" : (ctypes.c_uint8, lambda x:x.value),
                      "ACTION" :     (ctypes.c_uint8, lambda x:x.value),
                      "SINT" :       (ctypes.c_int8, lambda x:x.value),
                      "USINT" :      (ctypes.c_uint8, lambda x:x.value),
                      "BYTE" :       (ctypes.c_uint8, lambda x:x.value),
                      "STRING" :     (IEC_STRING, lambda x:x.body[:x.len]),
                      "INT" :        (ctypes.c_int16, lambda x:x.value),
                      "UINT" :       (ctypes.c_uint16, lambda x:x.value),
                      "WORD" :       (ctypes.c_uint16, lambda x:x.value),
                      "WSTRING" :    (None, None),#TODO
                      "DINT" :       (ctypes.c_int32, lambda x:x.value),
                      "UDINT" :      (ctypes.c_uint32, lambda x:x.value),
                      "DWORD" :      (ctypes.c_uint32, lambda x:x.value),
                      "LINT" :       (ctypes.c_int64, lambda x:x.value),
                      "ULINT" :      (ctypes.c_uint64, lambda x:x.value),
                      "LWORD" :      (ctypes.c_uint64, lambda x:x.value),
                      "REAL" :       (ctypes.c_float, lambda x:x.value),
                      "LREAL" :      (ctypes.c_double, lambda x:x.value),
                      } 
                           
    def GetTraceVariables(self):
        """
        Return a list of variables, corresponding to the list of required idx
        """
        status,data = self.HandleSerialTransaction(GET_TRACE_VARIABLETransaction())
        if data is not None:
            # transform serial string to real byte string in memory 
            buffer = ctypes.c_char_p(data)
            # tick is first value in buffer
            tick = ctypes.cast(buffer,ctypes.POINTER(ctypes.c_uint32)).contents
            # variable data starts just after tick 
            cursorp = ctypes.addressof(buffer) = ctypes.sizeof(ctypes.c_uint32)
            endp = offset + len(data)
            for idx, iectype in self._Idxs:
                cursor = ctypes.c_void_p(cursorp)
                c_type,unpack_func = self.TypeTranslator.get(iectype, (None,None))
                if c_type is not None and cursorp < endp:
                    res.append(unpack_func(ctypes.cast(cursor,
                                                       ctypes.POINTER(c_type)).contents))
                    cursorp += ctypes.sizeof(c_type) 
                else:
                    PLCprint("Debug error !")
                        break
            return self.PLCStatus, tick, res
        return self.PLCStatus, None, None

