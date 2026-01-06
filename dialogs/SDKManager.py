import os
import shutil
import wx
import zipfile
import json
import datetime
import subprocess
import threading

from util.paths import ThirdPartyPath, Bpath

class SDKManagerDialog(wx.Dialog):
    def __init__(self, parent, sdk_store_path):
        super(SDKManagerDialog, self).__init__(parent, title="PLC-SDK Manager", size=(500, 400))
        
        self.sdk_store_path = sdk_store_path
        if not os.path.exists(self.sdk_store_path):
            os.makedirs(self.sdk_store_path)

        self.selected_sdk = None

        # Layout
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # List of SDKs
        self.sdk_list = wx.ListBox(self, style=wx.LB_SINGLE)
        main_sizer.Add(self.sdk_list, 1, wx.EXPAND | wx.ALL, 10)
        self.sdk_list.Bind(wx.EVT_LISTBOX, self.OnSelectSDK)

        # Buttons
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        add_btn = wx.Button(self, label="Add SDK (Zip)")
        add_btn.Bind(wx.EVT_BUTTON, self.OnAddSDK)
        btn_sizer.Add(add_btn, 0, wx.ALL, 5)

        self.remove_btn = wx.Button(self, label="Remove SDK")
        self.remove_btn.Bind(wx.EVT_BUTTON, self.OnRemoveSDK)
        self.remove_btn.Disable()
        btn_sizer.Add(self.remove_btn, 0, wx.ALL, 5)

        if os.name == 'nt':
            self.shortcut_btn = wx.Button(self, label="Create Shortcut")
            self.shortcut_btn.Bind(wx.EVT_BUTTON, self.OnCreateShortcut)
            self.shortcut_btn.Disable()
            btn_sizer.Add(self.shortcut_btn, 0, wx.ALL, 5)
        else:
            self.shortcut_btn = None

        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        # Dialog Buttons (OK/Cancel)
        dlg_btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.ok_btn = self.FindWindow(wx.ID_OK)
        if self.ok_btn:
            self.ok_btn.SetLabel("Use PLC-SDK")
            self.ok_btn.Disable()
        main_sizer.Add(dlg_btn_sizer, 0, wx.ALIGN_CENTER | wx.BOTTOM, 10)

        self.SetSizer(main_sizer)
        
        self.RefreshSDKList()

    def RefreshSDKList(self):
        self.sdk_list.Clear()
        if os.path.exists(self.sdk_store_path):
            sdks = [d for d in os.listdir(self.sdk_store_path) if os.path.isdir(os.path.join(self.sdk_store_path, d))]
            for sdk in sdks:
                self.sdk_list.Append(sdk)

    def OnSelectSDK(self, event):
        selection = self.sdk_list.GetSelection()
        if selection != wx.NOT_FOUND:
            self.selected_sdk = self.sdk_list.GetString(selection)
            self.remove_btn.Enable()
            self.ok_btn.Enable()
            if self.shortcut_btn:
                self.shortcut_btn.Enable()
        else:
            self.selected_sdk = None
            self.remove_btn.Disable()
            self.ok_btn.Disable()
            if self.shortcut_btn:
                self.shortcut_btn.Disable()

    def OnAddSDK(self, event):
        with wx.FileDialog(self, "Select PLC-SDK Zip Archive", wildcard="Zip files (*.zip)|*.zip",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            zip_path = fileDialog.GetPath()
            try:
                sdk_name = None
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    manifest_path = None
                    name_list = zip_ref.namelist()
                    
                    if 'manifest.json' in name_list:
                        manifest_path = 'manifest.json'
                    else:
                        # Check if there is a single top level directory containing manifest.json
                        top_dirs = {name.split('/')[0] for name in name_list if '/' in name}
                        if len(top_dirs) == 1:
                            possible = list(top_dirs)[0] + '/manifest.json'
                            if possible in name_list:
                                manifest_path = possible
                    
                    if manifest_path:
                        try:
                            with zip_ref.open(manifest_path) as f:
                                manifest = json.load(f)
                                sdk_name = manifest.get('name')
                        except Exception:
                            pass

                if not sdk_name:
                    name = os.path.splitext(os.path.basename(zip_path))[0]
                    date = datetime.datetime.fromtimestamp(os.path.getmtime(zip_path)).strftime('%Y-%m-%d')
                    sdk_name = f"{name}-{date}"

                # Sanitize sdk_name to be safe for filesystem
                sdk_name = "".join([c for c in sdk_name if c.isalnum() or c in (' ', '.', '_', '-')]).strip()

                target_dir = os.path.join(self.sdk_store_path, sdk_name)

                if os.path.exists(target_dir):
                    wx.MessageBox(f"SDK '{sdk_name}' already exists.", "Error", wx.OK | wx.ICON_ERROR)
                    return

                # Create a progress dialog with a spinner (indeterminate gauge)
                self.progress_dlg = wx.ProgressDialog("Extracting SDK", 
                                                      f"Extracting '{sdk_name}'...", 
                                                      parent=self, 
                                                      style=wx.PD_APP_MODAL | wx.PD_ELAPSED_TIME | wx.PD_AUTO_HIDE)
                
                # Timer to pulse the dialog
                self.pulse_timer = wx.Timer(self)
                self.Bind(wx.EVT_TIMER, self.OnPulseTimer, self.pulse_timer)
                self.pulse_timer.Start(100)

                # Start extraction in a separate thread
                t = threading.Thread(target=self.ExtractWorker, args=(zip_path, target_dir, sdk_name))
                t.start()

            except Exception as e:
                wx.MessageBox(f"Failed to add SDK: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    def OnPulseTimer(self, event):
        if hasattr(self, 'progress_dlg') and self.progress_dlg:
             self.progress_dlg.Pulse()

    def ExtractWorker(self, zip_path, target_dir, sdk_name):
        error = None
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)
        except Exception as e:
            error = str(e)
            
        wx.CallAfter(self.OnExtractionComplete, sdk_name, error)

    def OnExtractionComplete(self, sdk_name, error):
        if hasattr(self, 'pulse_timer') and self.pulse_timer.IsRunning():
            self.pulse_timer.Stop()
            
        if hasattr(self, 'progress_dlg') and self.progress_dlg:
            self.progress_dlg.Destroy()
            self.progress_dlg = None
            
        if error:
             wx.MessageBox(f"Failed to add SDK: {error}", "Error", wx.OK | wx.ICON_ERROR)
        else:
             self.RefreshSDKList()
             wx.MessageBox(f"SDK '{sdk_name}' added successfully.", "Success", wx.OK | wx.ICON_INFORMATION)

    def OnRemoveSDK(self, event):
        selection = self.sdk_list.GetSelection()
        if selection != wx.NOT_FOUND:
            sdk_name = self.sdk_list.GetString(selection)
            target_dir = os.path.join(self.sdk_store_path, sdk_name)
            
            dlg = wx.MessageDialog(self, f"Are you sure you want to delete SDK '{sdk_name}'?",
                                   "Confirm Deletion", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal() == wx.ID_YES:
                try:
                    shutil.rmtree(target_dir)
                    self.RefreshSDKList()
                    self.selected_sdk = None
                    self.remove_btn.Disable()
                    if self.shortcut_btn:
                        self.shortcut_btn.Disable()
                except Exception as e:
                    wx.MessageBox(f"Failed to remove SDK: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
            dlg.Destroy()

    def OnCreateShortcut(self, event):
        if not self.selected_sdk:
            return
            
        sdk_path = self.GetSelectedSDKPath()
        
        target_cmd = ThirdPartyPath("beremiz_ide.cmd")
             
        try:
            # Start Menu Programs folder
            start_menu = os.path.join(os.environ['APPDATA'], "Microsoft", "Windows", "Start Menu", "Programs")
            if not os.path.exists(start_menu):
                 # Fallback to Desktop if Start Menu folder not found (unlikely on standard Windows)
                 try:
                    start_menu = wx.StandardPaths.Get().GetDesktopDir()
                 except:
                    start_menu = os.path.expanduser("~/Desktop")
        except:
            start_menu = os.path.expanduser("~")
            
        shortcut_name = f"Beremiz {self.selected_sdk}"
        
        icon_path = Bpath("images", "brz.ico")
        if not os.path.exists(icon_path):
            icon_path = None

        try:
            if os.name == 'nt':
                shortcut_path = os.path.join(start_menu, f"{shortcut_name}.lnk")
                self.create_windows_shortcut(target_cmd, f"--sdkpath \"{sdk_path}\"", shortcut_path, icon_path)
                wx.MessageBox(f"Shortcut created at {shortcut_path}", "Success", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Failed to create shortcut: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    def create_windows_shortcut(self, target, arguments, shortcut_path, icon_path=None):
        # Escape double quotes for VBScript which uses "" for escaping "
        arguments = arguments.replace('"', '""')
        
        icon_line = ""
        if icon_path:
             icon_path = icon_path.replace('"', '""')
             icon_line = f'oLink.IconLocation = "{icon_path}"'
        
        vbs_script = f"""
        Set oWS = WScript.CreateObject("WScript.Shell")
        Set oLink = oWS.CreateShortcut("{shortcut_path}")
        oLink.TargetPath = "{target}"
        oLink.Arguments = "{arguments}"
        {icon_line}
        oLink.Save
        """
        vbs_file = os.path.join(os.environ.get('TEMP', os.getcwd()), "create_shortcut.vbs")
        with open(vbs_file, "w") as f:
            f.write(vbs_script)
        subprocess.call(["cscript", "//nologo", vbs_file])
        os.remove(vbs_file)

    def GetSelectedSDKPath(self):
        if self.selected_sdk:
            return os.path.join(self.sdk_store_path, self.selected_sdk)
        return None

if __name__ == "__main__":
    app = wx.App(False)
    # Example usage: store SDKs in a local 'sdks' folder
    dlg = SDKManagerDialog(None, os.path.abspath("./sdks"))
    if dlg.ShowModal() == wx.ID_OK:
        print(f"Selected SDK Path: {dlg.GetSelectedSDKPath()}")
    dlg.Destroy()
    app.MainLoop()