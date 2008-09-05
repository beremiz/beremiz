import os, shutil, sys
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "wxsvg", "SVGUIEditor"))
sys.path.append(os.path.join(base_folder, "plcopeneditor", "graphics"))

import wx

from SVGUIGenerator import *
from SVGUIControler import *
from SVGUIEditor import *
from FBD_Objects import *

from wxPopen import ProcessLogger
import subprocess
from wx.wxsvg import SVGDocument

[ID_SVGUIEDITORFBDPANEL, 
] = [wx.NewId() for _init_ctrls in range(1)]

SVGUIFB_Types = {ITEM_CONTAINER : "Container",
                 ITEM_BUTTON : "Button", 
                 ITEM_TEXT : "TextCtrl", 
                 ITEM_SCROLLBAR : "ScrollBar", 
                 ITEM_ROTATING : "RotatingCtrl", 
                 ITEM_NOTEBOOK : "NoteBook", 
                 ITEM_TRANSFORM : "Transform"}

class _SVGUIEditor(SVGUIEditor):
    """
    This Class add IEC specific features to the SVGUIEditor :
        - FDB preview
        - FBD begin drag 
    """
    
    def _init_coll_EditorGridSizer_Items(self, parent):
        SVGUIEditor._init_coll_EditorGridSizer_Items(self, parent)
        parent.AddWindow(self.FBDPanel, 0, border=0, flag=wx.GROW)
    
    def _init_ctrls(self, prnt):
        SVGUIEditor._init_ctrls(self, prnt, False)
        
        self.FBDPanel = wx.Panel(id=ID_SVGUIEDITORFBDPANEL, 
                  name='FBDPanel', parent=self.EditorPanel, pos=wx.Point(0, 0),
                  size=wx.Size(0, 0), style=wx.TAB_TRAVERSAL|wx.SIMPLE_BORDER)
        self.FBDPanel.SetBackgroundColour(wx.WHITE)
        self.FBDPanel.Bind(wx.EVT_LEFT_DOWN, self.OnFBDPanelClick)
        self.FBDPanel.Bind(wx.EVT_PAINT, self.OnPaintFBDPanel)
        
        setattr(self.FBDPanel, "GetScaling", lambda: None) 
        
        self._init_sizers()
    
    def __init__(self, parent, controler = None, fileOpen = None):
        SVGUIEditor.__init__(self, parent, controler, fileOpen)
        
        self.FBDBlock = None
    
    def RefreshView(self, select_id = None):
        SVGUIEditor.RefreshView(self, select_id)
        self.FBDPanel.Refresh()
    
    def OnPaintFBDPanel(self,event):
        dc = wx.ClientDC(self.FBDPanel)
        dc.Clear()
        selected = self.GetSelected()
        if selected is not None:
            selected_type = self.Controler.GetElementType(selected)
            if selected_type is not None:
                self.FBDBlock = FBD_Block(parent=self.FBDPanel,type=SVGUIFB_Types[selected_type],name=self.Controler.GetElementName(selected))
                width, height = self.FBDBlock.GetMinSize()
                self.FBDBlock.SetSize(width,height)
                clientsize = self.FBDPanel.GetClientSize()
                x = (clientsize.width - width) / 2
                y = (clientsize.height - height) / 2
                self.FBDBlock.SetPosition(x, y)
                self.FBDBlock.Draw(dc)
        else:
            self.FBDBlock = None
        event.Skip()
        
    def OnFBDPanelClick(self, event):
        if self.FBDBlock:
            data = wx.TextDataObject(str((self.FBDBlock.GetType(), "functionBlock", self.FBDBlock.GetName())))
            DropSrc = wx.DropSource(self.FBDPanel)
            DropSrc.SetData(data)
            DropSrc.DoDragDrop()
        event.Skip()
    
    def OnInterfaceTreeItemSelected(self, event):
        self.FBDPanel.Refresh()
        SVGUIEditor.OnInterfaceTreeItemSelected(self, event)
    
    def OnGenerate(self,event):
        self.SaveProject()
        self.Controler.PlugGenerate_C(sys.path[0],(0,0,4,5),None)
        event.Skip()    
    
TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", "REAL" : "D", "LREAL" : "L",
    "STRING" : "B", "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L", "WSTRING" : "W"}

CTYPECONVERSION = {"BOOL" : "IEC_BOOL", "UINT" : "IEC_UINT", "STRING" : "IEC_STRING", "REAL" : "IEC_REAL"}
CPRINTTYPECONVERSION = {"BOOL" : "d", "UINT" : "d", "STRING" : "s", "REAL" : "f"}

