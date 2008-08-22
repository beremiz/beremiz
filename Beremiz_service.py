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

import os, sys, getopt

def usage():
    print """
Usage of Beremiz PLC execution service :\n
%s {[-n name] [-i ip] [-p port]|-h|--help} working_dir
           -n        - zeroconf service name
           -i        - ip of interface to bind to (x.x.x.x)
           -p        - port number
           -h        - print this help text and quit
           
           working_dir - directory where are stored PLC files
"""%sys.argv[0]

try:
    opts, args = getopt.getopt(sys.argv[1:], "i:p:n:h")
except getopt.GetoptError, err:
    # print help information and exit:
    print str(err) # will print something like "option -a not recognized"
    usage()
    sys.exit(2)

# default values
ip = ""
port = 3000
name = os.environ[{
     "linux2":"USER",
     "win32":"USERNAME",
     }.get(sys.platform, "USER")]

for o, a in opts:
    if o == "-h":
        usage()
        sys.exit()
    elif o == "-i":
        if len(a.split(".")) == 4 or a == "localhost":
            ip = a
    elif o == "-p":
        # port: port that the service runs on
        port = int(a)
    elif o == "-n":
        name = a
    else:
        usage()
        sys.exit()

if len(args) > 1:
    usage()
    sys.exit()
elif len(args) == 1:
    WorkingDir = args[0]
elif len(args) == 0:
    WorkingDir = os.getcwd()
    args=[WorkingDir]

from runtime import PLCObject, ServicePublisher
import Pyro.core as pyro

if not os.path.isdir(WorkingDir):
    os.mkdir(WorkingDir)


pyro.initServer()
daemon=pyro.Daemon(host=ip, port=port)
uri = daemon.connect(PLCObject(WorkingDir, daemon, args),"PLCObject")

print "The daemon runs on port :",daemon.port
print "The object's uri is :",uri
print "The working directory :",WorkingDir

# Configure and publish service
# Not publish service if localhost in address params
if ip != "localhost" and ip != "127.0.0.1":    
    print "Publish service on local network"
    service = ServicePublisher.ServicePublisher(name, ip, port)

sys.stdout.flush()

daemon.requestLoop()
