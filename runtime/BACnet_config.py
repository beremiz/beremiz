#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz runtime.
#
# Copyright (C) 2020: Mario de Sousa
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


import json
import os
import ctypes

from formless import annotate, webform



# reference to the PLCObject in runtime/PLCObject.py
# PLCObject is a singleton, created in runtime/__init__.py
_plcobj = None

# reference to the Nevow web server (a.k.a as NS in Beremiz_service.py)
# (Note that NS will reference the NevowServer.py _module_, and not an object/class)
_NS = None


# WorkingDir: the directory on which Beremiz_service.py is running, and where 
#             all the files downloaded to the PLC get stored
_WorkingDir = None


# Will contain references to the C functions 
# (implemented in beremiz/bacnet/runtime/server.c)
# used to get/set the BACnet specific configuration paramters
GetParamFuncs = {}
SetParamFuncs = {}


# Upon PLC load, this Dictionary is initialised with the BACnet configuration
# hardcoded in the C file
# (i.e. the configuration inserted in Beremiz IDE when project was compiled)
_DefaultConfiguration = None


# Dictionary that contains the BACnet configuration currently being shown
# on the web interface
# This configuration will almost always be identical to the current
# configuration in the PLC (i.e., the current state stored in the 
# C variables in the .so file).
# The configuration viewed on the web will only be different to the current 
# configuration when the user edits the configuration, and when
# the user asks to save the edited configuration but it contains an error.
_WebviewConfiguration = None


# Dictionary that stores the BACnet configuration currently stored in a file
# Currently only used to decide whether or not to show the "Delete" button on the
# web interface (only shown if _SavedConfiguration is not None)
_SavedConfiguration = None


# File to which the new BACnet configuration gets stored on the PLC
# Note that the stored configuration is likely different to the
# configuration hardcoded in C generated code (.so file), so
# this file should be persistent across PLC reboots so we can
# re-configure the PLC (change values of variables in .so file)
# before it gets a chance to start running
#
#_BACnetConfFilename = None
_BACnetConfFilename = "/tmp/BeremizBACnetConfig.json"




class BN_StrippedString(annotate.String):
    def __init__(self, *args, **kwargs):
        annotate.String.__init__(self, strip = True, *args, **kwargs)



BACnet_parameters = [
    #    param. name             label                                            ctype type      annotate type
    # (C code var name)         (used on web interface)                          (C data type)    (web data type)
    #                                                                                             (annotate.String,
    #                                                                                              annotate.Integer, ...)
    ("network_interface"      , _("Network Interface")                         , ctypes.c_char_p, BN_StrippedString),
    ("port_number"            , _("UDP Port Number")                           , ctypes.c_char_p, BN_StrippedString),
    ("comm_control_passwd"    , _("BACnet Communication Control Password")     , ctypes.c_char_p, annotate.String),
    ("device_id"              , _("BACnet Device ID")                          , ctypes.c_int,    annotate.Integer),
    ("device_name"            , _("BACnet Device Name")                        , ctypes.c_char_p, annotate.String),
    ("device_location"        , _("BACnet Device Location")                    , ctypes.c_char_p, annotate.String),
    ("device_description"     , _("BACnet Device Description")                 , ctypes.c_char_p, annotate.String),
    ("device_appsoftware_ver" , _("BACnet Device Application Software Version"), ctypes.c_char_p, annotate.String)
    ]






def _CheckPortnumber(port_number):
    """ check validity of the port number """
    try:
        portnum = int(port_number)
        if (portnum < 0) or (portnum > 65535):
           raise Exception
    except Exception:    
        return False
        
    return True    
    


def _CheckDeviceID(device_id):
    """ 
    # check validity of the Device ID 
    # NOTE: BACnet device (object) IDs are 22 bits long (not counting the 10 bits for the type ID)
    #       so the Device instance ID is limited from 0 to 22^2-1 = 4194303
    #       However, 4194303 is reserved for special use (similar to NULL pointer), so last
    #       valid ID becomes 4194302
    """
    try:
        devid = int(device_id)
        if (devid < 0) or (devid > 4194302):
            raise Exception
    except Exception:    
        return False
        
    return True    





