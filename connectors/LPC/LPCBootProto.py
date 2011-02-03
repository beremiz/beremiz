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

class KEEPBOOTINGTransaction(LPCBootTransaction):
    def __init__(self):
        LPCBootTransaction.__init__(self, "md5\n")
    ExchangeData = LPCBootTransaction.SendData

class LOADTransaction(LPCBootTransaction):
    def __init__(self, data, PLCprint):
        self.PLCprint = PLCprint
        LPCBootTransaction.__init__(self, data)

    def sendDataHook(self):
        #file("fw.bin","w").write(self.OptData)
        data = self.OptData
        loptdata = len(self.OptData)
        count=0
        self.PLCprint("%dkB:" % (loptdata/1024))
        while len(data)>0:
            res = self.pseudofile.write(data[:loptdata/100])
            data = data[res:]
            count += 1
            if count % 10 == 0 :
                self.PLCprint("%d%%" % count)
            else :
                self.PLCprint(".")
        self.PLCprint("\n")
        return True
    ExchangeData = sendDataHook

if __name__ == "__main__":
    TestConnection = LPCBootProto(2,115200,1200)
    mystr=file("fw.bin").read()
    def mylog(blah):
        print blah,

    TestConnection.HandleTransaction(LOADTransaction(mystr, mylog))
