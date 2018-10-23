import os
from binascii import hexlify

restart_stunnel_cmdline = ["/etc/init.d/S50stunnel","restart"]

def pskgen(ID, pskpath):
    secretstring = hexlify(os.urandom(256))
    pskstring = ID+":"+secretstring
    with open(pskpath, 'w') as f:
        f.write(pskstring)
    call(restart_stunnel_cmdline)

def ensurepsk(ID, pskpath):
    # check if already there
    if not os.path.exists(pskpath):
        # create if needed
        pskgen(IS, pskpath)

