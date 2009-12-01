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
import traceback


def LPC_connector_factory(uri, pluginsroot):
    """
    This returns the connector to LPC style PLCobject
    """
    pluginsroot.logger.write(_("Connecting to URI : %s\n")%uri)

    servicetype, location = uri.split("://")
    
    # Try to get the proxy object
    try :
        # TODO: Open Serial Port
        RemotePLCObjectProxy = LPCObject(pluginsroot) # LPC_PLCObject_Proxy
    except Exception, msg:
        pluginsroot.logger.write_error(_("Couldn't connect !\n"))
        pluginsroot.logger.write_error(traceback.format_exc())
        return None

    def LPCCatcher(func, default=None):
        """
        A function that catch a pyserial exceptions, write error to logger
        and return defaul value when it happen
        """
        def catcher_func(*args,**kwargs):
            try:
                return func(*args,**kwargs)
            except Exception,e:
                #pluginsroot.logger.write_error(traceback.format_exc())
                pluginsroot.logger.write_error(str(e)+"\n")
                pluginsroot._connector = None
                return default
        return catcher_func

    # Check connection is effective. 
    # lambda is for getattr of GetPLCstatus to happen inside catcher
    if LPCCatcher(lambda:RemotePLCObjectProxy.GetPLCstatus())() == None:
        pluginsroot.logger.write_error(_("Cannot get PLC status - connection failed.\n"))
        return None


    class LPCProxy:
        """
        A Serial proxy class to handle Beremiz Pyro interface specific behavior.
        And to put LPC exception catcher in between caller and pyro proxy
        """
        def _LPCGetTraceVariables(self):
            return self.RemotePLCObjectProxy.GetTraceVariables()
        GetTraceVariables = LPCCatcher(_LPCGetTraceVariables,("Broken",None,None))

        def _LPCGetPLCstatus(self):
            return RemotePLCObjectProxy.GetPLCstatus()
        GetPLCstatus = LPCCatcher(_LPCGetPLCstatus, "Broken")
        
        def __getattr__(self, attrName):
            member = self.__dict__.get(attrName, None)
            if member is None:
                def my_local_func(*args,**kwargs):
                    return RemotePLCObjectProxy.__getattr__(attrName)(*args,**kwargs)
                member = LPCCatcher(my_local_func, None)
                self.__dict__[attrName] = member
            return member

    return LPCProxy()
    

