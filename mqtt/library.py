# mqtt/client.py

from __future__ import absolute_import

import os

from POULibrary import POULibrary
import util.paths as paths

mqtt_python_lib_code = """
def MQTT_publish(clientname, topic, payload, QoS = 1, Retained = False):
    c_function_name = "__mqtt_python_publish_" + clientname
    c_function = getattr(PLCBinary, c_function_name)
    c_function.restype = ctypes.c_int # error or 0
    c_function.argtypes = [
        ctypes.c_char_p,  # topic
        ctypes.c_char_p,  # data
        ctypes.c_uint32,  # datalen
        ctypes.c_uint8,   # QoS
        ctypes.c_uint8,   # Retained
    ]
    res = c_function(topic, payload, len(payload), QoS, Retained)
    return res

# C per client CallBack type for __mqtt_python_subscribe_{name}
c_cb_type = ctypes.CFUNCTYPE(ctypes.c_int,                   # return
                             ctypes.c_char_p,                # topic
                             ctypes.POINTER(ctypes.c_char),  # data
                             ctypes.c_uint32)                # data length

# CallBacks management
# - each call to MQTT_subscribe registers a callback
MQTT_subscribers_cbs = {}

# - one callback registered to C side per client
MQTT_client_cbs = {}

def per_client_cb_factory(client):
    def per_client_cb(topic, dataptr, datalen):
        payload = ctypes.string_at(dataptr, datalen)
        subscriber = MQTT_subscribers_cbs[client].get(topic, None)
        if subscriber:
            subscriber(topic, payload)
            return 0
        return 1
    return per_client_cb
    
def MQTT_subscribe(clientname, topic, cb, QoS = 1):
    global MQTT_client_cbs, MQTT_subscribers_cbs
    c_function_name = "__mqtt_python_subscribe_" + clientname
    c_function = getattr(PLCBinary, c_function_name)
    c_function.restype = ctypes.c_int # error or 0
    c_function.argtypes = [
        ctypes.c_char_p,  # topic
        ctypes.c_uint8]   # QoS

    MQTT_subscribers_cbs.setdefault(clientname, {})[topic] = cb

    c_cb = MQTT_client_cbs.get(clientname, None)
    if c_cb is None:
        c_cb = c_cb_type(per_client_cb_factory(clientname))
        MQTT_client_cbs[clientname] = c_cb
        register_c_function = getattr(PLCBinary, "__mqtt_python_callback_setter_"+clientname )
        register_c_function.argtypes = [c_cb_type]
        register_c_function(c_cb)

    res = c_function(topic, QoS)
    return res

"""

class MQTTLibrary(POULibrary):
    
    def GetLibraryPath(self):
        return paths.AbsNeighbourFile(__file__, "pous.xml")

    def Generate_C(self, buildpath, varlist, IECCFLAGS):

        runtimefile_path = os.path.join(buildpath, "runtime_00_mqtt.py")
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write(mqtt_python_lib_code)
        runtimefile.close()
        return ((["mqtt"], [], False), "",
                ("runtime_00_mqtt.py", open(runtimefile_path, "rb")))
