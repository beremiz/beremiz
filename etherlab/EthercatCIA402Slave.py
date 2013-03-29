import os

import wx

from PLCControler import LOCATION_CONFNODE, LOCATION_MODULE, LOCATION_GROUP, LOCATION_VAR_INPUT, LOCATION_VAR_OUTPUT, LOCATION_VAR_MEMORY

from MotionLibrary import Headers, AxisXSD
from EthercatSlave import _EthercatSlaveCTN
from ConfigEditor import CIA402NodeEditor

NODE_VARIABLES = [
    ("ControlWord", 0x6040, 0x00, "UINT", "Q"),
    ("TargetPosition", 0x607a, 0x00, "DINT", "Q"),
    ("ModesOfOperation", 0x06060, 0x00, "SINT", "Q"),
    ("StatusWord", 0x6041, 0x00, "UINT", "I"),
    ("ModesOfOperationDisplay", 0x06061, 0x00, "SINT", "I"),
    ("ActualPosition", 0x6064, 0x00, "DINT", "I"),
    ("ActualVelocity", 0x606C, 0x00, "DINT", "I"),
]

DEFAULT_RETRIEVE = "    __CIA402Node_%(location)s.axis->%(name)s = *(__CIA402Node_%(location)s.%(name)s);"
DEFAULT_PUBLISH = "    *(__CIA402Node_%(location)s.%(name)s) = __CIA402Node_%(location)s.axis->%(name)s;"

EXTRA_NODE_VARIABLES = [
    ("ErrorCode", [
        {"description": ("ErrorCode", 0x603F, 0x00, "UINT", "I"),
         "publish": None}
        ]),
    ("DigitalInputs", [
        {"description": ("DigitalInputs", 0x60FD, 0x00, "UDINT", "I"),
         "publish": None}
        ]),
    ("DigitalOutputs", [
        {"description": ("DigitalOutputs", 0x60FE, 0x00, "UDINT", "Q"),
         "retrieve": None}
        ])
]
EXTRA_NODE_VARIABLES_DICT = dict([("Enable" + name, value) for name, value in EXTRA_NODE_VARIABLES])

BLOCK_INPUT_TEMPLATE = "    __SET_VAR(%(blockname)s->,%(input_name)s, %(input_value)s);"
BLOCK_OUTPUT_TEMPLATE = "    __SET_VAR(data__->,%(output_name)s, __GET_VAR(%(blockname)s->%(output_name)s));"

BLOCK_FUNCTION_TEMPLATE = """
extern void ETHERLAB%(ucase_blocktype)s_body__(ETHERLAB%(ucase_blocktype)s* data__);
void __%(blocktype)s_%(location)s(MC_%(ucase_blocktype)s *data__) {
__DECLARE_GLOBAL_PROTOTYPE(ETHERLAB%(ucase_blocktype)s, %(blockname)s);
ETHERLAB%(ucase_blocktype)s* %(blockname)s = __GET_GLOBAL_%(blockname)s();
%(extract_inputs)s
ETHERLAB%(ucase_blocktype)s_body__(%(blockname)s);
%(return_outputs)s
}
"""

BLOCK_FUNTION_DEFINITION_TEMPLATE = """    if (!__CIA402Node_%(location)s.axis->__mcl_func_MC_%(blocktype)s)
__CIA402Node_%(location)s.axis->__mcl_func_MC_%(blocktype)s = __%(blocktype)s_%(location)s;"""

GLOBAL_INSTANCES = [
    {"blocktype": "GetTorqueLimit", 
     "inputs": [],
     "outputs": [{"name": "TorqueLimitPos", "type": "UINT"},
                 {"name": "TorqueLimitNeg", "type": "UINT"}]},
    {"blocktype": "SetTorqueLimit", 
     "inputs": [{"name": "TorqueLimitPos", "type": "UINT"},
                {"name": "TorqueLimitNeg", "type": "UINT"}],
     "outputs": []},
]

#--------------------------------------------------
#                 Ethercat CIA402 Node
#--------------------------------------------------

