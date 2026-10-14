""" This test opens, builds and runs exemple project named "python".
Test succeeds if runtime's stdout behaves as expected
"""

# common test definitions module
from ide_harness import BeremizApp


def test_run_python_exemple():
    with BeremizApp(exemple="python") as app:

        app.k.Clean()

        app.waitForChangeAndIdleStdout()

        app.k.Build()

        app.waitPatternInStdout("Successfully built.", 10)

        app.k.Connect()

        app.waitForChangeAndIdleStdout()

        app.k.Transfer()

        app.waitForChangeAndIdleStdout()

        app.k.Run()

        # wait up to 10 seconds for 10 Grumpfs
        assert app.waitPatternInStdout("Grumpf", 10, 10)
