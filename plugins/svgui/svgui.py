import os, shutil, sys
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "wxsvg", "SVGUIEditor"))
sys.path.append(os.path.join(base_folder, "plcopeneditor", "graphics"))

import wx

from SVGUIControler import *
from SVGUIEditor import *
from FBD_Objects import *

from wxPopen import ProcessLogger

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
    def _OpenView(self, logger):
        if not self._View:
            def _onclose():
                self._View = None
            def _onsave():
                self.GetPlugRoot().SaveProject()
            self._View = _SVGUIEditor(self.GetPlugRoot().AppFrame, self)
            self._View._onclose = _onclose
            self._View._onsave = _onsave
            self._View.Show()

    def _ImportSVG(self, logger):
        if not self._View:
            dialog = wx.FileDialog(self.GetPlugRoot().AppFrame, "Choose a SVG file", os.getcwd(), "",  "SVG files (*.svg)|*.svg|All files|*.*", wx.OPEN)
            if dialog.ShowModal() == wx.ID_OK:
                svgpath = dialog.GetPath()
                if os.path.isfile(svgpath):
                    shutil.copy(svgpath, os.path.join(self.PlugPath(), "gui.svg"))
                else:
                    logger.write_error("No such SVG file: %s\n"%svgpath)
            dialog.Destroy()

    def _ImportXML(self, logger):
        if not self._View:
            dialog = wx.FileDialog(self.GetPlugRoot().AppFrame, "Choose a XML file", os.getcwd(), "",  "XML files (*.xml)|*.xml|All files|*.*", wx.OPEN)
            if dialog.ShowModal() == wx.ID_OK:
                xmlpath = dialog.GetPath()
                if os.path.isfile(xmlpath):
                    shutil.copy(xmlpath, os.path.join(self.PlugPath(), "gui.xml"))
                else:
                    logger.write_error("No such XML file: %s\n"%xmlpath)
            dialog.Destroy()

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
    ]
    
    def OnPlugSave(self):
        self.SaveXMLFile()
        return True
    
    def GenerateProgramHeadersPublicVars(self, elements):
        text = """    void OnPlcOutEvent(wxEvent& event);

    void Retrieve();
    void Publish();
    void Initialize();
"""
#        text += "    void Print();\n"
        return text
    
    def GenerateIECVars(self, elements):
        text = ""
        for element in elements:
            text += "volatile int out_state_%d;\n"%element.getid()
            text += "volatile int in_state_%d;\n"%element.getid()
        text +="\n"
        current_location = "_".join(map(str, self.GetCurrentLocation()))
        #Declaration des variables
        for element in elements:
            block_infos = GetBlockType(SVGUIFB_Types[GetElementType(element)])
            block_id = element.getid()
            for i, input in enumerate(block_infos["inputs"]):
                element_c_type = CTYPECONVERSION[input[1]]
                variable = "__Q%s%s_%d_%d"%(TYPECONVERSION[input[1]], current_location, block_id, i + 1)
                text += "%s %s;\n"%(element_c_type, variable)
                text += "%s _copy%s;\n"%(element_c_type, variable)
            for i, output in enumerate(block_infos["outputs"]):
                element_c_type = CTYPECONVERSION[output[1]]
                variable = "__I%s%s_%d_%d"%(TYPECONVERSION[output[1]], current_location, block_id, i + 1)
                text += "%s %s;\n"%(element_c_type, variable)
                text += "%s _copy%s;\n"%(element_c_type, variable)
            text +="\n"
        return text
    
    def GenerateGlobalVarsAndFuncs(self, elements, size):
        text = "#include \"iec_std_lib.h\"\n\n"
        
        text += self.GenerateIECVars(elements)
        
        text += """IMPLEMENT_APP_NO_MAIN(SVGViewApp);
IMPLEMENT_WX_THEME_SUPPORT;
SVGViewApp *myapp = NULL;
pthread_t wxMainLoop;
"""
#        text += "pthread_t wxMainLoop,automate;\n"
        text += """int myargc = 0;
char** myargv = NULL;
        
#define UNCHANGED 1
#define PLC_BUSY 2
#define CHANGED 3
#define GUI_BUSY 4

bool refreshing = false;

void* InitWxEntry(void* args)
{
  wxEntry(myargc,myargv);
  return args;
}

"""
#        text += """void* SimulAutomate(void* args)
#{
#  while(1){
#    myapp->frame->m_svgCtrl->IN_"+self.BusNumber+"();
#    //printf(\"AUTOMATE\\n\");
#    myapp->frame->m_svgCtrl->OUT_"+self.BusNumber+"();
#    sleep(1);
#  }
#  return args;
#}
#
#"""
      
        text += """bool SVGViewApp::OnInit()
{
  #ifndef __WXMSW__
    setlocale(LC_NUMERIC, "C");
  #endif
"""
        #text += "  frame = new MainFrame(NULL, wxT(\"Program\"),wxDefaultPosition, wxSize(%d, %d));\n"%size
        text += """  frame = new MainFrame(NULL, wxT("Program"),wxDefaultPosition, wxDefaultSize);
  myapp = this;
"""
#        text += "  pthread_create(&automate, NULL, SimulAutomate, NULL);\n"
        text += """  return true;
}

extern "C" {

int __init_%(location)s(int argc, char** argv)
{
  myargc = argc;
  myargv = argv;
  pthread_create(&wxMainLoop, NULL, InitWxEntry, NULL);
}

void __cleanup_%(location)s()
{
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
  STRING res = {0,""};
  int i;
  for(i = 0; i<s.Length() && i<STR_MAX_LEN; i++)
    res.body[i] = s.GetChar(i);
  res.len = i;
  return res;
}

"""%{"location" : "_".join(map(str, self.GetCurrentLocation()))}
        
        return text
    
    def GenerateProgramEventTable(self, elements):
        text = ""        
        #text += "wxEVT_PLCOUT = wxNewEventType();\n\n";
        
        text += """BEGIN_DECLARE_EVENT_TYPES()
DECLARE_LOCAL_EVENT_TYPE( EVT_PLC, wxNewEventType() )
END_DECLARE_EVENT_TYPES()
         
DEFINE_LOCAL_EVENT_TYPE( EVT_PLC )

"""     
        #Event Table Declaration
        text += "BEGIN_EVENT_TABLE(Program, SVGUIWindow)\n"
        for element in elements:
            element_type = GetElementType(element)
            element_name = element.getname()
            if element_type == ITEM_BUTTON:
                text += "  EVT_BUTTON (SVGUIID(\"%s\"), Program::On%sClick)\n"%(element_name, element_name)
            elif element_type in [ITEM_SCROLLBAR, ITEM_ROTATING]:
                text += "  EVT_COMMAND_SCROLL_THUMBTRACK (SVGUIID(\"%s\"), Program::On%sChanged)\n"%(element_name, element_name)
            elif element_type == ITEM_NOTEBOOK:
                text += "  EVT_NOTEBOOK_PAGE_CHANGED (SVGUIID(\"%s\"), Program::On%sTabChanged)\n"%(element_name, element_name)
