"""Commons definitions for beremiz IDE GUI tests

IDE runs on GTK Broadway backend, displayed in headless Chromium driven by
Playwright. Widgets are located by ide_test_agent.py, running in IDE process.
"""

import os
import sys
import re
import glob
import socket
import signal
import tempfile
import subprocess
import traceback
import xmlrpc.client
from threading import Thread, Event
from time import time as timesec, sleep
from xml.sax.saxutils import escape as escape_xml

from playwright.sync_api import sync_playwright

beremiz_path = os.environ["BEREMIZPATH"]
python_bin = os.environ.get("BEREMIZPYTHONPATH", sys.executable)
opj = os.path.join

ide_tests_path = os.path.dirname(os.path.abspath(__file__))
agent_path = opj(ide_tests_path, "ide_test_agent.py")

# Broadway's javascript client throws on commands targeting a surface it doesn't
# know, losing the rest of the batch of commands. wxWidgets' first command is
# deleting surface 0, that never existed.
broadway_client_fix = """() => {
    for (const name of ["cmdDeleteSurface", "cmdShowSurface", "cmdHideSurface", "cmdMoveResizeSurface",
                        "cmdRaiseSurface", "cmdLowerSurface", "cmdPutBuffer", "cmdSetTransientFor"]) {
        const cmd = window[name];
        window[name] = (id, ...args) => { if (id in surfaces) return cmd(id, ...args); };
    }
}"""

ansi_escape = re.compile(r'\x1B[@-_][0-?]*[ -/]*[@-~]')
def escape_ansi(line):
    return ansi_escape.sub('', line)

def escape(txt):
    return escape_xml(escape_ansi(txt))

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

def relay_tcp(port, local_port):
    """
    Relay TCP connections on given port, on all addresses, to given port on
    loopback. Returns listening socket, to be shut down when done.
    """
    server = socket.create_server(("0.0.0.0", port))

    def pipe(src, dst):
        try:
            while data := src.recv(65536):
                dst.sendall(data)
        except OSError:
            pass
        finally:
            try:
                dst.shutdown(socket.SHUT_WR)
            except OSError:
                pass

    def serve():
        while True:
            try:
                client, _address = server.accept()
            except OSError:
                return  # relay shut down
            try:
                local = socket.create_connection(("127.0.0.1", local_port))
            except OSError:
                client.close()
                continue
            Thread(target=pipe, args=(client, local), daemon=True).start()
            Thread(target=pipe, args=(local, client), daemon=True).start()

    Thread(target=serve, daemon=True).start()
    return server

def broadway_shm_segments():
    "Shared memory files used by GDK to pass windows content to broadwayd"
    return set(glob.glob("/dev/shm/bdw-*"))

def center(rect):
    "Center of screen rect given by test agent"
    return rect["x"] + rect["width"] // 2, rect["y"] + rect["height"] // 2


