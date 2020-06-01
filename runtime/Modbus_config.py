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




##############################################################################################
# This file implements an extension to the web server embedded in the Beremiz_service.py     #
# runtime manager (webserver is in runtime/NevowServer.py).                                  #
#                                                                                            #
# The extension implemented in this file allows for runtime configuration                    #
# of Modbus plugin parameters                                                                #
##############################################################################################



import json
import os
import ctypes
import string
import hashlib

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

# Directory in which to store the persistent configurations
# Should be a directory that does not get wiped on reboot!
_ModbusConfFiledir = "/tmp"

# Will contain references to the C functions 
# (implemented in beremiz/modbus/mb_runtime.c)
# used to get/set the Modbus specific configuration paramters
GetParamFuncs = {}
SetParamFuncs = {}


# List of all TCP clients configured in the loaded PLC (i.e. the .so file loaded into memory)
# Each entry will be a dictionary. See _Add_TCP_Client() for the data structure details...
_TCPclient_list = []




# Paramters we will need to get from the C code, but that will not be shown
# on the web interface. Common to all modbus entry types (client/server, tcp/rtu/ascii)
General_parameters = [
    #    param. name       label                        ctype type         annotate type
    # (C code var name)   (used on web interface)      (C data type)       (web data type)
    #                                                                      (annotate.String,
    #                                                                       annotate.Integer, ...)
    ("config_name"      , _("")                      , ctypes.c_char_p,    annotate.String),
    ("addr_type"        , _("")                      , ctypes.c_char_p,    annotate.String)
    ]                                                                      
                                                                           
TCPclient_parameters = [                                                   
    #    param. name       label                        ctype type         annotate type
    # (C code var name)   (used on web interface)      (C data type)       (web data type)
    #                                                                      (annotate.String,
    #                                                                       annotate.Integer, ...)
    ("host"             , _("Remote IP Address")     , ctypes.c_char_p,    annotate.String),
    ("port"             , _("Remote Port Number")    , ctypes.c_char_p,    annotate.String),
    ("comm_period"      , _("Invocation Rate (ms)")  , ctypes.c_ulonglong, annotate.Integer)
    ]

RTUclient_parameters = [                                                   
    #    param. name       label                        ctype type         annotate type
    # (C code var name)   (used on web interface)      (C data type)       (web data type)
    #                                                                      (annotate.String,
    #                                                                       annotate.Integer, ...)
    ("device"           , _("Serial Port")           , ctypes.c_char_p,    annotate.String),
    ("baud"             , _("Baud Rate")             , ctypes.c_int,       annotate.Integer),
    ("parity"           , _("Parity")                , ctypes.c_int,       annotate.Integer),
    ("stop_bits"        , _("Stop Bits")             , ctypes.c_int,       annotate.Integer),
    ("comm_period"      , _("Invocation Rate (ms)")  , ctypes.c_ulonglong, annotate.Integer)
    ]


# Note: the dictionary key must be the same as the string returned by the 
# __modbus_get_ClientNode_addr_type()
# __modbus_get_ServerNode_addr_type()
# functions implemented in C (see modbus/mb_runtime.c)
_client_parameters = {}
_client_parameters["tcp"  ] = TCPclient_parameters
_client_parameters["rtu"  ] = RTUclient_parameters
_client_parameters["ascii"] = []  # (Note: ascii not yet implemented in Beremiz modbus plugin)


#def _CheckPortnumber(port_number):
#    """ check validity of the port number """
#    try:
#        portnum = int(port_number)
#        if (portnum < 0) or (portnum > 65535):
#           raise Exception
#    except Exception:    
#        return False
#        
#    return True




#def _CheckConfiguration(BACnetConfig):
#    res = True    
#    res = res and _CheckPortnumber(BACnetConfig["port_number"])
#    res = res and _CheckDeviceID  (BACnetConfig["device_id"])
#    return res