def _CheckConfiguration(BACnetConfig):
    res = True    
    res = res and _CheckPortnumber(BACnetConfig["port_number"])
    res = res and _CheckDeviceID  (BACnetConfig["device_id"])
    return res



def _CheckWebConfiguration(BACnetConfig):
    res = True
    
    # check the port number
    if not _CheckPortnumber(BACnetConfig["port_number"]):
        raise annotate.ValidateError(
            {"port_number": "Invalid port number: " + str(BACnetConfig["port_number"])},
            _("BACnet configuration error:"))
        res = False
    
    if not _CheckDeviceID(BACnetConfig["device_id"]):
        raise annotate.ValidateError(
            {"device_id": "Invalid device ID: " + str(BACnetConfig["device_id"])},
            _("BACnet configuration error:"))
        res = False
        
    return res






def _SetSavedConfiguration(BACnetConfig):
    """ Stores in a file a dictionary containing the BACnet parameter configuration """
    with open(os.path.realpath(_BACnetConfFilename), 'w') as f:
        json.dump(BACnetConfig, f, sort_keys=True, indent=4)
    global _SavedConfiguration
    _SavedConfiguration = BACnetConfig


def _DelSavedConfiguration():
    """ Deletes the file cotaining the persistent BACnet configuration """
    if os.path.exists(_BACnetConfFilename):
        os.remove(_BACnetConfFilename)


def _GetSavedConfiguration():
    """
    # Returns a dictionary containing the BACnet parameter configuration
    # that was last saved to file. If no file exists, then return None
    """
    try:
        #if os.path.isfile(_BACnetConfFilename):
        saved_config = json.load(open(_BACnetConfFilename))
    except Exception:    
        return None

    if _CheckConfiguration(saved_config):
        return saved_config
    else:
        return None


def _GetPLCConfiguration():
    """
    # Returns a dictionary containing the current BACnet parameter configuration
    # stored in the C variables in the loaded PLC (.so file)
    """
    current_config = {}
    for par_name, x1, x2, x3 in BACnet_parameters:
        value = GetParamFuncs[par_name]()
        if value is not None:
            current_config[par_name] = value
    
    return current_config


def _SetPLCConfiguration(BACnetConfig):
    """
    # Stores the BACnet parameter configuration into the
    # the C variables in the loaded PLC (.so file)
    """
    for par_name in BACnetConfig:
        value = BACnetConfig[par_name]
        #_plcobj.LogMessage("BACnet web server extension::_SetPLCConfiguration()  Setting "
        #                       + par_name + " to " + str(value) )
        if value is not None:
            SetParamFuncs[par_name](value)
    # update the configuration shown on the web interface
    global _WebviewConfiguration 
    _WebviewConfiguration = _GetPLCConfiguration()



def _GetWebviewConfigurationValue(ctx, argument):
    """
    # Callback function, called by the web interface (NevowServer.py)
    # to fill in the default value of each parameter
    """
    try:
        return _WebviewConfiguration[argument.name]
    except Exception:
        return ""


# The configuration of the web form used to see/edit the BACnet parameters
webFormInterface = [(name, web_dtype (label=web_label, default=_GetWebviewConfigurationValue)) 
                    for name, web_label, c_dtype, web_dtype in BACnet_parameters]



def _updateWebInterface():
    """
    # Add/Remove buttons to/from the web interface depending on the current state
    #
    #  - If there is a saved state => add a delete saved state button
    """

    # Add a "Delete Saved Configuration" button if there is a saved configuration!
    if _SavedConfiguration is None:
        _NS.ConfigurableSettings.delSettings("BACnetConfigDelSaved")
    else:
        _NS.ConfigurableSettings.addSettings(
            "BACnetConfigDelSaved",                   # name
            _("BACnet Configuration"),                # description
            [],                                       # fields  (empty, no parameters required!)
            _("Delete Configuration Stored in Persistent Storage"), # button label
            OnButtonDel,                              # callback    
            "BACnetConfigParm")                       # Add after entry xxxx


