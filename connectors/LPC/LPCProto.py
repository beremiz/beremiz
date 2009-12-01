import serial
from threading import Lock

LPC_CMDS=dict(IDLE = 0x00,
              START = 0x01,
              STOP = 0x02,
              SET_TRACE_VARIABLE = 0x04,
              GET_TRACE_VARIABLES = 0x05,
              SET_FORCED_VARIABLE = 0x06,
              GET_PLCID = 0x07)

WAIT_DATA = 0x04

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
        # open serial port
        self.serialPort = serial.Serial( port, rate, timeout = timeout )
        self.serialPort.flush()
        # handshake
        self.HandleTransaction(LPCTransaction("IDLE"))
        # serialize access lock
        self.TransactionLock = Lock()
    
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
    def __init__(self, command, optdata):
        self.Command =  LPC_CMDS[command]
        self.OptData = optdata[:]
        self.serialPort = None
        
    def SetPseudoFile(pseudofile):
        self.pseudofile = pseudofile
        
    def SendCommand(self):
        # send command thread
        self.pseudofile.write(chr(self.Command))
        
    def GetCommandAck(self):
        comm_status, current_plc_status = map(ord, self.pseudofile.read(2))
        # LPC returns command itself as an ack for command
        if(comm_status == self.Command):
            return current_plc_status
        return None 
        
    def ExchangeData(self):
        if self.Command & WAIT_DATA :
            length = len(self.OptData)
            # transform length into a byte string
            # we presuppose endianess of LPC same as PC
            lengthstr = ctypes.string_at(ctypes.pointer(ctypes.c_int(length)),4) 
            self.pseudofile.write(lengthstr + self.OptData)
            
            lengthstr = self.pseudofile.read(4)
            # transform a byte string into length 
            length = ctypes.cast(ctypes.c_char_p(lengthstr), ctypes.POINTER(ctypes.c_int)).contents.value
            return self.pseudofile.read(length)
        return None
        
if __name__ == "__main__":
    TestConnection = LPCProto()
    