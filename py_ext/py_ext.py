import os
from POULibrary import POULibrary
from PythonFileCTNMixin import PythonFileCTNMixin

class PythonLibrary(POULibrary):
    def GetLibraryPath(self):
        return os.path.join(os.path.split(__file__)[0], "pous.xml") 

    def Generate_C(self, buildpath, varlist, IECCFLAGS):
        
        plc_python_filepath = os.path.join(os.path.split(__file__)[0], "plc_python.c")
        plc_python_file = open(plc_python_filepath, 'r')
        plc_python_code = plc_python_file.read()
        plc_python_file.close()
        python_eval_fb_list = []
        for v in varlist:
            if v["vartype"] == "FB" and v["type"] in ["PYTHON_EVAL","PYTHON_POLL"]:
                python_eval_fb_list.append(v)
        python_eval_fb_count = max(1, len(python_eval_fb_list))
        
        # prepare python code
        plc_python_code = plc_python_code % { "python_eval_fb_count": python_eval_fb_count }
        
        Gen_Pythonfile_path = os.path.join(buildpath, "py_ext.c")
        pythonfile = open(Gen_Pythonfile_path,'w')
        pythonfile.write(plc_python_code)
        pythonfile.close()
        
        return (["py_ext"], [(Gen_Pythonfile_path, IECCFLAGS)], True), ""

class PythonFile(PythonFileCTNMixin):
    
    def GetIconName(self):
        return "Pyfile"
    
    def CTNGenerate_C(self, buildpath, locations):
        current_location = self.GetCurrentLocation()
        # define a unique name for the generated C file
        location_str = "_".join(map(lambda x:str(x), current_location))
        
        runtimefile_path = os.path.join(buildpath, "runtime_%s.py"%location_str)
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write(self.GetPythonCode())
        runtimefile.close()
        
        return [], "", False, ("runtime_%s.py"%location_str, file(runtimefile_path,"rb"))

