import serial
import exceptions
from threading import Lock
import time

class LPCProtoError(exceptions.Exception):
        """Exception class"""
        def __init__(self, msg):
                self.msg = msg

        def __str__(self):
                return "Exception in PLC protocol : " + str(self.msg)

class LPCProto:
    def __init__(self, port, rate, timeout):
        # serialize access lock
        self.TransactionLock = Lock()
        if BMZ_DBG:
            # Debugging serial stuff
            self._serialPort = serial.Serial( port, rate, timeout = timeout, writeTimeout = timeout )
            class myser:
                def readline(self_):
                    res = self._serialPort.readline() 
                    print 'Recv :"', res, '"' 
                    return res

                def read(self_,cnt):
                    res = self._serialPort.read(cnt)
                    if len(res) > 16:
                        print "Recv :", map(hex,map(ord,res[:16])), "[...]"
                    else:
                        print "Recv :", map(hex,map(ord,res))
                        
                    return res
                def write(self_, string):
                    lstr=len(string)
                    if lstr > 16:
                        print "Send :", map(hex,map(ord,string[:16])), "[...]"
                    else:
                        print "Send :", map(hex,map(ord,string))
                    return self._serialPort.write(string)
                    # while len(string)>0:
                    #     i = self._serialPort.write(string[:4096])
                    #     print ".",
                    #     string = string[i:]
                    # print
                    #return lstr
                def flush(self_):
                    return self._serialPort.flush()
                def close(self_):
                    self._serialPort.close()
            self.serialPort = myser()
        else:
            # open serial port
            self.serialPort = serial.Serial( port, rate, timeout = timeout )
        # start with empty buffer
        self.serialPort.flush()
    
    def __del__(self):
        if self.serialPort:
            self.serialPort.close()

    def close(self):
        self.serialPort.close()
        self.serialPort = None
