"Commons definitions for sikuli based beremiz IDE GUI tests"

import os
import sys
import subprocess
from threading import Thread, Event, Lock
from time import time as timesec

import sikuli

beremiz_path = os.environ["BEREMIZPATH"]
python_bin = os.environ.get("BEREMIZPYTHONPATH", "/usr/bin/python")

opj = os.path.join


class KBDShortcut:
    """Send shortut to app by calling corresponding methods.

    example:
        k = KBDShortcut()
        k.Clean()
    """

    fkeys = {"Stop":     sikuli.Key.F4,
             "Run":      sikuli.Key.F5,
             "Transfer": sikuli.Key.F6,
             "Connect":  sikuli.Key.F7,
             "Clean":    sikuli.Key.F9,
             "Build":    sikuli.Key.F11,
             "Save":     ("s",sikuli.Key.CTRL),
             "New":      ("n",sikuli.Key.CTRL),
             "Address":  ("l",sikuli.Key.CTRL)}  # to reach address bar in GTK's file selector

    def __init__(self, app):
        self.app = app.sikuliapp
    
    def __getattr__(self, name):
        fkey = self.fkeys[name]
        if type(fkey) != tuple:
            fkey = (fkey,)
        app = self.app

        def PressShortCut():
            app.focus()
            sikuli.type(*fkey)

        return PressShortCut


class IDEIdleObserver:
    "Detects when IDE is idle. This is particularly handy when staring an operation and witing for the en of it."

    def __init__(self):
        """
        Parameters: 
            app (class BeremizApp)
        """
        self.r = sikuli.Region(self.sikuliapp.window())

        self.idechanged = False
        
        # 200 was selected because default 50 was still catching cursor blinking in console
        # FIXME : remove blinking cursor in console
        self.r.onChange(200,self._OnIDEWindowChange)
        self.r.observeInBackground()

    def __del__(self):
        self.r.stopObserver()

    def _OnIDEWindowChange(self, event):
        self.idechanged = True

    def WaitIdleUI(self, period=1, timeout=15):
        """
        Wait for IDE to stop changing
        Parameters: 
            period (int): how many seconds with no change to consider idle
            timeout (int): how long to wait for idle, in seconds
        """
        c = max(timeout/period,1)
        while c > 0:
            self.idechanged = False
            sikuli.wait(period)
            if not self.idechanged:
                break
            c = c - 1

        if c == 0:
            raise Exception("Window did not idle before timeout")

 
class stdoutIdleObserver:
    "Detects when IDE's stdout is idle. Can be more reliable than pixel based version (false changes ?)"

    def __init__(self):
        """
        Parameters: 
            app (class BeremizApp)
        """
        self.stdoutchanged = False

        self.event = Event()

        self.pattern = None
        self.success_event = Event()

        self.thread = Thread(target = self._waitStdoutProc).start()

    def _waitStdoutProc(self):
        while True:
            a = self.proc.stdout.readline()
            if len(a) == 0 or a is None: 
                break
            sys.stdout.write(a)
            self.event.set()
            if self.pattern is not None and a.find(self.pattern) >= 0:
                sys.stdout.write("found pattern in '" + a +"'")
                self.success_event.set()

    def waitForChangeAndIdleStdout(self, period=2, timeout=15):
        """
        Wait for IDE'stdout to start changing
        Parameters: 
            timeout (int): how long to wait for change, in seconds
        """
        start_time = timesec()

        if self.event.wait(timeout):
            self.event.clear()
        else:
            raise Exception("Stdout didn't become active before timeout")

        self.waitIdleStdout(period, timeout - (timesec() - start_time))

    def waitIdleStdout(self, period=2, timeout=15):
        """
        Wait for IDE'stdout to stop changing
        Parameters: 
            period (int): how many seconds with no change to consider idle
            timeout (int): how long to wait for idle, in seconds
        """
        end_time = timesec() + timeout
        self.event.clear()
        while timesec() < end_time:
            if self.event.wait(period):
                # no timeout -> got event -> not idle -> loop again
                self.event.clear()
            else:
                # timeout -> no event -> idle -> exit
                return True

        raise Exception("Stdout did not idle before timeout")

    def waitPatternInStdout(self, pattern, timeout, count=1):
        found = 0
        self.pattern = pattern
        end_time = timesec() + timeout
        self.event.clear()
        while True:
            remain = end_time - timesec()
            if remain <= 0 :
                res = False
                break

            res = self.success_event.wait(remain)
            if res:
                self.success_event.clear()
                found = found + 1
                if found >= count:
                    break
        self.pattern = None
        return res

class BeremizApp(IDEIdleObserver, stdoutIdleObserver):
    def __init__(self, projectpath=None, exemple=None):
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

        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=0)

        # Window are macthed against process' PID
        ppid = self.proc.pid

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

            sikuli.wait(0.1)
            c = c - 1

        if c == 0:
            raise Exception("Couldn't find Beremiz window")

        # Maximize window x and y
        subprocess.check_call(["wmctrl", "-i", "-r", windowID, "-b", "add,maximized_vert,maximized_horz"])

        # switchApp creates an App object by finding window by title, is not supposed to spawn a process
        self.sikuliapp = sikuli.switchApp(wtitle)
        self.k = KBDShortcut(self)

        IDEIdleObserver.__init__(self)
        stdoutIdleObserver.__init__(self)

        # stubs for common sikuli calls to allow adding hooks later
        for n in ["click","doubleClick","type"]:
            setattr(self, n, getattr(sikuli, n))

    def close(self):
        self.sikuliapp.close()
        self.sikuliapp = None

    def __del__(self):
        if self.sikuliapp is not None:
            self.sikuliapp.close()
        IDEIdleObserver.__del__(self)
        stdoutIdleObserver.__del__(self)