##            elif element_type in [ITEM_CONTAINER, ITEM_TRANSFORM]:
##                text += "  EVT_PAINT(Program::On%sPaint)\n"%element_name
        text += "  EVT_LEFT_UP (Program::OnClick)\n"
        text += "  EVT_CUSTOM( EVT_PLC, wxID_ANY, Program::OnPlcOutEvent )\n"
        text += "END_EVENT_TABLE()\n\n"
        return text
    
    def GenerateProgramInitFrame(self, elements):
        text = """MainFrame::MainFrame(wxWindow *parent, const wxString& title, const wxPoint& pos,const wxSize& size, long style): wxFrame(parent, wxID_ANY, title, pos, size, style)
{
  m_svgCtrl = new Program(this);
  if (m_svgCtrl->LoadFiles(wxT("%s"), wxT("%s")))
  {
    Show(true);
    m_svgCtrl->SetFocus();
    m_svgCtrl->SetFitToFrame(true);
    m_svgCtrl->RefreshScale();
    m_svgCtrl->InitScrollBars();
    m_svgCtrl->Initialize();
    m_svgCtrl->Update();
  }
  else
  {
    printf("Error while opening files\\n");
    exit(0);
  }
}


"""%(self.GetSVGFilePath(), self.GetFilePath())

        return text
    
    def GenerateProgramInitProgram(self, elements):
        text = "Program::Program(wxWindow* parent):SVGUIWindow(parent)\n{\n"
        for element in elements:
            text += "    out_state_%d = UNCHANGED;\n"%element.getid()
            text += "    in_state_%d = UNCHANGED;\n"%element.getid()
        text += "}\n\n"
        return text
    
    def GenerateProgramEventFunctions(self, elements):
        text = ""
        current_location = "_".join(map(str, self.GetCurrentLocation()))
        for element in elements:
            element_type = GetElementType(element)
            element_state = "  in_state_%d = %s;\n"%(element.getid(), "%s")
            element_name = element.getname()
                
            if element_type == ITEM_BUTTON:
                text += """void Program::On%sClick(wxCommandEvent& event)
{
  SVGUIButton* button = (SVGUIButton*)GetElementByName(wxT("%s"));\n"""%(element_name, element_name)
                text += element_state%"GUI_BUSY"
                text += "  _copy__IX%s_%d_1 = button->GetToggle();\n"%(current_location, element.getid())
                text += element_state%"CHANGED"
                text += "  event.Skip();\n}\n\n"
            elif element_type == ITEM_ROTATING:
                text += """void Program::On%sChanged(wxScrollEvent& event)
{
  SVGUIRotatingCtrl* rotating = (SVGUIRotatingCtrl*)GetElementByName(wxT("%s"));
"""%(element_name, element_name)
                text += element_state%"GUI_BUSY"
                text += "  _copy__ID%s_%d_1 = rotating->GetAngle();\n"%(current_location, element.getid())
                text += element_state%"CHANGED"
                text += "  event.Skip();\n}\n\n"
            elif element_type == ITEM_NOTEBOOK:
                text += """void Program::On%sTabChanged(wxNotebookEvent& event)
{
  SVGUINoteBook* notebook = (SVGUINoteBook*)GetElementByName(wxT("%s"));
"""%(element_name, element_name)
                text += element_state%"GUI_BUSY"
                text += "  _copy__IB%s_%d_1 = notebook->GetCurrentPage();\n"%(current_location, element.getid())
                text += element_state%"CHANGED"
                text += "  event.Skip();\n}\n\n"
            elif element_type == ITEM_TRANSFORM:
                text += """void Program::On%sPaint(wxPaintEvent& event)
{
  SVGUITransform* transform = (SVGUITransform*)GetElementByName(wxT("%s"));
"""%(element_name, element_name)
                text += element_state%"GUI_BUSY"
                text += "  _copy__ID%s_%d_1 = transform->GetX();\n"%(current_location, element.getid())
                text += "  _copy__ID%s_%d_2 = transform->GetY();\n"%(current_location, element.getid())
                text += element_state%"CHANGED"
                text += "  event.Skip();\n}\n\n"

        text += """void Program::OnChar(wxKeyEvent& event)
{
  SVGUIContainer* container = GetSVGUIRootElement();
  if (container->GetFocusedElementName() == wxT("TextCtrl"))
  {
    wxString focusedId = container->GetFocusedElement();
    SVGUITextCtrl* text = (SVGUITextCtrl*)GetElementById(focusedId);
    text->OnChar(event);
"""
        for element in elements:
            element_type = GetElementType(element)
            if element_type == ITEM_TEXT:
                texts = {"location" : current_location, "id" : element.getid()}
                
                text += """    if (focusedId == wxT("%(id)d"))
    {
      in_state_%(id)d = GUI_BUSY;
      _copy__IB%(location)s_%(id)d_1 = wxStringToIEC_STRING(text->GetValue());
      _copy__IX%(location)s_%(id)d_2 = true;
      in_state_%(id)d = CHANGED;
    }
"""%texts

        text += "  }\n  event.Skip();\n}\n\n"


        text += """void Program::OnClick(wxMouseEvent& event)
{
  SVGUIContainer* container = GetSVGUIRootElement();
  if (container->GetFocusedElementName() == wxT("ScrollBar"))
  {
    wxString focusedId = container->GetFocusedElement();
    SVGUIScrollBar* scrollbar = (SVGUIScrollBar*)GetElementById(focusedId);
    scrollbar->OnLeftDown(event);
"""
        for element in elements:
            element_type = GetElementType(element)
            if element_type == ITEM_SCROLLBAR:
                texts = {"location" : current_location, "id" : element.getid()}
                
                text += """    if (focusedId == wxT("%(id)d"))
    {
      unsigned int scrollPos = scrollbar->GetThumbPosition();
      _copy__IW%(location)s_%(id)d_1 = scrollPos;
      _copy__IX%(location)s_%(id)d_2 = true;\n"
    }
"""%texts

        text += "  }\n  event.Skip();\n}\n\n"

        
        text += "/* OnPlcOutEvent update GUI with provided IEC __Q* PLC output variables */\n"
        text += """void Program::OnPlcOutEvent(wxEvent& event)
{
  SVGUIElement* element;

  refreshing = true;

  wxMutexGuiEnter();
"""
        for element in elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            
            text += """  if (__sync_bool_compare_and_swap (&out_state_%(id)d, CHANGED, GUI_BUSY))
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
        copy__QD%(location)s_%(id)d_4 != ((SVGUITransform*)element)->GetY())
      transform->Move(_copy__QD%(location)s_%(id)d_3, _copy__QD%(location)s_%(id)d_4);
    if (_copy__QD%(location)s_%(id)d_5 != ((SVGUITransform*)element)->GetXScale() ||
        copy__QD%(location)s_%(id)d_6 != ((SVGUITransform*)element)->GetYScale())
      transform->Scale(_copy__QD%(location)s_%(id)d_5, _copy__QD%(location)s_%(id)d_6);
    if (_copy__QD%(location)s_%(id)d_7 != ((SVGUITransform*)element)->GetAngle())
      transform->Rotate(_copy__QD%(location)s_%(id)d_7);
"""%texts
            text += "    __sync_bool_compare_and_swap (&out_state_%(id)d, GUI_BUSY, UNCHANGED);\n  }\n"%texts
            
        text += """  wxMutexGuiLeave();

  refreshing = false;

  event.Skip();
}

"""
        return text
    
    def GenerateProgramPrivateFunctions(self, elements):
        current_location = "_".join(map(str, self.GetCurrentLocation()))
        
        text = "void Program::Retrieve()\n{\n"
        for element in elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            block_infos = GetBlockType(SVGUIFB_Types[GetElementType(element)])
            
            text += """  do{
    if ( __sync_val_compare_and_swap (&in_state_%(id)d, CHANGED, PLC_BUSY) == CHANGED){
"""%texts
            for i, output in enumerate(block_infos["outputs"]):
                texts["type"] = TYPECONVERSION[output[1]]
                texts["pin"] = i + 1
                
                variable = "__I%(type)s%(location)s_%(id)d_%(pin)d"%texts
                text +="      %s = _copy%s;\n"%(variable, variable)
            
            text += """    }
    else {
      break;
    }
"""
            #If GUI did change data while publishing, do it again (in real-time this should be avoided with priority stuff)
            text += "  }while(__sync_val_compare_and_swap (&in_state_%(id)s, PLC_BUSY, UNCHANGED) != PLC_BUSY);\n"%texts
        text += "}\n\n" 

        text += """void Program::Publish()
{
  bool refresh = false;
"""
        for element in elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            block_infos = GetBlockType(SVGUIFB_Types[GetElementType(element)])
            
            text += """  if ( __sync_bool_compare_and_swap (&out_state_%(id)d, UNCHANGED, PLC_BUSY) ||
       __sync_bool_compare_and_swap (&out_state_%(id)d, CHANGED, PLC_BUSY)) {
"""%texts
            for i, input in enumerate(block_infos["inputs"]):
                texts["type"] = TYPECONVERSION[input[1]]
                texts["pin"] = i + 1
                variable = "__Q%(type)s%(location)s_%(id)d_%(pin)d"%texts
                text += "    if (_copy%s != %s) {\n"%(variable, variable)
                text += "      _copy%s = %s;\n"%(variable, variable)
                text += "      out_state_%(id)d = CHANGED;\n    }\n"%texts
            text += """    if (out_state_%(id)d == CHANGED) {
      refresh = true;
    }
    else {
      out_state_%(id)d = UNCHANGED;
    }
  }
"""%texts
        
        text += """  /*Replace this with determinist signal if called from RT*/;
  if (refresh && !refreshing) {
    wxCommandEvent event( EVT_PLC );
    ProcessEvent(event);
  }
};

"""

        text += """void Program::Initialize()
{
  SVGUIElement* element;
"""
        for element in elements:
            element_type = GetElementType(element)
            texts = {"location" : current_location, "id" : element.getid()}
            
            text += """
  element = (SVGUIElement*)GetElementById(wxT("%(id)d"));
  __QX%(location)s_%(id)d_1 = 1;
  _copy__QX%(location)s_%(id)d_1 = 1;
  __QX%(location)s_%(id)d_2 = 1;
  _copy__QX%(location)s_%(id)d_2 = 1;
"""%texts
            if element_type == ITEM_BUTTON:
                text += "  _copy__IX%(location)s_%(id)d_1 = ((SVGUIButton*)element)->GetToggle();\n"%texts
            elif element_type == ITEM_TEXT:
                text += "  _copy__IB%(location)s_%(id)d_1 = ((SVGUITextCtrl*)element)->GetValue();\n"%texts
            elif element_type == ITEM_SCROLLBAR:
                text += "  _copy__IW%(location)s_%(id)d_1 = ((SVGUIScrollBar*)element)->GetThumbPosition();\n"%texts
            elif element_type == ITEM_ROTATING:
                text += "  _copy__ID%(location)s_%(id)d_1 = ((SVGUIRotatingCtrl*)element)->GetAngle();\n"%texts
            elif element_type == ITEM_NOTEBOOK:
                text += "  _copy__IB%(location)s_%(id)d_1 = ((SVGUINoteBook*)element)->GetCurrentPage();\n"%texts
            elif element_type == ITEM_TRANSFORM:
                text += "  _copy__ID%(location)s_%(id)d_1 = ((SVGUITransform*)element)->GetX();\n"%texts
                text += "  _copy__ID%(location)s_%(id)d_2 = ((SVGUITransform*)element)->GetY();\n"%texts
        text += "}\n\n"
        
        #DEBUG Fonction d'affichage