class _EthercatCIA402SlaveCTN(_EthercatSlaveCTN):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="CIA402SlaveParams">
        <xsd:complexType>
          %s
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """ % ("\n".join(['<xsd:attribute name="Enable%s" type="xsd:boolean" use="optional" default="false"/>' % category 
                      for category, variables in EXTRA_NODE_VARIABLES]) + AxisXSD)
    
    NODE_PROFILE = 402
    EditorType = CIA402NodeEditor
    
    ConfNodeMethods = [
        {"bitmap" : "CIA402AxisRef",
         "name" : _("Axis Ref"),
         "tooltip" : _("Initiate Drag'n drop of Axis ref located variable"),
         "method" : "_getCIA402AxisRef",
         "push": True},
    ]
    
    def GetIconName(self):
        return "CIA402Slave"
    
    def SetParamsAttribute(self, path, value):
        if path == "CIA402SlaveParams.Type":
            path = "SlaveParams.Type"
        elif path == "CIA402SlaveParams.Alias":
            path = "SlaveParams.Alias"
        return _EthercatSlaveCTN.SetParamsAttribute(self, path, value)
    
    def GetVariableLocationTree(self):
        axis_name = self.CTNName()
        current_location = self.GetCurrentLocation()
        children = [{"name": "%s Axis Ref" % (axis_name),
                     "type": LOCATION_VAR_INPUT,
                     "size": "W",
                     "IEC_type": "AXIS_REF",
                     "var_name": axis_name,
                     "location": "%%IW%s.0" % (".".join(map(str, current_location))),
                     "description": "",
                     "children": []}]
        children.extend(self.CTNParent.GetDeviceLocationTree(self.GetSlavePos(), current_location, axis_name))
        return  {"name": axis_name,
                 "type": LOCATION_CONFNODE,
                 "location": self.GetFullIEC_Channel(),
                 "children": children,
        }
    
    def CTNGlobalInstances(self):
        current_location = self.GetCurrentLocation()
        return [("%s_%s" % (block_infos["blocktype"], "_".join(map(str, current_location))),
                 "EtherLab%s" % block_infos["blocktype"]) for block_infos in GLOBAL_INSTANCES]
    
    def _getCIA402AxisRef(self):
        data = wx.TextDataObject(str(("%%IW%s.0" % ".".join(map(str, self.GetCurrentLocation())), 
                                      "location", "AXIS_REF", self.CTNName(), "")))
        dragSource = wx.DropSource(self.GetCTRoot().AppFrame)
        dragSource.SetData(data)
        dragSource.DoDragDrop()
    
    def CTNGenerate_C(self, buildpath, locations):
        current_location = self.GetCurrentLocation()
        
        location_str = "_".join(map(lambda x:str(x), current_location))
        
        plc_cia402node_filepath = os.path.join(os.path.split(__file__)[0], "plc_cia402node.c")
        plc_cia402node_file = open(plc_cia402node_filepath, 'r')
        plc_cia402node_code = plc_cia402node_file.read()
        plc_cia402node_file.close()
        
        str_completion = {
            "slave_pos": self.GetSlavePos(),
            "location": location_str,
            "MCL_headers": Headers,
            "extern_located_variables_declaration": [],
            "fieldbus_interface_declaration": [],
            "fieldbus_interface_definition": [],
            "entry_variables": [],
            "init_axis_params": [],
            "init_entry_variables": [],
            "extra_variables_retrieve": [],
            "extra_variables_publish": []
        }
        
        for blocktype_infos in GLOBAL_INSTANCES:
            texts = {
                "blocktype": blocktype_infos["blocktype"],
                "ucase_blocktype": blocktype_infos["blocktype"].upper(),
                "location": "_".join(map(str, current_location))
            }
            texts["blockname"] = "%(ucase_blocktype)s_%(location)s" % texts
            
            inputs = [{"input_name": "POS", "input_value": str(self.GetSlavePos())},
                      {"input_name": "EXECUTE", "input_value": "__GET_VAR(data__->EXECUTE)"}] +\
                     [{"input_name": input["name"].upper(), 
                       "input_value": "__GET_VAR(data__->%s)" % input["name"].upper()}
                      for input in blocktype_infos["inputs"]]
            input_texts = []
            for input_infos in inputs:
                input_infos.update(texts)
                input_texts.append(BLOCK_INPUT_TEMPLATE % input_infos)
            texts["extract_inputs"] = "\n".join(input_texts)
            
            outputs = [{"output_name": output} for output in ["DONE", "BUSY", "ERROR"]] + \
                      [{"output_name": output["name"].upper()} for output in blocktype_infos["outputs"]]
            output_texts = []
            for output_infos in outputs:
                output_infos.update(texts)
                output_texts.append(BLOCK_OUTPUT_TEMPLATE % output_infos)
            texts["return_outputs"] = "\n".join(output_texts)
            
            str_completion["fieldbus_interface_declaration"].append(
                    BLOCK_FUNCTION_TEMPLATE % texts)
            
            str_completion["fieldbus_interface_definition"].append(
                    BLOCK_FUNTION_DEFINITION_TEMPLATE % texts)
            
        variables = NODE_VARIABLES[:]
        
        params = self.CTNParams[1].getElementInfos(self.CTNParams[0])
        for param in params["children"]:
            if param["name"] in EXTRA_NODE_VARIABLES_DICT:
                if param["value"]:
                    extra_variables = EXTRA_NODE_VARIABLES_DICT.get(param["name"])
                    for variable_infos in extra_variables:
                        var_infos = {
                            "location": location_str,
                            "name": variable_infos["description"][0]
                        }
                        variables.append(variable_infos["description"])
                        retrieve_template = variable_infos.get("retrieve", DEFAULT_RETRIEVE)
                        publish_template = variable_infos.get("publish", DEFAULT_PUBLISH)
                        
                        if retrieve_template is not None:
                            str_completion["extra_variables_retrieve"].append(
                                retrieve_template % var_infos)
                        if publish_template is not None:
                            str_completion["extra_variables_publish"].append(
                                publish_template % var_infos)
            elif param["value"] is not None:
                param_infos = {
                    "location": location_str,
                    "param_name": param["name"],
                }
                if param["type"] == "boolean":
                    param_infos["param_value"] = {True: "true", False: "false"}[param["value"]]
                else:
                    param_infos["param_value"] = str(param["value"])
                str_completion["init_axis_params"].append(
                    "        __CIA402Node_%(location)s.axis->%(param_name)s = %(param_value)s;" % param_infos)
        
        for variable in variables:
            var_infos = dict(zip(["name", "index", "subindex", "var_type", "dir"], variable))
            var_infos["location"] = location_str
            var_infos["var_size"] = self.GetSizeOfType(var_infos["var_type"])
            var_infos["var_name"] = "__%(dir)s%(var_size)s%(location)s_%(index)d_%(subindex)d" % var_infos
            
            str_completion["extern_located_variables_declaration"].append(
                    "IEC_%(var_type)s *%(var_name)s;" % var_infos)
            str_completion["entry_variables"].append(
                    "    IEC_%(var_type)s *%(name)s;" % var_infos)
            str_completion["init_entry_variables"].append(
                    "    __CIA402Node_%(location)s.%(name)s = %(var_name)s;" % var_infos)
            
            self.CTNParent.FileGenerator.DeclareVariable(
                    self.GetSlavePos(), var_infos["index"], var_infos["subindex"], 
                    var_infos["var_type"], var_infos["dir"], var_infos["var_name"])
        
        for element in ["extern_located_variables_declaration", 
                        "fieldbus_interface_declaration",
                        "fieldbus_interface_definition",
                        "entry_variables", 
                        "init_axis_params", 
                        "init_entry_variables",
                        "extra_variables_retrieve",
                        "extra_variables_publish"]:
            str_completion[element] = "\n".join(str_completion[element])
        
        Gen_CIA402Nodefile_path = os.path.join(buildpath, "cia402node_%s.c"%location_str)
        cia402nodefile = open(Gen_CIA402Nodefile_path, 'w')
        cia402nodefile.write(plc_cia402node_code % str_completion)
        cia402nodefile.close()
        
        return [(Gen_CIA402Nodefile_path, '"-I%s"'%os.path.abspath(self.GetCTRoot().GetIECLibPath()))],"",True
