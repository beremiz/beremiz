#!/usr/bin/env python
# -*- coding: utf-8 -*-

# this file is part of beremiz
#
# copyright (c) 2011-2014: laurent bessard, edouard tisserant
#                          rtes lab : crkim, jblee, youcu
#                          higen motor : donggu kang
#
# see copying file for copyrights details.


import os
import signal
import subprocess
import ctypes
from threading import Thread
import time
import re
import pickle
import runtime
import threading
import struct
from etherlab.sdo import SDOEntry, SDODataPack

import runtime.PLCObject as PLCObject
from runtime.loglevels import LogLevelsDict

SDOAnswered = PLCBinary.SDOAnswered
SDOAnswered.restype = None
SDOAnswered.argtypes = []

SDOThread = None
SDOProc = None
Result = None

SDOTraceThread = None
SDOLock = threading.Lock()
SDOTraceValues = []
SDOMonitorEntries = {}
SDOMonitorSlavePos = 0
SDOThreadFlag = False

_sdo_busy = False
_sdo_snapshot = []
_sdo_index = 0

def EthercatSDOThreadProc(*params):
    global Result, SDOProc
    if params[0] == "upload":
        cmdfmt = "ethercat upload -p %d -t %s 0x%.4x 0x%.2x"
    else:
        cmdfmt = "ethercat download -p %d -t %s 0x%.4x 0x%.2x %s"

    command = cmdfmt % params[1:]
    SDOProc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    res = SDOProc.wait()
    output = SDOProc.communicate()[0]

    if params[0] == "upload":
        Result = None
        if res == 0:
            if params[2] in ["float", "double"]:
                Result = float(output)
            elif params[2] in ["string", "octet_string", "unicode_string"]:
                Result = output
            else:
                hex_value, dec_value = output.split()
                if int(hex_value, 16) == int(dec_value):
                    Result = int(dec_value)
    else:
        Result = res == 0

    SDOAnswered()
    if res != 0:
        PLCObject.LogMessage(
            LogLevelsDict["WARNING"],
            "%s : %s" % (command, output))


def EthercatSDOUpload(pos, index, subindex, var_type):
    global SDOThread
#    SDOThread = Thread(target=SDOThreadProc, args=["upload", pos, var_type, index, subindex])
    SDOThread = Thread(target=EthercatSDOThreadProc, args=["upload", pos, var_type, index, subindex])
    SDOThread.start()


def EthercatSDODownload(pos, index, subindex, var_type, value):
    global SDOThread
#    SDOThread = Thread(target=SDOThreadProc, args=["download", pos, var_type, index, subindex, value])
    SDOThread = Thread(target=EthercatSDOThreadProc, args=["download", pos, var_type, index, subindex, value])
    SDOThread.start()


def GetResult():
    return Result


KMSGPollThread = None
StopKMSGThread = False


def KMSGPollThreadProc():
    """
    Logs Kernel messages starting with EtherCAT
    Uses GLibc wrapper to Linux syscall "klogctl"
    Last 4 KB are polled, and lines compared to last
    captured line to detect new lines
    """
    libc = ctypes.CDLL("libc.so.6")
    klog = libc.klogctl
    klog.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    klog.restype = ctypes.c_int
    s = ctypes.create_string_buffer(4*1024)
    last = None
    while not StopKMSGThread:
        bytes_to_read = klog(3, s, len(s)-1)
        log = s.value[:bytes_to_read-1]
        if last:
            log = log.rpartition(last)[2]
        if log:
            last = log.rpartition('\n')[2]
            for lvl, msg in re.findall(
                    r'<(\d)>\[\s*\d*\.\d*\]\s*(EtherCAT\s*.*)$',
                    log, re.MULTILINE):
                PLCObject.LogMessage(
                    LogLevelsDict[{
                        "4": "WARNING",
                        "3": "CRITICAL"}.get(lvl, "DEBUG")],
                    msg)
        time.sleep(0.5)

def GetSDODataHandler(argument):

    result = type("obj", (), {})()

    GetSDOData(result)

    return pickle.dumps(result.value)
    
def GetSDOEntriesDataHandler(argument):

    entries, slave_pos = pickle.loads(argument)

    result = type("obj", (), {})()

    GetSDOEntriesData(
        entries,
        slave_pos,
        result
    )

    return pickle.dumps(result.value)
    
