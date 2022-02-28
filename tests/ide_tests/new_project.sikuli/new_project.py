""" This test opens, builds and runs a new project.
Test succeeds if runtime's stdout behaves as expected
"""

import os
import time

# allow module import from current test directory's parent
addImportPath(os.path.dirname(getBundlePath()))

# common test definitions module
from sikuliberemiz import *

# Start the app without any project given
proc,app = StartBeremizApp()

new_project_path = os.path.join(os.path.abspath(os.path.curdir), "new_test_project")

# New project path must exist (usually created in directory selection dialog)
os.mkdir(new_project_path)

# To detect when actions did finish because IDE content isn't changing
idle = IDEIdleObserver(app)

# To send keyboard shortuts
k = KBDShortcut(app)

idle.Wait(1,15)

# Create new project (opens new project directory selection dialog)
k.New()

idle.Wait(1,15)

# Move to "Home" section of file selecor, otherwise address is 
# "file ignored" at first run
type("f", Key.CTRL)
type(Key.ESC)
type(Key.TAB)

# Enter directory by name
k.Address()

# Fill address bar
type(new_project_path + Key.ENTER)

idle.Wait(1,15)

# When prompted for creating first program select type ST
type(Key.TAB*4)  # go to lang dropdown
type(Key.DOWN*2) # change selected language
type(Key.ENTER)  # validate

idle.Wait(1,15)

# Name created program
type("Test program")

idle.Wait(1,15)

# Focus on Variable grid
type(Key.TAB*4)

# Add 2 variables
type(Key.ADD*2)

# Focus on ST text
idle.Wait(1,15)

type(Key.TAB*8)

type("""\
LocalVar0 := LocalVar1;
{printf("Test OK\\n");fflush(stdout);}
""")

k.Save()

# Close ST POU
type("w", Key.CTRL)

idle.Wait(1,15)

# Focus project tree and select root item
type(Key.TAB)

type(Key.LEFT)

type(Key.UP)

# Edit root item
type(Key.ENTER)

idle.Wait(1,15)

# Switch to config tab
type(Key.RIGHT*2)

# Focus on URI
type(Key.TAB)

# Set URI
type("LOCAL://")

# FIXME: Select other field to ensure URI is validated
type(Key.TAB)

k.Save()

# Close project config editor
type("w", Key.CTRL)

idle.Wait(1,15)

# Focus seems undefined at that time (FIXME)
# Force focussing on "something" so that next shortcut is taken
type(Key.TAB)

del idle

stdoutIdle = stdoutIdleObserver(proc)
stdoutIdle.Wait(2,15)

k.Build()

stdoutIdle.Wait(5,15)

k.Connect()

stdoutIdle.Wait(2,15)

k.Transfer()

stdoutIdle.Wait(2,15)

del stdoutIdle

k.Run()

# wait 10 seconds
found = waitPatternInStdout(proc, "Test OK", 10)

app.close()

if found:
    exit(0)
else:
    exit(1)

