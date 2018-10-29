import os
#from binascii import hexlify
from runtime.spawn_subprocess import call

restart_stunnel_cmdline = ["/etc/init.d/S50stunnel","restart"]

# stunnel takes no encoding for PSK, so we try to lose minimum entropy 
# by using all possible chars except '\0\n\r' (checked stunnel parser to be sure)
translator = ''.join([(lambda c: '#' if c in '\0\n\r' else c)(chr(i)) for i in xrange(256)])

_PSKpath = None

def PSKgen(ID, PSKpath):
    secret = os.urandom(256) # 2048 bits is still safe nowadays

    # following makes 512 length string, rejected by stunnel
    # using binascii hexlify loses 50% entropy
    # secretstring = hexlify(secret)

    secretstring = secret.translate(translator)
    PSKstring = ID+":"+secretstring
    with open(PSKpath, 'w') as f:
        f.write(PSKstring)
    call(restart_stunnel_cmdline)

def ensurePSK(ID, PSKpath):
    global _PSKpath
    _PSKpath = PSKpath
    # check if already there
    if not os.path.exists(PSKpath):
        # create if needed
        PSKgen(ID, PSKpath)

def getPSKID():
    if _PSKpath is not None :
        if not os.path.exists(_PSKpath):
            confnodesroot.logger.write_error(
                'Error: Pre-Shared-Key Secret in %s is missing!\n' % _PSKpath)
            return None
        ID,_sep,PSK = open(_PSKpath).read().partition(':')
        PSK = PSK.rstrip('\n\r')
        return (ID,PSK)
    return None
    
