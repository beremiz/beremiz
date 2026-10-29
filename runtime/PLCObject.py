#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING.Runtime file for copyrights details.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


from threading import Thread, Lock, Event, Condition
import ctypes
import os
import sys
import traceback
import shutil
import platform as platform_module
from time import time, sleep
import hashlib
from tempfile import mkstemp
from functools import wraps
import _ctypes

from runtime.typemapping import IEC_types_enum
from runtime.loglevels import LogLevelsDefault, LogLevelsCount
from runtime.Stunnel import getPSKID
from runtime import PlcStatus
from runtime import MainWorker
from runtime import default_evaluator

# Callback type matching __recurse_cb_t signature for ScanInstances
SCAN_CB_FUNC = ctypes.CFUNCTYPE(
    ctypes.c_int,           # return value (controls traversal)
    ctypes.c_int,           # type (__IEC_types_enum)
    ctypes.c_void_p,        # ptr
    ctypes.c_uint,          # cumulated
    ctypes.c_uint,          # local
    ctypes.c_uint,          # count
    ctypes.c_char_p,        # name
    ctypes.c_void_p)        # userdata

if os.name in ("nt", "ce"):
    dlopen = _ctypes.LoadLibrary
    dlclose = _ctypes.FreeLibrary
elif os.name == "posix":
    dlopen = _ctypes.dlopen
    dlclose = _ctypes.dlclose


def get_last_traceback(tb):
    while tb.tb_next:
        tb = tb.tb_next
    return tb


lib_ext = {
    "linux": ".so",
    "win32":  ".dll",
}.get(sys.platform, "")


def PLCprint(message):
    if sys.stdout:
        sys.stdout.write("PLCobject : "+message+"\n")
        sys.stdout.flush()


def RunInMain(func):
    @wraps(func)
    def func_wrapper(*args, **kwargs):
        return MainWorker.call(func, *args, **kwargs)
    return func_wrapper


class _DeprecatedPLCBinary(object):
    """
    Backward-compat shim for the former single ``PLCBinary`` handle.

    IOs and logic now live in two shared libraries exposed as ``PLCIOsBinary``
    and ``PLCLogicBinary``.  Legacy runtime extension code that still references
    ``PLCBinary`` gets this proxy: it resolves each requested symbol against the
    IOs library first, then the logic library, and logs a one-shot deprecation
    notice.  Note: ctypes ``in_dll`` reads ``_handle`` and therefore only ever
    reaches the IOs binary (its historical target) — new logic-side globals
    should use ``PLCLogicBinary`` explicitly.
    """
    def __init__(self, parent):
        object.__setattr__(self, "_parent", parent)
        object.__setattr__(self, "_warned", set())

    def __getattr__(self, name):
        parent = object.__getattribute__(self, "_parent")
        warned = object.__getattribute__(self, "_warned")
        for libname, lib in (("PLCIOsBinary", parent.PLClibraryHandle),
                             ("PLCLogicBinary", parent.PLCLogicLibrary)):
            if lib is None:
                continue
            try:
                attr = getattr(lib, name)
            except AttributeError:
                continue
            if name not in warned:
                warned.add(name)
                parent.LogMessage(1,
                    "Deprecation: PLCBinary.%s resolved from %s — use "
                    "PLCIOsBinary or PLCLogicBinary explicitly." % (name, libname))
            return attr
        raise AttributeError(
            "'%s' not found in PLCIOsBinary nor PLCLogicBinary" % name)


