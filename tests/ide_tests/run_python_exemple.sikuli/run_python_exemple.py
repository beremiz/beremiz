""" This test opens, builds and runs exemple project named "python".
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

stdoutIdle = stdoutIdleObserver(proc)

# To send keyboard shortuts
k = KBDShortcut(app)

k.Clean()

stdoutIdle.Wait(2,15)

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
found = waitPatternInStdout(proc, "Grumpf", 10, 10)

app.close()

if found:
    exit(0)
else:
    exit(1)

