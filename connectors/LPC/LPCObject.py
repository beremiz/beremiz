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
        self.StorageConnection = None
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

    class IEC_STRING(ctypes.Structure):
        """
        Must be changed according to changes in iec_types.h
        """
        _fields_ = [("len", ctypes.c_uint8),
                    ("body", ctypes.c_char * 126)] 
    
    TypeTranslator = {"BOOL" :       (ctypes.c_uint8,  lambda x:x.value!=0,     lambda t,x:t(x)),
                      "STEP" :       (ctypes.c_uint8,  lambda x:x.value,        lambda t,x:t(x)),
                      "TRANSITION" : (ctypes.c_uint8,  lambda x:x.value,        lambda t,x:t(x)),
                      "ACTION" :     (ctypes.c_uint8,  lambda x:x.value,        lambda t,x:t(x)),
                      "SINT" :       (ctypes.c_int8,   lambda x:x.value,        lambda t,x:t(x)),
                      "USINT" :      (ctypes.c_uint8,  lambda x:x.value,        lambda t,x:t(x)),
                      "BYTE" :       (ctypes.c_uint8,  lambda x:x.value,        lambda t,x:t(x)),
                      "STRING" :     (IEC_STRING,      lambda x:x.body[:x.len], lambda t,x:t(len(x),x)),
                      "INT" :        (ctypes.c_int16,  lambda x:x.value,        lambda t,x:t(x)),
                      "UINT" :       (ctypes.c_uint16, lambda x:x.value,        lambda t,x:t(x)),
                      "WORD" :       (ctypes.c_uint16, lambda x:x.value,        lambda t,x:t(x)),
                      "WSTRING" :    (None,            None,                    None),#TODO
                      "DINT" :       (ctypes.c_int32,  lambda x:x.value,        lambda t,x:t(x)),
                      "UDINT" :      (ctypes.c_uint32, lambda x:x.value,        lambda t,x:t(x)),
                      "DWORD" :      (ctypes.c_uint32, lambda x:x.value,        lambda t,x:t(x)),
                      "LINT" :       (ctypes.c_int64,  lambda x:x.value,        lambda t,x:t(x)),
                      "ULINT" :      (ctypes.c_uint64, lambda x:x.value,        lambda t,x:t(x)),
                      "LWORD" :      (ctypes.c_uint64, lambda x:x.value,        lambda t,x:t(x)),
                      "REAL" :       (ctypes.c_float,  lambda x:x.value,        lambda t,x:t(x)),
                      "LREAL" :      (ctypes.c_double, lambda x:x.value,        lambda t,x:t(x)),
                      } 

    def SetTraceVariablesList(self, idxs):
        self._Idxs = idxs[:]
        status,data = self.HandleSerialTransaction(
               SET_TRACE_VARIABLETransaction(
                     ''.join(map(chr,idx))))

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
                           ctypes.c_uint32(length)),4)
                if force !=None:
                    c_type,unpack_func, pack_func = self.TypeTranslator.get(iectype, (None,None,None))
                    forcedsizestr = chr(ctypes.sizeof(c_type))
                    forcestr = ctypes.string_at(
                                ctypes.pointer(
                                 pack_func(c_type,force)),
                                 forced_type_size)
                    buff += idxstr + forced_type_size_str + forcestr
                else:
                    buff += idxstr + chr(0)
            status,data = self.HandleSerialTransaction(
                   SET_TRACE_VARIABLETransaction(buff))
        else:
            self._Idxs =  []

    def GetTraceVariables(self):
        """
        Return a list of variables, corresponding to the list of required idx
        """
        if self.PLCStatus == "Started":
            res=[]
            tick = ctypes.c_uint32()
            size = ctypes.c_uint32()
            buffer = ctypes.c_void_p()
            offset = 0
            if self.PLClibraryLock.acquire(False) and \
               self._GetDebugData(ctypes.byref(tick),ctypes.byref(size),ctypes.byref(buffer)) == 0 :
                if size.value:
                    for idx, iectype, forced in self._Idxs:
                        cursor = ctypes.c_void_p(buffer.value + offset)
                        c_type,unpack_func, pack_func = self.TypeTranslator.get(iectype, (None,None,None))
                        if c_type is not None and offset < size:
                            res.append(unpack_func(ctypes.cast(cursor,
                                                               ctypes.POINTER(c_type)).contents))
                            offset += ctypes.sizeof(c_type)
                        else:
                            if c_type is None:
                                PLCprint("Debug error - " + iectype + " not supported !")
                            if offset >= size:
                                PLCprint("Debug error - buffer too small !")
                            break
                self._FreeDebugData()
                self.PLClibraryLock.release()
            if offset and offset == size.value:
                return self.PLCStatus, tick.value, res
            elif size.value:
                PLCprint("Debug error - wrong buffer unpack !")
        return self.PLCStatus, None, None

