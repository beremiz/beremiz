self.logger.write_error("Welcome to the Beremiz Demo\n\n")            
self.logger.write("This demo provides a PLC working with the CANopen plugin\n")
self.logger.write("""Some external programs are also provided:\n
- a CAN TCP server to simulate the CANopen network
- a virtual slave node to simulate input block
- a virtual slave node to simulate output block
""")
self.logger.write("\nInfo: For this demo, %s plugin has some special methods to run external programs.\nThese methods are defined in methods.py\n" % (PlugName or "Root"))
#open_pdf(os.path.join(os.path.split(__file__)[0], "doc", "manual_beremiz.pdf"), pagenum=21)

if wx.Platform == '__WXMSW__':
    self.listLaunchProg = [
        {'name' : 'Can Tcp Server',
         'command' : 'can_tcp_win32_server.exe',
         'keyword' : 'Accepts',
         'pid' : None,
         'no_gui' : True}
    ]

def my_methods(self): 
    def _Run():
        # External programs list 
        # Launch them and get their pid
        for prog in self.listLaunchProg:
            self.logger.write("Starting %s\n" % prog['name'])
            prog['pid'] = ProcessLogger(self.logger, prog['command'], no_gui=prog['no_gui'])
            prog['pid'].spin(
            		 timeout=200,
                     keyword = prog['keyword'],
                     kill_it = False)
        
        PluginsRoot._Run(self)

    def _Debug():
        # External programs list 
        # Launch them and get their pid
        for prog in self.listLaunchProg:
            self.logger.write("Starting %s\n" % prog['name'])
            prog['pid'] = ProcessLogger(self.logger, prog['command'], no_gui=prog['no_gui'])
            prog['pid'].spin(
                     timeout=200,
                     keyword = prog['keyword'],
                     kill_it = False)
        
        PluginsRoot._Debug(self)
        
    def _Stop():
        PluginsRoot._Stop(self)
        for prog in self.listLaunchProg:
            self.logger.write("Stopping %s\n" % prog['name'])
            prog['pid'].kill()
    
    return _Run, _Stop, _Debug
   
self._Run, self._Stop, self._Debug = my_methods(self)