class BroadwayDisplay:
    """
    GTK Broadway display server, shown in headless Chromium driven by Playwright,
    or in any other browser connecting to self.port if browser is False.
    GTK apps started with self.env, or created in current process after calling
    self.use(), are displayed in self.page.

    Environment variables:
        BEREMIZ_TEST_DEVTOOLS: Chromium remote debugging port, i.e. to watch
            tests live from chrome://inspect
        BEREMIZ_TEST_SLOWMO: delay in milliseconds added to each input action
        BEREMIZ_TEST_TRACE: if set, playwright trace is saved in trace.zip
    """

    def __init__(self, browser=True):
        self.shm_segments = broadway_shm_segments()
        self.broadwayd = self.playwright = self.browser = self.page = self.devtools_relay = None

        self.env = dict(os.environ)
        self.env.setdefault("XDG_RUNTIME_DIR", tempfile.gettempdir())  # where broadway socket goes

        # Broadway display number is arbitrary, use http port to keep it unique
        port = self.port = free_port()
        self.name = ":%d" % port

        try:
            with open("broadwayd.log", "w") as log:
                self.broadwayd = subprocess.Popen(
                    ["broadwayd", "--address", "127.0.0.1", "--port", str(port), self.name],
                    stdout=log, stderr=subprocess.STDOUT, env=self.env)

            if browser:
                self.start_browser()
        except:
            self.close()
            raise

        self.env.update(GDK_BACKEND="broadway", BROADWAY_DISPLAY=self.name)
        # sitecustomize module there lets wxPython start on Broadway, in apps and in processes they spawn
        self.env["PYTHONPATH"] = os.pathsep.join(filter(None, [opj(ide_tests_path, "broadway"), self.env.get("PYTHONPATH")]))
        # apps must not depend on X11 or Wayland
        self.env.pop("DISPLAY", None)
        self.env.pop("WAYLAND_DISPLAY", None)

    def start_browser(self):
        "Browser must connect before apps start, since it gives screen size"
        options = {}
        devtools_port = os.environ.get("BEREMIZ_TEST_DEVTOOLS")
        if devtools_port:
            # Chromium only listens on loopback. Port is relayed on all
            # addresses, so that it can be published by docker
            local_port = free_port()
            options["args"] = ["--remote-debugging-port=%d" % local_port]
            self.devtools_relay = relay_tcp(int(devtools_port), local_port)
        if os.environ.get("BEREMIZ_TEST_SLOWMO"):
            options["slow_mo"] = float(os.environ["BEREMIZ_TEST_SLOWMO"])
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(**options)
        context = self.browser.new_context(viewport={"width": 1920, "height": 1080})
        # pages alert when losing connection, i.e. when test ends
        context.add_init_script("window.alert = () => {};")
        if os.environ.get("BEREMIZ_TEST_TRACE"):
            context.tracing.start(screenshots=True)
        self.page = context.new_page()

        end_time = timesec() + 5
        while True:
            try:
                self.page.goto("http://127.0.0.1:%d/" % self.port)
                break
            except Exception:
                if timesec() > end_time:
                    raise
                sleep(0.05)
        self.page.evaluate(broadway_client_fix)

    def use(self):
        "Display GTK app created later in current process"
        for name in ("DISPLAY", "WAYLAND_DISPLAY"):
            os.environ.pop(name, None)
        for name in ("GDK_BACKEND", "BROADWAY_DISPLAY", "XDG_RUNTIME_DIR"):
            os.environ[name] = self.env[name]
        # same as broadway/sitecustomize.py, that comes too late if wx is already imported
        import wx
        wx.App.IsDisplayAvailable = staticmethod(lambda: True)

    def close(self):
        if self.page is not None and os.environ.get("BEREMIZ_TEST_TRACE"):
            self.page.context.tracing.stop(path="trace.zip")

        if self.browser is not None:
            self.browser.close()

        if self.playwright is not None:
            self.playwright.stop()

        if self.devtools_relay is not None:
            self.devtools_relay.shutdown(socket.SHUT_RDWR)
            self.devtools_relay.close()

        if self.broadwayd is not None:
            self.broadwayd.kill()
            self.broadwayd.wait()

        # killed processes leave their shared memory behind, filling /dev/shm (64MB in docker)
        for path in broadway_shm_segments() - self.shm_segments:
            os.remove(path)


class KBDShortcut:
    """Send shortcut to app by calling corresponding methods.

    example:
        k = KBDShortcut()
        k.Clean()
    """

    fkeys = {"Stop":     "F4",
             "Run":      "F5",
             "Transfer": "F6",
             "Connect":  "F7",
             "Clean":    "F9",
             "Build":    "F11",
             "Save":     "Control+s",
             "New":      "Control+n",
             "Address":  "Control+l"}  # to reach address bar in GTK's file selector

    def __init__(self, app):
        self.app = app

    def __getattr__(self, name):
        fkey = self.fkeys[name]

        def PressShortCut():
            self.app.page.keyboard.press(fkey)
            self.app.ReportText("Sending " + name + " shortcut")

        return PressShortCut


class stdoutIdleObserver:
    "Detects when IDE's stdout is idle. Can be more reliable than pixel based version (false changes ?)"

    def __init__(self):
        self.event = Event()

        self.pattern = None
        self.success_event = Event()

        if self.proc is not None:
            Thread(target=self._waitStdoutProc, daemon=True).start()

    def _waitStdoutProc(self):
        for line in iter(self.proc.stdout.readline, b""):
            a = line.decode(errors="replace")
            self.ReportOutput(a)
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

        wait_result = self.event.wait(timeout)

        self.ReportScreenShot("stdout changed" if wait_result else "stdout didn't change")

        if wait_result:
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
                self.ReportScreenShot("stdout is idle")
                return True

        self.ReportScreenShot("stdout did not idle")

        raise Exception("Stdout did not idle before timeout")

    def waitPatternInStdout(self, pattern, timeout, count=1):
        found = 0
        self.pattern = pattern
        end_time = timesec() + timeout
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
        self.ReportScreenShot("found pattern" if res else "pattern not found")
        return res