#        fct += "void Program::Print()\n{\n"
#        for element in elementsTab:
#            infos = element.getElementAttributes()
#            for info in infos:
#                if info["name"] == "id":
#                    element_id = str(info["value"])
#            type = element.GetElementInfos()["type"]
#            FbdBlock = self.GetBlockType(type)
#            element_num_patte = 1
#            for input in FbdBlock["inputs"]:
#                element_type = TYPECONVERSION[input[1]]
#                c_type = CPRINTTYPECONVERSION[input[1]]
#                var = "_copy__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)
#                fct +="  printf(\""+var+": %"+c_type+"\\n\","+var+");\n"
#                element_num_patte +=1
#            element_num_patte = 1
#            for output in FbdBlock["outputs"]:
#                element_type = TYPECONVERSION[output[1]]
#                c_type = CPRINTTYPECONVERSION[output[1]]
#                var = "_copy__I"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)
#                fct +="  printf(\""+var+": %"+c_type+"\\n\","+var+");\n"
#                element_num_patte +=1
        #fct +="    wxPostEvent(Program,wxEVT_PLCOUT);\n"
#        fct +="};\n\n"    
        return text
    
    def PlugGenerate_C(self, buildpath, locations, logger):
        progname = "SVGUI_%s"%"_".join(map(str, self.GetCurrentLocation()))
        self.GenerateProgram((0, 0), buildpath, progname)
        Gen_C_file = os.path.join(buildpath, progname+".cpp" )
        
        status, result, err_result = ProcessLogger(logger, "wx-config --cxxflags", no_stdout=True).spin()
        if status:
            logger.write_error("Unable to get wx cxxflags\n")
        cxx_flags = result.strip() + " -I../matiec/lib"
        
        status, result, err_result = ProcessLogger(logger, "wx-config --libs", no_stdout=True).spin()
        if status:
            logger.write_error("Unable to get wx libs\n")
        libs = result.strip() + " -lwxsvg"
        
        return [(Gen_C_file, cxx_flags)],libs,True
    
    def BlockTypesFactory(self):
        def generate_svgui_block(generator, block, body, link, order=False):
            name = block.getinstanceName()
            block_id = self.GetElementIdFromName(name)
            if block_id == None:
                raise ValueError, "No corresponding block found"
            type = block.gettypeName()
            block_infos = GetBlockType(type)
            current_location = ".".join(map(str, self.GetCurrentLocation()))
            if not generator.ComputedBlocks.get(name, False) and not order:
                for num, variable in enumerate(block.inputVariables.getvariable()):
                    connections = variable.connectionPointIn.getconnections()
                    if connections and len(connections) == 1:
                        parameter = "%sQ%s%s.%d.%d"%("%", TYPECONVERSION[block_infos["inputs"][num][1]], current_location, block_id, num+1)
                        value = generator.ComputeFBDExpression(body, connections[0])
                        generator.Program += ("  %s := %s;\n"%(parameter, generator.ExtractModifier(variable, value)))
                generator.ComputedBlocks[block] = True
            if link:
                connectionPoint = link.getposition()[-1]
                for num, variable in enumerate(block.outputVariables.getvariable()):
                    blockPointx, blockPointy = variable.connectionPointOut.getrelPositionXY()
                    if block.getx() + blockPointx == connectionPoint.getx() and block.gety() + blockPointy == connectionPoint.gety():
                        return "%sI%s%s.%d.%d"%("%", TYPECONVERSION[block_infos["outputs"][num][1]], current_location, block_id, num+1)
                raise ValueError, "No output variable found"
            else:
                return None

        def initialise_block(type, name, block = None):
            block_id = self.GetElementIdFromName(name)
            if block_id == None:
                raise ValueError, "No corresponding block found"
            block_infos = GetBlockType(type)
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

        return [{"name" : "SVGUI function blocks", "list" :
                [{"name" : "Container", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none")], 
                    "outputs" : [],
                    "comment" : "SVGUI Container",
                    "generate" : generate_svgui_block, "initialise" : initialise_block},
                {"name" : "Button", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("Show","BOOL","none"),("Enable","BOOL","none"),("Toggle","BOOL","none")], 
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
        ]

