""" This test opens, modifies, builds and runs exemple project named "python".
Test succeeds if runtime's stdout behaves as expected
"""

import os
import time

# allow module import from current test directory's parent
addImportPath(os.path.dirname(getBundlePath()))

# common test definitions module
from sikuliberemiz import *

# Start the app
proc,app = StartBeremizApp(exemple="python")

# To detect when actions did finish because IDE content isn't changing
idle = IDEIdleObserver(app)

doubleClick("1646062660770.png")

idle.Wait(1,15)

click("1646066794902.png")

idle.Wait(1,15)

type(Key.DOWN * 10, Key.CTRL)

idle.Wait(1,15)

doubleClick("1646066996620.png")

idle.Wait(1,15)

type(Key.TAB*3)  # select text content

type("'sys.stdout.write(\"EDIT TEST OK\\n\")'")

type(Key.ENTER)

idle.Wait(1,15)

k = KBDShortcut(app)

k.Save()

del idle

stdoutIdle = stdoutIdleObserver(proc)

k.Clean()

stdoutIdle.WaitForChangeAndIdle(2,15)

k.Build()

stdoutIdle.WaitForChangeAndIdle(2,15)

k.Connect()

stdoutIdle.WaitForChangeAndIdle(2,15)

k.Transfer()

stdoutIdle.WaitForChangeAndIdle(2,15)

del stdoutIdle

k.Run()

# wait 10 seconds for 10 Grumpfs
found = waitPatternInStdout(proc, "EDIT TEST OK", 10)

app.close()

if found:
    exit(0)
else:
    exit(1)

