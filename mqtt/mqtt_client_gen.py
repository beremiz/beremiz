from __future__ import print_function
from __future__ import absolute_import

import csv
import functools
from threading import Thread
from collections import OrderedDict as OD

import wx
import wx.dataview as dv

import util.paths as paths

MQTT_UNSUPPORTED_types = set([
    "TIME",
    "DATE",
    "TOD",
    "DT",
    "STEP",
    "TRANSITION",
    "ACTION",
    "STRING"
])

MQTT_IEC_types_list =[ 
# IEC61131|  C  type   | sz
    ("BOOL" , ("uint8_t" , "X")),
    ("SINT" , ("int8_t"  , "B")),
    ("USINT", ("uint8_t" , "B")),
    ("BYTE" , ("uint8_t" , "X")),
    ("INT"  , ("int16_t" , "W")),
    ("UINT" , ("uint16_t", "W")),
    ("WORD" , ("uint16_t", "W")),
    ("DINT" , ("int32_t" , "D")),
    ("UDINT", ("uint32_t", "D")),
    ("DWORD", ("uint32_t", "D")),
    ("LINT" , ("int64_t" , "L")),
    ("ULINT", ("uint64_t", "L")),
    ("LWORD", ("uint64_t", "L")),
    ("REAL" , ("float"   , "D")),
    ("LREAL", ("double"  , "L"))
]
MQTT_IEC_SUPPORTED_types = list(zip(*MQTT_IEC_types_list)[0])
MQTT_IEC_types = dict(MQTT_IEC_types_list)

MQTT_JSON_SUPPORTED_types = set(MQTT_IEC_types.keys()+["STRING"])

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