def OnButtonSave(**kwargs):
    """
    # Function called when user clicks 'Save' button in web interface
    # The function will configure the BACnet plugin in the PLC with the values
    # specified in the web interface. However, values must be validated first!
    """

    #_plcobj.LogMessage("BACnet web server extension::OnButtonSave()  Called")
    
    newConfig = {}
    for par_name, x1, x2, x3 in BACnet_parameters:
        value = kwargs.get(par_name, None)
        if value is not None:
            newConfig[par_name] = value

    global _WebviewConfiguration
    _WebviewConfiguration = newConfig
    
    # First check if configuration is OK.
    if not _CheckWebConfiguration(newConfig):
        return

    # store to file the new configuration so that 
    # we can recoup the configuration the next time the PLC
    # has a cold start (i.e. when Beremiz_service.py is retarted)
    _SetSavedConfiguration(newConfig)

    # Configure PLC with the current BACnet parameters
    _SetPLCConfiguration(newConfig)

    # File has just been created => Delete button must be shown on web interface!
    _updateWebInterface()




def OnButtonDel(**kwargs):
    """
    # Function called when user clicks 'Delete' button in web interface
    # The function will delete the file containing the persistent
    # BACnet configution
    """

    # Delete the file
    _DelSavedConfiguration()
    # Set the current configuration to the default (hardcoded in C)
    _SetPLCConfiguration(_DefaultConfiguration)
    # Reset global variable
    global _SavedConfiguration
    _SavedConfiguration = None
    # File has just been deleted => Delete button on web interface no longer needed!
    _updateWebInterface()



def OnButtonShowCur(**kwargs):
    """
    # Function called when user clicks 'Show Current PLC Configuration' button in web interface
    # The function will load the current PLC configuration into the web form
    """
    
    global _WebviewConfiguration
    _WebviewConfiguration = _GetPLCConfiguration()
    # File has just been deleted => Delete button on web interface no longer needed!
    _updateWebInterface()




def OnLoadPLC():
    """
    # Callback function, called (by PLCObject.py) when a new PLC program
    # (i.e. XXX.so file) is transfered to the PLC runtime
    # and oaded into memory
    """

    #_plcobj.LogMessage("BACnet web server extension::OnLoadPLC() Called...")

    if _plcobj.PLClibraryHandle is None:
        # PLC was loaded but we don't have access to the library of compiled code (.so lib)?
        # Hmm... This shold never occur!! 
        return  
    
    # Get the location (in the Config. Node Tree of Beremiz IDE) the BACnet plugin
    # occupies in the currently loaded PLC project (i.e., the .so file)
    # If the "__bacnet_plugin_location" C variable is not present in the .so file,
    # we conclude that the currently loaded PLC does not have the BACnet plugin
    # included (situation (2b) described above init())
    try:
        location = ctypes.c_char_p.in_dll(_plcobj.PLClibraryHandle, "__bacnet_plugin_location")
    except Exception:
        # Loaded PLC does not have the BACnet plugin => nothing to do
        #   (i.e. do _not_ configure and make available the BACnet web interface)
        return

    # Map the get/set functions (written in C code) we will be using to get/set the configuration parameters
    for name, web_label, c_dtype, web_dtype in BACnet_parameters:
        GetParamFuncName = "__bacnet_" + location.value + "_get_ConfigParam_" + name
        SetParamFuncName = "__bacnet_" + location.value + "_set_ConfigParam_" + name
        
        GetParamFuncs[name]          = getattr(_plcobj.PLClibraryHandle, GetParamFuncName)
        GetParamFuncs[name].restype  = c_dtype
        GetParamFuncs[name].argtypes = None
        
        SetParamFuncs[name]          = getattr(_plcobj.PLClibraryHandle, SetParamFuncName)
        SetParamFuncs[name].restype  = None
        SetParamFuncs[name].argtypes = [c_dtype]

    # Default configuration is the configuration done in Beremiz IDE
    # whose parameters get hardcoded into C, and compiled into the .so file
    # We read the default configuration from the .so file before the values
    # get changed by the user using the web server, or by the call (further on)
    # to _SetPLCConfiguration(SavedConfiguration)
    global _DefaultConfiguration 
    _DefaultConfiguration = _GetPLCConfiguration()
    
    # Show the current PLC configuration on the web interface        
    global _WebviewConfiguration
    _WebviewConfiguration = _GetPLCConfiguration()
 
    # Read from file the last used configuration, which is likely
    # different to the hardcoded configuration.
    # We Reset the current configuration (i.e., the config stored in the 
    # variables of .so file) to this saved configuration
    # so the PLC will start off with this saved configuration instead
    # of the hardcoded (in Beremiz C generated code) configuration values.
    #
    # Note that _SetPLCConfiguration() will also update 
    # _WebviewConfiguration , if necessary.
    global _SavedConfiguration
    _SavedConfiguration  = _GetSavedConfiguration()
    if _SavedConfiguration is not None:
        if _CheckConfiguration(_SavedConfiguration):
            _SetPLCConfiguration(_SavedConfiguration)
            
    # Configure the web interface to include the BACnet config parameters
    _NS.ConfigurableSettings.addSettings(
        "BACnetConfigParm",                # name
        _("BACnet Configuration"),         # description
        webFormInterface,                  # fields
        _("Save Configuration to Persistent Storage"),  # button label
        OnButtonSave)                      # callback    
    
    # Add a "View Current Configuration" button 
    _NS.ConfigurableSettings.addSettings(
        "BACnetConfigViewCur",                    # name
        _("BACnet Configuration"),                # description
        [],                                       # fields  (empty, no parameters required!)
        _("Show Current PLC Configuration"),      # button label
        OnButtonShowCur)                          # callback    

    # Add the Delete button to the web interface, if required
    _updateWebInterface()