#def _CheckWebConfiguration(BACnetConfig):
#    res = True
#    
#    # check the port number
#    if not _CheckPortnumber(BACnetConfig["port_number"]):
#        raise annotate.ValidateError(
#            {"port_number": "Invalid port number: " + str(BACnetConfig["port_number"])},
#            _("Modbus configuration error:"))
#        res = False
#    
#    if not _CheckDeviceID(BACnetConfig["device_id"]):
#        raise annotate.ValidateError(
#            {"device_id": "Invalid device ID: " + str(BACnetConfig["device_id"])},
#            _("Modbus configuration error:"))
#        res = False
#        
#    return res






def _SetSavedConfiguration(node_id, newConfig):
    """ Stores a dictionary in a persistant file containing the Modbus parameter configuration """
    
    filename = _TCPclient_list[node_id]["filename"]

    with open(os.path.realpath(filename), 'w') as f:
        json.dump(newConfig, f, sort_keys=True, indent=4)
        
    _TCPclient_list[node_id]["SavedConfiguration"] = newConfig




def _DelSavedConfiguration(node_id):
    """ Deletes the file cotaining the persistent Modbus configuration """
    filename = _TCPclient_list[node_id]["filename"]
    
    if os.path.exists(filename):
        os.remove(filename)




def _GetSavedConfiguration(node_id):
    """
    Returns a dictionary containing the Modbus parameter configuration
    that was last saved to file. If no file exists, then return None
    """
    filename = _TCPclient_list[node_id]["filename"]
    try:
        #if os.path.isfile(filename):
        saved_config = json.load(open(filename))
    except Exception:    
        return None

    #if _CheckConfiguration(saved_config):
    #    return saved_config
    #else:
    #    return None

    return saved_config



def _GetPLCConfiguration(node_id):
    """
    Returns a dictionary containing the current Modbus parameter configuration
    stored in the C variables in the loaded PLC (.so file)
    """
    current_config = {}
    addr_type = _TCPclient_list[node_id]["addr_type"]

    for par_name, x1, x2, x3 in _client_parameters[addr_type]:
        value = GetParamFuncs[par_name](node_id)
        if value is not None:
            current_config[par_name] = value
    
    return current_config



def _SetPLCConfiguration(node_id, newconfig):
    """
    Stores the Modbus parameter configuration into the
    the C variables in the loaded PLC (.so file)
    """
    addr_type = _TCPclient_list[node_id]["addr_type"]
    
    for par_name in newconfig:
        value = newconfig[par_name]
        if value is not None:
            SetParamFuncs[par_name](node_id, value)
            



def _GetWebviewConfigurationValue(ctx, node_id, argument):
    """
    Callback function, called by the web interface (NevowServer.py)
    to fill in the default value of each parameter of the web form
    
    Note that the real callback function is a dynamically created function that
    will simply call this function to do the work. It will also pass the node_id 
    as a parameter.
    """
    try:
        return _TCPclient_list[node_id]["WebviewConfiguration"][argument.name]
    except Exception:
        return ""




def _updateWebInterface(node_id):
    """
    Add/Remove buttons to/from the web interface depending on the current state
       - If there is a saved state => add a delete saved state button
    """

    config_hash = _TCPclient_list[node_id]["config_hash"]
    config_name = _TCPclient_list[node_id]["config_name"]
    
    # Add a "Delete Saved Configuration" button if there is a saved configuration!
    if _TCPclient_list[node_id]["SavedConfiguration"] is None:
        _NS.ConfigurableSettings.delSettings("ModbusConfigDelSaved" + config_hash)
    else:
        def __OnButtonDel(**kwargs):
            return OnButtonDel(node_id = node_id, **kwargs)
                
        _NS.ConfigurableSettings.addSettings(
            "ModbusConfigDelSaved"      + config_hash,  # name (internal, may not contain spaces, ...)
            _("Modbus Configuration: ") + config_name,  # description (user visible label)
            [],                                         # fields  (empty, no parameters required!)
            _("Delete Configuration Stored in Persistent Storage"), # button label
            __OnButtonDel,                              # callback    
            "ModbusConfigParm"          + config_hash)  # Add after entry xxxx



