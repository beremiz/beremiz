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
app = BeremizApp(exemple="python")

app.k.Clean()

app.waitForChangeAndIdleStdout()

app.k.Build()

app.waitForChangeAndIdleStdout()

app.k.Connect()

app.waitForChangeAndIdleStdout()

app.k.Transfer()

app.waitForChangeAndIdleStdout()

app.k.Run()

# wait 10 seconds for 10 Grumpfs
found = app.waitPatternInStdout("Grumpf", 10, 10)

app.close()

if found:
    exit(0)
else:
    exit(1)

