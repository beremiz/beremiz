import ctypes
from LPCProto import *

LPC_STATUS={0xaa : "Started",
            0x55 : "Stopped"}

class LPCAppProto(LPCProto):
    def HandleTransaction(self, transaction):
        self.TransactionLock.acquire()
        try:
            transaction.SetPseudoFile(self.serialPort)
            # send command, wait ack (timeout)
            transaction.SendCommand()
            current_plc_status = transaction.GetCommandAck()
            if current_plc_status is not None:
                res = transaction.ExchangeData()
            else:
                raise LPCProtoError("controller did not answer as expected")
        except Exception, e:
            raise LPCProtoError("application mode transaction error : "+str(e))
        finally:
            self.TransactionLock.release()
        return LPC_STATUS.get(current_plc_status,"Broken"), res
    
class LPCAppTransaction:
    def __init__(self, command, optdata = ""):
        self.Command = command
        self.OptData = optdata
        self.pseudofile = None
        
    def SetPseudoFile(self, pseudofile):
        self.pseudofile = pseudofile
        
    def SendCommand(self):
        # send command thread
        self.pseudofile.write(chr(self.Command))
        
    def GetCommandAck(self):
        res = self.pseudofile.read(2)
        if len(res) == 2:
            comm_status, current_plc_status = map(ord, res)
        else:
            raise LPCProtoError("LPC transaction error - controller did not ack order")
        # LPC returns command itself as an ack for command
        if(comm_status == self.Command):
            return current_plc_status
        return None 
        
    def SendData(self):
        length = len(self.OptData)
        # transform length into a byte string
        # we presuppose endianess of LPC same as PC
        lengthstr = ctypes.string_at(ctypes.pointer(ctypes.c_int(length)),4)
        buffer = lengthstr + self.OptData
        return self.pseudofile.write(buffer)

    def GetData(self):
        lengthstr = self.pseudofile.read(4)
        # transform a byte string into length 
        length = ctypes.cast(ctypes.c_char_p(lengthstr), ctypes.POINTER(ctypes.c_int)).contents.value
        return self.pseudofile.read(length)

    def ExchangeData(self): 
        pass

class IDLETransaction(LPCAppTransaction):
    def __init__(self):
        LPCAppTransaction.__init__(self, 0x07)
    ExchangeData = LPCAppTransaction.GetData

class STARTTransaction(LPCAppTransaction):
    def __init__(self):
        LPCAppTransaction.__init__(self, 0x01)
    
class STOPTransaction(LPCAppTransaction):
    def __init__(self):
        LPCAppTransaction.__init__(self, 0x02)

class RESETTransaction(LPCAppTransaction):
    def __init__(self):
        LPCAppTransaction.__init__(self, 0x03)

class SET_TRACE_VARIABLETransaction(LPCAppTransaction):
    def __init__(self, data):
        LPCAppTransaction.__init__(self, 0x04, data)
    ExchangeData = LPCAppTransaction.SendData

class GET_TRACE_VARIABLETransaction(LPCAppTransaction):
    def __init__(self):
        LPCAppTransaction.__init__(self, 0x05)
    ExchangeData = LPCAppTransaction.GetData

class GET_PLCIDTransaction(LPCAppTransaction):
    def __init__(self):
        LPCAppTransaction.__init__(self, 0x07)
    ExchangeData = LPCAppTransaction.GetData

if __name__ == "__main__":
    __builtins__.BMZ_DBG = True
    TestConnection = LPCAppProto(6,115200,2)
#    TestConnection.HandleTransaction(GET_PLCIDTransaction())
    TestConnection.HandleTransaction(STARTTransaction())
#    TestConnection.HandleTransaction(SET_TRACE_VARIABLETransaction(
#           "\x03\x00\x00\x00"*200))
#    TestConnection.HandleTransaction(STARTTransaction())
    while True:
        TestConnection.HandleTransaction(SET_TRACE_VARIABLETransaction(
           "\x01\x00\x00\x00"+
           "\x04"+
           "\x01\x02\x02\x04"+
           "\x01\x00\x00\x00"+
           "\x08"+
           "\x01\x02\x02\x04"+
           "\x01\x02\x02\x04"+
           "\x01\x00\x00\x00"+
           "\x04"+
           "\x01\x02\x02\x04"))
    #status,res = TestConnection.HandleTransaction(GET_TRACE_VARIABLETransaction())
    #print len(res)
    #print "GOT : ", map(hex, map(ord, res))
    #TestConnection.HandleTransaction(STOPTransaction())
