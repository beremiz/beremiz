import os
from DEFControler import DEFControler
from defeditor import EditorFrame

class _EditorFramePlug(EditorFrame):
    def OnClose(self, event):
        self.OnPlugClose()
        event.Skip()

class _DEFControlerPlug(DEFControler):

    ViewClass = _EditorFramePlug
    
    def __init__(self, buspath):
        filepath = os.path.join(buspath, "gui.def")
        if os.path.isfile(filepath):
            self.OpenXMLFile(filepath)
        else:
            self.CreateRootElement()
            self.SetFilePath(filepath)

    def ReqSave(self):
        self.SaveXMLFile()
        return True

    def Generate_C(self, dirpath, locations):
        self.GenerateProgram(filepath)
        return {"headers":["program.h"],"sources":["program.cpp"]}
    
TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", "REAL" : "D", "LREAL" : "L",
    "STRING" : "B", "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L", "WSTRING" : "W"}

class RootClass:
    
    ChildsType = _DEFControlerPlug
    
    def BlockTypesFactory(self):
        def generate_svgui_block(generator, block, body, link):
            controller = generator.GetController()
            name = block.getInstanceName()
            type = block.getTypeName()
            block_infos = GetBlockType(type)
            bus_id, name = [word for word in name.split("_") if word != ""]
            block_id = self.PlugChilds[bus_id].GetElementIdFromName(name)
            if block_id == None:
                raise ValueError, "No corresponding block found"
            if not generator.ComputedBlocks.get(name, False):
                for num, variable in enumerate(block.inputVariables.getVariable()):
                    connections = variable.connectionPointIn.getConnections()
                    if connections and len(connections) == 1:
                        parameter = "__I%s%d_%d_%d"%(TYPECONVERSION[block_infos["inputs"][num][1]], bus_id, block_id, num)
                        value = generator.ComputeFBDExpression(body, connections[0])
                        generator.Program += ("  %s := %s;\n"%(parameter, generator.ExtractModifier(variable, value)))
                generator.ComputedBlocks[name] = True
            if link:
                connectionPoint = link.getPosition()[-1]
                for num, variable in enumerate(block.outputVariables.getVariable()):
                    blockPointx, blockPointy = variable.connectionPointOut.getRelPosition()
                    if block.getX() + blockPointx == connectionPoint.getX() and block.getY() + blockPointy == connectionPoint.getY():
                        return "__Q%s%d_%d_%d"%(TYPECONVERSION[block_infos["outputs"][num][1]], bus_id, block_id, num)
                raise ValueError, "No output variable found"
            else:
                return None

        return [{"name" : "SVGUI function blocks", "list" :
           [{"name" : "Container", "type" : "functionBlock", "extensible" : False, 
             "inputs" : [("X","FLOAT","none"),("SetX","BOOL","none"),("Y","FLOAT","none"),("SetY","BOOL","none"),("Angle","FLOAT","none"),("SetAngle","BOOL","none")], 
             "outputs" : [("X","FLOAT","none"),("X Changed","BOOL","none"),("Y","FLOAT","none"),("Y Changed","BOOL","none"),("Angle","FLOAT","none"),("Angle Changed","BOOL","none")],
             "comment" : "SVGUI Container", "generate": generate_svgui_block},
            {"name" : "Button", "type" : "functionBlock", "extensible" : False, 
             "inputs" : [("Show","BOOL","none"),("Toggle","BOOL","none")], 
             "outputs" : [("Visible","BOOL","none"),("State","BOOL","none")],
             "comment" : "SVGUI Button", "generate": generate_svgui_block},
            {"name" : "TextCtrl", "type" : "functionBlock", "extensible" : False, 
             "inputs" : [("Text","STRING","none"),("Set Text","BOOL","none")], 
             "outputs" : [("Text","STRING","none"),("Text Changed","BOOL","none")],
             "comment" : "SVGUI Text Control", "generate": generate_svgui_block},
            {"name" : "ScrollBar", "type" : "functionBlock", "extensible" : False, 
             "inputs" : [("Position","UINT","none"),("Set Position","BOOL","none")], 
             "outputs" : [("Position","UINT","none"),("Position Changed","BOOL","none")],
             "comment" : "SVGUI ScrollBar", "generate": generate_svgui_block},
            {"name" : "NoteBook", "type" : "functionBlock", "extensible" : False, 
             "inputs" : [("Selected","UINT","none"),("Set Selected","BOOL","none")], 
             "outputs" : [("Selected","UINT","none"),("Selected Changed","BOOL","none")],
             "comment" : "SVGUI Notebook", "generate": generate_svgui_block},
            {"name" : "RotatingCtrl", "type" : "functionBlock", "extensible" : False, 
             "inputs" : [("Angle","FLOAT","none"),("Set Angle","BOOL","none")], 
             "outputs" : [("Angle","FLOAT","none"),("Angle changed","BOOL","none")],
             "comment" : "SVGUI Rotating Control", "generate": generate_svgui_block}
           ]}]