class BeremizApp(stdoutIdleObserver):
    """
    Beremiz IDE under test. Use as context manager:

        with BeremizApp(exemple="python") as app:
            app.k.Build()
    """

    def __init__(self, projectpath=None, exemple=None, testproject=None):
        """
        Starts Beremiz IDE, waits for main window to appear, maximize it.

            Parameters:
                projectpath (str): path to project to open
                exemple (str): path relative to exemples directory
                testproject (str): path relative to tests/projects directory
        """
        self.imgnum = 0
        self.starttime = timesec()
        self.display = self.proc = None

        self.report = open("report.xhtml", "w")
        self.report.write("""\
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta charset="utf-8"/>
    <meta name="color-scheme" content="light dark"/>
    <title>Test report</title>
  </head>
  <body>
""")

        try:
            self.start(projectpath, exemple, testproject)
        except:
            self.__exit__(*sys.exc_info())
            raise

    def start(self, projectpath, exemple, testproject):
        self.display = BroadwayDisplay()
        self.page = self.display.page
        self.ReportText("Broadway display " + self.display.name + " ready")

        command = [python_bin, opj(beremiz_path, "Beremiz.py"), "--log=/dev/stdout", "--devmode", "-e", agent_path]

        if exemple is not None:
            command.append(opj(beremiz_path, "exemples", exemple))
        elif projectpath is not None:
            command.append(projectpath)
        elif testproject is not None:
            command.append(opj(beremiz_path, "tests", "projects", testproject))

        agent_port = free_port()
        env = dict(self.display.env, BEREMIZ_TEST_AGENT_PORT=str(agent_port))

        self.ReportText("Launching " + repr(command))

        # new session, so that runtime spawned by IDE is killed with it
        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, env=env, start_new_session=True)

        stdoutIdleObserver.__init__(self)

        self.agent = xmlrpc.client.ServerProxy("http://127.0.0.1:%d" % agent_port, allow_none=True)
        self.wait_for(self.agent.ready, "IDE main window", timeout=30)
        self.agent.maximize()
        # without window manager, main window doesn't always get keyboard focus
        self.agent.activate()

        self.k = KBDShortcut(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        if exc_type is not None:
            self.ReportOutput("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        self.close()

    def close(self):
        if self.proc is not None:
            self.ReportScreenShot("Close app")
            if self.proc.poll() is not None:
                self.ReportText("IDE had already exited with status %d" % self.proc.returncode)
            try:
                os.killpg(self.proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.proc.wait()

        if self.display is not None:
            self.display.close()

        self.report.write("""
  </body>
</html>""")
        self.report.close()

    def wait_for(self, condition, what, timeout=10):
        """
        Wait for condition, typically a query to test agent, to become true
        Parameters:
            condition (callable): returns true when condition is met, may raise
            what (str): description of condition for report
            timeout (int): how long to wait, in seconds
        """
        end_time = timesec() + timeout
        error = None
        while timesec() < end_time:
            try:
                if condition():
                    self.ReportText("Got " + what)
                    return
            except Exception as e:
                error = e
            sleep(0.05)

        if self.proc is not None:
            self.ReportScreenShot("Timeout waiting for " + what)
        raise Exception("Timeout waiting for " + what + ("" if error is None else ": " + repr(error)))

    def WaitIdleUI(self):
        """
        Wait for IDE to process pending events, i.e. wx.CallAfter queued by
        previous actions, since requests to test agent are queued the same way
        """
        for _i in range(2):
            self.agent.value("None")
        self.ReportScreenShot("UI is idle")

    def _action(self, name, arg, action):
        desc = name + "(" + repr(arg) + ")"
        self.ReportScreenShot("Begin: " + desc)
        try:
            action()
        finally:
            self.ReportScreenShot("end: " + desc)

    def click(self, rect):
        self._action("click", rect, lambda: self.page.mouse.click(*center(rect)))

    def doubleClick(self, rect):
        self._action("doubleClick", rect, lambda: self.page.mouse.dblclick(*center(rect)))

    def rightClick(self, rect):
        self._action("rightClick", rect, lambda: self.page.mouse.click(*center(rect), button="right"))

    def type(self, text):
        self._action("type", text, lambda: self.page.keyboard.type(text, delay=20))

    def key(self, key, count=1):
        """
        Press key, possibly with modifiers, e.g. "Enter", "Control+a"
        (see playwright's Keyboard.press)
        """
        def press():
            for _i in range(count):
                self.page.keyboard.press(key)
        self._action("key", key, press)

    def popup_menu(self, *labels):
        """
        Choose item in shown popup menu with keyboard, given its label preceded by
        labels of submenus leading to it, e.g. popup_menu("Base Types", "BOOL")
        """
        keys = []
        for depth, position in enumerate(self.agent.popup_menu(labels)):
            if depth:
                # opening submenu selects its first item
                keys.append("ArrowRight")
                keys += ["ArrowDown"] * position
            else:
                keys += ["ArrowDown"] * (position + 1)
        keys.append("Enter")

        def press():
            for key in keys:
                self.page.keyboard.press(key)
        self._action("popup_menu", labels, press)

    def dragNdrop(self, src, dst):
        self.ReportScreenShot("Drag: (" + repr(src) + ")")
        mouse = self.page.mouse
        x, y = center(src)
        dst_x, dst_y = center(dst)
        mouse.move(x, y)
        mouse.down()
        # some widgets (i.e. wx generic trees) start dragging after a few moves
        # in a quarter second, that must be slow enough not to be merged by GTK
        path = [(x + dx, y) for dx in range(1, 11)] + \
               [(x + (dst_x - x) * i // 10, y + (dst_y - y) * i // 10) for i in range(1, 11)]
        for point in path:
            mouse.move(*point)
            sleep(0.05)
        mouse.up()
        # drop is done by agent, since GTK Broadway backend can't
        self.agent.drop(dst_x, dst_y)
        self.ReportScreenShot("Drop: (" + repr(dst) + ")")

    def ReportScreenShot(self, msg, page=None):
        elapsed = "%.3fs: "%(timesec() - self.starttime)
        fname = "capture"+str(self.imgnum)+".png"
        (page or self.page).screenshot(path=fname)
        sys.stdout.write(elapsed + " [" + fname + "] " + msg + "\n")
        self.imgnum = self.imgnum + 1
        self.report.write( "<p>" + escape(elapsed + msg) + "<br/><img src=\""+ fname + "\"/>" + "</p>")

    def ReportText(self, text):
        elapsed = "%.3fs: "%(timesec() - self.starttime)
        sys.stdout.write(elapsed + text + "\n")
        self.report.write("<p>" + escape(elapsed + text) + "</p>")

    def ReportOutput(self, text):
        elapsed = "%.3fs: "%(timesec() - self.starttime)
        sys.stdout.write(elapsed + text)
        self.report.write("<pre>" + escape(elapsed + text) + "</pre>")


class AuxiliaryProcess(stdoutIdleObserver):
    """
    Process running aside IDE during test, i.e. a server. Use as context manager:

        with AuxiliaryProcess(app, ["/bin/bash", "server.bash"]) as server:
            server.waitPatternInStdout("READY", 5)
    """

    def __init__(self, beremiz_app, command):
        self.app = beremiz_app
        self.app.ReportText("Launching process " + repr(command))
        self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=0)
        self.app.ReportText("Launched process " + repr(command) + " PID: " + str(self.proc.pid))
        stdoutIdleObserver.__init__(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def close(self):
        if self.proc is not None:
            proc = self.proc
            self.proc = None
            self.app.ReportText("Kill process PID: " + str(proc.pid))
            try:
                os.kill(proc.pid, signal.SIGTERM)
            except OSError:
                pass
            proc.wait()

    def ReportOutput(self, text):
        self.app.ReportOutput("Aux: "+text)

    def ReportScreenShot(self, msg):
        self.app.ReportOutput("Aux: "+msg)
