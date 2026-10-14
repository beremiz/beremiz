""" This test opens, modifies, builds and runs exemple project named "python".
Test succeeds if runtime's stdout behaves as expected
"""

# common test definitions module
from ide_harness import BeremizApp


def test_edit_project():
    with BeremizApp(exemple="python") as app:

        app.doubleClick(app.agent.tree_item("main_pytest"))

        app.wait_for(lambda: app.agent.active_tab() == "main_pytest", "main_pytest editor")

        app.doubleClick(app.agent.viewer_element("Hello"))

        app.wait_for(lambda: app.agent.modal_dialog() == "FBDVariableDialog", "variable dialog")

        app.click(app.agent.window("dialog.Expression"))

        app.key("Control+a")  # select text content

        app.type("'sys.stdout.write(\"EDIT TEST OK\\n\")'")

        app.key("Enter")

        app.wait_for(lambda: app.agent.modal_dialog() is None, "variable dialog to close")

        # without window manager, closed dialog doesn't give focus back to main window
        app.agent.activate()

        app.k.Clean()

        app.waitForChangeAndIdleStdout()

        app.k.Build()

        app.waitPatternInStdout("Successfully built.", 10)

        app.k.Connect()

        app.waitForChangeAndIdleStdout()

        app.k.Transfer()

        app.waitForChangeAndIdleStdout()

        app.k.Run()

        # wait 10 seconds for 10 patterns
        assert app.waitPatternInStdout("EDIT TEST OK", 10)
