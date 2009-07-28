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

import Pyro.core as pyro
from threading import Timer, Thread, Lock
import ctypes, os, commands, types, sys

if os.name in ("nt", "ce"):
    from _ctypes import LoadLibrary as dlopen
    from _ctypes import FreeLibrary as dlclose
elif os.name == "posix":
    from _ctypes import dlopen, dlclose

import traceback

lib_ext ={
     "linux2":".so",
     "win32":".dll",
     }.get(sys.platform, "")

def PLCprint(message):
    sys.stdout.write("PLCobject : "+message+"\n")
    sys.stdout.flush()

class PLCObject(pyro.ObjBase):
    _Idxs = []
    def __init__(self, workingdir, daemon, argv, statuschange, evaluator):
        pyro.ObjBase.__init__(self)
        self.evaluator = evaluator
        self.argv = [workingdir] + argv # force argv[0] to be "path" to exec...
        self.workingdir = workingdir
        self.PLCStatus = "Stopped"
        self.PLClibraryHandle = None
        self.PLClibraryLock = Lock()
        # Creates fake C funcs proxies
        self._FreePLC()
        self.daemon = daemon
        self.statuschange = statuschange
        self.hmi_frame = None
        
        # Get the last transfered PLC if connector must be restart
        try:
            self.CurrentPLCFilename=open(
                             self._GetMD5FileName(),
                             "r").read().strip() + lib_ext
        except Exception, e:
            self.PLCStatus = "Empty"
            self.CurrentPLCFilename=None

    def StatusChange(self):
        if self.statuschange is not None:
            self.statuschange(self.PLCStatus)

    def _GetMD5FileName(self):
        return os.path.join(self.workingdir, "lasttransferedPLC.md5")

    def _GetLibFileName(self):
        return os.path.join(self.workingdir,self.CurrentPLCFilename)


    def _LoadNewPLC(self):
        """
        Load PLC library
        Declare all functions, arguments and return values
        """
        PLCprint("Load PLC")
        try:
            self._PLClibraryHandle = dlopen(self._GetLibFileName())
            self.PLClibraryHandle = ctypes.CDLL(self.CurrentPLCFilename, handle=self._PLClibraryHandle)
    
            self._startPLC = self.PLClibraryHandle.startPLC
            self._startPLC.restype = ctypes.c_int
            self._startPLC.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
            
            def StopPLCLock():
                self.PLClibraryLock.acquire()
                self.PLClibraryHandle.stopPLC()
                self.PLClibraryLock.release()
            
            self._stopPLC = StopPLCLock
            self._stopPLC.restype = None
    
            self._ResetDebugVariables = self.PLClibraryHandle.ResetDebugVariables
            self._ResetDebugVariables.restype = None
    
            self._RegisterDebugVariable = self.PLClibraryHandle.RegisterDebugVariable
            self._RegisterDebugVariable.restype = None
            self._RegisterDebugVariable.argtypes = [ctypes.c_int]
    
            self._IterDebugData = self.PLClibraryHandle.IterDebugData
            self._IterDebugData.restype = ctypes.c_void_p
            self._IterDebugData.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_char_p)]
    
            self._FreeDebugData = self.PLClibraryHandle.FreeDebugData
            self._FreeDebugData.restype = None
            
            self._WaitDebugData = self.PLClibraryHandle.WaitDebugData
            self._WaitDebugData.restype = ctypes.c_int  

            self._suspendDebug = self.PLClibraryHandle.suspendDebug
            self._suspendDebug.restype = None

            self._resumeDebug = self.PLClibraryHandle.resumeDebug
            self._resumeDebug.restype = None

            self._PythonIterator = self.PLClibraryHandle.PythonIterator
            self._PythonIterator.restype = ctypes.c_char_p
            self._PythonIterator.argtypes = [ctypes.c_char_p]
            
            return True
        except:
            PLCprint(traceback.format_exc())
            return False

    def _FreePLC(self):
        """
        Unload PLC library.
        This is also called by __init__ to create dummy C func proxies
        """
        self.PLClibraryLock.acquire()
        # Forget all refs to library
        self._startPLC = lambda:None
        self._stopPLC = lambda:None
        self._ResetDebugVariables = lambda:None
        self._RegisterDebugVariable = lambda x:None
        self._IterDebugData = lambda x,y:None
        self._FreeDebugData = lambda:None
        self._WaitDebugData = lambda:-1
        self._suspendDebug = lambda:None
        self._resumeDebug = lambda:None
        self._PythonIterator = lambda:""
        self.PLClibraryHandle = None
        # Unload library explicitely
        if getattr(self,"_PLClibraryHandle",None) is not None:
            PLCprint("Unload PLC")
            dlclose(self._PLClibraryHandle)
            res = self._DetectDirtyLibs()
        else:
            res = False

        self._PLClibraryHandle = None
        self.PLClibraryLock.release()
        return res

    def _DetectDirtyLibs(self):
        # Detect dirty libs
        # Get lib dependencies (for dirty lib detection)
        if os.name == "posix":
            # parasiting libs listed with ldd
            badlibs = [ toks.split()[0] for toks in commands.getoutput(
                            "ldd "+self._GetLibFileName()).splitlines() ]
            for badlib in badlibs:
                if badlib[:6] in ["libwx_",
                                  "libwxs",
                                  "libgtk",
                                  "libgdk",
                                  "libatk",
                                  "libpan",
                                  "libX11",
                                  ]:
                    #badhandle = dlopen(badlib, dl.RTLD_NOLOAD)
                    PLCprint("Dirty lib detected :" + badlib)
                    #dlclose(badhandle)
                    return True
        return False

    def PrepareRuntimePy(self):
        self.python_threads_vars = globals().copy()
        self.python_threads_vars["WorkingDir"] = self.workingdir
        pyfile = os.path.join(self.workingdir, "runtime.py")
        hmifile = os.path.join(self.workingdir, "hmi.py")
        if os.path.exists(hmifile):
            try:
                execfile(hmifile, self.python_threads_vars)
                if os.path.exists(pyfile):
                    try:
                        # TODO handle exceptions in runtime.py
                        # pyfile may redefine _runtime_cleanup
                        # or even call _PythonThreadProc itself.
                        execfile(pyfile, self.python_threads_vars)
                    except:
                        PLCprint(traceback.format_exc())
                if self.python_threads_vars.has_key('wx'):
                    wx = self.python_threads_vars['wx']
                    # try to instanciate the first frame found.
                    for name, obj in self.python_threads_vars.iteritems():
                        # obj is a class
                        if type(obj)==type(type) and issubclass(obj,wx.Frame):
                            def create_frame():
                                self.hmi_frame = obj(None)
                                self.python_threads_vars[name] = self.hmi_frame
                                # keep track of class... never know
                                self.python_threads_vars['Class_'+name] = obj
                                self.hmi_frame.Bind(wx.EVT_CLOSE, OnCloseFrame)
                                self.hmi_frame.Show()
                            
                            def OnCloseFrame(evt):
                                wx.MessageBox(_("Please stop PLC to close"))
                            create_frame()
                            break
            except:
                PLCprint(traceback.format_exc())
        elif os.path.exists(pyfile):
            try:
                # TODO handle exceptions in runtime.py
                # pyfile may redefine _runtime_cleanup
                # or even call _PythonThreadProc itself.
                execfile(pyfile, self.python_threads_vars)
            except:
                PLCprint(traceback.format_exc())
        runtime_begin = self.python_threads_vars.get("_runtime_begin",None)
        if runtime_begin is not None:
            runtime_begin()

    def FinishRuntimePy(self):
        runtime_cleanup = None
        if self.python_threads_vars is not None:
            runtime_cleanup = self.python_threads_vars.get("_runtime_cleanup",None)
        if runtime_cleanup is not None:
            runtime_cleanup()
        if self.hmi_frame is not None:
            self.hmi_frame.Destroy()
        self.python_threads_vars = None

    def PythonThreadProc(self, debug):
        PLCprint("PythonThreadProc started")
        c_argv = ctypes.c_char_p * len(self.argv)
        error = None
        if self._LoadNewPLC():
            if self._startPLC(len(self.argv),c_argv(*self.argv)) == 0:
                if debug:
                    for idx in self._Idxs:
                        self._RegisterDebugVariable(idx)
                    self._resumeDebug()
                self.PLCStatus = "Started"
                self.StatusChange()
                self.evaluator(self.PrepareRuntimePy)
                res,cmd = "None","None"
                while True:
                    #print "_PythonIterator(", res, ")",
                    cmd = self._PythonIterator(res)
                    #print " -> ", cmd
                    if cmd is None:
                        break
                    try :
                        res = str(self.evaluator(eval,cmd,self.python_threads_vars))
                    except Exception,e:
                        res = "#EXCEPTION : "+str(e)
                        PLCprint(res)
                self.PLCStatus = "Stopped"
                self.StatusChange()
                self.evaluator(self.FinishRuntimePy)
            else:
                error = "starting"
        else:
            error = "loading"
        if error is not None:
            PLCprint("Problem %s PLC"%error)
            self.PLCStatus = "Broken"
        self._FreePLC()
        PLCprint("PythonThreadProc interrupted")
    
    def StartPLC(self, debug=False):
        PLCprint("StartPLC")
        if self.CurrentPLCFilename is not None:
            self.PythonThread = Thread(target=self.PythonThreadProc, args=[debug])
            self.PythonThread.start()
            
    def StopPLC(self):
        PLCprint("StopPLC")
        if self.PLCStatus == "Started":
            self._stopPLC()
            return True
        return False

    def _Reload(self):
        self.daemon.shutdown(True)
        self.daemon.sock.close()
        os.execv(sys.executable,[sys.executable]+sys.argv[:])
        # never reached
        return 0

    def ForceReload(self):
        # respawn python interpreter
        Timer(0.1,self._Reload).start()
        return True

    def GetPLCstatus(self):
        return self.PLCStatus
    
    def NewPLC(self, md5sum, data, extrafiles):
        PLCprint("NewPLC (%s)"%md5sum)
        if self.PLCStatus in ["Stopped", "Empty", "Dirty", "Broken"]:
            NewFileName = md5sum + lib_ext
            extra_files_log = os.path.join(self.workingdir,"extra_files.txt")
            try:
                os.remove(os.path.join(self.workingdir,
                                       self.CurrentPLCFilename))
                for filename in file(extra_files_log, "r").readlines() + extra_files_log:
                    try:
                        os.remove(os.path.join(self.workingdir, filename))
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
            if tick == -1:
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

