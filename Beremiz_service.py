#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os, sys, getopt, socket

def usage():
    print "\nUsage of Beremiz PLC execution service :"
    print "\n   %s [PLC path]\n"%sys.argv[0]

try:
    opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
except getopt.GetoptError:
    # print help information and exit:
    usage()
    sys.exit(2)

for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()

if len(args) > 1:
    usage()
    sys.exit()
elif len(args) == 1:
    WorkingDir = args[0]
elif len(args) == 0:
    WorkingDir = os.getcwd()
else:
    usage()
    sys.exit()

from runtime import PLCObject, ServicePublisher
import Pyro.core as pyro

if not os.path.isdir(WorkingDir):
    os.mkdir(WorkingDir)

# type: fully qualified service type name
type = '_PYRO._tcp.local.'
# name: fully qualified service name
name = 'First test.%s'%(type)
# address: IP address as unsigned short, network byte order

def gethostaddr(dst = '224.0.1.41'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((dst, 7))
        (host, port) = s.getsockname()
        s.close()
        if host != '0.0.0.0':
            return host
    except error:
        pass
    return socket.gethostbyname(socket.gethostname())

ip = gethostaddr()
# port: port that the service runs on
port = 3000
# properties: dictionary of properties (or a string holding the bytes for the text field)
serviceproperties = {'description':'Remote control for PLC'}

pyro.initServer()
daemon=pyro.Daemon(host=ip, port=port)
uri = daemon.connect(PLCObject(WorkingDir, daemon),"PLCObject")
print "The daemon runs on port :",daemon.port
print "The object's uri is :",uri
print "The working directory :",WorkingDir
print "Publish service on local network"

ip_32b = socket.inet_aton(ip)
# Configure and publish service
service = ServicePublisher.PublishService()
service.ConfigureService(type, name, ip_32b, port, serviceproperties)
service.PublishService()

daemon.requestLoop()
