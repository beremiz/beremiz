import os, sys
base_folder = os.path.split(sys.path[0])[0]
sys.path.append(os.path.join(base_folder, "wxsvg", "defeditor"))

from DEFControler import *
from defeditor import *
from FBD_Objects import *

class _EditorFramePlug(EditorFrame):
    """
    This Class add IEC specific features to the SVGUI DEFEditor :
        - FDB preview
        - FBD begin drag 
    """
    def __init__(self,controller):
        EditorFrame.__init__(self,controller)
        self.FbdWindow = wx.Panel(name='fbdwindow',parent=self.EditorPanel,
                                       pos=wx.Point(300, 355),size=wx.Size(240, 240),
                                       style=wx.TAB_TRAVERSAL|wx.SIMPLE_BORDER)
        self.FbdWindow.SetBackgroundColour(wxColour(255,255,255))
        self.FbdWindow.Bind(wx.EVT_LEFT_DOWN, self.OnFbdClick)
        wx.EVT_PAINT(self.FbdWindow,self.OnPaintFBD)
        
        self.FbdData = None
        self.RefreshProjectTree()
        if (controller.SvgFilepath):
            self.OpenSVGFile(controller.filepath)
            self.mySVGctrl.Refresh()
        self.OnNewFile()
        self.RefreshFBD()
        
    def SetFbdDragData(self,selected_type):
        self.FbdBlock = FBD_Block(parent=self.FbdWindow,type=selected_type,name='')
        name = self.Controler.GetSelectedElementName()
        self.FbdData = str((selected_type,"functionBlock", name))
        
    def RefreshFBD(self):
        dc = wx.ClientDC(self.FbdWindow)
        dc.Clear()
        if self.Controler.HasOpenedProject():
            selected_type = self.Controler.GetSelectedElementType()
            if selected_type:
                self.SetFbdDragData(selected_type)
                self.FbdBlock = FBD_Block(parent=self.FbdWindow,type=selected_type,name='')
                width,height = self.FbdBlock.GetMinSize()
                self.FbdBlock.SetSize(width,height)
                clientsize = self.FbdWindow.GetClientSize()
                x = (clientsize.width - width) / 2
                y = (clientsize.height - height) / 2
                self.FbdBlock.SetPosition(x, y)
                self.FbdBlock.Draw(dc)
                
    def OnPaintFBD(self,event):
        self.RefreshFBD()
        event.Skip()
        
    def OnFbdClick(self,event):
        if self.FbdData:
            data = wx.TextDataObject(self.FbdData)
            DropSrc = wx.DropSource(self.FbdWindow)
            DropSrc.SetData(data)
            DropSrc.DoDragDrop()
            
    def OnProjectTreeItemSelected(self,event):
        EditorFrame.OnProjectTreeItemSelected(self,event)
        self.RefreshFBD()
        
    def OnNew(self,event):
        EditorFrame.OnNew(self,event)
        self.RefreshFBD()
        
    def OnOpen(self,event):
        EditorFrame.OnOpen(self,event)
        self.RefreshFBD()
        
    def OnGenerate(self,event):
        self.SaveProject()
        self.Controler.PlugGenerate_C(sys.path[0],(0,0,4,5),None)
        event.Skip()    
    
    def OnClose(self, event):
        self.OnPlugClose()
        event.Skip()
    