# expected configuration entries with internal default value
authParams = {
    "x509":[
        ("Verify", True),
        ("KeyStore", None),
        ("TrustStore", None)],
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

        line = self.data[row]
        line[col] = v
        self.data[row] = line
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
    def __init__(self, parent, log, model, direction, types_getter):
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

        self.types_getter = types_getter
        self.direction =  direction
        self.CreateDVCColumns()

        self.Sizer = wx.BoxSizer(wx.VERTICAL)

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


    def CreateDVCColumns(self):
        dsc = lstcoldsc[self.direction]
        for idx,(colname,width) in enumerate(zip(dsc.lstcolnames,dsc.lstcolwidths)):
            if colname == "Type":
                choice_DV_render = dv.DataViewChoiceRenderer(MQTT_IEC_SUPPORTED_types + self.types_getter())
                choice_DV_col = dv.DataViewColumn(colname, choice_DV_render, idx, width=width)
                self.dvc.AppendColumn(choice_DV_col)
            else:
                self.dvc.AppendTextColumn(colname,  idx, width=width, mode=dv.DATAVIEW_CELL_EDITABLE)

    def ResetDVCColumns(self):
        self.dvc.ClearColumns()
        self.CreateDVCColumns()

    def OnAddRow(self, evt):
        items = self.dvc.GetSelections()
        row = self.model.GetRow(items[0]) if items else 0
        self.model.InsertDefaultRow(row)

    def OnDeleteRows(self, evt):
        items = self.dvc.GetSelections()
        rows = [self.model.GetRow(item) for item in items]
        self.model.DeleteRows(rows)


class MQTTClientPanel(wx.SplitterWindow):
    def __init__(self, parent, modeldata, log, types_getter):
        self.log = log
        wx.SplitterWindow.__init__(self, parent, style=wx.SUNKEN_BORDER | wx.SP_3D)

        self.selected_datas = modeldata
        self.selected_models = { direction:MQTTTopicListModel(
            self.selected_datas[direction], log, direction) for direction in directions }
        self.selected_lists = { direction:MQTTTopicListPanel(
                self, log, 
                self.selected_models[direction], direction, types_getter) 
            for direction in directions }

        self.SplitHorizontally(*[self.selected_lists[direction] for direction in directions]+[300])

        self.SetAutoLayout(True)

    def RefreshView(self):
        for direction in directions:
            self.selected_lists[direction].ResetDVCColumns()
        
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

    def _filter_line(self, value):
        v = dict(list(zip(self.dsc.lstcolnames, value)))

        if type(v["Location"]) != int:
            if len(self) == 0:
                v["Location"] = 0
            else:
                iecnums = set(zip(*self)[self.dsc.Location_column])
                greatest = max(iecnums)
                holes = set(range(greatest)) - iecnums
                v["Location"] = min(holes) if holes else greatest+1

        try:
            for t,n in zip(self.dsc.lstcoltypess, self.dsc.lstcolnames):
                v[n] = t(v[n]) 
        except ValueError: 
            self.log("MQTT topic {} (Location={}) has invalid type\n".format(v["Topic"],v["Location"]))
            return None

        if v["QoS"] not in QoS_values:
            self.log("Unknown QoS\n".format(value))
            return None

        if len(self)>0 and v["Topic"] in list(zip(*self))[self.dsc.lstcolnames.index("Topic")]:
            self.log("MQTT topic {} (Location={}) already in the list\n".format(v["Topic"],v["Location"]))
            return None

        return [v[n] for n in self.dsc.lstcolnames]

    def insert(self, row, value):
        v = self._filter_line(value)
        if v is not None:
            list.insert(self, row, v)
            self.change_callback()
            return True
        return False

    def append(self, value):
        v = self._filter_line(value)
        if v is not None:
            list.append(self, v)
            self.change_callback()
            return True
        return False

    def __setitem__(self, index, value):
        list.__setitem__(self, index, value)
        self.change_callback()

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
                l = self[direction]
                v = l._filter_line(row[1:])
                if v is not None:
                    list.append(l,v)
                # TODO be verbose in case of malformed CSV

    def SaveCSV(self,path):
        with open(path, 'w') as csvfile:
            for direction, data in self.items():
                writer = csv.writer(csvfile, delimiter=',',
                                quotechar='"', quoting=csv.QUOTE_MINIMAL)
                for row in data:
                    writer.writerow([direction] + row)

    def GenerateC(self, path, locstr, config, datatype_info_getter):
        c_template_filepath = paths.AbsNeighbourFile(__file__, "mqtt_template.c")
        c_template_file = open(c_template_filepath , 'rb')
        c_template = c_template_file.read()
        c_template_file.close()

        json_types = OD()

        formatdict = dict(
            locstr          = locstr,
            uri             = config["URI"],
            clientID        = config["clientID"],
            decl            = "",
            topics          = "",
            cleanup         = "",
            init            = "",
            init_pubsub     = "",
            retrieve        = "",
            publish         = "",
            publish_changes = "",
            json_decl       = ""
        )


        # Use Config's "MQTTVersion" to switch between protocol version at build time
        if config["UseMQTT5"]:
            formatdict["decl"] += """
#define USE_MQTT_5""".format(**config)

        AuthType = config["AuthType"]
        if AuthType == "x509":
            for k in ["KeyStore","TrustStore"]:
                config[k] = '"'+config[k]+'"' if config[k] else "NULL"
            formatdict["init"] += """
    INIT_x509({Verify:d}, {KeyStore}, {TrustStore})""".format(**config)
        if AuthType == "PSK":
            formatdict["init"] += """
    INIT_PSK("{Secret}", "{ID}")""".format(**config)
        elif AuthType == "UserPassword":
            formatdict["init"] += """
    INIT_UserPassword("{User}", "{Password}")""".format(**config)
        else:
            formatdict["init"] += """
    INIT_NoAuth()"""

        for row in self["output"]:
            Topic, QoS, _Retained, iec_type, iec_number = row
            Retained = 1 if _Retained=="True" else 0
            if iec_type in MQTT_IEC_types:
                C_type, iec_size_prefix = MQTT_IEC_types[iec_type]
                c_loc_name = "__Q" + iec_size_prefix + locstr + "_" + str(iec_number)
                encoding = "SIMPLE"
            elif iec_type in MQTT_UNSUPPORTED_types:
                raise Exception("Type "+iec_type+" is not supported in MQTT")
            else:
                C_type = iec_type.upper();
                c_loc_name = "__Q" + locstr + "_" + str(iec_number)
                json_types.setdefault(iec_type,OD()).setdefault("OUTPUT",[]).append(c_loc_name)
                encoding = "JSON"



            formatdict["decl"] += """
DECL_VAR({iec_type}, {C_type}, {c_loc_name})""".format(**locals())
            formatdict["init_pubsub"] += """
    INIT_PUBLICATION({encoding}, {Topic}, {QoS}, {C_type}, {c_loc_name}, {Retained})""".format(**locals())
            formatdict["publish"] += """
        WRITE_VALUE({c_loc_name}, {C_type})""".format(**locals())
            formatdict["publish_changes"] += """
            PUBLISH_CHANGE({encoding}, {Topic}, {QoS}, {C_type}, {c_loc_name}, {Retained})""".format(**locals())

        # inputs need to be sorted for bisection search
        for row in sorted(self["input"]):
            Topic, QoS, iec_type, iec_number = row
            if iec_type in MQTT_IEC_types:
                C_type, iec_size_prefix = MQTT_IEC_types[iec_type]
                c_loc_name = "__I" + iec_size_prefix + locstr + "_" + str(iec_number)
                init_topic_call = "INIT_TOPIC"
            elif iec_type in MQTT_UNSUPPORTED_types:
                raise Exception("Type "+iec_type+" is not supported in MQTT")
            else:
                C_type = iec_type.upper();
                c_loc_name = "__I" + locstr + "_" + str(iec_number)
                init_topic_call = "INIT_JSON_TOPIC"
                json_types.setdefault(iec_type,OD()).setdefault("INPUT",[]).append(c_loc_name)

            formatdict["decl"] += """
DECL_VAR({iec_type}, {C_type}, {c_loc_name})""".format(**locals())
            formatdict["topics"] += """
    {init_topic_call}({Topic}, {iec_type}, {c_loc_name})""".format(**locals())
            formatdict["init_pubsub"] += """
    INIT_SUBSCRIPTION({Topic}, {QoS})""".format(**locals())
            formatdict["retrieve"] += """
        READ_VALUE({c_loc_name}, {C_type})""".format(**locals())

        # collect all used type with their dependencies
        basetypes=[]
        arrays=set()
        structures=set()
        already_generated_types = set()

        def recurseJsonTypes(datatype):
            # append derivated type first so we can expect the list
            # to be sorted with base types in last position
            basetypes.append(datatype)
            infos = datatype_info_getter(datatype)
            element_type = infos["type"]
            if element_type == "Structure":
                structures.add(datatype)
                for element in infos["elements"]:
                    field_datatype = element["Type"]
                    if field_datatype not in MQTT_JSON_SUPPORTED_types and\
                       field_datatype not in MQTT_UNSUPPORTED_types:
                        recurseJsonTypes(field_datatype)
            elif element_type == "Array":
                arrays.add(datatype)
                item_datatype = infos["base_type"]
                if item_datatype not in MQTT_JSON_SUPPORTED_types and\
                   item_datatype not in MQTT_UNSUPPORTED_types:
                    recurseJsonTypes(item_datatype)
        def typeCategory(iec_type):
            if field_iec_type in arrays:
                return "ARRAY"
            elif field_iec_type in structures:
                return "OBJECT"
            return "SIMPLE"

        for iec_type,_instances in json_types.items():
            recurseJsonTypes(iec_type)

        # go backard to get most derivated type definition last
        # so that CPP can always find base type deinition before
        for iec_type in reversed(basetypes):
            # avoid repeating type definition
            if iec_type in already_generated_types:
                continue
            already_generated_types.add(iec_type)

            C_type = iec_type.upper()
            json_decl = "#define TYPE_" + C_type + "(_P, _A) \\\n"

            infos = datatype_info_getter(iec_type)

            element_type = infos["type"]
            if element_type == "Structure":
                elements = infos["elements"]
                last = len(elements) - 1
                for idx, element in enumerate(elements):
                    field_iec_type = element["Type"]
                    if type(field_iec_type) == tuple and field_iec_type[0] == "array":
                        raise Exception("Inline arrays in structure are not supported. Please use a separate data type for array.")

                    field_C_type = field_iec_type.upper()
                    field_name = element["Name"]
                    field_C_name = field_name.upper()
                    decl_type = typeCategory(field_iec_type)

                    json_decl += ("    _P##_" + decl_type + "(" + 
                                  field_C_type + ", " + field_C_name + ", " + field_name + ", _A)" +
                                  ("\n\n" if idx == last else " _P##_separator \\\n"))

            elif element_type == "Array":
                dimensions = infos["dimensions"]
                if len(dimensions) > 1:
                    raise Exception("Only 1 dimension arrays are supported")
                count = int(dimensions[0][1]) - int(dimensions[0][0]) + 1
                field_iec_type = infos["base_type"]
                decl_type = typeCategory(field_iec_type)
                field_C_type = field_iec_type.upper()
                last = count - 1
                for idx in range(count):
                    json_decl += ("    _P##_ARRAY_" + decl_type + "(" +
                                  field_C_type + ", " + repr(idx) + " , _A)" +
                                  ("\n\n" if idx == last else " _P##_separator \\\n"))

            formatdict["json_decl"] += json_decl

        for iec_type, instances in json_types.items():
            C_type = iec_type.upper()
            for direction, instance_list in instances.items():
                for c_loc_name in instance_list:
                    formatdict["json_decl"] += "DECL_JSON_"+direction+"("+C_type+", "+c_loc_name+")\n"

        Ccode = c_template.format(**formatdict)

        return Ccode

