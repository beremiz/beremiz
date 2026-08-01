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
import runtime
import threading
import struct
import base64
import json

import runtime.PLCObject as PLCObject
from runtime.loglevels import LogLevelsDict

# --------------------------------------------------
#    Transport, mirror of etherlab/rpc.py
# --------------------------------------------------

# This file is shipped alone to the PLC and executed there, so it cannot
# import anything from the etherlab package.  It only has to agree with
# etherlab/rpc.py, which holds the description of the protocol.

EXTENDED_CALL = "EtherCAT"

SDO_ENTRY_FIELDS = ("idx", "subIdx", "datatype", "size", "value")


def EncodeBinary(data):
    return base64.b64encode(data).decode("ascii")


def DecodeBinary(text):
    return base64.b64decode(text.encode("ascii"))


def DecodeRequest(payload):
    request = json.loads(payload.decode("utf-8"))
    return request["cmd"], request.get("args", [])


def EncodeAnswer(result):
    return json.dumps({"result": result}).encode("utf-8")


def EncodeError(message):
    return json.dumps({"error": message}).encode("utf-8")


def SDOEntryFromDict(description):
    """Normalise an SDO entry description coming from the IDE."""
    return dict((field, description.get(field, ""))
                for field in SDO_ENTRY_FIELDS)

SDOAnswered = PLCBinary.SDOAnswered
SDOAnswered.restype = None
SDOAnswered.argtypes = []

PLCGetSDOData = PLCBinary.GetSDOData
PLCGetSDOData.restype = ctypes.c_uint32
PLCGetSDOData.argtypes = [
    ctypes.c_uint16,                  # slave position
    ctypes.c_uint16,                  # index
    ctypes.c_uint8,                   # sub index
    ctypes.POINTER(ctypes.c_uint8),   # buffer
    ctypes.c_uint32,                  # buffer size
]

PLCGetMasterData = PLCBinary.GetMasterData
PLCGetMasterData.restype = ctypes.c_int
PLCGetMasterData.argtypes = []

PLCReleaseMasterData = PLCBinary.ReleaseMasterData
PLCReleaseMasterData.restype = None
PLCReleaseMasterData.argtypes = []

SDOThread = None
SDOProc = None
Result = None

SDOTraceThread = None
SDOLock = threading.Lock()
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
    SDOThread = Thread(target=EthercatSDOThreadProc, args=["upload", pos, var_type, index, subindex])
    SDOThread.start()


def EthercatSDODownload(pos, index, subindex, var_type, value):
    global SDOThread
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

# --------------------------------------------------
#         Etherlab commands, run on the PLC
# --------------------------------------------------

