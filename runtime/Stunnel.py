import os
#from binascii import hexlify
from runtime.spawn_subprocess import call

restart_stunnel_cmdline = ["/etc/init.d/S50stunnel","restart"]

# stunnel takes no encoding for psk, so we try to lose minimum entropy 
# by using all possible chars except '\0\n\r' (checked stunnel parser to be sure)
translator = ''.join([(lambda c: '#' if c in '\0\n\r' else c)(chr(i)) for i in xrange(256)])

def pskgen(ID, pskpath):
    secret = os.urandom(256) # 2048 bits is still safe nowadays

    # following makes 512 length string, rejected by stunnel
    # using binascii hexlify loses 50% entropy
    # secretstring = hexlify(secret)

    secretstring = secret.translate(translator)
    pskstring = ID+":"+secretstring
    with open(pskpath, 'w') as f:
        f.write(pskstring)
    call(restart_stunnel_cmdline)

def ensurepsk(ID, pskpath):
    # check if already there
    if not os.path.exists(pskpath):
        # create if needed
        pskgen(ID, pskpath)

