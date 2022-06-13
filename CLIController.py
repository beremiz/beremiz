#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from functools import wraps

import click

import fake_wx

from ProjectController import ProjectController
from LocalRuntimeMixin import LocalRuntimeMixin

class Log:

    def __init__(self):
        self.crlfpending = False

    def write(self, s):
        if s:
            if self.crlfpending:
                sys.stdout.write("\n")
            sys.stdout.write(s)
            self.crlfpending = 0

    def write_error(self, s):
        if s:
            self.write("Error: "+s)

    def write_warning(self, s):
        if s:
            self.write("Warning: "+s)

    def flush(self):
        sys.stdout.flush()
        
    def isatty(self):
        return False

    def progress(self, s):
        if s:
            sys.stdout.write(s+"\r")
            self.crlfpending = True


def with_project_loaded(func):
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        if not self.HasOpenedProject():
            if self.check_and_load_project():
                return 1 
            self.apply_config()
        return func(self, *args, **kwargs)

    return func_wrapper

def connected(func):
    @wraps(func)
    def func_wrapper(self, *args, **kwargs):
        if self._connector is None:
            if self.session.uri:
                self.BeremizRoot.setURI_location(self.session.uri)
            if not self._Connect():
                return 1
        return func(self, *args, **kwargs)

    return func_wrapper

class CLIController(LocalRuntimeMixin, ProjectController):
    def __init__(self, session):
        self.session = session
        log = Log()
        LocalRuntimeMixin.__init__(self, log)
        ProjectController.__init__(self, None, log)

    def check_and_load_project(self):
        if not os.path.isdir(self.session.project_home):
            self.logger.write_error(
                _("\"%s\" is not a valid Beremiz project\n") % self.session.project_home)
            return True

        errmsg, error = self.LoadProject(self.session.project_home, self.session.buildpath)
        if error:
            self.logger.write_error(errmsg)
            return True

    def apply_config(self):
        for k,v in self.session.config:
            self.SetParamsAttribute("BeremizRoot."+k, v)

    @with_project_loaded
    def build_project(self, target):

        if target:
            self.SetParamsAttribute("BeremizRoot.TargetType", target)
            
        return 0 if self._Build() else 1

    @with_project_loaded
    @connected
    def transfer_project(self):

        return 0 if self._Transfer() else 1

    @with_project_loaded
    @connected
    def run_project(self):

        return 0 if self._Run() else 1
        

    def finish(self):

        self._Disconnect()

        if not self.session.keep:
            self.KillLocalRuntime()


