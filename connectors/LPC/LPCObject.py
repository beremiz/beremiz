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

class LPCObject():
    _Idxs = []
    def __init__(self,pluginsroot):
        self.PLCStatus = "Stopped"
        self.pluginsroot = pluginsroot
        self.PLCprint = pluginsroot.logger.write
    
    def StartPLC(self, debug=False):
        PLCprint("StartPLC")
        if self.CurrentPLCFilename is not None:
            self.PLCStatus = "Started"
            self.PythonThread = Thread(target=self.PythonThreadProc, args=[debug])
            self.PythonThread.start()
            
    def StopPLC(self):
        PLCprint("StopPLC")
        if self.PLCStatus == "Started":
            self._stopPLC()
            return True
        return False

    def ForceReload(self):
        # respawn python interpreter
        Timer(0.1,self._Reload).start()
        return True

    def GetPLCstatus(self):
        return self.PLCStatus
    
    def NewPLC(self, md5sum, data, extrafiles):
        PLCprint("NewPLC (%s)"%md5sum)
        if self.PLCStatus in ["Stopped", "Empty", "Broken"]:
            NewFileName = md5sum + lib_ext
            extra_files_log = os.path.join(self.workingdir,"extra_files.txt")
            try:
                os.remove(os.path.join(self.workingdir,
                                       self.CurrentPLCFilename))
                for filename in file(extra_files_log, "r").readlines() + [extra_files_log]:
                    try:
                        os.remove(os.path.join(self.workingdir, filename.strip()))
                    except:
                        pass
            except:
                pass
                        
            try:
                # Create new PLC file
                open(os.path.join(self.workingdir,NewFileName),
                     'wb').write(data)
        
                # Store new PLC filename based on md5 key
                open(self._GetMD5FileName(), "w").write(md5sum)
        
                # Then write the files
                log = file(extra_files_log, "w")
                for fname,fdata in extrafiles:
                    fpath = os.path.join(self.workingdir,fname)
                    open(fpath, "wb").write(fdata)
                    log.write(fname+'\n')

                # Store new PLC filename
                self.CurrentPLCFilename = NewFileName
            except:
                PLCprint(traceback.format_exc())
                return False
            if self.PLCStatus == "Empty":
                self.PLCStatus = "Stopped"
            return True
        return False

    def MatchMD5(self, MD5):
        try:
            last_md5 = open(self._GetMD5FileName(), "r").read()
            return last_md5 == MD5
        except:
            return False
    
    def SetTraceVariablesList(self, idxs):
        """
        Call ctype imported function to append 
        these indexes to registred variables in PLC debugger
        """
        self._suspendDebug()
        # keep a copy of requested idx
        self._Idxs = idxs[:]
        self._ResetDebugVariables()
        for idx in idxs:
            self._RegisterDebugVariable(idx)
        self._resumeDebug()

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
        if self.PLCStatus == "Started":
            self.PLClibraryLock.acquire()
            tick = self._WaitDebugData()
            #PLCprint("Debug tick : %d"%tick)
            if tick == 2**32 - 1:
                tick = -1
                res = None
            else:
                idx = ctypes.c_int()
                typename = ctypes.c_char_p()
                res = []
        
                for given_idx in self._Idxs:
                    buffer=self._IterDebugData(ctypes.byref(idx), ctypes.byref(typename))
                    c_type,unpack_func = self.TypeTranslator.get(typename.value, (None,None))
                    if c_type is not None and given_idx == idx.value:
                        res.append(unpack_func(ctypes.cast(buffer,
                                                           ctypes.POINTER(c_type)).contents))
                    else:
                        PLCprint("Debug error idx : %d, expected_idx %d, type : %s"%(idx.value, given_idx,typename.value))
                        res.append(None)
            self._FreeDebugData()
            self.PLClibraryLock.release()
            return tick, res
        return -1, None