class PLCObject(object):
    def __init__(self, WorkingDir, argv, statuschange, evaluator, pyruntimevars,
                 servicename=None):
        self.workingdir = WorkingDir  # must exits already
        self.servicename = servicename
        self.tmpdir = os.path.join(WorkingDir, 'tmp')
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        os.mkdir(self.tmpdir)
        self.argv = []
        self.statuschange = statuschange
        self.evaluator = evaluator
        self.pyruntimevars = pyruntimevars
        self.PLCStatus = PlcStatus.Empty
        self.PLClibraryHandle = None
        self.PLCLogicLibrary = None
        self.PLClibraryLock = Lock()
        self.CurrentLogicFilename = None
        # Creates fake C funcs proxies
        self._InitPLCStubCalls()
        self._loading_error = None
        self.python_runtime_vars = None
        self.TraceThread = None
        self.TraceLock = Lock()
        self.Traces = []
        self.DebugToken = 0

        # Event to signal when PLC is stopped.
        self.PlcStopped = Event()
        self.PlcStopped.set()

        self._init_blobs()
        
        # initialize extended calls with GetVersions call, ignoring arguments
        self.extended_calls = {"GetVersions":lambda *_args:self.GetVersions().encode()}

    # First task of worker -> no @RunInMain
    def AutoLoad(self, autostart):
        # Get the last transfered PLC (both IOs and logic binaries)
        try:
            self.CurrentPLCFilename = open(
                self._GetMD5FileName(),
                "r").read().strip() + lib_ext
            self.CurrentLogicFilename = open(
                self._GetLogicMD5FileName(),
                "r").read().strip() + lib_ext
            self.PLCStatus = PlcStatus.Stopped
            if autostart:
                if self.LoadPLC():
                    self.StartPLC()
                else:
                    self._fail(_("Problem autostarting PLC : can't load PLC"))
                return
        except Exception:
            self.PLCStatus = PlcStatus.Empty
            self.CurrentPLCFilename = None
            self.CurrentLogicFilename = None

        self.StatusChange()

    def StatusChange(self):
        if self.statuschange is not None:
            for callee in self.statuschange:
                callee(self.PLCStatus)

    def LogMessage(self, *args):
        if len(args) == 2:
            level, msg = args
        else:
            level = LogLevelsDefault
            msg, = args
        PLCprint(msg)
        if self._LogMessage is not None:
            bmsg = msg.encode()
            return self._LogMessage(level, bmsg, len(bmsg))
        return None

    @RunInMain
    def ResetLogCount(self):
        if self._ResetLogCount is not None:
            self._ResetLogCount()

    # used internaly
    def GetLogCount(self, level):
        if self._GetLogCount is not None:
            return int(self._GetLogCount(level))
        elif self._loading_error is not None and level == 0:
            return 1
        return 0

    @RunInMain
    def GetLogMessage(self, level, msgid):
        tick = ctypes.c_uint32()
        tv_sec = ctypes.c_uint32()
        tv_nsec = ctypes.c_uint32()
        if self._GetLogMessage is not None:
            maxsz = len(self._log_read_buffer)-1
            sz = self._GetLogMessage(level, msgid,
                                     self._log_read_buffer, maxsz,
                                     ctypes.byref(tick),
                                     ctypes.byref(tv_sec),
                                     ctypes.byref(tv_nsec))
            return ("<empty>" if sz==0 else "<overflow>" if sz > maxsz else self._log_read_buffer[:sz].decode(),
                    tick.value, tv_sec.value, tv_nsec.value)
        elif self._loading_error is not None and level == 0:
            return self._loading_error, 0, 0, 0
        return "", 0, 0, 0

    def _GetMD5FileName(self):
        return os.path.join(self.workingdir, "lasttransferedPLC.md5")

    def _GetLogicMD5FileName(self):
        return os.path.join(self.workingdir, "lasttransferedPLC_logic.md5")

    def _GetLibFileName(self):
        return os.path.join(self.workingdir, self.CurrentPLCFilename)

    def _GetLogicLibFileName(self):
        return os.path.join(self.workingdir, self.CurrentLogicFilename)

    def _LoadPLC(self):
        """
        Load IOs and PLC logic shared libraries.
        Declare all functions, arguments and return values.

        IOs .so  (PLClibraryHandle)   : startPLC, stopPLC, PythonIterator,
                                        suspendDebug, resumeDebug, logging,
                                        loadPLCLogic, preparePLCLogicSwap.
        Logic .so (PLCLogicLibrary)   : RegisterDebugVariable, GetDebugData,
                                        FreeDebugData, ResetDebugVariables,
                                        ScanInstances, __init_PLCLogic,
                                        __cleanup_PLCLogic.
        """
        ios_md5 = open(self._GetMD5FileName(), "r").read()
        logic_md5 = open(self._GetLogicMD5FileName(), "r").read()

        self.PLClibraryLock.acquire()
        try:
            # --- Load IOs .so with RTLD_GLOBAL so its symbols (located vars,
            #     debug mutexes, logging, global var accessors) are visible when
            #     logic .so resolves externs at load time.
            if os.name == "posix":
                self._PLClibraryHandle = dlopen(
                    self._GetLibFileName(), ctypes.RTLD_GLOBAL)
            else:
                self._PLClibraryHandle = dlopen(self._GetLibFileName())

            self.PLClibraryHandle = ctypes.CDLL(
                self.CurrentPLCFilename, handle=self._PLClibraryHandle)

            self.PLC_ID = ctypes.c_char_p.in_dll(self.PLClibraryHandle, "PLC_ID")
            if len(ios_md5) == 32:
                self.PLC_ID.value = ios_md5.encode()

            # let PLC code identify this runtime instance, extensions such as
            # MQTT need it to tell apart PLCs running the same binary
            self.PLC_SERVICE_NAME = ctypes.c_char_p.in_dll(
                self.PLClibraryHandle, "PLC_SERVICE_NAME")
            if self.servicename is not None:
                self.PLC_SERVICE_NAME.value = self.servicename.encode()

            # --- Load logic .so (resolves externs from RTLD_GLOBAL IOs namespace)
            if os.name == "posix":
                self._PLCLogicLibraryHandle = dlopen(self._GetLogicLibFileName())
                PLCLogicLibrary = ctypes.CDLL(
                    self.CurrentLogicFilename, handle=self._PLCLogicLibraryHandle)
                self.PLCLogicLibrary = PLCLogicLibrary

                PLC_ID_LOGIC = ctypes.c_char_p.in_dll(PLCLogicLibrary, "PLC_ID_LOGIC")
                if len(logic_md5) == 32:
                    PLC_ID_LOGIC.value = logic_md5.encode()

                # Connect logic to IOs: set plc_logic_run_fn / plc_logic_scan_fn
                # and update common_ticktime__ / greatest_tick_count__.
                _loadPLCLogic = self.PLClibraryHandle.loadPLCLogic
                _loadPLCLogic.restype = ctypes.c_int
                _loadPLCLogic.argtypes = [ctypes.c_void_p]
                if _loadPLCLogic(self._PLCLogicLibraryHandle) != 0:
                    raise Exception("loadPLCLogic failed: symbols missing in logic .so")

                # Bind logic init/cleanup. init runs once here (load-time); after a
                # stop it is re-run (with cleanup first) on the next StartPLC.
                # cleanup is deferred off the stop path to the next start or _FreePLC.
                # Use subscript to avoid Python name mangling of __ prefix
                self._initPLCLogicState_fn = PLCLogicLibrary["__init_PLCLogicState"]
                self._initPLCLogicState_fn.restype = None
                self._initPLCLogicState_fn.argtypes = []

                self._initPLCLogic_fn = PLCLogicLibrary["__init_PLCLogic"]
                self._initPLCLogic_fn.restype = ctypes.c_int
                self._initPLCLogic_fn.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]

                self._cleanupPLCLogic_fn = PLCLogicLibrary["__cleanup_PLCLogic"]
                self._cleanupPLCLogic_fn.restype = None

                # Initialize PLC logic instance tree (config_init__) and debug state.
                # Called here (Python main thread) before the PLC thread is spawned.
                self._PLCLogicInitialized = False
                self._PLCLogicRestartPending = False
                self._initPLCLogicState_fn()          # config_init__
                ret = self._initPLCLogic_fn(0, None)  # load-time init, lock already held
                if ret != 0:
                    raise Exception("__init_PLCLogic failed with %d" % ret)
                self._PLCLogicInitialized = True
            else:
                PLCLogicLibrary = self.PLClibraryHandle

            # --- Bind IOs .so interface functions ---
            self._startPLC = self.PLClibraryHandle.startPLC
            self._startPLC.restype = ctypes.c_int
            self._startPLC.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]

            self._stopPLC_real = self.PLClibraryHandle.stopPLC
            self._stopPLC_real.restype = None

            if os.name == "posix":
                self._plcIECTypeSize = self.PLClibraryHandle.plcIECTypeSize
                self._plcIECTypeSize.restype = ctypes.c_size_t
                self._plcIECTypeSize.argtypes = [ctypes.c_int]

                self._getInitState = self.PLClibraryHandle.getPLCLogicInitState
                self._getInitState.restype = ctypes.c_int
                self._getInitState.argtypes = []

                self._cancelInit = self.PLClibraryHandle.cancelPLCLogicInit
                self._cancelInit.restype = ctypes.c_int
                self._cancelInit.argtypes = []

                self._getSwapState = self.PLClibraryHandle.getPLCLogicSwapState
                self._getSwapState.restype = ctypes.c_int
                self._getSwapState.argtypes = []

                self._cancelSwap = self.PLClibraryHandle.cancelPLCLogicSwap
                self._cancelSwap.restype = ctypes.c_int
                self._cancelSwap.argtypes = []

                self._PythonSetPurge = getattr(self.PLClibraryHandle, "PythonSetPurge", None)
                if self._PythonSetPurge is not None:
                    self._PythonSetPurge.restype = None
                    self._PythonSetPurge.argtypes = [ctypes.c_int]

            self._PythonIterator = getattr(self.PLClibraryHandle, "PythonIterator", None)
            if self._PythonIterator is not None:
                self._PythonIterator.restype = ctypes.c_char_p
                self._PythonIterator.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_int)]

                self._stopPLC = self._stopPLC_real
            else:
                # If python confnode is not enabled, we reuse _PythonIterator
                # as a call that blocks pythonthread until StopPLC
                self.PlcStopping = Event()

                def PythonIterator(res, blkid, is_last):
                    self.PlcStopping.clear()
                    self.PlcStopping.wait()
                    return None
                self._PythonIterator = PythonIterator

                def __StopPLC():
                    self._stopPLC_real()
                    self.PlcStopping.set()
                self._stopPLC = __StopPLC

            self._suspendDebug = self.PLClibraryHandle.suspendDebug
            self._suspendDebug.restype = ctypes.c_int
            self._suspendDebug.argtypes = [ctypes.c_int]

            self._resumeDebug = self.PLClibraryHandle.resumeDebug
            self._resumeDebug.restype = None

            self._ResetLogCount = self.PLClibraryHandle.ResetLogCount
            self._ResetLogCount.restype = None

            self._GetLogCount = self.PLClibraryHandle.GetLogCount
            self._GetLogCount.restype = ctypes.c_uint32
            self._GetLogCount.argtypes = [ctypes.c_uint8]

            self._LogMessage = self.PLClibraryHandle.LogMessage
            self._LogMessage.restype = ctypes.c_int
            self._LogMessage.argtypes = [ctypes.c_uint8, ctypes.c_char_p, ctypes.c_uint32]

            self._log_read_buffer = ctypes.create_string_buffer(1 << 14)  # 16K
            self._GetLogMessage = self.PLClibraryHandle.GetLogMessage
            self._GetLogMessage.restype = ctypes.c_uint32
            self._GetLogMessage.argtypes = [ctypes.c_uint8, ctypes.c_uint32, ctypes.c_char_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)]

            # --- Bind logic .so debug/scan functions ---
            self._ResetDebugVariables = PLCLogicLibrary.ResetDebugVariables
            self._ResetDebugVariables.restype = None

            self._RegisterDebugVariable = PLCLogicLibrary.RegisterDebugVariable
            self._RegisterDebugVariable.restype = ctypes.c_int
            self._RegisterDebugVariable.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t]

            self._FreeDebugData = PLCLogicLibrary.FreeDebugData
            self._FreeDebugData.restype = None

            self._GetDebugData = PLCLogicLibrary.GetDebugData
            self._GetDebugData.restype = ctypes.c_int
            self._GetDebugData.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]

            self._ScanInstances = PLCLogicLibrary.ScanInstances
            self._ScanInstances.restype = None
            self._ScanInstances.argtypes = [SCAN_CB_FUNC, ctypes.c_void_p, ctypes.c_int]

            self._loading_error = None

        except Exception:
            self._loading_error = traceback.format_exc()
            PLCprint(self._loading_error)
            return False
        finally:
            self.PLClibraryLock.release()

        return True

    @RunInMain
    def LoadPLC(self):
        res = self._LoadPLC()
        if res:
            try:
                self.PythonRuntimeInit()
            except Exception:
                self._loading_error = traceback.format_exc()
                PLCprint(self._loading_error)
                return False
        else:
            self._FreePLC()

        return res

    @RunInMain
    def UnLoadPLC(self):
        self.PythonRuntimeCleanup()
        self._FreePLC()

    def _InitPLCStubCalls(self):
        """
        create dummy C func proxies
        """
        self._startPLC = lambda x, y: None
        self._stopPLC = lambda: None
        self._ResetDebugVariables = lambda: None
        self._RegisterDebugVariable = lambda x, y, z: 0
        self._IterDebugData = lambda x, y: None
        self._FreeDebugData = lambda: None
        self._GetDebugData = lambda: -1
        self._suspendDebug = lambda x: -1
        self._resumeDebug = lambda: None
        self._PythonIterator = lambda *a: ""
        self._PythonSetPurge = None
        self._ScanInstances = lambda cb, ud, co: None
        self._GetLogCount = None
        self._LogMessage = None
        self._GetLogMessage = None
        self._PLClibraryHandle = None
        self.PLClibraryHandle = None
        self.PLCLogicLibrary = None
        self._PLCLogicLibraryHandle = None
        self._PendingOldLogicHandle = None
        self._initPLCLogic_fn = None
        self._initPLCLogicState_fn = None
        self._plcIECTypeSize = lambda t: 0
        self._getInitState = lambda: 0
        self._cancelInit = lambda: 1
        self._getSwapState = lambda: 0
        self._cancelSwap = lambda: 1
        self._cleanupPLCLogic_fn = None
        self._PLCLogicInitialized = False
        self._PLCLogicRestartPending = False
        self._swap_copy_ops = None  # keep ctypes array alive until next swap/unload
        self._swap_snapshot = None  # idem, for the init phase snapshot

    def _FreePLC(self):
        """
        Unload IOs and logic PLC libraries.
        Order: cleanup logic first (debug references IOs mutexes), then close
        logic .so, then any pending old-logic handle, then IOs .so.
        """
        self.PLClibraryLock.acquire()
        try:
            # Flush any still-live logic tree (deferred cleanup from a stop, or a
            # PLC loaded but never started) while both .so files are still mapped
            if getattr(self, "_PLCLogicInitialized", False):
                cleanup = getattr(self, "_cleanupPLCLogic_fn", None)
                if cleanup is not None:
                    try:
                        cleanup()
                    except Exception:
                        pass
                self._PLCLogicInitialized = False

            if getattr(self, "_PLCLogicLibraryHandle", None) is not None:
                dlclose(self._PLCLogicLibraryHandle)

            # Close deferred old-logic handle from a previous hot-swap
            if getattr(self, "_PendingOldLogicHandle", None) is not None:
                dlclose(self._PendingOldLogicHandle)

            # Unload IOs library last
            if getattr(self, "_PLClibraryHandle", None) is not None:
                dlclose(self._PLClibraryHandle)

            # Forget all refs to libraries
            self._InitPLCStubCalls()

        finally:
            self.PLClibraryLock.release()

        return False

    def _InitPLCLogic(self):
        """Run __init_PLCLogicState + __init_PLCLogic. Caller ensures no live tree."""
        init = getattr(self, "_initPLCLogic_fn", None)
        if init is None:
            return True  # nothing loaded / stub
        self.PLClibraryLock.acquire()
        try:
            self._initPLCLogicState_fn()
            ret = init(0, None)
        finally:
            self.PLClibraryLock.release()
        if ret != 0:
            self.LogMessage(0, _("__init_PLCLogic failed with %d") % ret)
            return False
        self._PLCLogicInitialized = True
        return True

    def _CleanupPLCLogic(self):
        """Run __cleanup_PLCLogic if a logic tree is live. Idempotent."""
        if not self._PLCLogicInitialized:
            return
        cleanup = getattr(self, "_cleanupPLCLogic_fn", None)
        if cleanup is not None:
            self.PLClibraryLock.acquire()
            try:
                cleanup()
            except Exception:
                pass
            finally:
                self.PLClibraryLock.release()
        self._PLCLogicInitialized = False

    def PythonRuntimeCall(self, methodname, use_evaluator=True, reverse_order=False):
        """
        Calls init, start, stop or cleanup method provided by
        runtime python files, loaded when new PLC uploaded
        """
        methods = self.python_runtime_vars.get("_runtime_%s" % methodname, [])
        if reverse_order:
            methods = reversed(methods)
        for method in methods:
            if use_evaluator:
                _res, exp = self.evaluator(method)
            else:
                _res, exp = default_evaluator(method)
            if exp is not None:
                self.LogMessage(0, '\n'.join(traceback.format_exception(*exp)))

    # used internaly
    def PythonRuntimeInit(self):
        MethodNames = ["init", "start", "stop", "swap", "cleanup"]
        self.python_runtime_vars = globals().copy()
        self.python_runtime_vars.update(self.pyruntimevars)
        parent = self

        class PLCSafeGlobals(object):
            def __getattr__(self, name):
                try:
                    t = parent.python_runtime_vars["_"+name+"_ctype"]
                except KeyError:
                    raise KeyError("Try to get unknown shared global variable : %s" % name)
                v = t()
                parent.python_runtime_vars["_PySafeGetPLCGlob_"+name](ctypes.byref(v))
                return parent.python_runtime_vars["_"+name+"_unpack"](v)

            def __setattr__(self, name, value):
                try:
                    t = parent.python_runtime_vars["_"+name+"_ctype"]
                except KeyError:
                    raise KeyError("Try to set unknown shared global variable : %s" % name)
                v = parent.python_runtime_vars["_"+name+"_pack"](t, value)
                parent.python_runtime_vars["_PySafeSetPLCGlob_"+name](ctypes.byref(v))

        class OnChangeStateClass(object):
            def __getattr__(self, name):
                u = parent.python_runtime_vars["_"+name+"_unpack"]
                return type("changedesc",(),dict(
                    count = parent.python_runtime_vars["_PyOnChangeCount_"+name].value,
                    first = u(parent.python_runtime_vars["_PyOnChangeFirst_"+name]),
                    last = u(parent.python_runtime_vars["_PyOnChangeLast_"+name])))


        self.python_runtime_vars.update({
            "PLCGlobals":     PLCSafeGlobals(),
            "OnChange":       OnChangeStateClass(),
            "WorkingDir":     self.workingdir,
            "PLCObject":      self,
            "PLCIOsBinary":   self.PLClibraryHandle,
            "PLCLogicBinary": self.PLCLogicLibrary,
            "PLCBinary":      _DeprecatedPLCBinary(self),
            "PLCGlobalsDesc": [],
            "OnIdle":         []})

        for methodname in MethodNames:
            self.python_runtime_vars["_runtime_%s" % methodname] = []

        try:
            filenames = os.listdir(self.workingdir)
            filenames.sort()
            for filename in filenames:
                name, ext = os.path.splitext(filename)
                if name.upper().startswith("RUNTIME") and ext.upper() == ".PY":
                    exec(compile(open(os.path.join(self.workingdir, filename), "rb").read(), os.path.join(self.workingdir, filename), 'exec'), self.python_runtime_vars)
                    for methodname in MethodNames:
                        method = self.python_runtime_vars.get("_%s_%s" % (name, methodname), None)
                        if method is not None:
                            self.python_runtime_vars["_runtime_%s" % methodname].append(method)
        except Exception:
            self.LogMessage(0, traceback.format_exc())
            raise

        self.PythonRuntimeCall("init", use_evaluator=False)

        self.PythonThreadCondLock = Lock()
        self.PythonThreadCmdCond = Condition(self.PythonThreadCondLock)
        self.PythonThreadAckCond = Condition(self.PythonThreadCondLock)
        self.PythonThreadCmd = None
        self.PythonThreadAck = None
        self.PythonThread = Thread(target=self.PythonThreadProc, name="PLCPythonThread")
        self.PythonThread.start()

    # used internaly
    def PythonRuntimeCleanup(self):
        if self.python_runtime_vars is not None:
            self.PythonThreadCommand("Finish")
            self.PythonThread.join()
            self.PythonRuntimeCall("cleanup", use_evaluator=False, reverse_order=True)

        self.python_runtime_vars = None

    def PythonThreadLoop(self):
        res, cmd, blkid, is_last = "None", "None", ctypes.c_void_p(), ctypes.c_int()
        compile_cache = {}
        while True:
            cmd = self._PythonIterator(res.encode(), blkid, ctypes.byref(is_last))
            FBID = blkid.value
            GOING_IDLE = is_last.value != 0
            if cmd is None:
                break
            cmd = cmd.decode()
            try:
                self.python_runtime_vars["FBID"] = FBID
                ccmd, AST = compile_cache.get(FBID, (None, None))
                if ccmd is None or ccmd != cmd:
                    AST = compile(cmd, '<plc>', 'eval')
                    compile_cache[FBID] = (cmd, AST)
                result, exp = self.evaluator(eval, AST, self.python_runtime_vars)
                if exp is not None:
                    res = "#EXCEPTION : "+str(exp[1])
                    self.LogMessage(1, ('PyEval@0x%x(Code="%s") Exception "%s"') % (
                        FBID, cmd, '\n'.join(traceback.format_exception(*exp))))
                else:
                    res = str(result)
                self.python_runtime_vars["FBID"] = None
            except Exception as e:
                res = "#EXCEPTION : "+str(e)
                self.LogMessage(1, ('PyEval@0x%x(Code="%s") Exception "%s"') % (FBID, cmd, str(e)))

            if GOING_IDLE:
                todo = self.python_runtime_vars["OnIdle"]
                while todo:
                    todo.pop(0)()

    def PythonThreadProc(self):
        while True:
            self.PythonThreadCondLock.acquire()
            cmd = self.PythonThreadCmd
            while cmd is None:
                self.PythonThreadCmdCond.wait()
                cmd = self.PythonThreadCmd
            self.PythonThreadCmd = None
            self.PythonThreadCondLock.release()

            if cmd == "PreStart":
                self.PreStartPLC()
                # Ack once PreStart done, must be finished before StartPLC
                self.PythonThreadAcknowledge(cmd)
            elif cmd == "Start":
                # Ack Immediately, for responsiveness
                self.PythonThreadAcknowledge(cmd)
                self.PythonRuntimeCall("start")
                self.LogMessage("Python extensions started")
                self._PostStartPLC()
                self.PythonThreadLoop()
                self.PythonRuntimeCall("stop", reverse_order=True)
                
                # Signal that python runtime has stopped
                self.PlcStopped.set()

            elif cmd == "Finish":
                self.PythonThreadAcknowledge(cmd)
                break

    def PythonThreadAcknowledge(self, ack):
        self.PythonThreadCondLock.acquire()
        self.PythonThreadAck = ack
        self.PythonThreadAckCond.notify()
        self.PythonThreadCondLock.release()

    def PythonThreadCommand(self, cmd):
        self.PythonThreadCondLock.acquire()
        self.PythonThreadCmd = cmd
        self.PythonThreadCmdCond.notify()
        ack = None
        while ack != cmd:
            self.PythonThreadAckCond.wait()
            ack = self.PythonThreadAck
            self.PythonThreadAck = None

        self.PythonThreadCondLock.release()

    def _fail(self, msg):
        self.LogMessage(0, msg)
        self.PLCStatus = PlcStatus.Broken
        self.StatusChange()

    def PreStartPLC(self):
        """ 
        Here goes actions to be taken just before PLC starts, 
        with all libraries and python object already created.
        For example : restore saved proprietary parameters
        """
        pass

    def _PostStartPLC(self):
        try:
            self.PostStartPLC()
        except Exception:
            self.LogMessage(0, 'Post Start Exception'+'\n'.join(
                traceback.format_exception(*sys.exc_info())))

    def PostStartPLC(self):
        """ 
        Here goes actions to be taken after PLC is started, 
        with all libraries and python object already created,
        and python extensions "Start" methods being called.
        This is called before python thread processing py_eval blocks starts.
        For example : attach additional ressource to web services
        """
        pass

    @RunInMain
    def StartPLC(self):

        # Prevent accidental call to StartPLC when already Started
        if self.PLCStatus != PlcStatus.Stopped:
            self.LogMessage(0,_("Problem starting PLC : PLC is not Stopped"))
            return

        if self.PLClibraryHandle is None:
            if not self.LoadPLC():
                self._fail(_("Problem starting PLC : can't load PLC"))

        if self.CurrentPLCFilename is not None and self.PLCStatus == PlcStatus.Stopped:
            if self._PLCLogicRestartPending:
                # Restart after a stop: run the deferred cleanup, then a fresh init.
                self._CleanupPLCLogic()
                if not self._InitPLCLogic():
                    self._fail(_("Problem starting PLC : logic init failed"))
                    return
                self._PLCLogicRestartPending = False
            self.PythonThreadCommand("PreStart")
            c_argv = ctypes.c_char_p * len(self.argv)
            res = self._startPLC(len(self.argv), c_argv(*self.argv))
            if res == 0:
                self.LogMessage("PLC started")
                self.PLCStatus = PlcStatus.Started
                self.StatusChange()
                self.PythonThreadCommand("Start")
                self.PlcStopped.clear()
            else:
                self._fail(_("Problem starting PLC : error %d" % res))

    @RunInMain
    def StopPLCLoop(self):
        if self.PLCStatus == PlcStatus.Started:
            self.LogMessage("PLC stopped")
            self._stopPLC()
            if self.TraceThread is not None:
                self.TraceThread.join()
                self.TraceThread = None
            return True
        return False

    # Does not @RunInMain since python runtime Stop call must run in 
    # main thread, and StopPLC waits for it to complete
    def StopPLC(self):
        if self.StopPLCLoop():
            # Wait for python runtime stop to complete
            if self.PlcStopped.wait(timeout=5):
                self.PLCStatus = PlcStatus.Stopped
                # Defer __cleanup_PLCLogic to next start / _FreePLC; keep the
                # stopped tree intact so it still holds the last run's values.
                self._PLCLogicRestartPending = True
                self.StatusChange()
            else:
                self._fail(_("PLC timed out while stopping"))
                
        return self.PLCStatus == PlcStatus.Stopped

    def GetPLCstatus(self):
        try:
            return self._GetPLCstatus()
        except EOFError:
            return (PlcStatus.Disconnected, [0]*LogLevelsCount)

    @RunInMain
    def _GetPLCstatus(self):
        return self.PLCStatus, list(map(self.GetLogCount, range(LogLevelsCount)))

    @RunInMain
    def GetPLCID(self):
        try:
            res = getPSKID()
        except Exception as e:
            self.LogMessage(0, str(e))
            return ("","")
        return res

    def _init_blobs(self):
        self.blobs = {}  # dict of list
        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir)
        os.mkdir(self.tmpdir)

    def _append_blob(self, blob, newBlobID):
        self.blobs.setdefault(newBlobID,[]).append(blob)

    def _pop_blob(self, blobID):
        blobs = self.blobs.pop(blobID, None)

        if blobs is None:
            return None

        blob = blobs.pop()
        if blobs:
            # insert same blob list back if not empty
            blobs = self.blobs[blobID] = blobs
        return blob

    @RunInMain
    def SeedBlob(self, seed):
        blob = (mkstemp(dir=self.tmpdir) + (hashlib.new('md5'),))
        _fd, _path, md5sum = blob
        md5sum.update(seed)
        newBlobID = md5sum.digest()
        self._append_blob(blob, newBlobID)
        return newBlobID

    @RunInMain
    def AppendChunkToBlob(self, data, blobID):
        blob = self._pop_blob(blobID)

        fd, _path, md5sum = blob
        md5sum.update(data)
        newBlobID = md5sum.digest()
        os.write(fd, data)
        self._append_blob(blob, newBlobID)
        return newBlobID

    @RunInMain
    def PurgeBlobs(self):
        for blobs in list(self.blobs.values()):
            for fd, _path, _md5sum in blobs:
                os.close(fd)
        self._init_blobs()

    def BlobAsFile(self, blobID, newpath):
        blob = self._pop_blob(blobID)

        if blob is None:
            raise Exception(
                _(f"Missing data to create file: {newpath}"))

        self._BlobAsFile(blob, newpath)

    def _BlobAsFile(self, blob, newpath):
        fd, path, _md5sum = blob
        fobj = os.fdopen(fd)
        fobj.flush()
        os.fsync(fd)
        fobj.close()
        shutil.move(path, newpath)

    def _extra_files_log_path(self):
        return os.path.join(self.workingdir, "extra_files.txt")

    def RepairPLC(self):
        self.PurgePLC()
        MainWorker.finish()

    @RunInMain
    def PurgePLC(self):

        extra_files_log = self._extra_files_log_path()

        old_PLC_filename = os.path.join(self.workingdir, self.CurrentPLCFilename) \
            if self.CurrentPLCFilename is not None \
            else None

        old_logic_filename = os.path.join(self.workingdir, self.CurrentLogicFilename) \
            if self.CurrentLogicFilename is not None \
            else None

        try:
            allfiles = open(extra_files_log, "rt").readlines()
            allfiles.extend([extra_files_log,
                             old_PLC_filename,
                             old_logic_filename,
                             self._GetMD5FileName(),
                             self._GetLogicMD5FileName()])
        except Exception:
            self.LogMessage("No files to purge")
            allfiles = []

        for filename in allfiles:
            if filename:
                filename = filename.strip()
                try:
                    os.remove(os.path.join(self.workingdir, filename))
                except Exception:
                    self.LogMessage("Couldn't purge " + filename)

        self.PLCStatus = PlcStatus.Empty

        # TODO: PLCObject restart

    @RunInMain
    def NewPLC(self, md5sum, plc_object, extrafiles):
        # Close any deferred old-logic handle from a previous hot-swap.
        # Safe now: the PLC thread has already switched to the new logic.
        if self._PendingOldLogicHandle is not None:
            dlclose(self._PendingOldLogicHandle)
            self._PendingOldLogicHandle = None

        # extrafiles[0] is always the logic binary: (logic_md5 + lib_ext, blobID)
        if not extrafiles:
            self.LogMessage(0, "NewPLC: missing logic binary in extrafiles")
            return False

        logic_entry, other_extrafiles = extrafiles[0], extrafiles[1:]
        logic_fname, logic_blob_id = logic_entry
        logic_md5 = os.path.splitext(logic_fname)[0]  # strip extension

        # Hot-swap path: PLC running, IOs unchanged, only logic changed.
        if (self.PLCStatus == PlcStatus.Started
                and self.MatchMD5(md5sum)
                and not self._MatchLogicMD5(logic_md5)):
            return self._HotSwapPLCLogic(logic_md5, logic_blob_id)

        # Full reload path: PLC must be stopped/empty/broken.
        if self.PLCStatus not in [PlcStatus.Stopped, PlcStatus.Empty, PlcStatus.Broken]:
            return False

        NewFileName = md5sum + lib_ext
        NewLogicFileName = logic_fname
        extra_files_log = self._extra_files_log_path()

        new_PLC_filename = os.path.join(self.workingdir, NewFileName)
        new_logic_filename = os.path.join(self.workingdir, NewLogicFileName)

        self.UnLoadPLC()
        self.PurgePLC()

        self.LogMessage("NewPLC (%s / logic %s)" % (md5sum, logic_md5))

        try:
            # Write IOs binary
            self.BlobAsFile(plc_object, new_PLC_filename)

            # Write logic binary
            self.BlobAsFile(logic_blob_id, new_logic_filename)

            # Write other extra files (RUNTIME_*.py, etc.)
            # Logic binary is tracked separately via CurrentLogicFilename / _GetLogicMD5FileName()
            log = open(extra_files_log, "w")
            for fname, blobID in other_extrafiles:
                fpath = os.path.join(self.workingdir, fname)
                self.BlobAsFile(blobID, fpath)
                log.write(fname + '\n')

            # Persist IOs MD5
            with open(self._GetMD5FileName(), "w") as f:
                f.write(md5sum)
                f.flush()
                os.fsync(f.fileno())

            # Persist logic MD5
            with open(self._GetLogicMD5FileName(), "w") as f:
                f.write(logic_md5)
                f.flush()
                os.fsync(f.fileno())

            self.CurrentPLCFilename = NewFileName
            self.CurrentLogicFilename = NewLogicFileName
        except Exception:
            self.PLCStatus = PlcStatus.Broken
            self.StatusChange()
            PLCprint(traceback.format_exc())
            return False

        if self.LoadPLC():
            self.PLCStatus = PlcStatus.Stopped
            self.StatusChange()
        else:
            self._fail(_("Problem installing new PLC : can't load PLC"))

        return self.PLCStatus == PlcStatus.Stopped

    def MatchMD5(self, MD5):
        try:
            last_md5 = open(self._GetMD5FileName(), "r").read()
            return last_md5 == MD5
        except Exception:
            pass
        return False

    def _MatchLogicMD5(self, MD5):
        try:
            last_md5 = open(self._GetLogicMD5FileName(), "r").read()
            return last_md5 == MD5
        except Exception:
            pass
        return False

    def _PLCCyclePeriod(self):
        """Period of the slowest PLC task in seconds, 1ms if unknown."""
        try:
            return (ctypes.c_ulonglong.in_dll(
                        self.PLClibraryHandle, "common_ticktime__").value
                    * max(1, ctypes.c_ulong.in_dll(
                        self.PLClibraryHandle, "greatest_tick_count__").value)
                    / 1e9)
        except ValueError:
            return 0.001

    def _WaitPLCThread(self, get_state, cancel):
        """
        Wait for the PLC thread to carry out a prepared hot-swap phase.

        A barrier rather than mere reporting: each phase is what makes the next
        one's inputs valid.  If the PLC thread has not picked the phase up in
        time, withdraw it so the outcome is unambiguous.
        """
        period = self._PLCCyclePeriod()
        deadline = time() + min(5.0, max(1.0, 3 * period))
        while get_state() == 1:
            if time() > deadline:
                # lost the race only if the PLC thread got to it meanwhile
                return cancel() == 0
            sleep(0.01)
        return True

    def _HotSwapPLCLogic(self, new_logic_md5, logic_blob_id):
        """
        Hot-swap the PLC logic .so without stopping the PLC thread.

        1. Write new logic .so to disk and load it.
        2. Snapshot the running instance tree, then hand off to the PLC thread
           via preparePLCLogicInit: it saves, runs __init_PLCLogicState
           (config_init__) and restores in one pass, so the config level globals
           the running logic shares with the new .so are never observable at
           their initial values.
        3. Reconcile old and new instance trees (streaming two-pointer merge)
           and build the copy ops.  Only possible now: external references are
           pointers that config_init__ is what fills in.
        4. Hand off to PLC thread via preparePLCLogicSwap.
        5. Once committed, run __init_PLCLogicSwapped here: the retain list is
           built from flags config_init__ sets, so it cannot be built earlier.
        6. Rebind debug/scan symbols from new logic library.
        7. Store old handle for deferred dlclose on next NewPLC call.
        """
        from runtime.plc_hotswap import (scan_lib_instances,
                                         reconcile_instance_trees,
                                         build_copy_ops_array,
                                         build_snapshot_ops)

        new_logic_fname = new_logic_md5 + lib_ext
        new_logic_path = os.path.join(self.workingdir, new_logic_fname)

        try:
            # Write new logic binary to disk
            self.BlobAsFile(logic_blob_id, new_logic_path)

            # Load new logic .so
            new_handle = dlopen(new_logic_path)
            new_lib = ctypes.CDLL(new_logic_path, handle=new_handle)

            # Library and debug init for the swapped-in logic.  Deferred until
            # the PLC thread committed the swap: __init_PLCLogicState runs there,
            # and the retain list it enables can only be built afterwards.
            # Use subscript to avoid Python name mangling of __ prefix
            _init_swapped_fn = new_lib["__init_PLCLogicSwapped"]
            _init_swapped_fn.restype = ctypes.c_int
            _init_swapped_fn.argtypes = []

            _init_fn = new_lib["__init_PLCLogic"]
            _init_fn.restype = ctypes.c_int
            _init_fn.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]

            _init_state_fn = new_lib["__init_PLCLogicState"]
            _init_state_fn.restype = None
            _init_state_fn.argtypes = []

            # Type new scan function for use in scan_lib_instances generator
            new_scan_fn = new_lib.ScanInstances
            new_scan_fn.restype = None
            new_scan_fn.argtypes = [SCAN_CB_FUNC, ctypes.c_void_p, ctypes.c_int]

            self._suspendDebug(True)
            self.DebugToken = 0
            
            if self._PythonSetPurge is not None:
                self._PythonSetPurge(1)

            def _abort(msg):
                if self._PythonSetPurge is not None:
                    self._PythonSetPurge(0)
                dlclose(new_handle)
                self.LogMessage(0, "Hot-swap: " + msg)
                return False

            def _addr(arr, count):
                return ctypes.cast(arr, ctypes.c_void_p).value if count else None

            # --- Phase 1: initialize the new instance tree, on the PLC thread,
            # bracketed by a snapshot of the running one.
            # Configuration globals only: those are the ones shared with the
            # IOs .so, so the reset is what they have to be carried across.
            snapshot = build_snapshot_ops(self.PLCScan(config_only=True),
                                          self._plcIECTypeSize)
            self._swap_snapshot = snapshot

            _prepareInit = self.PLClibraryHandle.preparePLCLogicInit
            _prepareInit.restype = ctypes.c_int
            _prepareInit.argtypes = [
                ctypes.c_void_p,  # handle (dlopen result)
                ctypes.c_void_p,  # copy_op_t *save_ops
                ctypes.c_size_t,  # save count
                ctypes.c_void_p,  # copy_op_t *restore_ops
                ctypes.c_size_t,  # restore count
            ]
            if _prepareInit(new_handle,
                            _addr(snapshot.save, snapshot.count), snapshot.count,
                            _addr(snapshot.restore, snapshot.count), snapshot.count) != 0:
                return _abort("new logic .so is missing __init_PLCLogicState")

            if not self._WaitPLCThread(self._getInitState, self._cancelInit):
                return _abort("PLC thread did not initialize the new logic")

            # --- Phase 2: build copy-ops by streaming old and new instance trees
            # in parallel.  old_gen uses current self._ScanInstances (old logic,
            # still live); new_gen uses the new logic's ScanInstances, valid now
            # that its tree is initialized.
            c_ops, ops_count = build_copy_ops_array(
                reconcile_instance_trees(
                    self.PLCScan(),
                    scan_lib_instances(new_scan_fn)))

            # Hand off to PLC thread.  The C side resolves plc_logic_cycle /
            # ScanInstances / GetRetainSize from new_handle itself — no
            # pre-resolved pointers needed here.  The PLC thread will execute
            # copy ops and switch fn pointers on its next cycle boundary.
            _prepareSwap = self.PLClibraryHandle.preparePLCLogicSwap
            _prepareSwap.restype = ctypes.c_int
            _prepareSwap.argtypes = [
                ctypes.c_void_p,  # handle (dlopen result)
                ctypes.c_void_p,  # copy_op_t *ops
                ctypes.c_size_t,  # count
            ]
            if _prepareSwap(new_handle, _addr(c_ops, ops_count), ops_count) != 0:
                return _abort("new logic .so is missing symbols")

            if not self._WaitPLCThread(self._getSwapState, self._cancelSwap):
                return _abort("PLC thread did not commit the swap")

            # New logic is live now: finish its initialization.  A failure here
            # means retain setup failed, which is not something the swap can be
            # rolled back from, so report it and carry on.
            ret = _init_swapped_fn()
            if ret != 0:
                self.LogMessage(0, "Hot-swap: __init_PLCLogicSwapped failed (%d)" % ret)

            # Keep ctypes array alive until next swap/unload (PLC thread still references it)
            self._swap_copy_ops = c_ops

            # Rebind debug/scan symbols to new logic library.
            # The trace thread may call old GetDebugData one more time (acceptable —
            # old .so stays mapped until _PendingOldLogicHandle is closed); new
            # registrations will use the rebound functions below.
            self.PLClibraryLock.acquire()
            try:
                self._ResetDebugVariables = new_lib.ResetDebugVariables
                self._ResetDebugVariables.restype = None

                self._RegisterDebugVariable = new_lib.RegisterDebugVariable
                self._RegisterDebugVariable.restype = ctypes.c_int
                self._RegisterDebugVariable.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t]

                self._FreeDebugData = new_lib.FreeDebugData
                self._FreeDebugData.restype = None

                self._GetDebugData = new_lib.GetDebugData
                self._GetDebugData.restype = ctypes.c_int
                self._GetDebugData.argtypes = [ctypes.POINTER(ctypes.c_uint32),
                                               ctypes.POINTER(ctypes.c_uint32),
                                               ctypes.POINTER(ctypes.c_void_p)]

                self._ScanInstances = new_scan_fn

                self._initPLCLogicState_fn = _init_state_fn
                self._initPLCLogic_fn = _init_fn
                self._cleanupPLCLogic_fn = new_lib["__cleanup_PLCLogic"]
                self._cleanupPLCLogic_fn.restype = None
                # New lib is live; old lib is abandoned (deferred dlclose, no
                # cleanup). Flags now describe the swapped-in logic tree.
                self._PLCLogicInitialized = True
                self._PLCLogicRestartPending = False

                # Expose the swapped-in logic library to runtime extensions
                # (PLCLogicBinary / the PLCBinary deprecation shim).
                self.PLCLogicLibrary = new_lib
                if self.python_runtime_vars is not None:
                    self.python_runtime_vars["PLCLogicBinary"] = new_lib
            finally:
                self.PLClibraryLock.release()

            # Store old handle for deferred dlclose — closed at the start of
            # the NEXT NewPLC call, by which time the PLC thread has already
            # switched to the new logic.
            self._PendingOldLogicHandle = self._PLCLogicLibraryHandle
            self._PLCLogicLibraryHandle = new_handle
            self.CurrentLogicFilename = new_logic_fname

            # Persist new logic MD5
            with open(self._GetLogicMD5FileName(), "w") as f:
                f.write(new_logic_md5)
                f.flush()
                os.fsync(f.fileno())

            self.LogMessage("Hot-swap: logic updated to %s" % new_logic_md5)

            # The swapped-in logic .so brings fresh runtime state for extensions that
            # keep logic-tied storage (e.g. SVGHMI's HMI item array/buffers).  Notify
            # them so they can force clients to reconnect / re-subscribe.
            self.PythonRuntimeCall("swap")

            return True

        except Exception:
            self.LogMessage(0, "Hot-swap failed:\n" + traceback.format_exc())
            return False

    @RunInMain
    def SetTraceVariablesList(self, idxs):
        """
        Call ctype imported function to append
        these indexes to registred variables in PLC debugger
        """
        self.DebugToken += 1
        if idxs:
            # suspend but dont disable
            if self._suspendDebug(False) == 0:
                # keep a copy of requested idx
                self._ResetDebugVariables()
                for idx, force in idxs:
                    res = self._RegisterDebugVariable(idx, force, 0 if force is None else len(force))
                    if res != 0:
                        self._resumeDebug()
                        self._suspendDebug(True)
                        return -res
                self._TracesSwap()
                self._resumeDebug()
                return self.DebugToken
        else:
            self._suspendDebug(True)
        return -5 # DEBUG_SUSPENDED

    def _TracesSwap(self):
        self.LastSwapTrace = time()
        if self.TraceThread is None and self.PLCStatus == PlcStatus.Started:
            self.TraceThread = Thread(target=self.TraceThreadProc, name="PLCTrace")
            self.TraceThread.start()
        self.TraceLock.acquire()
        Traces = self.Traces
        self.Traces = []
        self.TraceLock.release()
        return Traces

    @RunInMain
    def GetTraceVariables(self, DebugToken):
        if DebugToken is not None and DebugToken == self.DebugToken:
            return self.PLCStatus, self._TracesSwap()
        return PlcStatus.Broken, []

    def TraceThreadProc(self):
        """
        Return a list of traces, corresponding to the list of required idx
        """
        self._resumeDebug()  # Re-enable debugger
        while self.PLCStatus == PlcStatus.Started:
            tick = ctypes.c_uint32()
            size = ctypes.c_uint32()
            buff = ctypes.c_void_p()
            TraceBuffer = None

            self.PLClibraryLock.acquire()

            res = self._GetDebugData(ctypes.byref(tick),
                                     ctypes.byref(size),
                                     ctypes.byref(buff))
            if res == 0:
                if size.value:
                    TraceBuffer = ctypes.string_at(buff.value, size.value)
                self._FreeDebugData()

            self.PLClibraryLock.release()

            # leave thread if GetDebugData isn't happy.
            if res != 0:
                break

            if TraceBuffer is not None:
                self.TraceLock.acquire()
                lT = len(self.Traces)
                if lT != 0 and lT * len(self.Traces[0]) > 1024 * 1024:
                    self.Traces.pop(0)
                self.Traces.append((tick.value, TraceBuffer))
                self.TraceLock.release()

            # TraceProc stops here if Traces not polled for 3 seconds
            traces_age = time() - self.LastSwapTrace
            if traces_age > 3:
                self.TraceLock.acquire()
                self.Traces = []
                self.TraceLock.release()
                self._suspendDebug(True)  # Disable debugger
                break

        self.TraceThread = None

    def GetVersions(self):
        return platform_module.system() + " " + platform_module.release()

    def PLCScan(self, config_only=False):
        """Walk PLC instance tree, yielding for every node.

        Yields (path, type_enum_value, type_category, count) tuples.
        The C scan runs in a background thread; each callback blocks
        until the generator consumer requests the next item.

        config_only restricts the walk to configuration domain globals.
        """
        item_ready = Event()
        item_consumed = Event()
        result = None
        done = False
        abort = False
        stack = []  # [[path_prefix, flat_count, type_category, done], ...]

        @SCAN_CB_FUNC
        def scan_callback(type_enum_value, ptr, cumulated, local, count, name, userdata):
            nonlocal result, abort
            name = name.decode() if name else ""

            # Mark completed level
            if stack and stack[-1][1] == (local + count):
                stack[-1][3] = True

            type_category = IEC_types_enum.Categorize(type_enum_value)

            path = name if not stack else (stack[-1][0] + (
                "[%d/%d]" % (local, stack[-1][1])
                if stack[-1][2] == IEC_types_enum.ARRAY else
                "." + name))

            if type_category in [IEC_types_enum.ARRAY, IEC_types_enum.STRUCT]:
                stack.append([path, count, type_category, False])
            else:
                # Pop completed level(s)
                while stack and stack[-1][3]:
                    stack.pop()

            # Hand item to generator, wait for it to consume
            result = (path, type_category, type_enum_value, ptr, cumulated, local, count, name, userdata)
            item_ready.set()
            item_consumed.wait()
            item_consumed.clear()

            if abort:
                return 0  # stop traversal
            return 1  # continue and recurse

        def run_scan():
            nonlocal done
            self._ScanInstances(scan_callback, None, 1 if config_only else 0)
            done = True
            item_ready.set()

        t = Thread(target=run_scan, name="PLCScan")
        t.start()

        try:
            while True:
                item_ready.wait()
                item_ready.clear()
                if done:
                    break
                yield result
                item_consumed.set()
        finally:
            abort = True
            item_consumed.set()
            t.join()

    @RunInMain
    def ExtendedCall(self, method, argument):
        """ Dispatch argument to registered service """
        return self.extended_calls[method](argument)

    def RegisterExtendedCall(self, method, callback):
        self.extended_calls[method] = callback

    def UnregisterExtendedCall(self, method):
        del self.extended_calls[method]

