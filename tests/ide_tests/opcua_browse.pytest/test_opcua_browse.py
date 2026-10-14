""" This test browses an OPC-UA server from OPC-UA client configuration editor of
test project named "opcua_browse", selects variables, then builds and runs it.
Test succeeds if runtime's stdout behaves as expected
"""

import os

# common test definitions module
from ide_harness import BeremizApp, AuxiliaryProcess

server_command = ["/bin/bash", os.path.join(os.path.dirname(__file__), "opcua_service.bash")]


def test_opcua_browse():
    with BeremizApp(testproject="opcua_browse") as app, \
         AuxiliaryProcess(app, server_command) as server:

        server.waitPatternInStdout("SERVER READY", 10)

        app.doubleClick(app.agent.tree_item("0.x: opcua_0"))

        panel = "page.ConfNodeNoteBook.GetPage(0)"

        app.wait_for(lambda: app.agent.value("page.__class__.__name__") == "OPCUAClientEditor",
                     "OPC-UA client editor")

        app.click(app.agent.window(panel + ".connect_button"))

        tree = panel + ".tree"

        for parent, child in [("Objects", "TestObject"), ("TestObject", "TestIn")]:
            app.wait_for(lambda: app.agent.tree_item(parent, tree), parent + " node")

            app.doubleClick(app.agent.tree_item(parent, tree))

            app.wait_for(lambda: app.agent.tree_item(child, tree), child + " node")

        selected = "len(%s.selected_models[%%r].data)" % panel

        app.dragNdrop(app.agent.tree_item("TestIn", tree), app.agent.window(panel + '.selected_lists["output"]'))

        app.wait_for(lambda: app.agent.value(selected % "output") == 1, "output variable")

        app.dragNdrop(app.agent.tree_item("TestOut", tree), app.agent.window(panel + '.selected_lists["input"]'))

        app.wait_for(lambda: app.agent.value(selected % "input") == 1, "input variable")

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
        assert app.waitPatternInStdout("6.8", 10)
