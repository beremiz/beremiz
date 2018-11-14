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


zeroconf_service_type = '_PYRO._tcp.local.'
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
        import connectors.PYRO.PSK_Adapter
        schemename = "PYROLOCPSK"
        url, ID = location.split('#') #TODO fix exception when # not found
        # load PSK from project
        secpath = os.path.join(str(confnodesroot.ProjectPath), 'psk', ID+'.secret')
        if not os.path.exists(secpath):
            confnodesroot.logger.write_error(
                'Error: Pre-Shared-Key Secret in %s is missing!\n' % secpath)
            return None
        secret = open(secpath).read().partition(':')[2].rstrip('\n\r')
        Pyro.config.PYROPSK = (secret, ID)
        # strip ID from URL, so that pyro can understand it.
        location = url
    else:
        schemename = "PYROLOC"

    if location.find(zeroconf_service_type) != -1:
        try:
            from zeroconf import Zeroconf
            r = Zeroconf()
            i = r.get_service_info(zeroconf_service_type, location)
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
    except Exception,e:
        confnodesroot.logger.write_error(_("Connection to '%s' failed with exception '%s'\n") % (location, str(e)))
        #confnodesroot.logger.write_error(traceback.format_exc())
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
    IDPSK = PyroCatcher(RemotePLCObjectProxy.GetPLCID)()
    if IDPSK is None:
        confnodesroot.logger.write_error(_("Cannot get PLC ID - connection failed.\n"))
        return None

    if servicetype != "PYROS":
        ID,PSK = IDPSK
        secdir = os.path.join(str(confnodesroot.ProjectPath), 'psk')
        if not os.path.exists(secdir):
            os.mkdir(secdir)
        secpath = os.path.join(secdir, ID+'.secret')
        with open(secpath, 'w') as f:
            f.write(ID+":"+PSK)

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

