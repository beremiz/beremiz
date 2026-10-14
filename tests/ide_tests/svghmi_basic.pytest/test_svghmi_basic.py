""" This test builds and runs test project named "svghmi_basic", and clicks
a button in its HMI.
Test succeeds if runtime's stdout behaves as expected
"""

# common test definitions module
from ide_harness import BeremizApp


def test_svghmi_basic():
    with BeremizApp(testproject="svghmi_basic") as app:

        app.k.Clean()

        app.waitForChangeAndIdleStdout()

        app.k.Build()

        app.waitPatternInStdout("Successfully built.", 10)

        app.k.Connect()

        app.waitForChangeAndIdleStdout()

        app.k.Transfer()

        app.waitForChangeAndIdleStdout()

        app.k.Run()

        app.waitForChangeAndIdleStdout()

        # Test project doesn't start any browser, HMI is opened in test's browser
        hmi = app.page.context.new_page()

        hmi.goto("http://localhost:8008/svghmi_0#watchdog")

        # widgets react to clicks once initialized
        hmi.wait_for_function("document.getElementById('g220').onclick !== null")

        app.ReportScreenShot("HMI ready", hmi)

        # "OFF" text in ToggleButton widget
        hmi.click("#text1542")

        # wait 10 seconds
        assert app.waitPatternInStdout("ALL GREEN LIGHTS", 10)
