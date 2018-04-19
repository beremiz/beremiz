#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


from __future__ import absolute_import
from __future__ import print_function
import traceback
from time import sleep
import copy
import socket
import os.path

import Pyro
import Pyro.core
import Pyro.util
from Pyro.errors import PyroError


service_type = '_PYRO._tcp.local.'
# this module attribute contains a list of DNS-SD (Zeroconf) service types
# supported by this connector confnode.
#
# for connectors that do not support DNS-SD, this attribute can be omitted
# or set to an empty list.


def PYRO_connector_factory(uri, confnodesroot):
    """
    This returns the connector to Pyro style PLCobject
    """
    confnodesroot.logger.write(_("PYRO connecting to URI : %s\n") % uri)

    servicetype, location = uri.split("://")
    if servicetype == "PYROS":
        schemename = "PYROLOCSSL"
        # Protect against name->IP substitution in Pyro3
        Pyro.config.PYRO_DNS_URI = True
        # Beware Pyro lib need str path, not unicode
        # don't rely on PYRO_STORAGE ! see documentation
        Pyro.config.PYROSSL_CERTDIR = os.path.abspath(str(confnodesroot.ProjectPath) + '/certs')
        if not os.path.exists(Pyro.config.PYROSSL_CERTDIR):
            confnodesroot.logger.write_error(
                'Error : the directory %s is missing for SSL certificates (certs_dir).'
                'Please fix it in your project.\n' % Pyro.config.PYROSSL_CERTDIR)
            return None
        else:
            confnodesroot.logger.write(_("PYRO using certificates in '%s' \n")
                                       % (Pyro.config.PYROSSL_CERTDIR))
        Pyro.config.PYROSSL_CERT = "client.crt"
        Pyro.config.PYROSSL_KEY = "client.key"

        # Ugly Monkey Patching
        def _gettimeout(self):
            return self.timeout

        def _settimeout(self, timeout):
            self.timeout = timeout
        from M2Crypto.SSL import Connection  # pylint: disable=import-error
        Connection.timeout = None
        Connection.gettimeout = _gettimeout
        Connection.settimeout = _settimeout
        # M2Crypto.SSL.Checker.WrongHost: Peer certificate commonName does not
        # match host, expected 127.0.0.1, got server
        Connection.clientPostConnectionCheck = None
    else:
        schemename = "PYROLOC"
    if location.find(service_type) != -1:
        try:
            from zeroconf import Zeroconf
            r = Zeroconf()
            i = r.get_service_info(service_type, location)
            if i is None:
                raise Exception("'%s' not found" % location)
            ip = str(socket.inet_ntoa(i.address))
            port = str(i.port)
            newlocation = ip + ':' + port
            confnodesroot.logger.write(_("'{a1}' is located at {a2}\n").format(a1=location, a2=newlocation))
            location = newlocation
            r.close()
        except Exception:
            confnodesroot.logger.write_error(_("MDNS resolution failure for '%s'\n") % location)
            confnodesroot.logger.write_error(traceback.format_exc())
            return None

    # Try to get the proxy object
    try:
        RemotePLCObjectProxy = Pyro.core.getAttrProxyForURI(schemename + "://" + location + "/PLCObject")
    except Exception:
        confnodesroot.logger.write_error(_("Connection to '%s' failed.\n") % location)
        confnodesroot.logger.write_error(traceback.format_exc())
        return None

    def PyroCatcher(func, default=None):
        """
        A function that catch a Pyro exceptions, write error to logger
        and return default value when it happen
        """
        def catcher_func(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Pyro.errors.ConnectionClosedError, e:
                confnodesroot.logger.write_error(_("Connection lost!\n"))
                confnodesroot._SetConnector(None)
            except Pyro.errors.ProtocolError, e:
                confnodesroot.logger.write_error(_("Pyro exception: %s\n") % e)
            except Exception, e:
                # confnodesroot.logger.write_error(traceback.format_exc())
                errmess = ''.join(Pyro.util.getPyroTraceback(e))
                confnodesroot.logger.write_error(errmess + "\n")
                print(errmess)
                confnodesroot._SetConnector(None)
            return default
        return catcher_func

    # Check connection is effective.
    # lambda is for getattr of GetPLCstatus to happen inside catcher
    if PyroCatcher(RemotePLCObjectProxy.GetPLCstatus)() is None:
        confnodesroot.logger.write_error(_("Cannot get PLC status - connection failed.\n"))
        return None

    _special_return_funcs = {
        "StartPLC": False,
        "GetTraceVariables": ("Broken", None),
        "GetPLCstatus": ("Broken", None),
        "RemoteExec": (-1, "RemoteExec script failed!")
    }

    class PyroProxyProxy(object):
        """
        A proxy proxy class to handle Beremiz Pyro interface specific behavior.
        And to put Pyro exception catcher in between caller and Pyro proxy
        """
        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                def my_local_func(*args, **kwargs):
                    return RemotePLCObjectProxy.__getattr__(attrName)(*args, **kwargs)
                member = PyroCatcher(my_local_func, _special_return_funcs.get(attrName, None))
                self.__dict__[attrName] = member
            return member

    return PyroProxyProxy()
