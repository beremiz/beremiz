from __future__ import print_function
from __future__ import absolute_import

import csv
import functools
from threading import Thread
from collections import OrderedDict

import wx
import wx.dataview as dv

import util.paths as paths

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

    def GenerateC(self, path, locstr, config):
        c_template_filepath = paths.AbsNeighbourFile(__file__, "mqtt_template.c")
        c_template_file = open(c_template_filepath , 'rb')
        c_template = c_template_file.read()
        c_template_file.close()

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
            formatdict["init_pubsub"] += """
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
            formatdict["init_pubsub"] += """
    INIT_SUBSCRIPTION({Topic}, {QoS})""".format(**locals())
            formatdict["retrieve"] += """
        READ_VALUE({c_loc_name}, {C_type})""".format(**locals())

        Ccode = c_template.format(**formatdict)

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