"""
TYPECONVERSION = {"BOOL" : "X", "SINT" : "B", "INT" : "W", "DINT" : "D", "LINT" : "L",
    "USINT" : "B", "UINT" : "W", "UDINT" : "D", "ULINT" : "L", "REAL" : "D", "LREAL" : "L",
    "STRING" : "B", "BYTE" : "B", "WORD" : "W", "DWORD" : "D", "LWORD" : "L", "WSTRING" : "W"}
"""
TYPECONVERSION = {"BOOL" : "X", "UINT" : "W","REAL" : "D","STRING" : "B"}
CTYPECONVERSION = {"BOOL" : "bool", "UINT" : "unsigned int", "STRING" : "char*", "REAL" : "float"}
CPRINTTYPECONVERSION = {"BOOL" : "d", "UINT" : "d", "STRING" : "s", "REAL" : "f"}
class RootClass(DEFControler):

    def __init__(self, buspath):
        DEFControler.__init__(self)
        filepath = os.path.join(self.PlugPath(), "gui.def")
        
        if os.path.isfile(filepath):
            svgfile = os.path.join(self.PlugPath(), "gui.svg")
            if os.path.isfile(svgfile):
                self.SvgFilepath = svgfile
            self.OpenXMLFile(filepath)
        else:
            self.CreateRootElement()
            self.SetFilePath(filepath)

    def OnPlugSave(self):
        self.SaveXMLFile()
        return True
    
    def GenerateProgramHeadersPublicVars(self):
        fct = ""
        fct += "    void OnPlcOutEvent(wxEvent& event);\n\n"
        fct += "    void IN_"+self.BusNumber+"();\n"
        fct += "    void OUT_"+self.BusNumber+"();\n"
        fct += "    void Initialize();\n"
        fct += "    void SetNoChanges();\n"
        fct += "    void Print();\n"
        return fct
    
    def GenerateProgramHeadersPrivateVars(self):
        text = ""
        elementsTab = self.GetElementsTab()
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            text += "    bool flag_"+element_id+";\n"
            text += "    volatile int step_"+element_id+";\n"
        text +="\n"
        #Declaration des variables
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            element_num_patte = 1
            for input in FbdBlock["inputs"]:
                element_type = TYPECONVERSION[input[1]]
                element_c_type = CTYPECONVERSION[input[1]]
                line = "__I"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)+";\n"
                text += "    "+element_c_type+" "+line
                text += "    "+element_c_type+" _copy"+line
                element_num_patte +=1
            element_num_patte = 1
            for output in FbdBlock["outputs"]:
                element_type = TYPECONVERSION[output[1]]
                element_c_type = CTYPECONVERSION[output[1]]
                    
                line = "__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)+";\n"
                text += "    "+element_c_type+" "+line
                text += "    "+element_c_type+" _copy"+line
                element_num_patte +=1
            text +="\n"
        return text
    
    def GenerateGlobalVarsAndFuncs(self):
        text = ""
        text += "IMPLEMENT_APP_NO_MAIN(SVGViewApp);\n"
        text += "IMPLEMENT_WX_THEME_SUPPORT;\n"
        text += "SVGViewApp *myapp;\n"
        text += "pthread_t wxMainLoop,automate;\n"
        text += "int myargc;\n"
        text += "char** myargv;\n\n"
        
        text += "#define FREE_AND_NO_CHANGES 1 \n"
        text += "#define PLC_BUSY 2 \n"
        text += "#define FREE_AND_CHANGES 3 \n"
        text += "#define PLC_OUT_BUSY 4 \n\n"
        
        
        text += "void* InitWxEntry(void* args)\n{\n"
        text += "  wxEntry(myargc,myargv);\n"
        text += "  return args;\n"
        text += "}\n\n"
        
        text += "void* SimulAutomate(void* args)\n{\n"
        text += "  while(1){\n"
        text += "    myapp->frame->m_svgCtrl->IN_"+self.BusNumber+"();\n"
        text += "    //printf(\"AUTOMATE\\n\");\n"
        text += "    myapp->frame->m_svgCtrl->OUT_"+self.BusNumber+"();\n"
        text += "    sleep(1);\n"
        text += "  }\n"
        text += "  return args;\n"
        text += "}\n\n"
        
        if (self.SVGUIRootElement):
            width = self.SVGUIRootElement.GetBBox().GetWidth()
            height = self.SVGUIRootElement.GetBBox().GetHeight()
        else :
            width = 250
            height = 350
        text += "bool SVGViewApp::OnInit()\n{\n"
        text += "  #ifndef __WXMSW__\n"
        text += "    setlocale(LC_NUMERIC, \"C\");\n"
        text += "  #endif\n"
        text += "  frame = new MainFrame(NULL, wxT(\"Program\"),wxDefaultPosition, wxSize((int)"+str(width)+", (int)"+str(height)+"));\n"
        text += "  myapp = this;\n"
        text += "  pthread_create(&automate, NULL, SimulAutomate, NULL);\n"
        text += "  return true;\n"
        text += "}\n\n"
        
        text += "int main(int argc, char** argv)\n{\n"
        text += "  myargc = argc;\n"
        text += "  myargv = argv;\n"
        text += "  pthread_create(&wxMainLoop, NULL, InitWxEntry, NULL);\n"
        text += "  pause();\n"
        text += "}\n\n"
        
        return text
    
    def GenerateProgramEventTable(self):
        evt = ""        
        elementsTab = self.GetElementsTab()
        #evt += "wxEVT_PLCOUT = wxNewEventType();\n\n";
        evt += "BEGIN_DECLARE_EVENT_TYPES()\n"
        evt += "DECLARE_LOCAL_EVENT_TYPE( EVT_PLC, wxNewEventType() )\n"
        evt += "END_DECLARE_EVENT_TYPES()\n\n"
         
        evt += "DEFINE_LOCAL_EVENT_TYPE( EVT_PLC )\n\n"
        #Event Table Declaration
        evt += "BEGIN_EVENT_TABLE(Program, SVGUIWindow)\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
                if info["name"] == "name":
                    element_name = str(info["value"])
            type = element.GetElementInfos()["type"]
            if type == "Button":
                evt += "  EVT_BUTTON (SVGUIID(\""+element_id+"\"), Program::On"+element_name+"Click)\n"
            elif type == "ScrollBar":
                pass
                #evt += "  EVT_LEFT_UP (Program::OnClick)\n"
                #evt += "  EVT_COMMAND_SCROLL_THUMBTRACK (SVGUIID(\""+element_id+"\"), Program::On"+element_name+"Changed)\n"
            elif type == "RotatingCtrl":
                evt += "  EVT_COMMAND_SCROLL_THUMBTRACK (SVGUIID(\""+element_id+"\"), Program::On"+element_name+"Changed)\n"
            elif type == "NoteBook":
                evt += "  EVT_NOTEBOOK_PAGE_CHANGED (SVGUIID(\""+element_id+"\"), Program::On"+element_name+"TabChanged)\n"
            elif type == "Container" or type == "Transform":
                evt += "  EVT_PAINT(Program::On"+element_name+"Paint)\n"
        evt += "  EVT_LEFT_UP (Program::OnClick)\n"
        evt += "  EVT_CUSTOM( EVT_PLC, wxID_ANY, Program::OnPlcOutEvent )\n"
        evt += "END_EVENT_TABLE()\n\n"
        return evt
    
    def GenerateProgramInitFrame(self):
        text = "MainFrame::MainFrame(wxWindow *parent, const wxString& title, const wxPoint& pos,const wxSize& size, long style): wxFrame(parent, wxID_ANY, title, pos, size, style)\n{\n"
        text += "  m_svgCtrl = new Program(this);\n"
        text += "  if (m_svgCtrl->LoadFiles(wxT(\""+self.SvgFilepath+"\"), wxT(\""+self.filepath+"\")))\n"
        text += "  {\n"
        text += "    Show(true);\n"
        text += "    m_svgCtrl->SetFocus();\n"
        text += "    m_svgCtrl->SetFitToFrame(true);\n"
        text += "    m_svgCtrl->RefreshScale();\n"
        text += "    m_svgCtrl->InitScrollBars();\n"
        text += "    m_svgCtrl->Initialize();\n"
        text += "    m_svgCtrl->Update();\n"
        text += "    //m_svgCtrl->Print();\n"
        text += "  }\n"
        text += "  else\n"
        text += "  {\n"
        text += "    printf(\"Error while opening files\\n\");\n"
        text += "    exit(0);\n"
        text += "  }\n"
        text += "}\n\n\n"
        return text
    
    def GenerateProgramInitProgram(self):
        elementsTab = self.GetElementsTab()
        text = "Program::Program(wxWindow* parent):SVGUIWindow(parent)\n{\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            text += "    flag_"+element_id+" = true;\n"
            text += "    step_"+element_id+" = FREE_AND_NO_CHANGES;\n"
        text += "}\n\n"
        return text
    
    def GenerateProgramEventFunctions(self):
        fct=""
        elementsTab = self.GetElementsTab()
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
                if info["name"] == "name":
                    element_name = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            if type == "Button":
                fct += "void Program::On"+element_name+"Click(wxCommandEvent& event)\n{\n"
                fct += "  if (flag_"+element_id+")\n  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                element_num_patte = 1
                for output in FbdBlock["outputs"]:
                    element_type = TYPECONVERSION[output[1]]
                    fct += "    _copy__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)+" = true;\n"
                    element_num_patte +=1
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  event.Skip();\n"
                fct += "}\n\n"               
                
            elif type == "RotatingCtrl":
                fct += "void Program::On"+element_name+"Changed(wxScrollEvent& event)\n{\n"
                fct += "  SVGUIRotatingCtrl* rotating = (SVGUIRotatingCtrl*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  rotating->SendScrollEvent(event);\n"
                fct += "  double angle = rotating->GetAngle();\n"
                fct += "  if (flag_"+element_id+")\n  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                element_num_patte = 1
                for output in FbdBlock["outputs"]:
                    element_type = TYPECONVERSION[output[1]]
                    
                    if element_num_patte == 1:
                        value = "angle"
                    elif element_num_patte == 2:
                        value = "true"
                    fct += "    _copy__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)+" = "+value+";\n"
                    element_num_patte +=1
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "}\n\n"
            elif type == "NoteBook":
                fct += "void Program::On"+element_name+"TabChanged(wxNotebookEvent& event)\n{\n"
                fct += "  SVGUINoteBook* notebook = (SVGUINoteBook*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  notebook->SendNotebookEvent(event);\n"
                fct += "  unsigned int selected = notebook->GetCurrentPage();\n"
                fct += "  if (flag_"+element_id+")\n  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                element_num_patte = 1
                for output in FbdBlock["outputs"]:
                    element_type = TYPECONVERSION[output[1]]
                    
                    if element_num_patte == 1:
                        value = "selected"
                    elif element_num_patte == 2:
                        value = "true"
                    fct += "    _copy__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)+" = "+value+";\n"
                    element_num_patte +=1
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "}\n\n"
            elif type == "Transform":
                fct += "void Program::On"+element_name+"Paint(wxPaintEvent& event)\n{\n"
                fct += "  SVGUITransform* transform = (SVGUITransform*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  if (flag_"+element_id+")\n  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                element_num_patte = 1
                for output in FbdBlock["outputs"]:                    
                    if element_num_patte == 1:
                        fct += "    if (transform->GetX() != _copy__QD"+self.BusNumber+"_"+element_id+"_1)\n"
                        fct += "    {\n"
                        fct += "      _copy__QD"+self.BusNumber+"_"+element_id+"_1 = transform->GetX();\n"
                        fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_6 = true;\n"
                        fct += "    }\n"
                    elif element_num_patte == 2:
                        fct += "    if (transform->GetY() != _copy__QD"+self.BusNumber+"_"+element_id+"_2)\n"
                        fct += "    {\n"
                        fct += "      _copy__QD"+self.BusNumber+"_"+element_id+"_2 = transform->GetY();\n"
                        fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_6 = true;\n"
                        fct += "    }\n"
                    elif element_num_patte == 3:
                        fct += "    if (transform->GetXScale() != _copy__QD"+self.BusNumber+"_"+element_id+"_3)\n"
                        fct += "    {\n"
                        fct += "      _copy__QD"+self.BusNumber+"_"+element_id+"_3 = transform->GetXScale();\n"
                        fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_6 = true;\n"
                        fct += "    }\n"
                    elif element_num_patte == 4:
                        fct += "    if (transform->GetYScale() != _copy__QD"+self.BusNumber+"_"+element_id+"_4)\n"
                        fct += "    {\n"
                        fct += "      _copy__QD"+self.BusNumber+"_"+element_id+"_4 = transform->GetYScale();\n"
                        fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_6 = true;\n"
                        fct += "    }\n"
                    elif element_num_patte == 5:
                        fct += "    if (transform->GetAngle() != _copy__QD"+self.BusNumber+"_"+element_id+"_5)\n"
                        fct += "    {\n"
                        fct += "      _copy__QD"+self.BusNumber+"_"+element_id+"_5 = transform->GetAngle();\n"
                        fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_6 = true;\n"
                        fct += "    }\n"
                    element_num_patte +=1
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  event.Skip();\n"
                fct += "}\n\n"
            elif type == "Container":
                fct += "void Program::On"+element_name+"Paint(wxPaintEvent& event)\n{\n"
                fct += "  SVGUIContainer* container = (SVGUIContainer*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  if (container->IsVisible() != _copy__QX"+self.BusNumber+"_"+element_id+"_1  && flag_"+element_id+")\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    _copy__QX"+self.BusNumber+"_"+element_id+"_1 = container->IsVisible();\n"
                fct += "    _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  event.Skip();\n"
                fct += "}\n\n"
        
        fct += "void Program::OnChar(wxKeyEvent& event)\n{\n"
        fct += "  SVGUIContainer* container = GetSVGUIRootElement();\n"
        fct += "  if (container->GetFocusedElementName() == wxT(\"TextCtrl\"))\n"
        fct += "  {\n"
        fct += "    wxString focusedId = container->GetFocusedElement();\n"
        fct += "    SVGUITextCtrl* text = (SVGUITextCtrl*)GetElementById(container->GetFocusedElement());\n"
        fct += "    text->SendKeyEvent(event);\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            if type == "TextCtrl":
                fct += "    if (focusedId == wxT(\""+element_id+"\") && flag_"+element_id+")\n"
                fct += "    {\n"
                fct += "      flag_"+element_id+" = false;\n"
                fct += "      _copy__QB"+self.BusNumber+"_"+element_id+"_1 = wxStringToStr(text->GetValue());\n"
                fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n"
                fct += "      flag_"+element_id+" = true;\n"
                fct += "    }\n"
        fct += "  }\n"
        fct += "}\n"

        
        
        fct += "void Program::OnClick(wxMouseEvent& event)\n{\n"
        fct += "  SVGUIContainer* container = GetSVGUIRootElement();\n"
        fct += "  if (container->GetFocusedElementName() == wxT(\"ScrollBar\"))\n"
        fct += "  {\n"
        fct += "    wxString focusedId = container->GetFocusedElement();\n"
        fct += "    SVGUIScrollBar* scrollbar = (SVGUIScrollBar*)GetElementById(focusedId);\n"
        fct += "    scrollbar->SendMouseEvent(event);\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            if type == "ScrollBar":
                fct += "    if (focusedId == wxT(\""+element_id+"\") && flag_"+element_id+")\n"
                fct += "    {\n"
                fct += "      flag_"+element_id+" = false;\n"
                fct += "      unsigned int scrollPos = scrollbar->GetThumbPosition();\n"
                fct += "      _copy__QW"+self.BusNumber+"_"+element_id+"_1 = scrollPos;\n"
                fct += "      _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n"
                fct += "      flag_"+element_id+" = true;\n"
                fct += "    }\n"
        fct += "  }\n"
        fct += "  event.Skip();\n"
        fct += "}\n"

        
        
        
        fct += "void Program::OnPlcOutEvent(wxEvent& event)\n{\n"
        fct += "  int old_state;\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            if type == "Button":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_2 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUIButton* button = (SVGUIButton*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    if (_copy__IX"+self.BusNumber+"_"+element_id+"_1)\n"
                fct += "      button->Show();\n"
                fct += "    else\n"
                fct += "      button->Hide();\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
            elif type == "Container":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_2 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUIContainer* container = (SVGUIContainer*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    if (_copy__IX"+self.BusNumber+"_"+element_id+"_1)\n"
                fct += "      container->Show();\n"
                fct += "    else\n"
                fct += "      container->Hide();\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
            elif type == "TextCtrl":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_2 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUITextCtrl* text = (SVGUITextCtrl*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    wxString str = wxString::FromAscii(_copy__IB"+self.BusNumber+"_"+element_id+"_1);\n"
                fct += "    text->SetText(str);\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
            elif type == "ScrollBar":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_2 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUIScrollBar* scrollbar = (SVGUIScrollBar*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    scrollbar->SetThumbPosition(_copy__IW"+self.BusNumber+"_"+element_id+"_1);\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
            elif type == "RotatingCtrl":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_2 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUIRotatingCtrl* rotating = (SVGUIRotatingCtrl*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    rotating->SetAngle(_copy__ID"+self.BusNumber+"_"+element_id+"_1);\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
            elif type == "NoteBook":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_2 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUINoteBook* notebook = (SVGUINoteBook*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    notebook->SetCurrentPage(_copy__IB"+self.BusNumber+"_"+element_id+"_1);\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
            elif type == "Transform":
                fct += "  old_state = __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_CHANGES, PLC_OUT_BUSY);\n"
                fct += "  if (_copy__IX"+self.BusNumber+"_"+element_id+"_6 && flag_"+element_id+" && old_state == FREE_AND_CHANGES)\n"
                fct += "  {\n"
                fct += "    flag_"+element_id+" = false;\n"
                fct += "    SVGUITransform* transform = (SVGUITransform*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "    transform->Move(_copy__ID"+self.BusNumber+"_"+element_id+"_1,_copy__ID"+self.BusNumber+"_"+element_id+"_2);\n"
                fct += "    transform->Scale(_copy__ID"+self.BusNumber+"_"+element_id+"_3,_copy__ID"+self.BusNumber+"_"+element_id+"_4);\n"
                fct += "    transform->Rotate(_copy__ID"+self.BusNumber+"_"+element_id+"_5);\n"
                fct += "    flag_"+element_id+" = true;\n"
                fct += "  }\n"
                fct += "  __sync_val_compare_and_swap (&step_"+element_id+", PLC_OUT_BUSY, FREE_AND_NO_CHANGES);\n"
        fct += "  Update_Elements();\n"
        fct += "  Refresh();\n"
        fct += "  event.Skip();\n"
        fct += "}\n\n"
        return fct
    
    def GenerateProgramPrivateFunctions(self):
        elementsTab = self.GetElementsTab()
        fct = "void Program::OUT_"+self.BusNumber+"()\n{\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            fct += "  if ( flag_"+element_id+" && __sync_val_compare_and_swap (&step_"+element_id+", PLC_BUSY, FREE_AND_CHANGES) == PLC_BUSY){\n"
            #fct += "  if ( flag_"+element_id+" ){\n"
            fct += "    flag_"+element_id+" = false;\n"
            element_num_patte = 1
            for input in FbdBlock["inputs"]:
                element_type = TYPECONVERSION[input[1]]
                var = "__I"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)
                fct +="    _copy"+var+ " = "+var+";\n"
                element_num_patte +=1
            fct += "    flag_"+element_id+" = true;\n"
            fct += "  }\n"
        fct +="  wxCommandEvent event( EVT_PLC );\n"
        fct +="  ProcessEvent(event);\n"
        fct +="};\n\n" 
        
        fct += "void Program::IN_"+self.BusNumber+"()\n{\n"

        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            fct += "  if ( flag_"+element_id+" && __sync_val_compare_and_swap (&step_"+element_id+", FREE_AND_NO_CHANGES, PLC_BUSY) == FREE_AND_NO_CHANGES){\n"
            fct += "    flag_"+element_id+" = false;\n"
            element_num_patte = 1
            for output in FbdBlock["outputs"]:
                element_type = TYPECONVERSION[output[1]]
                var = "__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)
                fct +="     "+var+ " = _copy"+var+";\n"
                element_num_patte +=1
            fct += "    flag_"+element_id+" = true;\n"
            fct += "  }\n"
        fct += "  SetNoChanges();\n"
        fct +="};\n\n" 
        
        fct += "void Program::Initialize()\n{\n"
        button = False
        container = False
        textctrl = False
        scrollbar = False
        rotatingctrl = False
        notebook = False
        transform = False
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            if type == "Button":
                if (not button):
                    fct += "  SVGUIButton* button;\n"
                fct += "  button = (SVGUIButton*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  if (button->IsVisible())\n"
                fct += "    _copy__QX"+self.BusNumber+"_"+element_id+"_1 = true;\n"
                fct += "  else\n"
                fct += "    _copy__QX"+self.BusNumber+"_"+element_id+"_1 = false;\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n\n"
                button = True
            elif type == "Container":
                if (not container):
                    fct += "  SVGUIContainer* container;\n"
                fct += "  container = (SVGUIContainer*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  if (container->IsVisible())\n"
                fct += "    _copy__QX"+self.BusNumber+"_"+element_id+"_1 = true;\n"
                fct += "  else\n"
                fct += "    _copy__QX"+self.BusNumber+"_"+element_id+"_1 = false;\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n\n"
                container = True
            elif type == "TextCtrl":
                if (not textctrl):
                    fct += "  SVGUITextCtrl* text;\n"
                fct += "  text = (SVGUITextCtrl*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  _copy__QB"+self.BusNumber+"_"+element_id+"_1 = wxStringToStr(text->GetValue());\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n\n"
                textctrl = True
            elif type == "ScrollBar":
                if (not scrollbar):
                    fct += "  SVGUIScrollBar* scrollbar;\n"
                fct += "  scrollbar = (SVGUIScrollBar*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  _copy__QW"+self.BusNumber+"_"+element_id+"_1 = scrollbar->GetThumbPosition();\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n\n"
                scrollbar = True
            elif type == "RotatingCtrl":
                if (not rotatingctrl):
                    fct += "  SVGUIRotatingCtrl* rotating;\n"
                fct += "  rotating = (SVGUIRotatingCtrl*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  _copy__QD"+self.BusNumber+"_"+element_id+"_1 = rotating->GetAngle();\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n\n"
                rotatingctrl = True
            elif type == "NoteBook":
                if (not notebook):
                    fct += "  SVGUINoteBook* notebook;\n"
                fct += "  notebook = (SVGUINoteBook*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  _copy__QB"+self.BusNumber+"_"+element_id+"_1 = notebook->GetCurrentPage();\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = true;\n\n"
                notebook = True
            elif type == "Transform":
                if (not transform):
                    fct += "  SVGUITransform* transform;\n"
                fct += "  transform = (SVGUITransform*)GetElementById(wxT(\""+element_id+"\"));\n"
                fct += "  _copy__QD"+self.BusNumber+"_"+element_id+"_1 = transform->GetX();\n"
                fct += "  _copy__QD"+self.BusNumber+"_"+element_id+"_2 = transform->GetY();\n"
                fct += "  _copy__QD"+self.BusNumber+"_"+element_id+"_3 = transform->GetXScale();\n"
                fct += "  _copy__QD"+self.BusNumber+"_"+element_id+"_4 = transform->GetYScale();\n"
                fct += "  _copy__QD"+self.BusNumber+"_"+element_id+"_5 = transform->GetAngle();\n"
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_6 = true;\n\n"
                transform = True
        fct += "}\n\n"
        
        fct += "void Program::SetNoChanges()\n{\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            if type == "Button":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = false;\n"
            elif type == "Container":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = false;\n"
            elif type == "TextCtrl":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = false;\n"
            elif type == "ScrollBar":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = false;\n"
            elif type == "RotatingCtrl":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = false;\n"
            elif type == "NoteBook":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_2 = false;\n"
            elif type == "Transform":
                fct += "  _copy__QX"+self.BusNumber+"_"+element_id+"_6 = false;\n"
        fct += "}\n\n"
        
        #DEBUG Fonction d'affichage
        fct += "void Program::Print()\n{\n"
        for element in elementsTab:
            infos = element.getElementAttributes()
            for info in infos:
                if info["name"] == "id":
                    element_id = str(info["value"])
            type = element.GetElementInfos()["type"]
            FbdBlock = self.GetBlockType(type)
            element_num_patte = 1
            for input in FbdBlock["inputs"]:
                element_type = TYPECONVERSION[input[1]]
                c_type = CPRINTTYPECONVERSION[input[1]]
                var = "_copy__I"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)
                fct +="  printf(\""+var+": %"+c_type+"\\n\","+var+");\n"
                element_num_patte +=1
            element_num_patte = 1
            for output in FbdBlock["outputs"]:
                element_type = TYPECONVERSION[output[1]]
                c_type = CPRINTTYPECONVERSION[output[1]]
                var = "_copy__Q"+element_type+self.BusNumber+"_"+element_id+"_"+str(element_num_patte)
                fct +="  printf(\""+var+": %"+c_type+"\\n\","+var+");\n"
                element_num_patte +=1
        #fct +="    wxPostEvent(Program,wxEVT_PLCOUT);\n"
        fct +="};\n\n"    
        return fct
    
    def PlugGenerate_C(self, buildpath, locations, logger):
        current_location = self.GetCurrentLocation()
        self.BusNumber = "_".join(map(lambda x:str(x), current_location))
        self.GenerateProgram(buildpath)
        Gen_C_file = os.path.join(buildpath, "program.cpp" )
        return [(Gen_C_file,"")],""
    
    def BlockTypesFactory(self):
        def generate_svgui_block(generator, block, body, link):
            controller = generator.GetController()
            name = block.getInstanceName()
            type = block.getTypeName()
            block_infos = self.GetBlockType(type)
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
                    "inputs" : [("Show","BOOL","none"),("Set State","BOOL","none")], 
                    "outputs" : [("Show","BOOL","none"),("State Changed","BOOL","none")],
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
                    "inputs" : [("Angle","REAL","none"),("Set Angle","BOOL","none")], 
                    "outputs" : [("Angle","REAL","none"),("Angle changed","BOOL","none")],
                    "comment" : "SVGUI Rotating Control"},
                {"name" : "Transform", "type" : "functionBlock", "extensible" : False, 
                    "inputs" : [("X","REAL","none"),("Y","REAL","none"),("Scale X","REAL","none"),("Scale Y","REAL","none"),("Angle","REAL","none"),("Set","BOOL","none")], 
                    "outputs" : [("X","REAL","none"),("Y","REAL","none"),("Scale X","REAL","none"),("Scale Y","REAL","none"),("Angle","REAL","none"),("Changed","BOOL","none")],
                    "comment" : "SVGUI Transform"},
               ]}
        ]
    
    def GetBlockType(self,type):
        for category in self.BlockTypesFactory():
            for blocktype in category["list"]:
                if blocktype["name"] == type:
                    return blocktype
        return None

#DEBUG
if __name__ == '__main__':
    app = wxPySimpleApp()
    wxInitAllImageHandlers()
    
    # Install a exception handle for bug reports
    #wxAddExceptHook(os.getcwd(),__version__)
    
    cont = RootClass(sys.path[0])
    frame = _EditorFramePlug(cont)

    frame.Show()
    app.MainLoop()
#DEBUG





