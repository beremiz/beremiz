import serial
import exceptions
import ctypes
import time
from threading import Lock

MAX_PACKET_SIZE=64

LPC_STATUS=dict(STARTED = 0x01,
                STOPPED = 0x02,
                DEBUG = 0x03)

class LPCError(exceptions.Exception):
        """Exception class"""
        def __init__(self, msg):
                self.msg = msg
                return

        def __str__(self):
                return "LPC communication error ! " + str(self.msg)

class LPCProto:
    def __init__(self, port, rate, timeout):
        # serialize access lock
        self.TransactionLock = Lock()
        # open serial port
#        self.serialPort = serial.Serial( port, rate, timeout = timeout )
        # Debugging serial stuff
        self._serialPort = serial.Serial( port, rate, timeout = timeout )
        class myser:
            def read(self_,cnt):
                res = self._serialPort.read(cnt)
                print "Recv :", map(hex,map(ord,res))
                return res
            def write(self_, str):
                print "Send :", map(hex,map(ord,str))
                self._serialPort.write(str)
            def flush(self_):
                self._serialPort.flush()
        self.serialPort = myser()
        # start with empty
        self.serialPort.flush()
        # handshake
        self.HandleTransaction(IDLETransaction())
    
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
                raise LPCError("LPC transaction error - controller did not answer as expected")
        finally:
            self.TransactionLock.release()
        return current_plc_status, res
    
class LPCTransaction:
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
            raise LPCError("LPC transaction error - controller did not ack order")
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
        ###################################################################
        # TO BE REMOVED AS SOON AS USB IS FIXED IN CONTROLLER
        ###################################################################
        length += 4
        cursor = 0
        while cursor < length:
            next_cursor = cursor + MAX_PACKET_SIZE
            # sent just enough bytes to not crash controller
            self.pseudofile.write(buffer[cursor:next_cursor])
            # if sent quantity was 128
            if next_cursor <= length:
                self.GetCommandAck()
            cursor = next_cursor

    def GetData(self):
        lengthstr = self.pseudofile.read(4)
        # transform a byte string into length 
        length = ctypes.cast(ctypes.c_char_p(lengthstr), ctypes.POINTER(ctypes.c_int)).contents.value
        return self.pseudofile.read(length)

    def ExchangeData(self): 
        pass

class IDLETransaction(LPCTransaction):
    def __init__(self):
        LPCTransaction.__init__(self, 0x00)

class STARTTransaction(LPCTransaction):
    def __init__(self):
        LPCTransaction.__init__(self, 0x01)
    
class STOPTransaction(LPCTransaction):
    def __init__(self):
        LPCTransaction.__init__(self, 0x02)

class SET_TRACE_VARIABLETransaction(LPCTransaction):
    def __init__(self, data):
        LPCTransaction.__init__(self, 0x04, data)
    ExchangeData = LPCTransaction.SendData

class GET_TRACE_VARIABLETransaction(LPCTransaction):
    def __init__(self):
        LPCTransaction.__init__(self, 0x05)
    ExchangeData = LPCTransaction.GetData

class SET_FORCED_VARIABLETransaction(LPCTransaction):
    def __init__(self, data):
        LPCTransaction.__init__(self, 0x06, data)
    ExchangeData = LPCTransaction.SendData

class GET_PLCIDTransaction(LPCTransaction):
    def __init__(self):
        LPCTransaction.__init__(self, 0x07)
    ExchangeData = LPCTransaction.GetData

if __name__ == "__main__":
    TestConnection = LPCProto(6,115200,2)
#    TestConnection.HandleTransaction(GET_PLCIDTransaction())
    TestConnection.HandleTransaction(STARTTransaction())
#    TestConnection.HandleTransaction(SET_TRACE_VARIABLETransaction(
#           "\x03\x00\x00\x00"*200))
#    TestConnection.HandleTransaction(STARTTransaction())
    TestConnection.HandleTransaction(SET_TRACE_VARIABLETransaction(
       "\x05\x00\x00\x00"+
       "\x01\x00\x00\x00"+
       "\x04"+
       "\x01\x02\x02\x04"))
    #status,res = TestConnection.HandleTransaction(GET_TRACE_VARIABLETransaction())
    #print len(res)
    #print "GOT : ", map(hex, map(ord, res))
    #TestConnection.HandleTransaction(STOPTransaction())
