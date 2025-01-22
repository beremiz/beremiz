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

# C per client CallBack type for __mqtt_python_onmsg_{name}
mqtt_c_cb_onmsg_type = ctypes.CFUNCTYPE(ctypes.c_int,                   # return
                                        ctypes.c_char_p,                # topic
                                        ctypes.POINTER(ctypes.c_char),  # data
                                        ctypes.c_uint32)                # data length

# C per client CallBack type for __mqtt_python_resub_{name}
mqtt_c_cb_resub_type = ctypes.CFUNCTYPE(ctypes.c_int)                  # return

# CallBacks management
# - each call to MQTT_subscribe registers a callback
MQTT_subscribers_cbs = {}

# - one callback registered to C side per client
MQTT_client_cbs = {}

def mqtt_per_client_cb_factory(clientname):
    def per_client_onmsg_cb(topic, dataptr, datalen):
        payload = ctypes.string_at(dataptr, datalen)
        subscriber,_Qos = MQTT_subscribers_cbs[clientname].get(topic, None)
        if subscriber:
            subscriber(topic, payload)
            return 0
        return 1
    def per_client_resub_cb():
        for topic,(_cb,QoS) in MQTT_subscribers_cbs[clientname].items():
            _MQTT_subscribe(clientname, topic, QoS)
        return 1
    return per_client_onmsg_cb,per_client_resub_cb
    
def _MQTT_subscribe(clientname, topic, QoS):
    c_function_name = "__mqtt_python_subscribe_" + clientname
    c_function = getattr(PLCBinary, c_function_name)
    c_function.restype = ctypes.c_int # error or 0
    c_function.argtypes = [
        ctypes.c_char_p,  # topic
        ctypes.c_uint8]   # QoS

    return c_function(topic, QoS)

def MQTT_subscribe(clientname, topic, cb, QoS = 1):
    global MQTT_client_cbs, MQTT_subscribers_cbs

    MQTT_subscribers_cbs.setdefault(clientname, {})[topic] = (cb, QoS)
    res = _MQTT_subscribe(clientname, topic, QoS)

    c_cbs = MQTT_client_cbs.get(clientname, None)
    if c_cbs is None:
        cb_onmsg, cb_resub = mqtt_per_client_cb_factory(clientname)
        c_cbs = (mqtt_c_cb_onmsg_type(cb_onmsg),
                 mqtt_c_cb_resub_type(cb_resub))
        MQTT_client_cbs[clientname] = c_cbs
        register_c_function = getattr(PLCBinary, "__mqtt_python_callback_setter_"+clientname )
        register_c_function.argtypes = [mqtt_c_cb_onmsg_type, mqtt_c_cb_resub_type]
        register_c_function(*c_cbs)

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
