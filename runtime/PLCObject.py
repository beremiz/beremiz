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
from threading import Timer, Thread, Lock, Semaphore
import ctypes, os, commands, types, sys
from targets.typemapping import SameEndianessTypeTranslator as TypeTranslator

if os.name in ("nt", "ce"):
    from _ctypes import LoadLibrary as dlopen
    from _ctypes import FreeLibrary as dlclose
elif os.name == "posix":
    from _ctypes import dlopen, dlclose

import traceback
def get_last_traceback(tb):
    while tb.tb_next:
        tb = tb.tb_next
    return tb

lib_ext ={
     "linux2":".so",
     "win32":".dll",
     }.get(sys.platform, "")

def PLCprint(message):
    sys.stdout.write("PLCobject : "+message+"\n")
    sys.stdout.flush()

class PLCObject(pyro.ObjBase):
    _Idxs = []
    def __init__(self, workingdir, daemon, argv, statuschange, evaluator, website):
        pyro.ObjBase.__init__(self)
        self.evaluator = evaluator
        self.argv = [workingdir] + argv # force argv[0] to be "path" to exec...
        self.workingdir = workingdir
        self.PLCStatus = "Stopped"
        self.PLClibraryHandle = None
        self.PLClibraryLock = Lock()
        self.DummyIteratorLock = None
        # Creates fake C funcs proxies
        self._FreePLC()
        self.daemon = daemon
        self.statuschange = statuschange
        self.hmi_frame = None
        self.website = website
        
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
        try:
            self._PLClibraryHandle = dlopen(self._GetLibFileName())
            self.PLClibraryHandle = ctypes.CDLL(self.CurrentPLCFilename, handle=self._PLClibraryHandle)
    
            self._startPLC = self.PLClibraryHandle.startPLC
            self._startPLC.restype = ctypes.c_int
            self._startPLC.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
            
            self._stopPLC_real = self.PLClibraryHandle.stopPLC
            self._stopPLC_real.restype = None
            
            self._PythonIterator = getattr(self.PLClibraryHandle, "PythonIterator", None)
            if self._PythonIterator is not None:
                self._PythonIterator.restype = ctypes.c_char_p
                self._PythonIterator.argtypes = [ctypes.c_char_p]
                
                self._stopPLC = self._stopPLC_real
            else:
                # If python confnode is not enabled, we reuse _PythonIterator
                # as a call that block pythonthread until StopPLC 
                self.PythonIteratorLock = Lock()
                self.PythonIteratorLock.acquire()
                def PythonIterator(res):
                    self.PythonIteratorLock.acquire()
                    self.PythonIteratorLock.release()
                    return None
                self._PythonIterator = PythonIterator
                
                def __StopPLC():
                    self._stopPLC_real()
                    self.PythonIteratorLock.release()
                self._stopPLC = __StopPLC
            
    
            self._ResetDebugVariables = self.PLClibraryHandle.ResetDebugVariables
            self._ResetDebugVariables.restype = None
    
            self._RegisterDebugVariable = self.PLClibraryHandle.RegisterDebugVariable
            self._RegisterDebugVariable.restype = None
            self._RegisterDebugVariable.argtypes = [ctypes.c_int, ctypes.c_void_p]
    
            self._FreeDebugData = self.PLClibraryHandle.FreeDebugData
            self._FreeDebugData.restype = None
            
            self._GetDebugData = self.PLClibraryHandle.GetDebugData
            self._GetDebugData.restype = ctypes.c_int  
            self._GetDebugData.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]

            self._suspendDebug = self.PLClibraryHandle.suspendDebug
            self._suspendDebug.restype = ctypes.c_int
            self._suspendDebug.argtypes = [ctypes.c_int]

            self._resumeDebug = self.PLClibraryHandle.resumeDebug
            self._resumeDebug.restype = None
            
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
        self._RegisterDebugVariable = lambda x, y:None
        self._IterDebugData = lambda x,y:None
        self._FreeDebugData = lambda:None
        self._GetDebugData = lambda:-1
        self._suspendDebug = lambda x:-1
        self._resumeDebug = lambda:None
        self._PythonIterator = lambda:""
        self.PLClibraryHandle = None
        # Unload library explicitely
        if getattr(self,"_PLClibraryHandle",None) is not None:
            dlclose(self._PLClibraryHandle)
            self._PLClibraryHandle = None
        
        self.PLClibraryLock.release()
        return False

    def PrepareRuntimePy(self):
        self.python_threads_vars = globals().copy()
        self.python_threads_vars["WorkingDir"] = self.workingdir
        self.python_threads_vars["website"] = self.website
        self.python_threads_vars["_runtime_begin"] = []
        self.python_threads_vars["_runtime_cleanup"] = []
        self.python_threads_vars["PLCObject"] = self
        self.python_threads_vars["PLCBinary"] = self.PLClibraryHandle
        
        for filename in os.listdir(self.workingdir):
            name, ext = os.path.splitext(filename)
            if name.upper().startswith("RUNTIME") and ext.upper() == ".PY":
                try:
                    # TODO handle exceptions in runtime.py
                    # pyfile may redefine _runtime_cleanup
                    # or even call _PythonThreadProc itself.
                    execfile(os.path.join(self.workingdir, filename), self.python_threads_vars)
                except:
                    PLCprint(traceback.format_exc())
                runtime_begin = self.python_threads_vars.get("_%s_begin" % name, None)
                if runtime_begin is not None:
                    self.python_threads_vars["_runtime_begin"].append(runtime_begin)
                runtime_cleanup = self.python_threads_vars.get("_%s_cleanup" % name, None)
                if runtime_cleanup is not None:
                    self.python_threads_vars["_runtime_cleanup"].append(runtime_cleanup)
        
        for runtime_begin in self.python_threads_vars.get("_runtime_begin", []):
            runtime_begin()
            
        if self.website is not None:
            self.website.PLCStarted()

    def FinishRuntimePy(self):
        for runtime_cleanup in self.python_threads_vars.get("_runtime_cleanup", []):
            runtime_cleanup()    
        if self.website is not None:
            self.website.PLCStopped()
        self.python_threads_vars = None

    def PythonThreadProc(self):
        c_argv = ctypes.c_char_p * len(self.argv)
        error = None
        if self._LoadNewPLC():
            if self._startPLC(len(self.argv),c_argv(*self.argv)) == 0:
                self.PLCStatus = "Started"
                self.StatusChange()
                self.StartSem.release()
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
            self.StatusChange()
            self.StartSem.release()
        self._FreePLC()
    
    def StartPLC(self):
        PLCprint("StartPLC")
        if self.CurrentPLCFilename is not None and self.PLCStatus == "Stopped":
            self.StartSem=Semaphore(0)
            self.PythonThread = Thread(target=self.PythonThreadProc)
            self.PythonThread.start()
            self.StartSem.acquire()
            
    def StopPLC(self):
        PLCprint("StopPLC")
        if self.PLCStatus == "Started":
            self.PLCStatus = "Stopped"
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
        if idxs:
            # suspend but dont disable
            if self._suspendDebug(False) == 0:
                # keep a copy of requested idx
                self._Idxs = idxs[:]
                self._ResetDebugVariables()
                for idx,iectype,force in idxs:
                    if force !=None:
                        c_type,unpack_func, pack_func = \
                            TypeTranslator.get(iectype,
                                                    (None,None,None))
                        force = ctypes.byref(pack_func(c_type,force)) 
                    self._RegisterDebugVariable(idx, force)
                self._resumeDebug()
        else:
            self._suspendDebug(True)
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
               self._GetDebugData(ctypes.byref(tick),
                                  ctypes.byref(size),
                                  ctypes.byref(buffer)) == 0 :
                if size.value:
                    for idx, iectype, forced in self._Idxs:
                        cursor = ctypes.c_void_p(buffer.value + offset)
                        c_type,unpack_func, pack_func = \
                            TypeTranslator.get(iectype,
                                                    (None,None,None))
                        if c_type is not None and offset < size.value:
                            res.append(unpack_func(
                                        ctypes.cast(cursor,
                                         ctypes.POINTER(c_type)).contents))
                            offset += ctypes.sizeof(c_type)
                        else:
                            if c_type is None:
                                PLCprint("Debug error - " + iectype +
                                         " not supported !")
                            #if offset >= size.value:
                                #PLCprint("Debug error - buffer too small ! %d != %d"%(offset, size.value))
                            break
                self._FreeDebugData()
                self.PLClibraryLock.release()
            if offset and offset == size.value:
                return self.PLCStatus, tick.value, res
            #elif size.value:
                #PLCprint("Debug error - wrong buffer unpack ! %d != %d"%(offset, size.value))
        return self.PLCStatus, None, []

    def RemoteExec(self, script, **kwargs):
        try:
            exec script in kwargs
        except:
            e_type, e_value, e_traceback = sys.exc_info()
            line_no = traceback.tb_lineno(get_last_traceback(e_traceback))
            return (-1, "RemoteExec script failed!\n\nLine %d: %s\n\t%s" % 
                        (line_no, e_value, script.splitlines()[line_no - 1]))
        return (0, kwargs.get("returnVal", None))
    
        