def OnButtonSave(**kwargs):
    """
    Function called when user clicks 'Save' button in web interface
    The function will configure the Modbus plugin in the PLC with the values
    specified in the web interface. However, values must be validated first!
    
    Note that this function does not get called directly. The real callback
    function is the dynamic __OnButtonSave() function, which will add the 
    "node_id" argument, and call this function to do the work.
    """

    #_plcobj.LogMessage("Modbus web server extension::OnButtonSave()  Called")
    
    newConfig = {}
    node_id   = kwargs.get("node_id", None)
    addr_type = _TCPclient_list[node_id]["addr_type"]
    
    for par_name, x1, x2, x3 in _client_parameters[addr_type]:
        value = kwargs.get(par_name, None)
        if value is not None:
            newConfig[par_name] = value

    _TCPclient_list[node_id]["WebviewConfiguration"] = newConfig
    
    # First check if configuration is OK.
    ## TODO...
    #if not _CheckWebConfiguration(newConfig):
    #    return

    # store to file the new configuration so that 
    # we can recoup the configuration the next time the PLC
    # has a cold start (i.e. when Beremiz_service.py is retarted)
    _SetSavedConfiguration(node_id, newConfig)

    # Configure PLC with the current Modbus parameters
    _SetPLCConfiguration(node_id, newConfig)

    # File has just been created => Delete button must be shown on web interface!
    _updateWebInterface(node_id)




def OnButtonDel(**kwargs):
    """
    Function called when user clicks 'Delete' button in web interface
    The function will delete the file containing the persistent
    Modbus configution
    """

    node_id = kwargs.get("node_id", None)
    
    # Delete the file
    _DelSavedConfiguration(node_id)

    # Set the current configuration to the default (hardcoded in C)
    new_config = _TCPclient_list[node_id]["DefaultConfiguration"]
    _SetPLCConfiguration(node_id, new_config)
    
    #Update the webviewconfiguration
    _TCPclient_list[node_id]["WebviewConfiguration"] = new_config
    
    # Reset SavedConfiguration
    _TCPclient_list[node_id]["SavedConfiguration"] = None
    
    # File has just been deleted => Delete button on web interface no longer needed!
    _updateWebInterface(node_id)




def OnButtonShowCur(**kwargs):
    """
    Function called when user clicks 'Show Current PLC Configuration' button in web interface
    The function will load the current PLC configuration into the web form

    Note that this function does not get called directly. The real callback
    function is the dynamic __OnButtonShowCur() function, which will add the 
    "node_id" argument, and call this function to do the work.
    """
    node_id = kwargs.get("node_id", None)
    
    _TCPclient_list[node_id]["WebviewConfiguration"] = _GetPLCConfiguration(node_id)
    