def decode_sdo(ret, buffer, dt):

    if ret < 0:
        return f"abort(0x{-ret:X})"


    if ret == 0:
        return "empty"


    raw = bytes(buffer[:ret])


    try:

        if "STRING" in dt:
            return raw.decode(
                "utf-8",
                errors="ignore"
            ).rstrip("\x00")


        if "USINT" in dt or "UNSIGNED8" in dt:
            return raw[0]


        if "UINT" in dt or "UNSIGNED16" in dt:
            return int.from_bytes(
                raw,
                "little"
            )


        if "UDINT" in dt or "UNSIGNED32" in dt:
            return int.from_bytes(
                raw,
                "little"
            )


        if "INT" in dt:
            return int.from_bytes(
                raw,
                "little",
                signed=True
            )


        if "DINT" in dt:
            return int.from_bytes(
                raw,
                "little",
                signed=True
            )


        if "REAL" in dt:
            return struct.unpack(
                "<f",
                raw[:4]
            )[0]


        if "LREAL" in dt:
            return struct.unpack(
                "<d",
                raw[:8]
            )[0]


        return raw.hex()


    except Exception as e:

        return f"decode_error: {e}"

def GetSDOEntriesData(SDOUploadEntries, SlavePos, result):

    global _sdo_busy
    global _sdo_snapshot
    global _sdo_index

    plcobj = runtime.GetPLCObjectSingleton()

    if not SDOUploadEntries:
        result.value = []
        return 0


    # Inicialización del escaneo
    if (not _sdo_busy or
        len(_sdo_snapshot) != len(SDOUploadEntries)):

        _sdo_snapshot = list(SDOUploadEntries or [])
        _sdo_index = 0
        _sdo_busy = True


    snapshot = _sdo_snapshot or []


    if len(snapshot) == 0:
        _sdo_busy = False
        result.value = []
        return 0


    CHUNK_SIZE = 14

    output = []


    start = _sdo_index
    end = min(start + CHUNK_SIZE, len(snapshot))


    print(f"SDO chunk {start} → {end}")


    for i in range(start, end):

        data = snapshot[i]


        if data is None:
            continue


        try:

            idx = int(str(data.idx), 16)
            sub = int(str(data.subIdx), 16)


            size_bits = int(data.size)

            size = max(1, size_bits // 8)


            buffer = (ctypes.c_uint8 * size)()


            ret = plcobj._GetSDOData(
                SlavePos,
                idx,
                sub,
                buffer,
                size
            )


            value = decode_sdo(
                ret,
                buffer,
                getattr(data, "datatype", "").upper()
            )


            output.append(
                SDOEntry(
                    idx=str(data.idx),
                    subIdx=str(data.subIdx),
                    datatype=getattr(data, "datatype", ""),
                    size=str(size_bits),
                    value=str(value)
                )
            )

        except Exception as e:

            print("SDO ITEM ERROR:", e)

            continue


        time.sleep(0.01)



    _sdo_index = end



    if _sdo_index >= len(snapshot):

        _sdo_busy = False
        _sdo_index = 0



    result.value = output

    return 0 

def SetSDOTraceValuesHandler(argument):

    entries, slavePos = pickle.loads(argument)

    result = type("obj", (), {})()

    SetSDOTraceValues(
        entries,
        slavePos,
        result
    )

    return pickle.dumps(result.value)

def StopSDOThreadHandler(argument):
    global SDOThreadFlag
    SDOThreadFlag = False
    return pickle.dumps(0)
    
def GetSDOEntryDataHandler(argument):

    SDOUploadEntry, SlavePos = pickle.loads(argument)

    plcobj = runtime.GetPLCObjectSingleton()

    if plcobj.PLCStatus != runtime.PlcStatus.Started:
        plcobj._GetMasterData()

    idx = SDOUploadEntry["idx"]
    subidx = SDOUploadEntry["subIdx"]
    size = int(SDOUploadEntry["size"]) // 8

    data = plcobj._GetSDOData(
        SlavePos,
        int(idx, 16),
        int(subidx, 16),
        size
    )

    if plcobj.PLCStatus != runtime.PlcStatus.Started:
        plcobj._ReleaseMasterData()

    return pickle.dumps(data)
    
SDOMonitorEntries = {}
SDOMonitorSlavePos = 0


def SetSDOTraceValues(SDOMonitorEntriesInput, SlavePos, result):

    global SDOMonitorEntries
    global SDOMonitorSlavePos

#    print("SDO TRACE RECIBIDO:", SDOMonitorEntriesInput, SlavePos)
#    print("====================================")
#    print("TIPO =", type(SDOMonitorEntriesInput))
#    print("CONTENIDO =", repr(SDOMonitorEntriesInput))
#    print("SLAVE =", SlavePos)

#    try:
#        print("LEN =", len(SDOMonitorEntriesInput))
#    except Exception as e:
#        print("NO LEN:", e)

#    print("====================================")

    entries_dict = {}

    for e in SDOMonitorEntriesInput:
        print("ENTRY =", e)
        try:
            idx = int(e.idx, 16) if isinstance(e.idx, str) else int(e.idx)
            subidx = int(e.subIdx, 16) if isinstance(e.subIdx, str) else int(e.subIdx)

            entries_dict[(idx, subidx)] = e

        except Exception as ex:
            print("[DEBUG] ERROR parsing SDO entry:", e, ex)

    SDOMonitorEntries = entries_dict
    SDOMonitorSlavePos = SlavePos

    result.value = 0

def GetSDOData(result):

    global SDOTraceThread
    global SDOThreadFlag

    global SDOMonitorEntries
    global SDOMonitorSlavePos

    global SDOLock

    global SDOTraceThread

#    print("GetSDOData() en runtime_etherlab")

    if SDOTraceThread is None:
#        print("CREANDO SDOTraceThread NUEVO")
        SDOTraceThread = Thread(target=SDOThreadProc)
        SDOThreadFlag = True
        SDOTraceThread.start()


    with SDOLock:
        entries_dict = SDOMonitorEntries or {}
        slave_pos = SDOMonitorSlavePos


    entries_list = list(entries_dict.values()) if isinstance(entries_dict, dict) else entries_dict

    pack = SDODataPack()
    pack.entries = entries_list
    pack.slavePos = slave_pos


    result.value = pack

def SDOThreadProc():

    global SDOThreadFlag
    global SDOMonitorEntries
    global SDOMonitorSlavePos

#    print("SDOThreadProc")

    while SDOThreadFlag:

        try:
            plcobj = runtime.GetPLCObjectSingleton()
            status, _ = plcobj.GetPLCstatus()

        except Exception as e:
            print("[SDOThread] PLC status error:", e)
            time.sleep(1)
            continue


        snapshot = list(SDOMonitorEntries.values())


        for entry in snapshot:

            try:

                idx = int(entry.idx,16)
                subidx = int(entry.subIdx,16)

                size = int(entry.size)//8 if entry.size else 1


                if status == runtime.PlcStatus.Started:

                    val = plcobj._GetSDOData(
                        SDOMonitorSlavePos,
                        idx,
                        subidx,
                        size
                    )

                else:

                    val = 0


                entry.value = val


            except Exception as e:

                entry.value = str(e)


        time.sleep(1)
#    print("====FIN SDOThreadProc====")

# TODO : rename to match _runtime_{location}_extname_init() format
def _runtime_etherlab_init():
    global KMSGPollThread, StopKMSGThread
    plcobj = runtime.GetPLCObjectSingleton()

#    print("PLCOBJ =", plcobj)
#    print("TIPO =", type(plcobj))

    plcobj.RegisterExtendedCall(
        "GetSDOData",
        GetSDODataHandler
    )

#    print("GetSDOData registrado")
    
    plcobj.RegisterExtendedCall(
    "GetSDOEntriesData",
    GetSDOEntriesDataHandler
    )

#    print("GetSDOEntriesData registrado")

    plcobj.RegisterExtendedCall(
        "SetSDOTraceValues",
        SetSDOTraceValuesHandler
    )
    
#    print("SetSDOTraceValues registrado")

    plcobj.RegisterExtendedCall(
        "StopSDOThread",
        StopSDOThreadHandler
    )
    
#    print("StopSDOThread registrado")
    
    plcobj.RegisterExtendedCall(
        "GetSDOEntryData",
        GetSDOEntryDataHandler
    )

#    print("GetSDOEntryData registrado")
    
    StopKMSGThread = False
    KMSGPollThread = Thread(target=KMSGPollThreadProc)
    KMSGPollThread.start()


# TODO : rename to match _runtime_{location}_extname_cleanup() format
def _runtime_etherlab_cleanup():
    global KMSGPollThread, StopKMSGThread, SDOThread
    try:
        os.kill(SDOProc.pid, signal.SIGTERM)
    except Exception:
        pass
    SDOThread = None
    StopKMSGThread = True
    KMSGPollThread = None
