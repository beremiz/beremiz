# Running test in a docker container

## Image and container lifecycle

Tests run in a container named `beremiz_playwright_current`, created from an image
named `beremiz_playwright`. Scripts in this directory manage both, and must be run
from this directory.

### Image

`./build_docker_image.sh` builds the image from `Dockerfile`. It contains
build tools, Python venv `~/beremizenv` with pinned requirements, Playwright's
headless Chromium, `broadwayd`, and `do_tests` command (`make` with
`tests/Makefile`). It contains no source code.

Image is built with your user's UID and GID, so that files written by tests in
mounted directories belong to you.

Rebuild image after changing `Dockerfile`, `../../../requirements_pinned.txt` or
`requirements_tests_pinned.txt`. Existing container keeps using old image until
it is created again, see `rebuild_docker.sh` below.

### Container

`./create_docker_container.sh [TESTDIR]` creates container, mounting:

- directory containing `beremiz`, `matiec`, `open62541`, etc. on `~/src`
- `TESTDIR` (default `~/test`) on `~/test`, container's working directory

Container is created once and reused. Its file system persists, but it is
stopped between runs.

### Running tests

`./do_test_in_docker.sh TARGET` starts container, runs `do_tests TARGET`,
and stops container. `TARGET` is any `tests/Makefile` target, and may include
variables:

```
./do_test_in_docker.sh ide_tests
./do_test_in_docker.sh "cli_tests pytest_ide_tests"
./do_test_in_docker.sh "BEREMIZ_TEST_TRACE=1 edit_project.pytest"
```

Sources are copied in `TESTDIR/build` and built there when changed. Results of
each test are in `TESTDIR/<test>_results` (`test_stdout.txt`, and for IDE tests
`report.xhtml` with screenshots). Passed tests are not run again until their
results are deleted, i.e. with `clean_results` target.

Restarting container also clears its `/dev/shm`, used by GTK Broadway backend.

### Interactive use

- `./enter_docker.sh`: shell as user `ubuntu`. Container stops when shell exits.
- `./enter_docker_as_root.sh`: shell as root, i.e. to install debugging tools.
- `./exec_in_docker_as_root.sh "COMMAND"`: run one command as root.

Changes made in container file system, i.e. installed packages, are lost when
container is created again.

### Cleanup and rebuild

- `./clean_docker_container.sh`: delete container. `TESTDIR` is kept.
- `./clean_docker_image.sh`: delete image.
- `./rebuild_docker.sh [TESTDIR]`: delete container and image, build image and
  create container.

### Debug mode: TESTDEBUG=YES

Published ports and mounts are fixed when container is created. Debug mode is
then selected at creation:

```
./clean_docker_container.sh
TESTDEBUG=YES ./create_docker_container.sh
```

or `TESTDEBUG=YES ./rebuild_docker.sh` if image must be rebuilt too.

Debug mode publishes on host:

- port 8080, for IDE session (`do_tests ide_session`)
- port 9222, for Chromium remote debugging (`BEREMIZ_TEST_DEVTOOLS=9222`)

Both are used by procedures below. Ports must be free on host.

Container must be created again without `TESTDEBUG` to leave debug mode.

## IDE UI tests: Monitor and interact

You can have a live view of running tests, and an interactive session where `Ctrl+Shift+click` on a widget prints the string to pass to the agent.

### Watching a test live.

The test's headless Chromium can expose a DevTools port instead:
```
./do_test_in_docker.sh "BEREMIZ_TEST_DEVTOOLS=9222 BEREMIZ_TEST_SLOWMO=300 edit_project.pytest"
```
Then, in Chrome or Chromium on the host, go to `chrome://inspect`, add `localhost:9222` under "Configure", and click "inspect" on the page. DevTools shows the page live and lets you interact. `BEREMIZ_TEST_SLOWMO` adds a delay (in ms) to each input action, so you can follow along.

For after the fact, `BEREMIZ_TEST_TRACE=1` still saves `trace.zip`.

### Writing a test.

A new session mode runs the IDE with the test agent, as in tests, but your own browser is the display:

```
./enter_docker.sh
do_tests ide_session ide_session_project=exemples/python
```

Open `http://localhost:8080`, and the IDE starts once your browser connects. Use it normally; Ctrl+Shift+click any widget and the call to use in a test is printed in the terminal and the IDE console:

```
INSPECT: app.agent.tree_item('main_pytest')
INSPECT: app.agent.viewer_pin('MOVE', 'OUT')
INSPECT: app.agent.grid_cell('page.VariableEditor.VariablesGrid', 0, 'Type')
INSPECT: app.agent.window('page.VariableEditor.AddButton')
INSPECT: app.agent.window('dialog.Expression')
INSPECT: app.agent.notebook_tab('page.ConfNodeNoteBook', 'Config')
```

Wrap whichever line fits in `app.click(...)`, `app.doubleClick(...)` or `app.dragNdrop(...)`.

- **How `window()` strings are found:** by searching named attributes (and dict entries and notebook pages) from the open dialog, the selected editor, then the main window. If nothing matches, it uses `wx.FindWindowByName`.
- **Trying expressions before writing them:** the session prints the agent's port, so you can test strings from a Python shell inside the container (`xmlrpc.client.ServerProxy(...).window("...")`).
- **How it shows up in your browser:** the session serves the Broadway page through a small proxy that applies the same client fix as the tests. Without that fix, wx's first command blanks the page.
- **Scope:** the inspector is only enabled in session mode (`BEREMIZ_TEST_INSPECT`), so normal test runs don't pay for the global wx event filter.
