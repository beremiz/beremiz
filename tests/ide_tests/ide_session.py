"""Interactive Beremiz IDE session, to help writing IDE tests

IDE runs with test agent on GTK Broadway backend, as during tests, but is
displayed in your own browser:

    BEREMIZPATH=path/to/beremiz python ide_session.py [project path]

or in docker container created with TESTDEBUG=YES, entered with enter_docker.sh:

    do_tests ide_session ide_session_project=exemples/python

then open http://localhost:8080 in your browser. Project path is relative to
beremiz directory. IDE starts once browser is connected, and session ends with
IDE.

Ctrl+Shift+click on any widget prints agent requests locating it. Agent
requests can also be tried from python, at printed agent port (in container
when using docker):

    import xmlrpc.client
    agent = xmlrpc.client.ServerProxy("http://localhost:PORT", allow_none=True)
    agent.window("page.VariableEditor.AddButton")
"""

import os
import re
import sys
import signal
import asyncio
import urllib.request
import xmlrpc.client

from ide_harness import BroadwayDisplay, broadway_client_fix, free_port, beremiz_path, python_bin, agent_path, opj

session_port = int(os.environ.get("BEREMIZ_SESSION_PORT", "8080"))


async def relay(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    finally:
        writer.close()


async def session(display, project):
    connected = asyncio.Event()

    async def handle(reader, writer):
        try:
            await proxy(reader, writer)
        except (ConnectionError, asyncio.IncompleteReadError):
            pass

    async def proxy(reader, writer):
        "Proxy to broadwayd, fixing broadway client as tests do"
        request = await reader.readuntil(b"\r\n\r\n")
        if request.startswith(b"GET / "):
            page = urllib.request.urlopen("http://127.0.0.1:%d/" % display.port).read()
            page = page.replace(b"</body>", b"<script>(%s)();</script></body>" % broadway_client_fix.encode())
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: %d\r\n"
                         b"Connection: close\r\n\r\n%s" % (len(page), page))
            await writer.drain()
            writer.close()
            return
        if b"\r\nupgrade: websocket" in request.lower():
            connected.set()
        else:
            # no keep-alive, so that reloaded page always gets fixed
            request = re.sub(rb"(?im)^connection:.*\r\n", b"", request)[:-2] + b"Connection: close\r\n\r\n"
        upstream_reader, upstream_writer = await asyncio.open_connection("127.0.0.1", display.port)
        upstream_writer.write(request)
        await asyncio.gather(relay(reader, upstream_writer), relay(upstream_reader, writer))

    await asyncio.start_server(handle, "0.0.0.0", session_port)
    print("Open http://localhost:%d in your browser" % session_port, flush=True)
    await connected.wait()

    command = [python_bin, opj(beremiz_path, "Beremiz.py"), "--devmode", "-e", agent_path]
    if project:
        command.append(opj(beremiz_path, project))
    agent_port = free_port()
    env = dict(display.env, BEREMIZ_TEST_AGENT_PORT=str(agent_port), BEREMIZ_TEST_INSPECT="1")
    # new session, so that runtime spawned by IDE is killed with it
    proc = await asyncio.create_subprocess_exec(*command, env=env, start_new_session=True)
    try:
        # same as in tests. Agent is called from other thread, not to block proxy
        agent = xmlrpc.client.ServerProxy("http://127.0.0.1:%d" % agent_port, allow_none=True)
        loop = asyncio.get_running_loop()
        while proc.returncode is None:
            try:
                if await loop.run_in_executor(None, agent.ready):
                    await loop.run_in_executor(None, agent.maximize)
                    await loop.run_in_executor(None, agent.activate)
                    print("Test agent on port %d" % agent_port, flush=True)
                    break
            except (ConnectionError, xmlrpc.client.Fault):
                pass  # IDE starting
            await asyncio.sleep(0.2)
        await proc.wait()
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


if __name__ == "__main__":
    display = BroadwayDisplay(browser=False)
    try:
        asyncio.run(session(display, sys.argv[1] if len(sys.argv) > 1 else None))
    except KeyboardInterrupt:
        pass
    finally:
        display.close()
