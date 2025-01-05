#!/usr/bin/env python
# -*- coding: utf-8 -*-

# copyright 2024: Edouard TISSERANT

"""
Setup and run Zephyr build tools on Windows.
"""

import os
from os.path import join, exists
from shutil import rmtree
from util.paths import ThirdPartyPath
from util.ProcessLogger import ProcessLogger
from .ZephyrBuildBase import ZephyrBuildBase, ZephyrBuildException


class ZephyrWindowsBuild(ZephyrBuildBase):
    """
    On windows, Beremiz IDE runs on MSYS2 python, but
    Zephyr build requires _native_ python and cmake.
    
    This class use nuget to install python and cmake in the Zephyr workspace.    
    """

    ZephyrSdkUnpackCommand = ["7z", "x"]
    ZephyrSdkOsName = "windows"
    ZephyrSdkArch = 'x86_64'
    ZephyrSdkTargets = ["arm-zephyr-eabi"]

    
    # Nuget packages versions
    package_versions = [
        # Python 3.12 not supported by Zephyr according to Getting Started Guide
        ("python", "3.11.9"),
        ("cmake", "3.5.2")]
    # TODO: Git ?

    def __init__(self, log):
        super().__init__(log)
        
        # Where to store tools installed by nuget
        self.NugetTools = join(self.ZephyrDir, "nuget_tools")

        # Paths to be used in the Zephyr environment
        self.PythonHome = join(self.NugetTools, "python", "tools")
        self.CmakeBin = join(self.NugetTools, "CMake", "bin")        

        # Compute environment for future executions:
        # - Get Beremiz installation directory
        inst_dir = ThirdPartyPath("")

        # - Remove internal Beremiz paths from PATH environment variable
        #   in order to avoid interference with the native build
        paths = os.environ["PATH"].split(os.pathsep)
        new_paths = [path for path in paths if not path.startswith(inst_dir)]
        
        # - Add installed tools paths
        new_paths += [self.PythonHome, join(self.PythonHome, "Scripts"), self.CmakeBin]

        # - Compose the environment
        self.ExecEnv = {"PATH": os.pathsep.join(new_paths),
                        "PYTHONHOME": self.PythonHome,
                        "ZEPHYR_SDK_INSTALL_DIR": self.ZephyrSDK,
                        "ZEPHYR_BASE": self.ZephyrWorkspace,
                        "HOME": self.ZephyrDir}

    def EnsureDependencies(self):
        if not (exists(self.PythonHome) and 
                exists(self.CmakeBin)):
            self.InstallDependencies()
            return True
        else:
            self.log.write(f"Using existing nuget tools in {self.NugetTools}\n")

    def InstallDependencies(self):
        "Use nuget to install python and cmake."
        
        if exists(self.NugetTools):
            rmtree(self.NugetTools)
        
        os.makedirs(self.NugetTools)
        
        self.Download(
            'https://dist.nuget.org/win-x86-commandline/latest/nuget.exe',
            join(self.NugetTools ,'nuget.exe'))

        for package, version in self.package_versions:
            self.log.write("Installing {package} {version}\n")
            res,*_ignore = self.RunBuildProcess([
                join(self.NugetTools ,'nuget.exe'), 'install', package, '-Version', version,
                '-ExcludeVersion', '-OutputDirectory', self.NugetTools])
            if res != 0:
                raise ZephyrBuildException(f"Failed to install {package}")

    def RunBuildProcess(self, command, working_dir=None, env=None):
        "Run command as a native (non-MSYS2) process."
        proc = ProcessLogger(
            self.log,command,
            cwd=self.ZephyrDir if working_dir is None else working_dir,
            env=self.ExecEnv if env is None else dict(self.ExecEnv, **env),
            show_cmd=True)
        return proc.spin()

    def RunPIP(self, command):
        "Run a pip command in the Zephyr workspace."
        return self.RunBuildProcess([join(self.PythonHome ,'python.exe'), '-m', 'pip'] + command)

    def RunWest(self, command, working_dir=None):
        "Run a west command in the Zephyr workspace."
        return self.RunBuildProcess([join(self.PythonHome ,'python.exe'), '-m', 'west'] + command,
                                    working_dir=working_dir)


