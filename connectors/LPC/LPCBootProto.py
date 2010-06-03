from LPCProto import *

class LPCBootProto(LPCProto):
    def HandleTransaction(self, transaction):
        self.TransactionLock.acquire()
        try:
            transaction.SetPseudoFile(self.serialPort)
            res = transaction.ExchangeData()
        finally:
            self.TransactionLock.release()
        return "Stopped", res
    
class LPCBootTransaction:
    def __init__(self, optdata = ""):
        self.OptData = optdata
        self.pseudofile = None
        
    def SetPseudoFile(self, pseudofile):
        self.pseudofile = pseudofile
        
    def SendData(self):
        res = self.pseudofile.write(self.OptData)
        return True 

    def GetData(self):
        pass # not impl

    def ExchangeData(self): 
        pass

class LOADTransaction(LPCBootTransaction):
    def __init__(self, data):
        LPCBootTransaction.__init__(self, data)
    ExchangeData = LPCBootTransaction.SendData

