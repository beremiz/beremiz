#!/usr/bin/env python
################################################################################
#                                                                              #
#   This program is free software: you can redistribute it and/or modify       #
#   it under the terms of the GNU General Public License as published by       #
#   the Free Software Foundation, either version 3 of the License, or          #
#   (at your option) any later version.                                        #
#                                                                              #
#   This program is distributed in the hope that it will be useful,            #
#   but WITHOUT ANY WARRANTY; without even the implied warranty of             #
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the              #
#   GNU General Public License for more details.                               #
#                                                                              #
#   You should have received a copy of the GNU General Public License          #
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.      #
#                                                                              #
################################################################################

import cwiid

## Configuration
wiimote_hwaddr = '' # Use your address to speed up the connection proccess
#wiimote_hwaddr = '00:19:1D:5D:5D:DC'

last_point = (0,0)
btA = 0
btB = 0

def cback(messages):
    '''Wiimote callback managing method
    Recieves a message list, each element is different, see the libcwiid docs'''
    global btA, btB, last_point
    #print "wiimote callback"
    for msg in messages:
        if msg[0] == cwiid.MESG_IR:
            # msg is of the form (cwiid.MESG_IR, (((x, y), size) or None * 4))
            for p in msg[1]:
                if p:
                    pos = p['pos'][0], p['pos'][1] # point is mirrored
                    #s = max(p['size'], 1)
                        
                    last_point = tuple(pos)
                    #print "last_point",last_point
        elif msg[0] == cwiid.MESG_BTN:
            # msg is of the form (cwiid.MESG_BTN, cwiid.BTN_*)
            if msg[1] & cwiid.BTN_A:
                btA = 1
                #print "btA = 1"
            else:
                btA = 0
                #print "btA = 0"
                
            if msg[1] & cwiid.BTN_B:
                btB = 1
                #print "btB = 1"
            else:
                btB = 0
                #print "btB = 0"
        #elif msg[0] == cwiid.MESG_STATUS:
        #    # msg is of the form (cwiid.MESG_BTN, { 'status' : value, ... })
        #    print msg[1]

try:
#if False:
    wm = cwiid.Wiimote(wiimote_hwaddr)
    if wm is not None:
        # each message will contain info about ir and buttons
        wm.rpt_mode = cwiid.RPT_IR | cwiid.RPT_BTN # | cwiid.RPT_STATUS
        # tell cwiid to use the callback interface and allways send button events
        wm.enable(cwiid.FLAG_MESG_IFC
                  #| cwiid.FLAG_NONBLOCK
                  | cwiid.FLAG_REPEAT_BTN)

        # specify wich function will manage messages AFTER the other settings
        wm.mesg_callback = cback

        # quick check on the wiimote
        print "Got Wiimote!"
        st = wm.state
        for e in st:
            print str(e).ljust(8), ">", st[e]
except:
#else:
    print "Error with wiimote " + str(wiimote_hwaddr)
            
def _runtime_cleanup():
    print "_runtime_cleanup() Called"
    runing = 0
    if wm is not None:
        wm.close()
