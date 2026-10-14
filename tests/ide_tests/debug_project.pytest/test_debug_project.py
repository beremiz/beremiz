""" This test builds and runs exemple project named "python", opens main program
in debugger, and forces a value from there.
Test succeeds if runtime's stdout behaves as expected
"""

# common test definitions module
from ide_harness import BeremizApp


def test_debug_project():
    with BeremizApp(exemple="python") as app:

        app.k.Clean()

        app.waitForChangeAndIdleStdout()

        app.k.Build()

        app.waitPatternInStdout("Successfully built.", 10)

        app.k.Connect()

        app.waitForChangeAndIdleStdout()

        app.k.Transfer()

        app.waitForChangeAndIdleStdout()

        # selected program's instance shows up in instance panel
        app.click(app.agent.tree_item("main_pytest"))

        # glasses button opens instance in debugger
        app.click(app.agent.window("frame.PouInstanceVariablesPanel.DebugButton"))

        app.wait_for(lambda: app.agent.value("page.IsDebugging()"), "main_pytest debugger")

        app.k.Run()

        # wait up to 10 seconds for 10 Grumpfs
        app.waitPatternInStdout("Grumpf", 10, 10)

        app.rightClick(app.agent.viewer_pin("MOVE", "OUT"))

        app.popup_menu("Force value")

        app.wait_for(lambda: app.agent.modal_dialog() == "ForceVariableDialog", "force dialog")

        app.click(app.agent.window("dialog.ValueCtrl"))

        app.key("Control+a")  # select text content

        app.type("'sys.stdout.write(\"DEBUG TEST OK\\n\")'")

        app.key("Enter")

        # wait 10 seconds for 10 patterns
        assert app.waitPatternInStdout("DEBUG TEST OK", 10)
