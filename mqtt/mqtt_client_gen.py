from __future__ import print_function
from __future__ import absolute_import

import csv
import functools
from threading import Thread
from collections import OrderedDict

import wx
import wx.dataview as dv

# from perfect_hash import generate_code, IntSaltHash

MQTT_IEC_types = dict(
# IEC61131|  C  type   | sz
    BOOL  = ("uint8_t" , "X"),
    SINT  = ("int8_t"  , "B"),
    USINT = ("uint8_t" , "B"),
    INT   = ("int16_t" , "W"),
    UINT  = ("uint16_t", "W"),
    DINT  = ("uint32_t", "D"),
    UDINT = ("int32_t" , "D"),
    LINT  = ("int64_t" , "L"),
    ULINT = ("uint64_t", "L"),
    REAL  = ("float"   , "D"),
    LREAL = ("double"  , "L"),
)

"""
 QoS - Quality of Service
  0  : "At most one delivery"
  1  : "At least one delivery"
  2  : "Exactly one delivery"
"""
QoS_values = [0, 1, 2]

def boolean(v):
    if v in ["False","0"]:
        return False
    else:
        return bool(v)

_lstcolnames  = [ "Topic",  "QoS",  "Retained", "Type", "Location"]
_lstcolwidths = [     100,     50,         100,    100,         50]
_lstcoltypess = [     str,    int,     boolean,    str,        int]
_lstcoldeflts = [ "a/b/c",    "1",       False, "DINT",        "0"]

subsublist = lambda l : l[0:2] + l[3:5]

lstcoldsc = {
    "input" : type("",(),dict(
        lstcolnames  = subsublist(_lstcolnames),
        lstcolwidths = subsublist(_lstcolwidths),
        lstcoltypess = subsublist(_lstcoltypess),
        lstcoldeflts = subsublist(_lstcoldeflts),
        Location_column = 3)),
    "output" : type("",(),dict(
        lstcolnames  = _lstcolnames,
        lstcolwidths = _lstcolwidths,
        lstcoltypess = _lstcoltypess,
        lstcoldeflts = _lstcoldeflts,
        Location_column = 4)),
}

directions = ["input", "output"]

authParams = {
    "x509":[
        ("Certificate", "certificate.der"),
        ("PrivateKey", "private_key.pem")],
    "UserPassword":[
        ("User", None),
        ("Password", None)]}

class MQTTTopicListModel(dv.PyDataViewIndexListModel):
    def __init__(self, data, log, direction):
        dv.PyDataViewIndexListModel.__init__(self, len(data))
        self.data = data
        self.log = log
        self.dsc = lstcoldsc[direction]

    def GetColumnType(self, col):
        return "string"

    def GetValueByRow(self, row, col):
        return str(self.data[row][col])

    # This method is called when the user edits a data item in the view.
    def SetValueByRow(self, value, row, col):
        expectedtype = self.dsc.lstcoltypess[col]

        try:
            v = expectedtype(value)
        except ValueError: 
            self.log("String {} is invalid for type {}\n".format(value,expectedtype.__name__))
            return False

        if col == self.dsc.lstcolnames.index("QoS") and v not in QoS_values:
            self.log("{} is invalid for IdType\n".format(value))
            return False

        self.data[row][col] = v
        return True

    # Report how many columns this model provides data for.
    def GetColumnCount(self):
        return len(self.dsc.lstcolnames)

    # Report the number of rows in the model
    def GetCount(self):
        #self.log.write('GetCount')
        return len(self.data)

    # Called to check if non-standard attributes should be used in the
    # cell at (row, col)
    def GetAttrByRow(self, row, col, attr):
        if col == self.dsc.Location_column:
            attr.SetColour('blue')
            attr.SetBold(True)
            return True
        return False


    def DeleteRows(self, rows):
        # make a copy since we'll be sorting(mutating) the list
        # use reverse order so the indexes don't change as we remove items
        rows = sorted(rows, reverse=True)

        for row in rows:
            # remove it from our data structure
            del self.data[row]
            # notify the view(s) using this model that it has been removed
            self.RowDeleted(row)


    def AddRow(self, value):
        if self.data.append(value):
            # notify views
            self.RowAppended()

    def InsertDefaultRow(self, row):
        self.data.insert(row, self.dsc.lstcoldeflts[:])
        # notify views
        self.RowInserted(row)
    
    def ResetData(self):
        self.Reset(len(self.data))