def _Load_TCP_Client(node_id):
    TCPclient_entry = {}

    config_name = GetParamFuncs["config_name"](node_id)
    # addr_type will be one of "tcp", "rtu" or "ascii"
    addr_type   = GetParamFuncs["addr_type"  ](node_id)   
    # For some operations we cannot use the config name (e.g. filename to store config)
    # because the user may be using characters that are invalid for that purpose ('/' for
    # example), so we create a hash of the config_name, and use that instead.
    config_hash = hashlib.md5(config_name).hexdigest()
    
    _plcobj.LogMessage("Modbus web server extension::_Load_TCP_Client("+str(node_id)+") config_name="+config_name)

    # Add the new entry to the global list
    # Note: it is OK, and actually necessary, to do this _before_ seting all the parameters in TCPclient_entry
    #       TCPclient_entry will be stored as a reference, so we can insert parameters at will.
    global _TCPclient_list
    _TCPclient_list.append(TCPclient_entry)

    # store all node_id relevant data for future reference
    TCPclient_entry["node_id"     ] = node_id
    TCPclient_entry["config_name" ] = config_name 
    TCPclient_entry["addr_type"   ] = addr_type
    TCPclient_entry["config_hash" ] = config_hash
    TCPclient_entry["filename"    ] = os.path.join(_ModbusConfFiledir, "Modbus_config_" + config_hash + ".json")
    
    # Dictionary that contains the Modbus configuration currently being shown
    # on the web interface
    # This configuration will almost always be identical to the current
    # configuration in the PLC (i.e., the current state stored in the 
    # C variables in the .so file).
    # The configuration viewed on the web will only be different to the current 
    # configuration when the user edits the configuration, and when
    # the user asks to save an edited configuration that contains an error.
    TCPclient_entry["WebviewConfiguration"] = None

    # Upon PLC load, this Dictionary is initialised with the Modbus configuration
    # hardcoded in the C file
    # (i.e. the configuration inserted in Beremiz IDE when project was compiled)
    TCPclient_entry["DefaultConfiguration"] = _GetPLCConfiguration(node_id)
    TCPclient_entry["WebviewConfiguration"] = TCPclient_entry["DefaultConfiguration"]
    
    # Dictionary that stores the Modbus configuration currently stored in a file
    # Currently only used to decide whether or not to show the "Delete" button on the
    # web interface (only shown if _SavedConfiguration is not None)
    SavedConfig = _GetSavedConfiguration(node_id)
    TCPclient_entry["SavedConfiguration"] = SavedConfig
    
    if SavedConfig is not None:
        _SetPLCConfiguration(node_id, SavedConfig)
        TCPclient_entry["WebviewConfiguration"] = SavedConfig
        
    # Define the format for the web form used to show/change the current parameters
    # We first declare a dynamic function to work as callback to obtain the default values for each parameter
    def __GetWebviewConfigurationValue(ctx, argument):
        return _GetWebviewConfigurationValue(ctx, node_id, argument)
    
    webFormInterface = [(name, web_dtype (label=web_label, default=__GetWebviewConfigurationValue)) 
                    for name, web_label, c_dtype, web_dtype in _client_parameters[addr_type]]

    # Configure the web interface to include the Modbus config parameters
    def __OnButtonSave(**kwargs):
        OnButtonSave(node_id=node_id, **kwargs)

    _NS.ConfigurableSettings.addSettings(
        "ModbusConfigParm"          + config_hash,     # name (internal, may not contain spaces, ...)
        _("Modbus Configuration: ") + config_name,     # description (user visible label)
        webFormInterface,                              # fields
        _("Save Configuration to Persistent Storage"), # button label
        __OnButtonSave)                                # callback   
    
    # Add a "View Current Configuration" button 
    def __OnButtonShowCur(**kwargs):
        OnButtonShowCur(node_id=node_id, **kwargs)

    _NS.ConfigurableSettings.addSettings(
        "ModbusConfigViewCur"       + config_hash, # name (internal, may not contain spaces, ...)
        _("Modbus Configuration: ") + config_name,     # description (user visible label)
        [],                                        # fields  (empty, no parameters required!)
        _("Show Current PLC Configuration"),       # button label
        __OnButtonShowCur)                         # callback    

    # Add the Delete button to the web interface, if required
    _updateWebInterface(node_id)