class RootClass(SVGUIControler):

    def __init__(self):
        SVGUIControler.__init__(self)
        filepath = os.path.join(self.PlugPath(), "gui.xml")
        
        if os.path.isfile(filepath):
            svgfile = os.path.join(self.PlugPath(), "gui.svg")
            if os.path.isfile(svgfile):
                self.SvgFilepath = svgfile
            self.OpenXMLFile(filepath)
        else:
            self.CreateNewInterface()
            self.SetFilePath(filepath)

    def GetElementIdFromName(self, name):
        element = self.GetElementByName(name)
        if element is not None:
            return element.getid()
        return None

    _View = None
    def _OpenView(self):
        if not self._View:
            def _onclose():
                self._View = None
            def _onsave():
                self.GetPlugRoot().SaveProject()
            self._View = _SVGUIEditor(self.GetPlugRoot().AppFrame, self)
            self._View._onclose = _onclose
            self._View._onsave = _onsave
            self._View.Show()

    def _ImportSVG(self):
        if not self._View:
            dialog = wx.FileDialog(self.GetPlugRoot().AppFrame, "Choose a SVG file", os.getcwd(), "",  "SVG files (*.svg)|*.svg|All files|*.*", wx.OPEN)
            if dialog.ShowModal() == wx.ID_OK:
                svgpath = dialog.GetPath()
                if os.path.isfile(svgpath):
                    shutil.copy(svgpath, os.path.join(self.PlugPath(), "gui.svg"))
                else:
                    self.logger.write_error("No such SVG file: %s\n"%svgpath)
            dialog.Destroy()

    def _ImportXML(self):
        if not self._View:
            dialog = wx.FileDialog(self.GetPlugRoot().AppFrame, "Choose a XML file", os.getcwd(), "",  "XML files (*.xml)|*.xml|All files|*.*", wx.OPEN)
            if dialog.ShowModal() == wx.ID_OK:
                xmlpath = dialog.GetPath()
                if os.path.isfile(xmlpath):
                    shutil.copy(xmlpath, os.path.join(self.PlugPath(), "gui.xml"))
                else:
                    self.logger.write_error("No such XML file: %s\n"%xmlpath)
            dialog.Destroy()

    def _StartInkscape(self):
        if not self._View:
            svgfile = os.path.join(self.PlugPath(), "gui.svg")
            popenargs = []

            if wx.Platform == '__WXMSW__':
                popenargs.append(os.path.join(base_folder, "Inkscape", "inkscape.exe"))
            else:
                popenargs.append("/usr/bin/inkscape")

            if os.path.isfile(svgfile):
                popenargs.append(svgfile)

            subprocess.Popen(popenargs).pid

    PluginMethods = [
        {"bitmap" : os.path.join("images","HMIEditor"),
         "name" : "HMI Editor",
         "tooltip" : "HMI Editor",
         "method" : "_OpenView"},
        {"bitmap" : os.path.join("images","ImportSVG"),
         "name" : "Import SVG",
         "tooltip" : "Import SVG",
         "method" : "_ImportSVG"},
        {"bitmap" : os.path.join("images","ImportDEF"),
         "name" : "Import XML",
         "tooltip" : "Import XML",
         "method" : "_ImportXML"},
         {"bitmap" : os.path.join("images","ImportSVG"),
         "name" : "Inkscape",
         "tooltip" : "Create HMI",
         "method" : "_StartInkscape"},
    ]
    
    def OnPlugSave(self):
        self.SaveXMLFile(os.path.join(self.PlugPath(), "gui.xml"))
        return True
    
    def PlugGenerate_C(self, buildpath, locations):
        progname = "SVGUI_%s"%"_".join(map(str, self.GetCurrentLocation()))
        
        doc = SVGDocument(self.GetSVGFilePath())
        root_element = doc.GetRootElement()
        window_size = (int(float(root_element.GetAttribute("width"))),
                       int(float(root_element.GetAttribute("height"))))

