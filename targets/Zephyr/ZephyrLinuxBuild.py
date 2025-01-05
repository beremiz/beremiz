#!/usr/bin/env python
# -*- coding: utf-8 -*-

# copyright 2024: Edouard TISSERANT

"""
Setup and run Zephyr build tools on Linux.
"""

import platform
import os
from shutil import rmtree
from os.path import join, exists

from util.ProcessLogger import ProcessLogger
from .ZephyrBuildBase import ZephyrBuildBase, ZephyrBuildException


class ZephyrLinuxBuild(ZephyrBuildBase):
    """
    Rely on python venv to setup the Zephyr build environment.
    """
    
    ZephyrSdkUnpackCommand = ["tar", "--checkpoint=1000", "--checkpoint-action=.", "-xJf"]
    ZephyrSdkOsName = "linux"
    ZephyrSdkArch = 'x86_64' if platform.machine() == 'x86_64' else 'aarch64'
    ZephyrSdkTargets = ["arm-zephyr-eabi"]# ,
                        # f"{ZephyrSdkArch}-zephyr-elf"] # for native_sim target
                        

    def __init__(self, *args):
        super().__init__(*args)

        self.venv = join(self.ZephyrDir, "venv")

        self.WestExecEnv = os.environ.copy()
        self.WestExecEnv.update(
            {"ZEPHYR_SDK_INSTALL_DIR": self.ZephyrSDK,
             "ZEPHYR_BASE": self.ZephyrBase,
             "HOME": self.ZephyrDir})        

    def EnsureDependencies(self):
        res,*_ignore = ProcessLogger(None,['cmake', '--version']).spin()
        if res != 0:
            raise ZephyrBuildException("Cmake is not installed")

        if not exists(self.venv):
            self.InstallDependencies()
            return True

        self.log.write(f"Using Zephyr's virtual env in {self.venv}.\n")        
        return False

    def InstallDependencies(self):
        self.log.write("Install virtual env for Zephyr.\n")

        if exists(self.venv):
            rmtree(self.venv)
            
        # Setup python virtual environment
        res,*_ignore = ProcessLogger(self.log,['python', '-m', 'venv', self.venv],
                                     show_cmd=True).spin()
        if res != 0:
            raise ZephyrBuildException("Failed to setup python virtual environment")

    def RunBuildProcess(self, command, working_dir=None, env=None):
        # Run the command in the python virtual environment
        bash_command = ["bash", "-c", f"source {join(self.venv, 'bin', 'activate')} && \"$@\"", "bash"] + command
        proc = ProcessLogger(self.log, bash_command,
                             cwd=self.ZephyrDir if working_dir is None else working_dir,
                             show_cmd=True, env=env)

        return proc.spin()

    def RunPIP(self, command):
        "Run a pip command in the Zephyr workspace."
        return self.RunBuildProcess(['python', '-m', 'pip'] + command)

    def RunWest(self, command, working_dir=None):
        "Run a west command in the Zephyr workspace."
        return self.RunBuildProcess(['python', '-m', 'west'] + command,
                                    env=self.WestExecEnv,
                                    working_dir=working_dir)
