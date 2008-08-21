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
    print """
Usage of Beremiz PLC execution service :\n
%s {[-a ip] [-d path] [-p port]|-h|--help}
           -a, --address            - authorized ip to connect (x.x.x.x)
           -d, --directory path     - set the working directory
           -p, --port port number   - set the port number
           -h, --help               - print this help text and quit
"""%sys.argv[0]

try:
    opts, args = getopt.getopt(sys.argv[1:], "a:d:p:h", ["directory=", "port=", "help"])
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
WorkingDir = os.getcwd()
ip = ""
port = 3000

for o, a in opts:
    if o in ("-h", "--help"):
        usage()
        sys.exit()
    elif o in ("-a", "--address"):
        if len(a.split(".")) == 4 or a == "localhost":
            ip = a
    elif o in ("-d", "--directory"):
        # overwrite default working directory
        WorkingDir = a
    elif o in ("-p", "--port"):
        # port: port that the service runs on
        port = int(a)
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

# properties: dictionary of properties (or a string holding the bytes for the text field)
serviceproperties = {'description':'Remote control for PLC'}

pyro.initServer()
daemon=pyro.Daemon(host=ip, port=port)
uri = daemon.connect(PLCObject(WorkingDir, daemon),"PLCObject")

print "The daemon runs on port :",daemon.port
print "The object's uri is :",uri
print "The working directory :",WorkingDir

# Configure and publish service
# Not publish service if localhost in address params
if ip != "localhost" and ip != "127.0.0.1":    
    # No ip params -> get host ip
    if ip == "":
        ip_32b = socket.inet_aton(gethostaddr(ip))
    else:
        ip_32b = ip
    print "Publish service on local network"
    service = ServicePublisher.PublishService()
    service.ConfigureService(type, name, ip_32b, port, serviceproperties)
    service.PublishService()

daemon.requestLoop()
