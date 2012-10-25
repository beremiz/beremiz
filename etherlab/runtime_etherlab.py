import subprocess,sys,ctypes
from threading import Thread

SDOAnswered = PLCBinary.SDOAnswered
SDOAnswered.restype = None
SDOAnswered.argtypes = []

SDOThread = None
Result = None

def SDOThreadProc(*params):
    global Result
    if params[0] == "upload":
        command = "ethercat upload -p %d -t %s 0x%.4x 0x%.2x"
    else:
        command = "ethercat download -p %d -t %s 0x%.4x 0x%.2x %s"
    
    proc = subprocess.Popen(command % params[1:], stdout=subprocess.PIPE, shell=True)
    res = proc.wait()
    output = proc.communicate()[0]
    
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
    
def EthercatSDOUpload(pos, index, subindex, var_type):
    global SDOThread
    SDOThread = Thread(target=SDOThreadProc, args=["upload", pos, var_type, index, subindex])
    SDOThread.start()
    
def EthercatSDODownload(pos, index, subindex, var_type, value):
    global SDOThread
    SDOThread = Thread(target=SDOThreadProc, args=["download", pos, var_type, index, subindex, value])
    SDOThread.start()

def GetResult():
    global Result
    return Result
