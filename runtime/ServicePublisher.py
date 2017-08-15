#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING.Runtime file for copyrights details.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA

import socket
import threading
from util import Zeroconf

service_type = '_PYRO._tcp.local.'


class ServicePublisher():
    def __init__(self):
        # type: fully qualified service type name
        self.serviceproperties = {'description': 'Beremiz remote PLC'}

        self.name = None
        self.ip_32b = None
        self.port = None
        self.server = None
        self.service_name = None
        self.retrytimer = None

    def RegisterService(self, name, ip, port):
        try:
            self._RegisterService(name, ip, port)
        except Exception, e:
            self.retrytimer = threading.Timer(2, self.RegisterService, [name, ip, port])
            self.retrytimer.start()

    def _RegisterService(self, name, ip, port):
        # name: fully qualified service name
        self.service_name = 'Beremiz_%s.%s' % (name, service_type)
        self.name = name
        self.port = port

        self.server = Zeroconf.Zeroconf(ip)
        print "MDNS brodcasting on :"+ip

        if ip == "0.0.0.0":
            ip = self.gethostaddr()
        print "MDNS brodcasted service address :"+ip
        self.ip_32b = socket.inet_aton(ip)

        self.server.registerService(
             Zeroconf.ServiceInfo(service_type,
                                  self.service_name,
                                  self.ip_32b,
                                  self.port,
                                  properties=self.serviceproperties))
        self.retrytimer = None

    def UnRegisterService(self):
        if self.retrytimer is not None:
            self.retrytimer.cancel()

        self.server.unregisterService(
                                      Zeroconf.ServiceInfo(service_type,
                                                           self.service_name,
                                                           self.ip_32b,
                                                           self.port,
                                                           properties=self.serviceproperties))
        self.server.close()
        self.server = None

    def gethostaddr(self, dst='224.0.1.41'):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((dst, 7))
            (host, port) = s.getsockname()
            s.close()
            if host != '0.0.0.0':
                return host
        except Exception, e:
            pass
        return socket.gethostbyname(socket.gethostname())
