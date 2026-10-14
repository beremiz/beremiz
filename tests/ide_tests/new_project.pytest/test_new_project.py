""" This test creates a new project with a ST program, then builds and runs it.
Test succeeds if runtime's stdout behaves as expected
"""

import os

# common test definitions module
from ide_harness import BeremizApp


def test_new_project():
    new_project_path = os.path.join(os.path.abspath(os.path.curdir), "new_test_project")

    # New project path must exist (usually created in directory selection dialog)
    os.mkdir(new_project_path)

    with BeremizApp() as app:

        # Create new project (opens new project directory selection dialog)
        app.k.New()

        app.wait_for(lambda: app.agent.modal_dialog() == "DirDialog", "directory selection dialog")

        # Enter directory by name in address bar of GTK's file selector
        app.k.Address()

        app.type(new_project_path)

        app.key("Enter")

        # When prompted for creating first program select language ST
        app.wait_for(lambda: app.agent.modal_dialog() == "PouDialog", "new program dialog")

        app.click(app.agent.window("dialog.Language"))

        languages = app.agent.value("dialog.Language.GetItems()")

        app.key("ArrowDown", languages.index("ST") + 1)

        app.key("Enter")

        app.click(app.agent.window("dialog.FindWindow(wx.ID_OK)"))

        app.wait_for(lambda: app.agent.active_tab() == "program0", "program editor")

        variables = "page.VariableEditor.VariablesGrid"

        # 2 first variables are BOOL. Variable can't be duplicated with
        # Ctrl+Add here, since wx.GetKeyState() only works with X11.
        for row in range(2):
            app.click(app.agent.window("page.VariableEditor.AddButton"))

            app.click(app.agent.grid_cell(variables, row, "Type"))

            app.key("Space")  # opens type selection menu

            app.popup_menu("Base Types", "BOOL")

        # 3rd variable is a LOGGER FB
        app.click(app.agent.window("page.VariableEditor.AddButton"))

        app.click(app.agent.grid_cell(variables, 2, "Type"))

        app.key("Space")

        app.popup_menu("Function Block Types", "LOGGER")

        types = "[str(table.GetValueByName(row, 'Type')) for table in [page.VariableEditor.Table] for row in range(table.GetNumberRows())]"
        app.wait_for(lambda: app.agent.value(types) == ["BOOL", "BOOL", "LOGGER"], "variables types")

        app.click(app.agent.window("page.Editor"))

        app.type("""\
LocalVar0 := NOT(LocalVar1);
LocalVar2(TRIG := LocalVar1, MSG := 'Test OK', LEVEL := LOGLEVEL#INFO);
LocalVar1 := LocalVar0;
""")

        # Editor updates project with typed text after a while
        app.WaitIdleUI()

        app.k.Save()

        # Close ST POU
        app.key("Control+w")

        # Edit project root
        app.doubleClick(app.agent.tree_item(None))

        app.wait_for(lambda: app.agent.value("page.__class__.__name__") == "ProjectNodeEditor", "project editor")

        app.click(app.agent.notebook_tab("page.ConfNodeNoteBook", "Config"))

        app.click(app.agent.window('wx.FindWindowByName("URI_location", page)'))

        app.type("LOCAL://")

        # Select other field to ensure URI is validated
        app.key("Tab")

        app.WaitIdleUI()

        app.k.Save()

        # Close project config editor
        app.key("Control+w")

        # Closed editor had focus. Focus on something else so that next shortcut is taken
        app.click(app.agent.tree_item(None))

        app.waitIdleStdout()

        app.k.Build()

        app.waitPatternInStdout("Successfully built.", 10)

        app.k.Connect()

        app.waitIdleStdout()

        app.k.Transfer()

        app.waitIdleStdout()

        app.k.Run()

        # wait 10 seconds
        assert app.waitPatternInStdout("Test OK", 10)