#        svgfilepath = self.GetSVGFilePath()
#        xmlfilepath = self.GetFilePath()
#        shutil.copy(svgfilepath, buildpath)
#        shutil.copy(xmlfilepath, buildpath)
        
        SVGFilePath = self.GetSVGFilePath()
        SVGFileBaseName = os.path.split(SVGFilePath)[1]
        FilePath = self.GetFilePath()
        FileBaseName = os.path.split(FilePath)[1]
        
        generator = _SVGUICGenerator(self, self.GetElementsByType(), 
                                     os.path.split(self.GetSVGFilePath())[1], 
                                     os.path.split(self.GetFilePath())[1], 
                                     self.GetCurrentLocation())
        generator.GenerateProgram(window_size, buildpath, progname)
        Gen_C_file = os.path.join(buildpath, progname+".cpp" )
        
        if wx.Platform == '__WXMSW__':
            cxx_flags = "-I..\\..\\wxPython-src-2.8.8.1\\bld\\lib\\wx\\include\\msw-unicode-release-2.8 -I..\\..\\wxPython-src-2.8.8.1\\include -I..\\..\\wxPython-src-2.8.8.1\\contrib\\include -I..\\..\\matiec\\lib -DWXUSINGDLL -D__WXMSW__ -mthreads"
            libs = "\"..\\lib\\libwxsvg.a\" \"..\\lib\\libwxsvg_agg.a\" \"..\\lib\\libagg.a\" \"..\\lib\\libaggplatformwin32.a\" \"..\\lib\\libaggfontwin32tt.a\" -L..\\..\\wxPython-src-2.8.8.1\\bld\\lib -mno-cygwin -mwindows -mthreads  -mno-cygwin -mwindows -Wl,--subsystem,windows -mwindows -lwx_mswu_richtext-2.8 -lwx_mswu_aui-2.8 -lwx_mswu_xrc-2.8 -lwx_mswu_qa-2.8 -lwx_mswu_html-2.8 -lwx_mswu_adv-2.8 -lwx_mswu_core-2.8 -lwx_baseu_xml-2.8 -lwx_baseu_net-2.8 -lwx_baseu-2.8"
        else:
            status, result, err_result = ProcessLogger(self.logger, "wx-config --cxxflags", no_stdout=True).spin()
            if status:
                self.logger.write_error("Unable to get wx cxxflags\n")
            cxx_flags = result.strip() + " -I../matiec/lib"
            
            status, result, err_result = ProcessLogger(self.logger, "wx-config --libs", no_stdout=True).spin()
            if status:
                self.logger.write_error("Unable to get wx libs\n")
            libs = result.strip() + " -lwxsvg"
        
        return [(Gen_C_file, cxx_flags)],libs,True,(SVGFileBaseName, file(SVGFilePath, "rb")), (FileBaseName, file(FilePath, "rb"))
    
    def BlockTypesFactory(self):
        
        SVGUIBlock_Types = []
        
        def GetSVGUIBlockType(type):
            for category in SVGUIBlock_Types:
                for blocktype in category["list"]:
                    if blocktype["name"] == type:
                        return blocktype
        setattr(self, "GetSVGUIBlockType", GetSVGUIBlockType)
        
        def generate_svgui_block(generator, block, body, link, order=False):
            name = block.getinstanceName()
            block_id = self.GetElementIdFromName(name)
            if block_id == None:
                raise ValueError, "No corresponding block found"
            type = block.gettypeName()
            block_infos = GetSVGUIBlockType(type)
            current_location = ".".join(map(str, self.GetCurrentLocation()))
            if not generator.ComputedBlocks.get(block, False) and not order:
                generator.ComputedBlocks[block] = True
                for num, variable in enumerate(block.inputVariables.getvariable()):
                    connections = variable.connectionPointIn.getconnections()
                    input_info = (generator.TagName, "block", block.getlocalId(), "input", num)
                    if connections and len(connections) == 1:
                        parameter = "%sQ%s%s.%d.%d"%("%", TYPECONVERSION[block_infos["inputs"][num][1]], current_location, block_id, num+1)
                        value = generator.ComputeFBDExpression(body, connections[0])
                        generator.Program += [(generator.CurrentIndent, ()),
                                              (parameter, input_info),
                                              (" := ", ())]
                        generator.Program += generator.ExtractModifier(variable, value, input_info)
                        generator.Program += [(";\n", ())]
            if link:
                connectionPoint = link.getposition()[-1]
                for num, variable in enumerate(block.outputVariables.getvariable()):
                    blockPointx, blockPointy = variable.connectionPointOut.getrelPositionXY()
                    output_info = (generator.TagName, "block", block.getlocalId(), "output", num)
                    if block.getx() + blockPointx == connectionPoint.getx() and block.gety() + blockPointy == connectionPoint.gety():
                        return [("%sI%s%s.%d.%d"%("%", TYPECONVERSION[block_infos["outputs"][num][1]], current_location, block_id, num+1), output_info)]
                raise ValueError, "No output variable found"
            else:
                return None

        def initialise_block(type, name, block = None):
            block_id = self.GetElementIdFromName(name)
            if block_id == None:
                raise ValueError, "No corresponding block found"
            block_infos = GetSVGUIBlockType(type)
            current_location = ".".join(map(str, self.GetCurrentLocation()))
            variables = []
            if block is not None:
                input_variables = block.inputVariables.getvariable()
                output_variables = block.outputVariables.getvariable()
            else:
                input_variables = None
                output_variables = None
            for num, (input_name, input_type, input_modifier) in enumerate(block_infos["inputs"]):
                if input_variables is not None and num < len(input_variables):
                    connections = input_variables[num].connectionPointIn.getconnections()
                if input_variables is None or connections and len(connections) == 1:
                    variables.append((input_type, None, "%sQ%s%s.%d.%d"%("%", TYPECONVERSION[input_type], current_location, block_id, num+1), None))
            for num, (output_name, output_type, output_modifier) in enumerate(block_infos["outputs"]):
                variables.append((output_type, None, "%sI%s%s.%d.%d"%("%", TYPECONVERSION[input_type], current_location, block_id, num+1), None))
            return variables

        SVGUIBlock_Types.extend([{"name" : "SVGUI function blocks", "list" :
                [{"name" : "Container", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none")], 
                    "outputs" : [],
                    "comment" : "SVGUI Container",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "Button", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("Value","BOOL","none")], 
                    "outputs" : [("State","BOOL","none")],
                    "comment" : "SVGUI Button",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "TextCtrl", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("SetText","STRING","none")], 
                    "outputs" : [("Text","STRING","none")],
                    "comment" : "SVGUI Text Control",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "ScrollBar", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("SetThumb","UINT","none"),("SetRange","UINT","none"),("SetPosition","UINT","none")], 
                    "outputs" : [("Position","UINT","none")],
                    "comment" : "SVGUI ScrollBar",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "NoteBook", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("SetSelected","BOOL","none")], 
                    "outputs" : [("Selected","UINT","none")],
                    "comment" : "SVGUI Notebook",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "RotatingCtrl", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("SetAngle","REAL","none")], 
                    "outputs" : [("Angle","REAL","none")],
                    "comment" : "SVGUI Rotating Control",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "Transform", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("SetX","REAL","none"),("SetY","REAL","none"),("SetXScale","REAL","none"),("SetYScale","REAL","none"),("SetAngle","REAL","none")], 
                    "outputs" : [("X","REAL","none"),("Y","REAL","none")],
                    "comment" : "SVGUI Transform",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
               ]}
        ])

        return SVGUIBlock_Types