def OnUnLoadPLC():
    """
    # Callback function, called (by PLCObject.py) when a PLC program is unloaded from memory
    """

    #_plcobj.LogMessage("BACnet web server extension::OnUnLoadPLC() Called...")
    
    # Delete the BACnet specific web interface extensions
    # (Safe to ask to delete, even if it has not been added!)
    _NS.ConfigurableSettings.delSettings("BACnetConfigParm")
    _NS.ConfigurableSettings.delSettings("BACnetConfigViewCur")  
    _NS.ConfigurableSettings.delSettings("BACnetConfigDelSaved")  
    GetParamFuncs = {}
    SetParamFuncs = {}
    _WebviewConfiguration = None
    _SavedConfiguration   = None




# The Beremiz_service.py service, along with the integrated web server it launches
# (i.e. Nevow web server, in runtime/NevowServer.py), will go through several states
# once started:
#  (1) Web server is started, but no PLC is loaded
#  (2) PLC is loaded (i.e. the PLC compiled code is loaded)
#         (a) The loaded PLC includes the BACnet plugin
#         (b) The loaded PLC does not have the BACnet plugin
#
# During (1) and (2a):
#     we configure the web server interface to not have the BACnet web configuration extension
# During (2b) 
#     we configure the web server interface to include the BACnet web configuration extension
#
# plcobj    : reference to the PLCObject defined in PLCObject.py
# NS        : reference to the web server (i.e. the NevowServer.py module)
# WorkingDir: the directory on which Beremiz_service.py is running, and where 
#             all the files downloaded to the PLC get stored, including
#             the .so file with the compiled C generated code
def init(plcobj, NS, WorkingDir):
    #plcobj.LogMessage("BACnet web server extension::init(plcobj, NS, " + WorkingDir + ") Called")
    global _WorkingDir
    _WorkingDir = WorkingDir
    global _plcobj
    _plcobj = plcobj
    global _NS
    _NS = NS
    global _BACnetConfFilename
    if _BACnetConfFilename is None:
        _BACnetConfFilename = os.path.join(WorkingDir, "BACnetConfig.json")
    
    _plcobj.RegisterCallbackLoad  ("BACnet_Settins_Extension", OnLoadPLC)
    _plcobj.RegisterCallbackUnLoad("BACnet_Settins_Extension", OnUnLoadPLC)
    OnUnLoadPLC() # init is called before the PLC gets loaded...  so we make sure we have the correct state
