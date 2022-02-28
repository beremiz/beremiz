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
# idle = IDEIdleObserver(app)
# screencap based idle detection was making many false positive. Test is more stable with stdout based idle detection

doubleClick("1646062660770.png")

click("1646066794902.png")

type(Key.DOWN * 10, Key.CTRL)

doubleClick("1646066996620.png")

type(Key.TAB*3)  # select text content

type("'sys.stdout.write(\"EDIT TEST OK\")'")

type(Key.ENTER)

stdoutIdle = stdoutIdleObserver(proc)

# To send keyboard shortuts
k = KBDShortcut(app)

k.Clean()

stdoutIdle.Wait(2,15)

k.Save()
k.Build()

stdoutIdle.Wait(2,15)

k.Connect()

stdoutIdle.Wait(2,15)

k.Transfer()

stdoutIdle.Wait(2,15)

#del idle

del stdoutIdle

k.Run()

# wait 10 seconds for 10 Grumpfs
found = waitPatternInStdout(proc, "EDIT TEST OK", 10)

app.close()

if found:
    exit(0)
else:
    exit(1)

