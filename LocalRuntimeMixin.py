#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import tempfile
import random
import shutil
from util.ProcessLogger import ProcessLogger
from util.paths import Bpath

class LocalRuntimeMixin():

    def __init__(self, log):
        self.local_runtime_log = log
        self.local_runtime = None
        self.runtime_port = None
        self.local_runtime_tmpdir = None

    def StartLocalRuntime(self, taskbaricon=True):
        if (self.local_runtime is None) or (self.local_runtime.exitcode is not None):
            # create temporary directory for runtime working directory
            self.local_runtime_tmpdir = tempfile.mkdtemp()
            # choose an arbitrary random port for runtime
            self.runtime_port = int(random.random() * 1000) + 61131
            self.local_runtime_log.write(_("Starting local runtime...\n"))
            # launch local runtime
            self.local_runtime = ProcessLogger(
                self.local_runtime_log,
                "\"%s\" \"%s\" -p %s -i localhost %s %s" % (
                    sys.executable,
                    Bpath("Beremiz_service.py"),
                    self.runtime_port,
                    {False: "-x 0", True: "-x 1"}[taskbaricon],
                    self.local_runtime_tmpdir),
                no_gui=False,
                timeout=500, keyword=self.local_runtime_tmpdir,
                cwd=self.local_runtime_tmpdir)
            self.local_runtime.spin()
        return self.runtime_port

    def KillLocalRuntime(self):
        if self.local_runtime is not None:
            # shutdown local runtime
            self.local_runtime.kill(gently=False)
            # clear temp dir
            shutil.rmtree(self.local_runtime_tmpdir)

            self.local_runtime = None

