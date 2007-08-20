
TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", "REAL" : "D", "LREAL" : "L",
    "STRING" : "B", "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L", "WSTRING" : "W"}

def GetBlockGenerationFunction(beremiz):
    def generate_svgui_block(generator, block, body, link):
        controller = generator.GetController()
        name = block.getInstanceName()
        type = block.getTypeName()
        block_infos = GetBlockType(type)
        bus_id, name = [word for word in name.split("_") if word != ""]
        block_id = beremiz.GetSVGUIElementId(bus_id, name)
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
    return generate_svgui_block

BlockList = {"name" : "SVGUI function blocks", "list" :
               [{"name" : "Container", "type" : "functionBlock", "extensible" : False, 
                 "inputs" : [("X","FLOAT","none"),("SetX","BOOL","none"),("Y","FLOAT","none"),("SetY","BOOL","none"),("Angle","FLOAT","none"),("SetAngle","BOOL","none")], 
                 "outputs" : [("X","FLOAT","none"),("X Changed","BOOL","none"),("Y","FLOAT","none"),("Y Changed","BOOL","none"),("Angle","FLOAT","none"),("Angle Changed","BOOL","none")],
                 "comment" : "SVGUI Container"},
                {"name" : "Button", "type" : "functionBlock", "extensible" : False, 
                 "inputs" : [("Show","BOOL","none"),("Toggle","BOOL","none")], 
                 "outputs" : [("Visible","BOOL","none"),("State","BOOL","none")],
                 "comment" : "SVGUI Button"},
                {"name" : "TextCtrl", "type" : "functionBlock", "extensible" : False, 
                 "inputs" : [("Text","STRING","none"),("Set Text","BOOL","none")], 
                 "outputs" : [("Text","STRING","none"),("Text Changed","BOOL","none")],
                 "comment" : "SVGUI Text Control"},
                {"name" : "ScrollBar", "type" : "functionBlock", "extensible" : False, 
                 "inputs" : [("Position","UINT","none"),("Set Position","BOOL","none")], 
                 "outputs" : [("Position","UINT","none"),("Position Changed","BOOL","none")],
                 "comment" : "SVGUI ScrollBar"},
                {"name" : "NoteBook", "type" : "functionBlock", "extensible" : False, 
                 "inputs" : [("Selected","UINT","none"),("Set Selected","BOOL","none")], 
                 "outputs" : [("Selected","UINT","none"),("Selected Changed","BOOL","none")],
                 "comment" : "SVGUI Notebook"},
                {"name" : "RotatingCtrl", "type" : "functionBlock", "extensible" : False, 
                 "inputs" : [("Angle","FLOAT","none"),("Set Angle","BOOL","none")], 
                 "outputs" : [("Angle","FLOAT","none"),("Angle changed","BOOL","none")],
                 "comment" : "SVGUI Rotating Control"},
               ]}
