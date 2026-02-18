#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import posixpath
import sys
import time

from functools import wraps
from importlib import import_module

import click

from util import SetDeveloperMode, SetSDKPath

class CLISession(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.controller = None

pass_session = click.make_pass_decorator(CLISession)


@click.group(chain=True)
@click.option(
    "--project-home",
    envvar="PROJECT_HOME",
    default=".",
    metavar="PATH",
    help="Changes the project folder location.",
)
@click.option(
    "--config",
    nargs=3,
    multiple=True,
    metavar="KEY TYPE VALUE",
    help="""Overrides a config key/value pair.
    KEY:
        ex: TargetType.Board.BuildType.EnableMCUBoot
    
    TYPE=boolean/string/integer
    VALUE:
        boolean: true/false
        string: "string with space"
        integer: 1234
    """,
)
@click.option(
    "--keep", "-k", is_flag=True,
    help="Keep local runtime, do not kill it after executing commands.",
)
@click.option("--verbose", "-v", is_flag=True, help="Enables verbose mode.")
@click.option(
    "--sdkpath", "-s", help="Path to PLC SDK folder."
)
@click.option(
    "--buildpath", "-b", help="Where to store files created during build."
)
@click.option(
    "--uri", "-u", help="URI to reach remote PLC."
)
@click.option(
    "--extend", "-e", multiple=True, metavar="PATH",
    help="Extend functionality by loading additional extension at start.",
)
@click.version_option("0.1")
@click.pass_context
def cli(ctx, **kwargs):
    """Beremiz CLI manipulates beremiz projects and runtimes. """

    ctx.obj = CLISession(**kwargs)

def ensure_controller(func):
    @wraps(func)
    def func_wrapper(session, *args, **kwargs):
        if session.controller is None:
            import_module("fake_wx")
            if session.verbose:
                SetDeveloperMode()
            if session.sdkpath is not None:
                SetSDKPath(session.sdkpath)
            LoadExtensions(session.extend)
            session.module = import_module("CLIController")
            session.controller = session.module.CLIController(session)
        ret = func(session, *args, **kwargs)
        return ret

    return func_wrapper


def LoadExtensions(extensions):
    for extfilename in extensions:
        from util.TranslationCatalogs import AddCatalog
        from util.BitmapLibrary import AddBitmapFolder
        extension_folder = os.path.split(os.path.realpath(extfilename))[0]
        sys.path.append(extension_folder)
        AddCatalog(os.path.join(extension_folder, "locale"))
        AddBitmapFolder(os.path.join(extension_folder, "images"))
        exec(compile(open(extfilename, "rb").read(), extfilename, 'exec'))


@cli.command()
@pass_session
@ensure_controller
def clean(session):
    """Cleans project. """
    def processor():
        return session.controller.clean_project()
    return processor

@cli.command()
@click.option(
    "--target", "-t", help="Target system triplet."
)
@pass_session
@ensure_controller
def build(session, target):
    """Builds project. """
    def processor():
        return session.controller.build_project(target)
    return processor

@cli.command()
@pass_session
@ensure_controller
def transfer(session):
    """Transfer program to PLC runtime."""
    def processor():
        return session.controller.transfer_project()
    return processor

@cli.command()
@pass_session
@ensure_controller
def run(session):
    """Run program already present in PLC."""
    def processor():
        return session.controller.run_project()
    return processor

@cli.command()
@pass_session
@ensure_controller
def stop(session):
    """Stop program running in PLC."""
    def processor():
        return session.controller.stop_project()
    return processor

@cli.command()
@pass_session
@ensure_controller
def connect(session):
    """Connect to PLC."""
    def processor():
        return session.controller.connect_project()
    return processor

@cli.command()
@pass_session
@ensure_controller
def flush(session):
    """Empty PLC log."""
    def processor():
        return session.controller.clear_log()
    return processor

@cli.result_callback()
@pass_session
@click.pass_context
def process_pipeline(ctx, session, processors, **kwargs):
    ret = 0
    for processor in processors:
        ret = processor()
        if ret != 0:
            if len(processors) > 1 :
                click.echo("Command sequence aborted")
            break

    if ret == 0 and session.keep:
        click.echo("Press Ctrl+C to quit")
        try:
            while True:
                PLC_State = session.controller.UpdateMethodsFromPLCStatus()
                if PLC_State == session.module.PlcStatus.Disconnected:
                    break
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    session.controller.finish()

    if ret != 0:
        click.echo("Command failed with code {}".format(ret))
        ctx.exit(ret)

if __name__ == '__main__':
    cli()