def OnLoadPLC():
    """
    Callback function, called (by PLCObject.py) when a new PLC program
    (i.e. XXX.so file) is transfered to the PLC runtime
    and loaded into memory
    """

    #_plcobj.LogMessage("Modbus web server extension::OnLoadPLC() Called...")

    if _plcobj.PLClibraryHandle is None:
        # PLC was loaded but we don't have access to the library of compiled code (.so lib)?
        # Hmm... This shold never occur!! 
        return  
    
    # Get the number of Modbus Client and Servers (Modbus plugin)
    # configured in the currently loaded PLC project (i.e., the .so file)
    # If the "__modbus_plugin_client_node_count" 
    # or the "__modbus_plugin_server_node_count" C variables 
    # are not present in the .so file we conclude that the currently loaded 
    # PLC does not have the Modbus plugin included (situation (2b) described above init())
    try:
        client_count = ctypes.c_int.in_dll(_plcobj.PLClibraryHandle, "__modbus_plugin_client_node_count").value
        server_count = ctypes.c_int.in_dll(_plcobj.PLClibraryHandle, "__modbus_plugin_server_node_count").value
    except Exception:
        # Loaded PLC does not have the Modbus plugin => nothing to do
        #   (i.e. do _not_ configure and make available the Modbus web interface)
        return

    if client_count < 0: client_count = 0
    if server_count < 0: server_count = 0
    
    if (client_count == 0) and (server_count == 0):
        # The Modbus plugin in the loaded PLC does not have any client and servers configured
        #  => nothing to do (i.e. do _not_ configure and make available the Modbus web interface)
        return
    
    # Map the get/set functions (written in C code) we will be using to get/set the configuration parameters
    for name, web_label, c_dtype, web_dtype in TCPclient_parameters + RTUclient_parameters + General_parameters:
        GetParamFuncName             = "__modbus_get_ClientNode_" + name        
        GetParamFuncs[name]          = getattr(_plcobj.PLClibraryHandle, GetParamFuncName)
        GetParamFuncs[name].restype  = c_dtype
        GetParamFuncs[name].argtypes = [ctypes.c_int]
        
    for name, web_label, c_dtype, web_dtype in TCPclient_parameters + RTUclient_parameters:
        SetParamFuncName             = "__modbus_set_ClientNode_" + name
        SetParamFuncs[name]          = getattr(_plcobj.PLClibraryHandle, SetParamFuncName)
        SetParamFuncs[name].restype  = None
        SetParamFuncs[name].argtypes = [ctypes.c_int, c_dtype]

    for node_id in range(client_count):
        _Load_TCP_Client(node_id)






def OnUnLoadPLC():
    """
    # Callback function, called (by PLCObject.py) when a PLC program is unloaded from memory
    """

    #_plcobj.LogMessage("Modbus web server extension::OnUnLoadPLC() Called...")
    
    # Delete the Modbus specific web interface extensions
    # (Safe to ask to delete, even if it has not been added!)
    global _TCPclient_list    
    for TCPclient_entry in _TCPclient_list:
        config_hash = TCPclient_entry["config_hash"]
        _NS.ConfigurableSettings.delSettings("ModbusConfigParm"     + config_hash)
        _NS.ConfigurableSettings.delSettings("ModbusConfigViewCur"  + config_hash)  
        _NS.ConfigurableSettings.delSettings("ModbusConfigDelSaved" + config_hash)  
        
    # Dele all entries...
    _TCPclient_list = []



# The Beremiz_service.py service, along with the integrated web server it launches
# (i.e. Nevow web server, in runtime/NevowServer.py), will go through several states
# once started:
#  (1) Web server is started, but no PLC is loaded
#  (2) PLC is loaded (i.e. the PLC compiled code is loaded)
#         (a) The loaded PLC includes the Modbus plugin
#         (b) The loaded PLC does not have the Modbus plugin
#
# During (1) and (2a):
#     we configure the web server interface to not have the Modbus web configuration extension
# During (2b) 
#     we configure the web server interface to include the Modbus web configuration extension
#
# PS: reference to the pyroserver  (i.e., the server object of Beremiz_service.py)
#     (NOTE: PS.plcobj is a reference to PLCObject.py)
# NS: reference to the web server (i.e. the NevowServer.py module)
# WorkingDir: the directory on which Beremiz_service.py is running, and where 
#             all the files downloaded to the PLC get stored, including
#             the .so file with the compiled C generated code
def init(plcobj, NS, WorkingDir):
    #PS.plcobj.LogMessage("Modbus web server extension::init(PS, NS, " + WorkingDir + ") Called")
    global _WorkingDir
    _WorkingDir = WorkingDir
    global _plcobj
    _plcobj = plcobj
    global _NS
    _NS = NS

    _plcobj.RegisterCallbackLoad  ("Modbus_Settins_Extension", OnLoadPLC)
    _plcobj.RegisterCallbackUnLoad("Modbus_Settins_Extension", OnUnLoadPLC)
    OnUnLoadPLC() # init is called before the PLC gets loaded...  so we make sure we have the correct state
