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
        
    def ExchangeData(self): 
        self.pseudofile.write(self.OptData)
        return map(lambda x:self.pseudofile.readline(), xrange(self.expectedlines))

class KEEPBOOTINGTransaction(LPCBootTransaction):
    def __init__(self):
        self.expectedlines = 2
        LPCBootTransaction.__init__(self, "md5\n")

class STARTTransaction(LPCBootTransaction):
    def __init__(self):
        self.expectedlines = 0
        LPCBootTransaction.__init__(self, "go\n")

class CHECKMD5Transaction(LPCBootTransaction):
    def __init__(self, md5ref):
        self.expectedlines = 5 
        LPCBootTransaction.__init__(self, md5ref+"md5\n")

class LOADTransaction(LPCBootTransaction):
    def __init__(self, data, PLCprint):
        self.PLCprint = PLCprint
        LPCBootTransaction.__init__(self, data)

    def ExchangeData(self):
        #file("fw.bin","w").write(self.OptData)
        data = self.OptData
        loptdata = len(self.OptData)
        count=0
        #self.PLCprint("%dkB:" % (loptdata/1024))
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

if __name__ == "__main__":
    __builtins__.BMZ_DBG = True
    TestConnection = LPCBootProto(2,115200,1200)
    mystr=file("fw.bin").read()
    def mylog(blah):
        print blah,

    TestConnection.HandleTransaction(LOADTransaction(mystr, mylog))
