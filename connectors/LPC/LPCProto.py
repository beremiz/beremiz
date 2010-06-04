import serial
import exceptions
from threading import Lock

class LPCProtoError(exceptions.Exception):
        """Exception class"""
        def __init__(self, msg):
                self.msg = msg

        def __str__(self):
                return "LPC communication error ! " + str(self.msg)

class LPCProto:
    def __init__(self, port, rate, timeout):
        # serialize access lock
        self.TransactionLock = Lock()
        # open serial port
#        self.serialPort = serial.Serial( port, rate, timeout = timeout )
        # Debugging serial stuff
        self.serialPort = serial.Serial( port, rate, timeout = timeout )
#        class myser:
#            def read(self_,cnt):
#                res = self._serialPort.read(cnt)
#                if len(res) > 16:
#                    print "Recv :", map(hex,map(ord,res[:16])), "[...]"
#                else:
#                    print "Recv :", map(hex,map(ord,res))
#                    
#                return res
#            def write(self_, str):
#                if len(str) > 16:
#                    print "Send :", map(hex,map(ord,str[:16])), "[...]"
#                else:
#                    print "Send :", map(hex,map(ord,str))
#                self._serialPort.write(str)
#            def flush(self_):
#                self._serialPort.flush()
#        self.serialPort = myser()
        # start with empty
        self.serialPort.flush()
    
    def __del__(self):
        if self.serialPort:
            self.serialPort.close()

    def close(self):
        self.serialPort.close()
        self.serialPort = None