def ethercat(*args, **kwargs):
    """
    Run the "ethercat" command line tool.
    @param args : arguments of the command, converted to strings
    @param binary : return the raw output instead of decoded text
    @param stdin : data to feed the command with
    @return output of the command, stderr included
    """
    binary = kwargs.pop("binary", False)
    stdin = kwargs.pop("stdin", None)

    process = subprocess.Popen(
        ["ethercat"] + [str(arg) for arg in args],
        stdin=subprocess.PIPE if stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    output = process.communicate(stdin)[0]

    if binary:
        return output
    return output.decode("utf-8", errors="replace").rstrip("\n")


def EthercatMasterState():
    return ethercat("master")


def EthercatSlaves():
    return ethercat("slaves")


def EthercatSlaveState(position, state):
    return ethercat("states", "-p", position, state)


def EthercatSlaveXml(position):
    return ethercat("xml", "-p", position)


def EthercatSDOUpload(position, entries):
    """
    @param entries : list of [datatype, index, subindex] to read
    @return one line of output per entry
    """
    return [ethercat("upload", "-p", position, "-t", datatype, index, subindex)
            for datatype, index, subindex in entries]


def EthercatSDODownload(position, datatype, index, subindex, value):
    return ethercat("download", "--type", datatype, "-p", position,
                    index, subindex, value)


def EthercatSiiRead(alias):
    """@return EEPROM content of the slave, base64 encoded"""
    return EncodeBinary(ethercat("sii_read", "-a", alias, binary=True))


def EthercatSiiWrite(position, data):
    """
    @param data : base64 encoded EEPROM content
    @return exit status of the command, 0 when it succeeded
    """
    process = subprocess.Popen(
        ["ethercat", "-f", "sii_write", "-p", str(position), "-"],
        stdin=subprocess.PIPE)
    process.communicate(DecodeBinary(data))
    return process.returncode


def EthercatRegRead(alias, address, size):
    return ethercat("reg_read", "-a", alias, address, size)


def EthercatMultiRegRead(slave_count, registers):
    """
    @param registers : list of [address, size] to read on every slave
    @return one "position,address,content" line per slave and register
    """
    return ["%d,%s,%s" % (position, address,
                          ethercat("reg_read", "-p", position, address, size))
            for position in range(slave_count)
            for address, size in registers]


def EthercatRegWrite(position, address, data):
    return ethercat("reg_write", "-p", position, "-t", "uint16", address, data)


def EthercatRescan(position):
    return ethercat("rescan", "-p", position)


def EthercatScan():
    """
    List the slaves present on the bus, with the identity each of them reports.
    @return list of slave descriptions
    """
    slaves = []
    for slave_line in EthercatSlaves().splitlines():
        chunks = slave_line.strip().split()
        # a slave line looks like "0  3:0  PREOP  +  CL3-E57H"
        if len(chunks) < 5 or ":" not in chunks[1]:
            continue
        alias, position = chunks[1].split(":", 1)
        try:
            slave = {"idx": int(chunks[0]),
                     "alias": int(alias),
                     "position": int(position),
                     "state": chunks[2],
                     "flag": chunks[3],
                     "name": " ".join(chunks[4:]),
                     "vendor_id": None,
                     "product_code": None,
                     "revision_number": None}
        except ValueError:
            continue

        for details_line in ethercat("slaves", "-p", slave["idx"], "-v").splitlines():
            details_line = details_line.strip()
            for header, param in [("Vendor Id:", "vendor_id"),
                                  ("Product code:", "product_code"),
                                  ("Revision number:", "revision_number")]:
                if details_line.startswith(header):
                    slave[param] = details_line.split()[-1]
                    break

        slaves.append(slave)

    return slaves


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

def GetSDOEntriesData(entries, SlavePos):
    """
    Read a chunk of the given SDO entries, so that a large set is spread over
    several calls instead of blocking the runtime.
    @param entries : list of SDO entry descriptions
    @param SlavePos : ring position of the slave to read from
    @return the entries read during this call, values included
    """
    global _sdo_busy
    global _sdo_snapshot
    global _sdo_index

    if not entries:
        return []

    # start of a new scan
    if not _sdo_busy or len(_sdo_snapshot) != len(entries):
        _sdo_snapshot = [SDOEntryFromDict(entry) for entry in entries]
        _sdo_index = 0
        _sdo_busy = True

    snapshot = _sdo_snapshot or []

    if len(snapshot) == 0:
        _sdo_busy = False
        return []

    CHUNK_SIZE = 14

    output = []

    start = _sdo_index
    end = min(start + CHUNK_SIZE, len(snapshot))

    for data in snapshot[start:end]:

        try:
            idx = int(str(data["idx"]), 16)
            sub = int(str(data["subIdx"]), 16)

            size_bits = int(data["size"])
            size = max(1, size_bits // 8)

            buffer = (ctypes.c_uint8 * size)()

            ret = PLCGetSDOData(SlavePos, idx, sub, buffer, size)

            value = decode_sdo(ret, buffer, str(data["datatype"]).upper())

            output.append({"idx": str(data["idx"]),
                           "subIdx": str(data["subIdx"]),
                           "datatype": data["datatype"],
                           "size": str(size_bits),
                           "value": str(value)})

        except Exception as e:
            PLCObject.LogMessage(
                LogLevelsDict["WARNING"],
                "EtherCAT SDO upload failed : %s" % str(e))
            continue

        time.sleep(0.01)

    _sdo_index = end

    if _sdo_index >= len(snapshot):
        _sdo_busy = False
        _sdo_index = 0

    return output


def StopSDOThread():
    global SDOThreadFlag
    SDOThreadFlag = False
    return 0


def GetSDOEntryData(entry, SlavePos):
    """
    Read a single SDO entry, whatever the PLC state.
    @param entry : description of the entry to read
    @param SlavePos : ring position of the slave to read from
    @return decoded value of the entry
    """
    plcobj = runtime.GetPLCObjectSingleton()

    # when the PLC is stopped, the master has to be opened by hand
    running = plcobj.PLCStatus == runtime.PlcStatus.Started
    if not running:
        PLCGetMasterData()

    try:
        size = max(1, int(entry["size"]) // 8)
        buffer = (ctypes.c_uint8 * size)()

        ret = PLCGetSDOData(SlavePos, int(entry["idx"], 16),
                            int(entry["subIdx"], 16), buffer, size)
        return decode_sdo(ret, buffer, str(entry.get("datatype", "")).upper())
    finally:
        if not running:
            PLCReleaseMasterData()


def SetSDOTraceValues(entries, SlavePos):
    """
    Set the list of SDO entries the monitoring thread has to poll.
    @param entries : list of SDO entry descriptions
    @param SlavePos : ring position of the slave to poll
    """
    global SDOMonitorEntries
    global SDOMonitorSlavePos

    entries_dict = {}

    for description in entries:
        entry = SDOEntryFromDict(description)
        try:
            idx = entry["idx"]
            subidx = entry["subIdx"]
            idx = int(idx, 16) if isinstance(idx, str) else int(idx)
            subidx = int(subidx, 16) if isinstance(subidx, str) else int(subidx)

            entries_dict[(idx, subidx)] = entry

        except Exception as ex:
            PLCObject.LogMessage(
                LogLevelsDict["WARNING"],
                "Unusable EtherCAT SDO monitor entry %s : %s"
                % (repr(description), str(ex)))

    with SDOLock:
        SDOMonitorEntries = entries_dict
        SDOMonitorSlavePos = SlavePos

    return 0


def GetSDOData():
    """
    Give back the values the monitoring thread collected, starting it when it
    is not running yet.
    @return the polled slave position and the entries with their last value
    """
    global SDOTraceThread
    global SDOThreadFlag

    if SDOTraceThread is None:
        SDOTraceThread = Thread(target=SDOThreadProc)
        SDOThreadFlag = True
        SDOTraceThread.start()

    with SDOLock:
        entries = list(SDOMonitorEntries.values())
        slave_pos = SDOMonitorSlavePos

    return {"slavePos": slave_pos, "entries": entries}


def SDOThreadProc():

    while SDOThreadFlag:

        try:
            plcobj = runtime.GetPLCObjectSingleton()
            status, _ = plcobj.GetPLCstatus()

        except Exception as e:
            PLCObject.LogMessage(
                LogLevelsDict["WARNING"],
                "Could not read PLC status : %s" % str(e))
            time.sleep(1)
            continue

        with SDOLock:
            snapshot = list(SDOMonitorEntries.values())
            slave_pos = SDOMonitorSlavePos

        for entry in snapshot:

            try:

                idx = int(entry["idx"], 16)
                subidx = int(entry["subIdx"], 16)

                size = int(entry["size"])//8 if entry["size"] else 1

                if status == runtime.PlcStatus.Started:
                    buffer = (ctypes.c_uint8 * size)()
                    ret = PLCGetSDOData(slave_pos, idx, subidx,
                                        buffer, size)
                    val = decode_sdo(ret, buffer,
                                     str(entry["datatype"]).upper())
                else:
                    val = 0

                entry["value"] = val

            except Exception as e:

                entry["value"] = str(e)

        time.sleep(1)

# --------------------------------------------------
#    Services offered to the IDE, see etherlab/rpc.py
# --------------------------------------------------

ETHERCAT_COMMANDS = {
    "master_state":     EthercatMasterState,
    "slaves":           EthercatSlaves,
    "slave_state":      EthercatSlaveState,
    "slave_xml":        EthercatSlaveXml,
    "sdo_upload":       EthercatSDOUpload,
    "sdo_download":     EthercatSDODownload,
    "sii_read":         EthercatSiiRead,
    "sii_write":        EthercatSiiWrite,
    "reg_read":         EthercatRegRead,
    "multi_reg_read":   EthercatMultiRegRead,
    "reg_write":        EthercatRegWrite,
    "rescan":           EthercatRescan,
    "scan":             EthercatScan,
    "get_sdo_data":         GetSDOData,
    "get_sdo_entry_data":   GetSDOEntryData,
    "get_sdo_entries_data": GetSDOEntriesData,
    "set_sdo_trace_values": SetSDOTraceValues,
    "stop_sdo_thread":      StopSDOThread,
}


def EtherCATCallHandler(argument):
    """
    Dispatch an EtherCAT request coming from the IDE.  Only the commands of
    ETHERCAT_COMMANDS can be reached, arguments are plain JSON values.
    """
    try:
        command, args = DecodeRequest(argument)
        handler = ETHERCAT_COMMANDS.get(command)
        if handler is None:
            raise ValueError("unknown EtherCAT command %s" % command)
        return EncodeAnswer(handler(*args))
    except Exception as e:
        message = "EtherCAT call failed : %s" % str(e)
        PLCObject.LogMessage(LogLevelsDict["WARNING"], message)
        return EncodeError(str(e))


# TODO : rename to match _runtime_{location}_extname_init() format
def _runtime_etherlab_init():
    global KMSGPollThread, StopKMSGThread
    plcobj = runtime.GetPLCObjectSingleton()

    plcobj.RegisterExtendedCall(EXTENDED_CALL, EtherCATCallHandler)

    StopKMSGThread = False
    KMSGPollThread = Thread(target=KMSGPollThreadProc)
    KMSGPollThread.start()


# TODO : rename to match _runtime_{location}_extname_cleanup() format
def _runtime_etherlab_cleanup():
    global KMSGPollThread, StopKMSGThread, SDOThread
    global SDOTraceThread, SDOThreadFlag

    runtime.GetPLCObjectSingleton().UnregisterExtendedCall(EXTENDED_CALL)

    try:
        os.kill(SDOProc.pid, signal.SIGTERM)
    except Exception:
        pass
    SDOThread = None
    SDOThreadFlag = False
    SDOTraceThread = None
    StopKMSGThread = True
    KMSGPollThread = None
