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

import Zeroconf, socket

# type: fully qualified service type name
service_type = '_PYRO._tcp.local.'

# properties: dictionary of properties (or a string holding the bytes for the text field)
serviceproperties = {'description':'Beremiz remote PLC'}

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


def ServicePublisher(name, ip, port):

        # name: fully qualified service name
        service_name = 'Beremiz_%s.%s'%(name,service_type)

        # No ip params -> get host ip
        if ip == "":
            ip = gethostaddr()

        print "Mon IP est :"+ip

        server = Zeroconf.Zeroconf(ip)

        # address: IP address as unsigned short, network byte order
        ip_32b = socket.inet_aton(ip)

        server.registerService(
             Zeroconf.ServiceInfo(service_type,
                                  service_name,
                                  ip_32b,
                                  port,
                                  properties = serviceproperties))
        
        return server