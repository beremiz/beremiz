#!/usr/bin/env python
# -*- coding: utf-8 -*-
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
import Pyro.core as pyro
from Pyro.errors import PyroError
import traceback
from time import sleep
import copy

def PYRO_connector_factory(uri, pluginsroot):
    """
    This returns the connector to Pyro style PLCobject
    """
    pluginsroot.logger.write("Connecting to URI : %s\n"%uri)

    servicetype, location = uri.split("://")
    
    # Try to get the proxy object
    try :
        RemotePLCObjectProxy = pyro.getAttrProxyForURI("PYROLOC://"+location+"/PLCObject")
    except Exception, msg:
        pluginsroot.logger.write_error("Wrong URI, please check it !\n")
        pluginsroot.logger.write_error(traceback.format_exc())
        return None

    def PyroCatcher(func, default=None):
        """
        A function that catch a pyro exceptions, write error to logger
        and return defaul value when it happen
        """
        def catcher_func(*args,**kwargs):
            try:
                return func(*args,**kwargs)
            except PyroError,e:
                #pluginsroot.logger.write_error(traceback.format_exc())
                pluginsroot.logger.write_error(str(e)+"\n")
                pluginsroot._Disconnect()
                return default
        return catcher_func

    # Check connection is effective. 
    # lambda is for getattr of GetPLCstatus to happen inside catcher
    if PyroCatcher(lambda:RemotePLCObjectProxy.GetPLCstatus())() == None:
        pluginsroot.logger.write_error("Cannot get PLC status - connection failed.\n")
        return None


    class PyroProxyProxy:
        """
        A proxy proxy class to handle Beremiz Pyro interface specific behavior.
        And to put pyro exception catcher in between caller and pyro proxy
        """
        def __init__(self):
            # for safe use in from debug thread, must create a copy
            self.RemotePLCObjectProxyCopy = None

        def GetPyroProxy(self):
            """
            This func returns the real Pyro Proxy.
            Use this if you musn't keep reference to it.
            """
            return RemotePLCObjectProxy

        def _PyroStartPLC(self, *args, **kwargs):
            """
            pluginsroot._connector.GetPyroProxy() is used 
            rather than RemotePLCObjectProxy because
            object is recreated meanwhile, 
            so we must not keep ref to it here
            """
            if pluginsroot._connector.GetPyroProxy().GetPLCstatus() == "Dirty":
                """
                Some bad libs with static symbols may polute PLC
                ask runtime to suicide and come back again
                """
                pluginsroot.logger.write("Force runtime reload\n")
                pluginsroot._connector.GetPyroProxy().ForceReload()
                pluginsroot._Disconnect()
                # let remote PLC time to resurect.(freeze app)
                sleep(0.5)
                pluginsroot._Connect()
            self.RemotePLCObjectProxyCopy = copy.copy(pluginsroot._connector.GetPyroProxy())
            return pluginsroot._connector.GetPyroProxy().StartPLC(*args, **kwargs)
        StartPLC = PyroCatcher(_PyroStartPLC, False)


        def _PyroGetTraceVariables(self):
            """
            for safe use in from debug thread, must use the copy
            """
            if self.RemotePLCObjectProxyCopy is not None and self.RemotePLCObjectProxyCopy.GetPLCstatus() == "Started":
                return self.RemotePLCObjectProxyCopy.GetTraceVariables()
            else:
                return None,None
        GetTraceVariables = PyroCatcher(_PyroGetTraceVariables,(None,None))

        
        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                def my_local_func(*args,**kwargs):
                    return RemotePLCObjectProxy.__getattr__(attrName)(*args,**kwargs)
                member = PyroCatcher(my_local_func, None)
                self.__dict__[attrName] = member
            return member

    return PyroProxyProxy()
    