class _SVGUICGenerator(SVGUICGenerator):

    def __init__(self, controler, elements, svgfile, xmlfile, current_location):
        SVGUICGenerator.__init__(self, elements, svgfile, xmlfile)
        
        self.CurrentLocation = current_location
        self.Controler = controler

    def GenerateProgramHeadersPublicVars(self):
        text = """
    void OnPlcOutEvent(wxEvent& event);

    void Retrieve();
    void Publish();
    void Initialize();
"""
#        text += "    void Print();\n"
        return text
    
    def GenerateIECVars(self):
        text = ""
        for element in self.Elements:
            text += "STATE_TYPE out_state_%d;\n"%element.getid()
            text += "STATE_TYPE in_state_%d;\n"%element.getid()
        text +="\n"
        current_location = "_".join(map(str, self.CurrentLocation))
        #Declaration des variables
        for element in self.Elements:
            block_infos = self.Controler.GetSVGUIBlockType(SVGUIFB_Types[GetElementType(element)])
            block_id = element.getid()
            for i, input in enumerate(block_infos["inputs"]):
                element_c_type = CTYPECONVERSION[input[1]]
                variable = "__Q%s%s_%d_%d"%(TYPECONVERSION[input[1]], current_location, block_id, i + 1)
                text += "%s beremiz%s;\n"%(element_c_type, variable)
                text += "%s* %s = &beremiz%s;\n"%(element_c_type, variable, variable)
                text += "%s _copy%s;\n"%(element_c_type, variable)
            for i, output in enumerate(block_infos["outputs"]):
                element_c_type = CTYPECONVERSION[output[1]]
                variable = "__I%s%s_%d_%d"%(TYPECONVERSION[output[1]], current_location, block_id, i + 1)
                text += "%s beremiz%s;\n"%(element_c_type, variable)
                text += "%s* %s = &beremiz%s;\n"%(element_c_type, variable, variable)
                text += "%s _copy%s;\n"%(element_c_type, variable)
            text +="\n"
        return text
    
    def GenerateGlobalVarsAndFuncs(self, size):
        text = """#include "iec_types.h"
#ifdef __WXMSW__
#define COMPARE_AND_SWAP_VAL(Destination, comparand, exchange) InterlockedCompareExchange(Destination, exchange, comparand)
#define THREAD_RETURN_TYPE DWORD WINAPI
#define STATE_TYPE long int
#else
#define COMPARE_AND_SWAP_VAL(Destination, comparand, exchange) __sync_val_compare_and_swap(Destination, comparand, exchange)
#define THREAD_RETURN_TYPE void*
#define STATE_TYPE volatile int
#endif

"""
        
        text += self.GenerateIECVars()
        
        text += """IMPLEMENT_APP_NO_MAIN(SVGViewApp);
SVGViewApp *myapp = NULL;
wxSemaphore MyInitSem;

#ifdef __WXMSW__
HANDLE wxMainLoop;
DWORD wxMainLoopId;
#else
pthread_t wxMainLoop;
#endif

"""

        text += """int myargc = 0;
char** myargv = NULL;
        
#define UNCHANGED 1
#define PLC_BUSY 2
#define CHANGED 3
#define GUI_BUSY 4
#ifdef __WXMSW__
#else
#endif

bool refresh = false;
bool refreshing = false;

THREAD_RETURN_TYPE InitWxEntry(void* args)
{
  wxEntry(myargc,myargv);
  myapp = NULL;
  MyInitSem.Post();
  return 0;
}

"""

        text += """
bool SVGViewApp::OnInit()
{
  #ifndef __WXMSW__
    setlocale(LC_NUMERIC, "C");
  #endif
"""
        
        text += """  frame = new MainFrame(NULL, wxT("Program"),wxDefaultPosition, wxSize(%d, %d));
  frame->Show();
  myapp = this;
"""%size
        text += """  return true;
}

extern "C" {

int __init_%(location)s(int argc, char** argv)
{
  myargc = argc;
  myargv = argv;
#ifdef __WXMSW__
  wxMainLoop = CreateThread(NULL, 0, InitWxEntry, 0, 0, &wxMainLoopId);
#else
  pthread_create(&wxMainLoop, NULL, InitWxEntry, NULL);
#endif
  MyInitSem.Wait();
  return 0;
}

void __cleanup_%(location)s()
{
  if(myapp){
      wxCloseEvent event(wxEVT_CLOSE_WINDOW);
      myapp->frame->AddPendingEvent(event);
      myapp = NULL;
  }
  MyInitSem.Wait();
}

void __retrieve_%(location)s()
{
  if(myapp){
    myapp->frame->m_svgCtrl->Retrieve();
  }        
}

void __publish_%(location)s()
{
  if(myapp){
    myapp->frame->m_svgCtrl->Publish();
  }
}

}

IEC_STRING wxStringToIEC_STRING(wxString s)
{
  IEC_STRING res = {0,""};
  int i;
  for(i = 0; i<s.Length() && i<STR_MAX_LEN; i++)
    res.body[i] = s.GetChar(i);
  res.len = i;
  return res;
}

"""%{"location" : "_".join(map(str, self.CurrentLocation))}
        
        return text
    
    def GenerateProgramEventTable(self):
        text = """BEGIN_DECLARE_EVENT_TYPES()
DECLARE_LOCAL_EVENT_TYPE( EVT_PLC, wxNewEventType() )
END_DECLARE_EVENT_TYPES()
         
DEFINE_LOCAL_EVENT_TYPE( EVT_PLC )

"""     
        #Event Table Declaration
        text += "BEGIN_EVENT_TABLE(Program, SVGUIWindow)\n"
        for element in self.Elements:
            element_type = GetElementType(element)
            element_name = element.getname()
            if element_type == ITEM_BUTTON:
                text += "  EVT_BUTTON (SVGUIID(\"%s\"), Program::On%sClick)\n"%(element_name, element_name)
            elif element_type in [ITEM_SCROLLBAR, ITEM_ROTATING, ITEM_TRANSFORM]:
                text += "  EVT_COMMAND_SCROLL_THUMBTRACK (SVGUIID(\"%s\"), Program::On%sChanging)\n"%(element_name, element_name)
            elif element_type == ITEM_NOTEBOOK:
                text += "  EVT_NOTEBOOK_PAGE_CHANGED (SVGUIID(\"%s\"), Program::On%sTabChanged)\n"%(element_name, element_name)
        text += "  EVT_CUSTOM(EVT_PLC, wxID_ANY, Program::OnPlcOutEvent)\n"
        text += "END_EVENT_TABLE()\n\n"
        return text
    
    def GenerateProgramInitFrame(self):
        text = """MainFrame::MainFrame(wxWindow *parent, const wxString& title, const wxPoint& pos,const wxSize& size, long style): wxFrame(parent, wxID_ANY, title, pos, size, style)
{
  wxFileName svgfilepath(wxTheApp->argv[1], wxT("%s"));
  wxFileName xmlfilepath(wxTheApp->argv[1], wxT("%s"));

  m_svgCtrl = new Program(this);
  if (m_svgCtrl->LoadFiles(svgfilepath.GetFullPath(), xmlfilepath.GetFullPath()))
  {
    Show(true);
    m_svgCtrl->SetFocus();
    m_svgCtrl->SetFitToFrame(true);
    m_svgCtrl->InitScrollBars();
    m_svgCtrl->Initialize();
    m_svgCtrl->Update();
  }
  else
  {
    printf("Error while opening SVGUI files\\n");
  }
}


"""%(self.SVGFilePath, self.XMLFilePath)

        return text
    
    def GenerateProgramInitProgram(self):
        text = "Program::Program(wxWindow* parent):SVGUIWindow(parent)\n{\n"
        for element in self.Elements:
            text += "    out_state_%d = UNCHANGED;\n"%element.getid()
            text += "    in_state_%d = UNCHANGED;\n"%element.getid()
        text += "}\n\n"
        return text
    
    def GenerateProgramEventFunctions(self):
        text = ""
        current_location = "_".join(map(str, self.CurrentLocation))
        for element in self.Elements:
            element_type = GetElementType(element)
            element_lock = """
  if (COMPARE_AND_SWAP_VAL(&in_state_%d, CHANGED, GUI_BUSY) == CHANGED ||
      COMPARE_AND_SWAP_VAL(&in_state_%d, UNCHANGED, GUI_BUSY) == UNCHANGED) {
"""%(element.getid(), element.getid())
            element_unlock = """
    COMPARE_AND_SWAP_VAL(&in_state_%d, GUI_BUSY, CHANGED);
    event.Skip();
  }else{
      /* re post event for idle */
      AddPendingEvent(event);
  }
}

"""%element.getid()
            element_name = element.getname()
                
            if element_type == ITEM_BUTTON:
                text += """void Program::On%sClick(wxCommandEvent& event)
{
  SVGUIButton* button = (SVGUIButton*)GetElementByName(wxT("%s"));\n"""%(element_name, element_name)
                text += element_lock
                text += "    _copy__IX%s_%d_1 = button->GetToggle();\n"%(current_location, element.getid())
                text += element_unlock
            elif element_type == ITEM_ROTATING:
                text += """void Program::On%sChanging(wxScrollEvent& event)
{
  SVGUIRotatingCtrl* rotating = (SVGUIRotatingCtrl*)GetElementByName(wxT("%s"));
"""%(element_name, element_name)
                text += element_lock
                text += "    _copy__ID%s_%d_1 = rotating->GetAngle();\n"%(current_location, element.getid())
                text += element_unlock
            elif element_type == ITEM_NOTEBOOK:
                text += """void Program::On%sTabChanged(wxNotebookEvent& event)
{
  SVGUINoteBook* notebook = (SVGUINoteBook*)GetElementByName(wxT("%s"));
"""%(element_name, element_name)
                text += element_lock
                text += "    _copy__IB%s_%d_1 = notebook->GetCurrentPage();\n"%(current_location, element.getid())
                text += element_unlock
            elif element_type == ITEM_TRANSFORM:
                text += """void Program::On%sChanging(wxScrollEvent& event)
{
  SVGUITransform* transform = (SVGUITransform*)GetElementByName(wxT("%s"));
"""%(element_name, element_name)
                text += element_lock
                text += "    _copy__ID%s_%d_1 = transform->GetX();\n"%(current_location, element.getid())
                text += "    _copy__ID%s_%d_2 = transform->GetY();\n"%(current_location, element.getid())
                text += element_unlock
        
        text += "/* OnPlcOutEvent update GUI with provided IEC __Q* PLC output variables */\n"
        text += """void Program::OnPlcOutEvent(wxEvent& event)
{
  SVGUIElement* element;
  
  refreshing = true;


"""
        for element in self.Elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            
            text += """  if (COMPARE_AND_SWAP_VAL(&out_state_%(id)d, CHANGED, GUI_BUSY) == CHANGED)
  {
    element = (SVGUIElement*)GetElementById(wxT("%(id)d"));
            
    if (_copy__QX%(location)s_%(id)d_1 != element->IsVisible()) {
      if (_copy__QX%(location)s_%(id)d_1)
        element->Show();
      else
        element->Hide();
    }
    if (_copy__QX%(location)s_%(id)d_2 != element->IsEnabled()) {
      if (_copy__QX%(location)s_%(id)d_2)
        element->Enable();
      else
        element->Disable();
    }
"""%texts
            if element_type == ITEM_BUTTON:
                text += """    if (_copy__QX%(location)s_%(id)d_3 != ((SVGUIButton*)element)->GetToggle())
      ((SVGUIButton*)element)->SetToggle(_copy__QX%(location)s_%(id)d_3);
"""%texts
            elif element_type == ITEM_TEXT:
                text += """    if (((SVGUITextCtrl*)element)->GetValue().compare(_copy__QX%(location)s_%(id)d_3))
    {
      wxString str = wxString::FromAscii(_copy__QB%(location)s_%(id)d_3);
      ((SVGUITextCtrl*)element)->SetText(str);
    }
"""%texts
            elif  element_type == ITEM_SCROLLBAR:
                text += """    if (_copy__QW%(location)s_%(id)d_3 != ((SVGUIScrollBar*)element)->GetThumbPosition() ||
        _copy__QW%(location)s_%(id)d_4 != ((SVGUIScrollBar*)element)->GetThumbSize() ||
        _copy__QW%(location)s_%(id)d_5 != ((SVGUIScrollBar*)element)->GetRange())
      ((SVGUIScrollBar*)element)->Init_ScrollBar(_copy__QW%(location)s_%(id)d_3, _copy__QW%(location)s_%(id)d_4, _copy__QW%(location)s_%(id)d_5);
"""%texts
            elif element_type == ITEM_ROTATING:
                text += """    if (_copy__QD%(location)s_%(id)d_3 != ((SVGUIRotatingCtrl*)element)->GetAngle())
      ((SVGUIRotatingCtrl*)element)->SetAngle(_copy__QD%(location)s_%(id)d_3);
"""%texts
            elif element_type == ITEM_NOTEBOOK:
                text += """    if (_copy__QB%(location)s_%(id)d_3 != ((SVGUINoteBook*)element)->GetCurrentPage())
      ((SVGUINoteBook*)element)->SetCurrentPage(_copy__QB%(location)s_%(id)d_3);
"""%texts
            elif element_type == ITEM_TRANSFORM:
                text += """    if (_copy__QD%(location)s_%(id)d_3 != ((SVGUITransform*)element)->GetX() ||
        _copy__QD%(location)s_%(id)d_4 != ((SVGUITransform*)element)->GetY())
      ((SVGUITransform*)element)->Move(_copy__QD%(location)s_%(id)d_3, _copy__QD%(location)s_%(id)d_4);
    if (_copy__QD%(location)s_%(id)d_5 != ((SVGUITransform*)element)->GetXScale() ||
        _copy__QD%(location)s_%(id)d_6 != ((SVGUITransform*)element)->GetYScale())
      ((SVGUITransform*)element)->Scale(_copy__QD%(location)s_%(id)d_5, _copy__QD%(location)s_%(id)d_6);
    if (_copy__QD%(location)s_%(id)d_7 != ((SVGUITransform*)element)->GetAngle())
      ((SVGUITransform*)element)->Rotate(_copy__QD%(location)s_%(id)d_7);
"""%texts
            text += "    COMPARE_AND_SWAP_VAL(&out_state_%(id)d, GUI_BUSY, UNCHANGED);\n  }\n"%texts
            
        text += """

  refreshing = false;

  event.Skip();
}

"""
        return text
    
    def GenerateProgramPrivateFunctions(self):
        current_location = "_".join(map(str, self.CurrentLocation))
        
        text = "void Program::Retrieve()\n{\n"
        for element in self.Elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            block_infos = self.Controler.GetSVGUIBlockType(SVGUIFB_Types[GetElementType(element)])
            if len(block_infos["outputs"]) > 0:
                text += """  if (COMPARE_AND_SWAP_VAL(&in_state_%(id)d, CHANGED, PLC_BUSY) == CHANGED) {
"""%texts
                for i, output in enumerate(block_infos["outputs"]):
                    texts["type"] = TYPECONVERSION[output[1]]
                    texts["pin"] = i + 1
                    
                    variable = "__I%(type)s%(location)s_%(id)d_%(pin)d"%texts
                    text +="    beremiz%s = _copy%s;\n"%(variable, variable)
                
                text += """    COMPARE_AND_SWAP_VAL(&in_state_%(id)d, PLC_BUSY, UNCHANGED);
  }
"""%texts
        text += "}\n\n" 

        text += "void Program::Publish()\n{\n  STATE_TYPE new_state;\n\n"
        for element in self.Elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            block_infos = self.Controler.GetSVGUIBlockType(SVGUIFB_Types[GetElementType(element)])
            
            text += """  if ((new_state = COMPARE_AND_SWAP_VAL(&out_state_%(id)d, UNCHANGED, PLC_BUSY)) == UNCHANGED ||
       (new_state = COMPARE_AND_SWAP_VAL(&out_state_%(id)d, CHANGED, PLC_BUSY)) == CHANGED) {
"""%texts
            for i, input in enumerate(block_infos["inputs"]):
                texts["type"] = TYPECONVERSION[input[1]]
                texts["pin"] = i + 1
                variable = "__Q%(type)s%(location)s_%(id)d_%(pin)d"%texts
                text += "    if (_copy%s != beremiz%s) {\n"%(variable, variable)
                text += "      _copy%s = beremiz%s;\n"%(variable, variable)
                text += "      new_state = CHANGED;\n    }\n"%texts
            text += """    COMPARE_AND_SWAP_VAL(&out_state_%(id)d, PLC_BUSY, new_state);
    refresh |= new_state == CHANGED;
  }
"""%texts
        
        text += """  /* Replace this with determinist signal if called from RT */
  if (refresh && !refreshing) {
    wxCommandEvent event( EVT_PLC );
    AddPendingEvent(event);
    refresh = false;
  }
};

"""

        text += """void Program::Initialize()
{
  SVGUIElement* element;
"""
        for element in self.Elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            
            text += """
  element = (SVGUIElement*)GetElementById(wxT("%(id)d"));
  beremiz__QX%(location)s_%(id)d_1 = _copy__QX%(location)s_%(id)d_1 = element->IsVisible();
  beremiz__QX%(location)s_%(id)d_2 = _copy__QX%(location)s_%(id)d_2 = element->IsEnabled();
"""%texts
            if element_type == ITEM_BUTTON:
                text += "  beremiz__QX%(location)s_%(id)d_3 = _copy__QX%(location)s_%(id)d_3 = ((SVGUIButton*)element)->GetToggle();\n"%texts
                text += "  beremiz__IX%(location)s_%(id)d_1 = _copy__IX%(location)s_%(id)d_1 = ((SVGUIButton*)element)->GetToggle();\n"%texts
            elif element_type == ITEM_TEXT:
                text += "  beremiz__QB%(location)s_%(id)d_3 = _copy__QB%(location)s_%(id)d_3 = ((SVGUITextCtrl*)element)->GetValue();\n"%texts
                text += "  beremiz__IB%(location)s_%(id)d_1 = _copy__IB%(location)s_%(id)d_1 = ((SVGUITextCtrl*)element)->GetValue();\n"%texts
            elif element_type == ITEM_SCROLLBAR:
                text += "  beremiz__QW%(location)s_%(id)d_3 = _copy__QW%(location)s_%(id)d_3 = ((SVGUIScrollBar*)element)->GetThumbSize();\n"%texts
                text += "  beremiz__QW%(location)s_%(id)d_4 = _copy__QW%(location)s_%(id)d_4 = ((SVGUIScrollBar*)element)->GetRange();\n"%texts
                text += "  beremiz__QW%(location)s_%(id)d_5 = _copy__QW%(location)s_%(id)d_5 = ((SVGUIScrollBar*)element)->GetThumbPosition();\n"%texts
                text += "  beremiz__IW%(location)s_%(id)d_1 = _copy__IW%(location)s_%(id)d_1 = ((SVGUIScrollBar*)element)->GetThumbPosition();\n"%texts
            elif element_type == ITEM_ROTATING:
                text += "  beremiz__QD%(location)s_%(id)d_3 = _copy__QD%(location)s_%(id)d_3 = ((SVGUIRotatingCtrl*)element)->GetAngle();\n"%texts
                text += "  beremiz__ID%(location)s_%(id)d_1 = _copy__ID%(location)s_%(id)d_1 = ((SVGUIRotatingCtrl*)element)->GetAngle();\n"%texts
            elif element_type == ITEM_NOTEBOOK:
                text += "  beremiz__QB%(location)s_%(id)d_3 = _copy__QB%(location)s_%(id)d_3 = ((SVGUINoteBook*)element)->GetCurrentPage();\n"%texts
                text += "  beremiz__IB%(location)s_%(id)d_1 = _copy__IB%(location)s_%(id)d_1 = ((SVGUINoteBook*)element)->GetCurrentPage();\n"%texts
            elif element_type == ITEM_TRANSFORM:
                text += "  beremiz__QD%(location)s_%(id)d_3 = _copy__QD%(location)s_%(id)d_3 = ((SVGUITransform*)element)->GetX();\n"%texts
                text += "  beremiz__QD%(location)s_%(id)d_4 = _copy__QD%(location)s_%(id)d_4 = ((SVGUITransform*)element)->GetY();\n"%texts
                text += "  beremiz__QD%(location)s_%(id)d_5 = _copy__QD%(location)s_%(id)d_5 = ((SVGUITransform*)element)->GetXScale();\n"%texts
                text += "  beremiz__QD%(location)s_%(id)d_6 = _copy__QD%(location)s_%(id)d_6 = ((SVGUITransform*)element)->GetYScale();\n"%texts
                text += "  beremiz__QD%(location)s_%(id)d_7 = _copy__QD%(location)s_%(id)d_7 = ((SVGUITransform*)element)->GetAngle();\n"%texts
                text += "  beremiz__ID%(location)s_%(id)d_1 = _copy__ID%(location)s_%(id)d_1 = ((SVGUITransform*)element)->GetX();\n"%texts
                text += "  beremiz__ID%(location)s_%(id)d_2 = _copy__ID%(location)s_%(id)d_2 = ((SVGUITransform*)element)->GetY();\n"%texts
        
        text += "\n  MyInitSem.Post();\n}\n\n"
        return text
