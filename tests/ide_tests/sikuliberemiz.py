"Commons definitions for sikuli based beremiz IDE GUI tests"

import os
import sys
import subprocess
from threading import Thread, Event

typeof=type

from sikuli import *

beremiz_path = os.environ["BEREMIZPATH"]
python_bin = os.environ.get("BEREMIZPYTHONPATH", "/usr/bin/python")

opj = os.path.join

def StartBeremizApp(projectpath=None, exemple=None):
    """
    Starts Beremiz IDE, waits for main window to appear, maximize it.

        Parameters: 
            projectpath (str): path to project to open
            exemple (str): path relative to exemples directory

        Returns:
            Sikuli App class instance
    """

    command = [python_bin, opj(beremiz_path,"Beremiz.py"), "--log=/dev/stdout"]

    if exemple is not None:
        command.append(opj(beremiz_path,"exemples",exemple))
    elif projectpath is not None:
        command.append(projectpath)

    # App class is broken in Sikuli 2.0.5: can't start process with arguments.
    # 
    # Workaround : - use subprocess module to spawn IDE process,
    #              - use wmctrl to find IDE window details and maximize it
    #              - pass exact window title to App class constructor

    proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=0)

    # Window are macthed against process' PID
    ppid = proc.pid

    # Timeout 5s
    c = 50
    while c > 0:
        # equiv to "wmctrl -l -p | grep $pid"
        try:
            wlist = filter(lambda l:(len(l)>2 and l[2]==str(ppid)), map(lambda s:s.split(None,4), subprocess.check_output(["wmctrl", "-l", "-p"]).splitlines()))
        except subprocess.CalledProcessError:
            wlist = []

        # window with no title only has 4 fields do describe it
        # beremiz splashcreen has no title
        # wait until main window is visible
        if len(wlist) == 1 and len(wlist[0]) == 5:
            windowID,_zero,wpid,_XID,wtitle = wlist[0] 
            break

        wait(0.1)
        c = c - 1

    if c == 0:
        raise Exception("Couldn't find Beremiz window")

    # Maximize window x and y
    subprocess.check_call(["wmctrl", "-i", "-r", windowID, "-b", "add,maximized_vert,maximized_horz"])

    # switchApp creates an App object by finding window by title, is not supposed to spawn a process
    return proc, switchApp(wtitle)

class KBDShortcut:
    """Send shortut to app by calling corresponding methods:
          Stop   
          Run    
          Transfer
          Connect
          Clean  
          Build  

    example:
        k = KBDShortcut(app)
        k.Clean()
    """

    fkeys = {"Stop":     Key.F4,
             "Run":      Key.F5,
             "Transfer": Key.F6,
             "Connect":  Key.F7,
             "Clean":    Key.F9,
             "Build":    Key.F11,
             "Save":     ("s",Key.CTRL),
             "New":      ("n",Key.CTRL),
             "Address":  ("l",Key.CTRL)}  # to reach address bar in GTK's file selector

    def __init__(self, app):
        self.app = app
    
    def __getattr__(self, name):
        fkey = self.fkeys[name]
        if typeof(fkey) != tuple:
            fkey = (fkey,)
        app = self.app

        def PressShortCut():
            app.focus()
            type(*fkey)

        return PressShortCut


class IDEIdleObserver:
    "Detects when IDE is idle. This is particularly handy when staring an operation and witing for the en of it."

    def __init__(self, app):
        """
        Parameters: 
            app (class App): Sikuli app given by StartBeremizApp
        """
        self.r = Region(app.window())

        self.idechanged = False
        
        # 200 was selected because default 50 was still catching cursor blinking in console
        # FIXME : remove blinking cursor in console
        self.r.onChange(200,self._OnIDEWindowChange)
        self.r.observeInBackground()

    def __del__(self):
        self.r.stopObserver()

    def _OnIDEWindowChange(self, event):
        self.idechanged = True

    def Wait(self, period, timeout):
        """
        Wait for IDE to stop changing
        Parameters: 
            period (int): how many seconds with no change to consider idle
            timeout (int): how long to wait for idle, in seconds
        """
        c = timeout/period
        while c > 0:
            self.idechanged = False
            wait(period)
            if not self.idechanged:
                break
            c = c - 1

        if c == 0:
            raise Exception("Window did not idle before timeout")

 
class stdoutIdleObserver:
    "Detects when IDE's stdout is idle. Can be more reliable than pixel based version (false changes ?)"

    def __init__(self, proc):
        """
        Parameters: 
            proc (subprocess.Popen): Beremiz process, given by StartBeremizApp
        """
        self.proc = proc
        self.stdoutchanged = False

        self.thread = Thread(target = self._waitStdoutProc).start()

    def _waitStdoutProc(self):
        while True:
            a = self.proc.stdout.read(1)
            if len(a) == 0 or a is None: 
                break
            sys.stdout.write(a)
            self.idechanged = True

    def Wait(self, period, timeout):
        """
        Wait for IDE'stdout to stop changing
        Parameters: 
            period (int): how many seconds with no change to consider idle
            timeout (int): how long to wait for idle, in seconds
        """
        c = timeout/period
        while c > 0:
            self.idechanged = False
            wait(period)
            if not self.idechanged:
                break
            c = c - 1

        if c == 0:
            raise Exception("Stdout did not idle before timeout")


def waitPatternInStdout(proc, pattern, timeout, count=1):
    
    success_event = Event()

    def waitPatternInStdoutProc():
        found = 0
        while True:
            a = proc.stdout.readline()
            if len(a) == 0 or a is None: 
                raise Exception("App finished before producing expected stdout pattern")
            sys.stdout.write(a)
            if a.find(pattern) >= 0:
                found = found + 1
                if found >= count:
                    success_event.set()
                    break


    Thread(target = waitPatternInStdoutProc).start()

    if not success_event.wait(timeout):
        # test timed out
        return False
    else:
        return True