class MQTTTopicListPanel(wx.Panel):
    def __init__(self, parent, log, model, direction):
        self.log = log
        wx.Panel.__init__(self, parent, -1)

        self.dvc = dv.DataViewCtrl(self,
                                   style=wx.BORDER_THEME
                                   | dv.DV_ROW_LINES
                                   | dv.DV_HORIZ_RULES
                                   | dv.DV_VERT_RULES
                                   | dv.DV_MULTIPLE
                                   )

        self.model = model

        self.dvc.AssociateModel(self.model)

        dsc = lstcoldsc[direction]
        for idx,(colname,width) in enumerate(zip(dsc.lstcolnames,dsc.lstcolwidths)):
            self.dvc.AppendTextColumn(colname,  idx, width=width, mode=dv.DATAVIEW_CELL_EDITABLE)


        self.Sizer = wx.BoxSizer(wx.VERTICAL)

        self.direction =  direction
        titlestr = direction + " variables"

        title = wx.StaticText(self, label = titlestr)

        addbt = wx.Button(self, label="Add")
        self.Bind(wx.EVT_BUTTON, self.OnAddRow, addbt)
        delbt = wx.Button(self, label="Delete")
        self.Bind(wx.EVT_BUTTON, self.OnDeleteRows, delbt)

        topsizer = wx.BoxSizer(wx.HORIZONTAL)
        topsizer.Add(title, 1, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 5)
        topsizer.Add(addbt, 0, wx.LEFT|wx.RIGHT, 5)
        topsizer.Add(delbt, 0, wx.LEFT|wx.RIGHT, 5)
        self.Sizer.Add(topsizer, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        self.Sizer.Add(self.dvc, 1, wx.EXPAND)


    def OnAddRow(self, evt):
        items = self.dvc.GetSelections()
        row = self.model.GetRow(items[0]) if items else 0
        self.model.InsertDefaultRow(row)

    def OnDeleteRows(self, evt):
        items = self.dvc.GetSelections()
        rows = [self.model.GetRow(item) for item in items]
        self.model.DeleteRows(rows)


class MQTTClientPanel(wx.SplitterWindow):
    def __init__(self, parent, modeldata, log, config_getter):
        self.log = log
        wx.SplitterWindow.__init__(self, parent, style=wx.SUNKEN_BORDER | wx.SP_3D)

        self.config_getter = config_getter

        self.selected_datas = modeldata
        self.selected_models = { direction:MQTTTopicListModel(
            self.selected_datas[direction], log, direction) for direction in directions }
        self.selected_lists = { direction:MQTTTopicListPanel(
                self, log, 
                self.selected_models[direction], direction) 
            for direction in directions }

        self.SplitHorizontally(*[self.selected_lists[direction] for direction in directions]+[300])

        self.SetAutoLayout(True)

    def OnClose(self):
        pass

    def __del__(self):
        self.OnClose()

    def Reset(self):
        for direction in directions:
            self.selected_models[direction].ResetData() 
        

class MQTTClientList(list):
    def __init__(self, log, change_callback, direction):
        super(MQTTClientList, self).__init__(self)
        self.log = log
        self.change_callback = change_callback
        self.dsc = lstcoldsc[direction]

    def append(self, value):
        v = dict(list(zip(self.dsc.lstcolnames, value)))

        if type(v["Location"]) != int:
            if len(self) == 0:
                v["Location"] = 0
            else:
                iecnums = set(zip(*self)[self.dsc.Location_column])
                greatest = max(iecnums)
                holes = set(range(greatest)) - iecnums
                v["Location"] = min(holes) if holes else greatest+1

        if v["QoS"] not in QoS_values:
            self.log("Unknown QoS\n".format(value))
            return False

        try:
            for t,n in zip(self.dsc.lstcoltypess, self.dsc.lstcolnames):
                v[n] = t(v[n]) 
        except ValueError: 
            self.log("MQTT topic {} (Location={}) has invalid type\n".format(v["Topic"],v["Location"]))
            return False

        if len(self)>0 and v["Topic"] in list(zip(*self))[self.dsc.lstcolnames.index("Topic")]:
            self.log("MQTT topic {} (Location={}) already in the list\n".format(v["Topic"],v["Location"]))
            return False

        list.append(self, [v[n] for n in self.dsc.lstcolnames])

        self.change_callback()

        return True

    def __delitem__(self, index):
        list.__delitem__(self, index)
        self.change_callback()

class MQTTClientModel(dict):
    def __init__(self, log, change_callback = lambda : None):
        super(MQTTClientModel, self).__init__()
        for direction in directions:
            self[direction] = MQTTClientList(log, change_callback, direction)

    def LoadCSV(self,path):
        with open(path, 'r') as csvfile:
            reader = csv.reader(csvfile, delimiter=',', quotechar='"')
            buf = {direction:[] for direction, _model in self.iteritems()}
            for direction, model in self.iteritems():
                self[direction][:] = []
            for row in reader:
                direction = row[0]
                # avoids calling change callback when loading CSV
                list.append(self[direction],row[1:])

    def SaveCSV(self,path):
        with open(path, 'w') as csvfile:
            for direction, data in self.items():
                writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for row in data:
                    writer.writerow([direction] + row)

    def GenerateC(self, path, locstr, config):
        template = """/* code generated by beremiz MQTT extension */

#include <stdint.h>
#include <unistd.h>
#include <pthread.h>
#include <string.h>
#include <stdio.h>

#include "MQTTClient.h"
#include "MQTTClientPersistence.h"

#define _Log(level, ...)                                                                          \\
    {{                                                                                            \\
        char mstr[256];                                                                           \\
        snprintf(mstr, 255, __VA_ARGS__);                                                         \\
        LogMessage(level, mstr, strlen(mstr));                                                    \\
        printf(__VA_ARGS__);                                                                      \\
        fflush(stdout);                                                                           \\
    }}

#define LogInfo(...) _Log(LOG_INFO, __VA_ARGS__);
#define LogError(...) _Log(LOG_CRITICAL, __VA_ARGS__);
#define LogWarning(...) _Log(LOG_WARNING, __VA_ARGS__);

void trace_callback(enum MQTTCLIENT_TRACE_LEVELS level, char* message)
{{
    LogInfo("Paho MQTT Trace : %d, %s\\n", level, message);
}}

#define CHANGED 1
#define UNCHANGED 0

#define DECL_VAR(iec_type, C_type, c_loc_name)                                                     \\
static C_type PLC_##c_loc_name##_buf = 0;                                                          \\
static C_type MQTT_##c_loc_name##_buf = 0;                                                         \\
static int MQTT_##c_loc_name##_state = UNCHANGED;  /* systematically published at init */          \\
C_type *c_loc_name = &PLC_##c_loc_name##_buf;

{decl}

static MQTTClient client;
#ifdef USE_MQTT_5
static MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer5;
#else
static MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
#endif

/* condition to quit publish thread */
static int MQTT_stop_thread = 0;

/* condition to wakeup publish thread */
static int MQTT_any_pub_var_changed = 0;

/* mutex to keep PLC data consistent, and protect MQTT_any_pub_var_changed */
static pthread_mutex_t MQTT_mutex;

/* wakeup publish thread when PLC changed published variable */
static pthread_cond_t MQTT_new_data = PTHREAD_COND_INITIALIZER;

/* publish thread */
static pthread_t publishThread;

#define INIT_TOPIC(topic, iec_type, c_loc_name)                                                    \\
{{#topic, &MQTT_##c_loc_name##_buf, &MQTT_##c_loc_name##_state, iec_type##_ENUM}},

static struct {{
    const char *topic; //null terminated topic string
    void *mqtt_pdata; // pointer to data from/for MQTT stack
    int *mqtt_pchanged; // pointer to changed flag
    __IEC_types_enum vartype;
}} topics [] = {{
{topics}
}};

static int _connect_mqtt(void)
{{
    int rc;

#ifdef USE_MQTT_5
    MQTTProperties props = MQTTProperties_initializer;
    MQTTProperties willProps = MQTTProperties_initializer;
    MQTTResponse response = MQTTResponse_initializer;

    response = MQTTClient_connect5(client, &conn_opts, &props, &willProps);
    rc = response.reasonCode;
    MQTTResponse_free(response);
#else
    rc = MQTTClient_connect(client, &conn_opts);
#endif

    return rc;
}}

void __cleanup_{locstr}(void)
{{
    int rc;

    /* stop publish thread */
    MQTT_stop_thread = 1;
    if (pthread_mutex_trylock(&MQTT_mutex) == 0){{
        /* unblock publish thread so that it can stop normally */
        pthread_cond_signal(&MQTT_new_data);
        pthread_mutex_unlock(&MQTT_mutex);
    }}
    pthread_join(publishThread, NULL);

#ifdef USE_MQTT_5
    if (rc = MQTTClient_disconnect5(client, 5000, MQTTREASONCODE_SUCCESS, NULL) != MQTTCLIENT_SUCCESS)
#else
    if (rc = MQTTClient_disconnect(client, 5000) != MQTTCLIENT_SUCCESS)
#endif
    {{
        LogError("MQTT Failed to disconnect, return code %d\\n", rc);
    }}
    MQTTClient_destroy(&client);
}}

void connectionLost(void* context, char* reason)
{{
    int rc;
    LogWarning("ConnectionLost, reconnecting\\n");
    // rc = _connect_mqtt();

    // if (rc != MQTTCLIENT_SUCCESS) {{
    //     LogError("MQTT reconnect Failed, waiting 5 seconds, return code %d\\n", rc);
    //     /* wait if error */
    //     sleep(5);
    // }}
}}

int messageArrived(void *context, char *topicName, int topicLen, MQTTClient_message *message)
{{
    int low = 0;
    int size = sizeof(topics) / sizeof(topics[0]);
    int high = size - 1;
    int mid;

    // bisect topic among subscribed topics
    while (low <= high) {{
        int res;
        mid = low + (high - low) / 2;
        res = strncmp(topics[mid].topic, topicName, topicLen);

        // Check if key is present at mid
        if (res == 0)
            goto found;

        // If key greater, ignore left half
        if (res < 0)
            low = mid + 1;

        // If key is smaller, ignore right half
        else
            high = mid - 1;
    }}
    // If we reach here, then the element was not present
    LogWarning("MQTT unknown topic: %s", topicName);
    goto exit;

found:
    if(__get_type_enum_size(topics[mid].vartype) == message->payloadlen){{
        memcpy(topics[mid].mqtt_pdata, (char*)message->payload, message->payloadlen);
        *topics[mid].mqtt_pchanged = 1;
    }} else {{
        LogWarning("MQTT wrong payload size for topic: %s. Should be %d, but got %d.", 
            topicName, __get_type_enum_size(topics[mid].vartype), message->payloadlen);
    }}
exit:
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}}

#define INIT_NoAuth()                                                                             \\
    LogInfo("MQTT Init no auth\\n");

#define INIT_x509(PrivateKey, Certificate)                                                        \\
    LogInfo("MQTT Init x509 %s,%s\\n", PrivateKey, Certificate);
    /* TODO */

#define INIT_UserPassword(User, Password)                                                         \\
    LogInfo("MQTT Init UserPassword %s,%s\\n", User, Password);                                   \\
    conn_opts.username = User;                                                                    \\
    conn_opts.password = Password;

#ifdef USE_MQTT_5
#define _SUBSCRIBE(Topic, QoS)                                                                    \\
        MQTTResponse response = MQTTClient_subscribe5(client, #Topic, QoS, NULL, NULL);           \\
        /* when using MQTT5 responce code is 1 for some reason even if no error */                \\
        rc = response.reasonCode == 1 ? MQTTCLIENT_SUCCESS : response.reasonCode;                 \\
        MQTTResponse_free(response);
#else
#define _SUBSCRIBE(Topic, QoS)                                                                    \\
        rc = MQTTClient_subscribe(client, #Topic, QoS);
#endif

#define INIT_SUBSCRIPTION(Topic, QoS)                                                             \\
    {{                                                                                            \\
        int rc;                                                                                   \\
        _SUBSCRIBE(Topic, QoS)                                                                  \\
        if (rc != MQTTCLIENT_SUCCESS)                                                             \\
        {{                                                                                        \\
            LogError("MQTT client failed to subscribe to '%s', return code %d\\n", #Topic, rc);   \\
        }}                                                                                        \\
    }}


#ifdef USE_MQTT_5
#define _PUBLISH(Topic, QoS, C_type, c_loc_name, Retained)                                        \\
        MQTTResponse response = MQTTClient_publish5(client, #Topic, sizeof(C_type),               \\
            &MQTT_##c_loc_name##_buf, QoS, Retained, NULL, NULL);                                  \\
        rc = response.reasonCode;                                                                 \\
        MQTTResponse_free(response);
#else
#define _PUBLISH(Topic, QoS, C_type, c_loc_name, Retained)                                        \\
        rc = MQTTClient_publish(client, #Topic, sizeof(C_type),                                   \\
            &PLC_##c_loc_name##_buf, QoS, Retained, NULL);
#endif

#define INIT_PUBLICATION(Topic, QoS, C_type, c_loc_name, Retained)                                \\
    {{                                                                                            \\
        int rc;                                                                                   \\
        _PUBLISH(Topic, QoS, C_type, c_loc_name, Retained)                                        \\
        if (rc != MQTTCLIENT_SUCCESS)                                                             \\
        {{                                                                                        \\
            LogError("MQTT client failed to init publication of '%s', return code %d\\n", #Topic, rc);\\
            /* TODO update status variable accordingly */                                         \\
        }}                                                                                        \\
    }}

#define PUBLISH_CHANGE(Topic, QoS, C_type, c_loc_name, Retained)                                  \\
    if(MQTT_##c_loc_name##_state == CHANGED)                                                      \\
    {{                                                                                            \\
        int rc;                                                                                   \\
        _PUBLISH(Topic, QoS, C_type, c_loc_name, Retained)                                        \\
        if (rc != MQTTCLIENT_SUCCESS)                                                             \\
        {{                                                                                        \\
            LogError("MQTT client failed to publish '%s', return code %d\\n", #Topic, rc);        \\
            /* TODO update status variable accordingly */                                         \\
        }} else {{                                                                                \\
            MQTT_##c_loc_name##_state = UNCHANGED;                                                \\
        }}                                                                                        \\
    }}

static void *__publish_thread(void *_unused) {{
    int rc = 0;
    while((rc = pthread_mutex_lock(&MQTT_mutex)) == 0 && !MQTT_stop_thread){{
        pthread_cond_wait(&MQTT_new_data, &MQTT_mutex);
        if(MQTT_any_pub_var_changed && MQTTClient_isConnected(client)){{

            /* publish changes, and reset variable's state to UNCHANGED */
{publish_changes}
            MQTT_any_pub_var_changed = 0;
        }}

        pthread_mutex_unlock(&MQTT_mutex);

        if(MQTT_stop_thread) break;
    }}

    if(!MQTT_stop_thread){{
        /* if thread exits outside of normal shutdown, report error*/
        LogError("MQTT client thread exited unexpectedly, return code %d\\n", rc);
    }}
}}
    
int __init_{locstr}(int argc,char **argv)
{{
    char *uri = "{uri}";
    char *clientID = "{clientID}";
    int rc;

    MQTTClient_createOptions createOpts = MQTTClient_createOptions_initializer;

#ifdef USE_MQTT_5
    conn_opts.MQTTVersion = MQTTVERSION_5;
    conn_opts.cleanstart = 1;

    createOpts.MQTTVersion = MQTTVERSION_5;
#else
    conn_opts.cleansession = 1;
#endif

    MQTTClient_setTraceCallback(trace_callback);
    MQTTClient_setTraceLevel(MQTTCLIENT_TRACE_ERROR);


    rc = MQTTClient_createWithOptions(
        &client, uri, clientID, MQTTCLIENT_PERSISTENCE_NONE, NULL, &createOpts);
    if (rc != MQTTCLIENT_SUCCESS)
    {{
        LogError("MQTT Failed to create client, return code %d\\n", rc);
        return rc;
    }}

    rc = MQTTClient_setCallbacks(client, NULL, connectionLost, messageArrived, NULL);
    if (rc != MQTTCLIENT_SUCCESS)
    {{
        LogError("MQTT Failed to set callbacks, return code %d\\n", rc);
        return rc;
    }}

    rc = _connect_mqtt();

    if (rc != MQTTCLIENT_SUCCESS) {{
        LogError("MQTT Connect Failed, return code %d\\n", rc);
        return rc;
    }}

{init}

    /* TODO start publish thread */
    rc = pthread_create(&publishThread, NULL, &__publish_thread, NULL);

    return 0;
}}

#define READ_VALUE(c_loc_name, C_type) \\
    if(MQTT_##c_loc_name##_state == CHANGED){{ \\
        /* TODO care about endianess */ \\
        PLC_##c_loc_name##_buf = MQTT_##c_loc_name##_buf; \\
        MQTT_##c_loc_name##_state = UNCHANGED; \\
    }}

void __retrieve_{locstr}(void)
{{
    if (pthread_mutex_trylock(&MQTT_mutex) == 0){{
{retrieve}
        pthread_mutex_unlock(&MQTT_mutex);
    }}
}}

#define WRITE_VALUE(c_loc_name, C_type) \\
    /* TODO care about endianess */ \\
    if(MQTT_##c_loc_name##_buf != PLC_##c_loc_name##_buf){{ \\
        MQTT_##c_loc_name##_buf = PLC_##c_loc_name##_buf; \\
        MQTT_##c_loc_name##_state = CHANGED; \\
        MQTT_any_pub_var_changed = 1; \\
    }}

void __publish_{locstr}(void)
{{
    if (pthread_mutex_trylock(&MQTT_mutex) == 0){{
        MQTT_any_pub_var_changed = 0;
        /* copy PLC_* variables to MQTT_*, and mark those who changed */
{publish}
        /* if any change detcted, unblock publish thread */
        if(MQTT_any_pub_var_changed){{
            pthread_cond_signal(&MQTT_new_data);
        }}
        pthread_mutex_unlock(&MQTT_mutex);
    }} else {{
        /* TODO if couldn't lock mutex set status variable accordingly */ 
    }}
}}

"""

        formatdict = dict(
            locstr          = locstr,
            uri             = config["URI"],
            clientID        = config["clientID"],
            decl            = "",
            topics          = "",
            cleanup         = "",
            init            = "",
            retrieve        = "",
            publish         = "",
            publish_changes = ""
        )


        # Use Config's "MQTTVersion" to switch between protocol version at build time
        if config["UseMQTT5"]:
            formatdict["decl"] += """
#define USE_MQTT_5""".format(**config)

        AuthType = config["AuthType"]
        if AuthType == "x509":
            formatdict["init"] += """
    INIT_x509("{PrivateKey}", "{Certificate}")""".format(**config)
        elif AuthType == "UserPassword":
            formatdict["init"] += """
    INIT_UserPassword("{User}", "{Password}")""".format(**config)
        else:
            formatdict["init"] += """
    INIT_NoAuth()"""

        for row in self["output"]:
            Topic, QoS, _Retained, iec_type, iec_number = row
            Retained = 1 if _Retained=="True" else 0
            C_type, iec_size_prefix = MQTT_IEC_types[iec_type]
            c_loc_name = "__Q" + iec_size_prefix + locstr + "_" + str(iec_number)

            formatdict["decl"] += """
DECL_VAR({iec_type}, {C_type}, {c_loc_name})""".format(**locals())
            formatdict["init"] += """
    INIT_PUBLICATION({Topic}, {QoS}, {C_type}, {c_loc_name}, {Retained})""".format(**locals())
            formatdict["publish"] += """
        WRITE_VALUE({c_loc_name}, {C_type})""".format(**locals())
            formatdict["publish_changes"] += """
            PUBLISH_CHANGE({Topic}, {QoS}, {C_type}, {c_loc_name}, {Retained})""".format(**locals())

        # inputs need to be sorted for bisection search 
        for row in sorted(self["input"]):
            Topic, QoS, iec_type, iec_number = row
            C_type, iec_size_prefix = MQTT_IEC_types[iec_type]
            c_loc_name = "__I" + iec_size_prefix + locstr + "_" + str(iec_number)
            formatdict["decl"] += """
DECL_VAR({iec_type}, {C_type}, {c_loc_name})""".format(**locals())
            formatdict["topics"] += """
    INIT_TOPIC({Topic}, {iec_type}, {c_loc_name})""".format(**locals())
            formatdict["init"] += """
    INIT_SUBSCRIPTION({Topic}, {QoS})""".format(**locals())
            formatdict["retrieve"] += """
        READ_VALUE({c_loc_name}, {C_type})""".format(**locals())

        Ccode = template.format(**formatdict)

        return Ccode

if __name__ == "__main__":

    import wx.lib.mixins.inspection as wit
    import sys,os

    app = wit.InspectableApp()

    frame = wx.Frame(None, -1, "MQTT Client Test App", size=(800,600))

    argc = len(sys.argv)

    config={}
    config["URI"] = sys.argv[1] if argc>1 else "tcp://localhost:1883"
    config["clientID"] = sys.argv[2] if argc>2 else ""
    config["AuthType"] = None
    config["UseMQTT5"] = True

    if argc > 3:
        AuthType = sys.argv[3]
        config["AuthType"] = AuthType
        for (name, default), value in zip_longest(authParams[AuthType], sys.argv[4:]):
            if value is None:
                if default is None:
                    raise Exception(name+" param expected")
                value = default
            config[name] = value

    test_panel = wx.Panel(frame)
    test_sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=2, vgap=0)
    test_sizer.AddGrowableCol(0)
    test_sizer.AddGrowableRow(0)

    modeldata = MQTTClientModel(print)

    mqtttestpanel = MQTTClientPanel(test_panel, modeldata, print, lambda:config)

    def OnGenerate(evt):
        dlg = wx.FileDialog(
            frame, message="Generate file as ...", defaultDir=os.getcwd(),
            defaultFile="",
            wildcard="C (*.c)|*.c", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            Ccode = """
/*
In case open62541 was built just aside beremiz, you can build this test with:
gcc %s -o %s \\
    -I ../../open62541/plugins/include/ \\
    -I ../../open62541/build/src_generated/ \\
    -I ../../open62541/include/ \\
    -I ../../open62541/arch/ ../../open62541/build/bin/libopen62541.a
*/

"""%(path, path[:-2]) + modeldata.GenerateC(path, "test", config) + """

int LogMessage(uint8_t level, char* buf, uint32_t size){
    printf("log level:%d message:'%.*s'\\n", level, size, buf);
};

int main(int argc, char *argv[]) {

    __init_test(arc,argv);

    __retrieve_test();

    __publish_test();

    __cleanup_test();

    return EXIT_SUCCESS;
}
"""

            with open(path, 'w') as Cfile:
                Cfile.write(Ccode)


        dlg.Destroy()

    def OnLoad(evt):
        dlg = wx.FileDialog(
            frame, message="Choose a file",
            defaultDir=os.getcwd(),
            defaultFile="",
            wildcard="CSV (*.csv)|*.csv",
            style=wx.FD_OPEN | wx.FD_CHANGE_DIR | wx.FD_FILE_MUST_EXIST )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            modeldata.LoadCSV(path)
            mqtttestpanel.Reset()

        dlg.Destroy()

    def OnSave(evt):
        dlg = wx.FileDialog(
            frame, message="Save file as ...", defaultDir=os.getcwd(),
            defaultFile="",
            wildcard="CSV (*.csv)|*.csv", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
            )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            modeldata.SaveCSV(path)

        dlg.Destroy()

    test_sizer.Add(mqtttestpanel, flag=wx.GROW|wx.EXPAND)

    testbt_sizer = wx.BoxSizer(wx.HORIZONTAL)

    loadbt = wx.Button(test_panel, label="Load")
    test_panel.Bind(wx.EVT_BUTTON, OnLoad, loadbt)

    savebt = wx.Button(test_panel, label="Save")
    test_panel.Bind(wx.EVT_BUTTON, OnSave, savebt)

    genbt = wx.Button(test_panel, label="Generate")
    test_panel.Bind(wx.EVT_BUTTON, OnGenerate, genbt)

    testbt_sizer.Add(loadbt, 0, wx.LEFT|wx.RIGHT, 5)
    testbt_sizer.Add(savebt, 0, wx.LEFT|wx.RIGHT, 5)
    testbt_sizer.Add(genbt, 0, wx.LEFT|wx.RIGHT, 5)

    test_sizer.Add(testbt_sizer, flag=wx.GROW)
    test_sizer.Layout()
    test_panel.SetAutoLayout(True)
    test_panel.SetSizer(test_sizer)

    def OnClose(evt):
        mqtttestpanel.OnClose()
        evt.Skip()

    frame.Bind(wx.EVT_CLOSE, OnClose)

    frame.Show()

    app.MainLoop()
