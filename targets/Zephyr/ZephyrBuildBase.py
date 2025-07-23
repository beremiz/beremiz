#!/usr/bin/env python
# -*- coding: utf-8 -*-

# copyright 2024: Edouard TISSERANT

"""
Setup and run Zephyr build tools.
Code common to Windows and Linux.
"""

import os
from os.path import join, exists
from shutil import rmtree

from util.net import Download
from util.paths import AppDataPath, Bpath
from util.ProcessLogger import ProcessLogger


# Zephyr versions
ZephyrGitTag = "v4.0.0"
ZephyrSdkVersion = "0.17.0"
WestVersion = "1.3.0"

# Where to download the Zephyr SDK
ZephyrSdkUrlBase = "https://github.com/zephyrproject-rtos/sdk-ng/releases/download"

ZephyrAdditionnalBoards = {
    "ooplc": ("https://gitlab.com/ooplc/zephyr_definitions/-/archive/master/","zephyr_definitions-master.tar.bz2")
}

ZephyrERPCManifest = """
manifest:
  projects:
    - name: erpc
      revision: e91333df98e89b6bb8952abefabc573cb202d1bf
      url: https://github.com/beremiz/erpc.git
      path: modules/lib/erpc
"""

class ZephyrBuildException(Exception):
    pass

class ZephyrBuildBase():

    def __init__(self, log, board, buildpath, options):
        self.log = log
        self.board = board
        self.buildpath = buildpath
        self.options = options
        
        self.ZephyrDir = AppDataPath("zephyr")
        self.ZephyrDownloads = AppDataPath("downloads")
        self.ZephyrWorkspace = join(self.ZephyrDir, 'zephyrproject')
        self.ZephyrBase = join(self.ZephyrWorkspace, 'zephyr')
        self.ZephyrSubManifests = join(self.ZephyrBase, 'submanifests')
        self.ZephyrBoards = join(self.ZephyrBase, 'boards', 'others')
        self.ZephyrSDK = join(self.ZephyrDir, 'zephyr-sdk-'+ZephyrSdkVersion)

        self.runtime_src = Bpath("C_runtime","zephyr")
        self.runtime_build = join(self.buildpath, "zephyr_runtime")

    def EnsureWest(self, force=False):
        if force:
            self.SetupWest()
            return True
        
        self.log.write("Check West availability.\n")
        
        res,*_ignore = self.RunWest(['--version'])
        if res != 0:
            self.SetupWest()
            return True
        return False
        
    def SetupWest(self):
        self.log.write("Install West.\n")
        # pip install west
        res,*_ignore = self.RunPIP(['install', f'west=={WestVersion}'])
        if res != 0:
            raise ZephyrBuildException("Failed to install west")

    def EnsureZephyrWorkspace(self, force=False):
        if force:
            self.SetupZephyrWorkspace()
            return True
            
        if exists(join(self.ZephyrWorkspace, ".stamp")):
            self.log.write(f"Using Zephyr workspace in {self.ZephyrWorkspace}.\n")
            return False
        
        self.SetupZephyrWorkspace()
        return True
            
    def SetupZephyrWorkspace(self):
        self.log.write(f"Install Zephyr workspace in {self.ZephyrWorkspace}.\n")
        if exists(self.ZephyrWorkspace):
            rmtree(self.ZephyrWorkspace)
            
        os.makedirs(self.ZephyrWorkspace)

        self.log.write(f"Initialize workspace with 'west init'.\n")
        # west init
        res,*_ignore = self.RunWest(['init', '--mr', ZephyrGitTag, self.ZephyrWorkspace])
        if res != 0:
            raise ZephyrBuildException("Failed to initialize west workspace")

        # inject erpc manifest
        with open(join(self.ZephyrSubManifests, "erpc.yml"), "w") as f:
            f.write(ZephyrERPCManifest)

        # west update
        res,*_ignore = self.RunWest(['update'], working_dir = self.ZephyrWorkspace)
        if res != 0:
            raise ZephyrBuildException("Failed to update west workspace")

        # west zephyr-export
        res,*_ignore = self.RunWest(['zephyr-export'], working_dir = self.ZephyrWorkspace)
        if res != 0:
            raise ZephyrBuildException("Failed to Export Zephyr CMake package")
        
        # Not working ?
        # # west packages pip --install
        # res,*_ignore = self.RunWest(['packages', 'pip', '--install'], working_dir = self.ZephyrWorkspace)
        # if res != 0:
        #     raise ZephyrBuildException("Failed to install west pip packages")
        
        # Previous command is not working, so we do it manually
        # pip install -r ~/zephyrproject/zephyr/scripts/requirements.txt
        res,*_ignore = self.RunPIP(['install', '-r', join(self.ZephyrWorkspace, 'zephyr', 'scripts', 'requirements.txt')])
        if res != 0:
            raise ZephyrBuildException("Failed to install Zephyr requirements")

        open(join(self.ZephyrWorkspace, ".stamp"), "w").close()

    def EnsureZephyrAdditionalBoard(self, force=False):
        if self.board not in ZephyrAdditionnalBoards:
            return False

        if force:
            self.SetupZephyrAdditionalBoard()
            return True

        if exists(join(self.ZephyrWorkspace, ".stamp_"+self.board)):
            self.log.write(f"Using additional Zephyr board {self.board} in {self.ZephyrBoards}.\n")
            return False

        self.SetupZephyrAdditionalBoard()
        return True
            
    def SetupZephyrAdditionalBoard(self):
        self.log.write(f"Install additional Zephyr board {self.board} in {self.ZephyrBoards}.\n")
        # add additional board
        url, archive = ZephyrAdditionnalBoards.get(self.board)
        board_dir = join(self.ZephyrBoards, self.board)
        if exists(board_dir):
            rmtree(board_dir)
        os.makedirs(board_dir)
        archive_path = join(self.ZephyrDownloads, archive)
        if not exists(archive_path):
            self.log.write(f"Downloading {archive} to {archive_path}\n")
            if not Download(self.log, url + archive, archive_path):
                raise ZephyrBuildException(f"Failed to download {archive}")
            
        res,*_ignore = ProcessLogger(self.log, ["tar", "-xjf", archive_path], 
                                        cwd=board_dir, show_cmd=True).spin()
        if res != 0:
            raise ZephyrBuildException(f"Failed to extract {archive}")
        
        open(join(self.ZephyrWorkspace, ".stamp_"+self.board), "w").close()


    def EnsureZephyrSDK(self):
        "Download and extract the Zephyr SDK if necessary"
        
        if os.path.exists(self.ZephyrSDK):
            self.log.write(f"Using existing Zephyr SDK directory {self.ZephyrSDK}\n")        
            return False

        SephyrSdkToolchains = [
            f"toolchain_{self.ZephyrSdkOsName}-{self.ZephyrSdkArch}_{ZephyrSdkTarget}.tar.xz" 
            for ZephyrSdkTarget in self.ZephyrSdkTargets]
        
        SephyrSdkMinimal = f"zephyr-sdk-{ZephyrSdkVersion}_{self.ZephyrSdkOsName}-{self.ZephyrSdkArch}_minimal.tar.xz"

        for SephyrSdkFileName in [ SephyrSdkMinimal ] + SephyrSdkToolchains:
            ZephyrSdkFilePath = join(self.ZephyrDownloads, SephyrSdkFileName)
            if not os.path.exists(ZephyrSdkFilePath):
                ZephyrSdkURL = f'{ZephyrSdkUrlBase}/v{ZephyrSdkVersion}/{SephyrSdkFileName}'
                self.log.write(f"Downloading Zephyr SDK\n")
                if not Download(self.log, ZephyrSdkURL, ZephyrSdkFilePath):
                    raise ZephyrBuildException(f"Failed to download {SephyrSdkFileName}")
            else:
                self.log.write(f"Using existing Zephyr SDK file {ZephyrSdkFilePath}\n")

        self.log.write("Extracting Zephyr Minimal SDK\n")
        res,*_ignore = ProcessLogger(
            self.log, self.ZephyrSdkUnpackCommand + [join(self.ZephyrDownloads, SephyrSdkMinimal)],
            cwd=self.ZephyrDir, show_cmd=True).spin()
        
        if res == 0:
            for SephyrSdkFileName in SephyrSdkToolchains:
                self.log.write(f"Extracting Zephyr SDK toolchain {SephyrSdkFileName}\n")
                res,*_ignore = ProcessLogger(self.log,
                    self.ZephyrSdkUnpackCommand + [join(self.ZephyrDownloads, SephyrSdkFileName)],
                    cwd=self.ZephyrSDK, show_cmd=True).spin()

        if res == 0:
            self.log.write("SDK installed successfully\n")

        else:
            # remove the SDK directory if the extraction failed
            if exists(self.ZephyrSDK):
                rmtree(self.ZephyrSDK)
            raise ZephyrBuildException("Failed to extract Zephyr SDK")

        return True

    def EnsureZephyrBuildEnvironment(self):
        "Setup the Zephyr build environment if necessary"
        
        if not exists(self.ZephyrDir):
            os.makedirs(self.ZephyrDir)
        if not exists(self.ZephyrDownloads):
            os.makedirs(self.ZephyrDownloads)

        # Dependency chain from tools to workspace
        need_reinstall = self.EnsureDependencies()
        need_reinstall |= self.EnsureWest(force=need_reinstall)
        need_reinstall |= self.EnsureZephyrWorkspace(force=need_reinstall)
        need_reinstall |= self.EnsureZephyrAdditionalBoard(force=need_reinstall)
        
        # Zephyr SDK download is not questionned by other dependencies
        need_reinstall |= self.EnsureZephyrSDK()

        # If any of the dependencies was reinstalled, we need to rebuild the runtime
        return need_reinstall

    def BuildPLC(self, plc_c_files, plc_c_flags,
                 user_c_flags, user_dts, user_conf,
                 verbose_build, force=False):
        "Build Zephyr runtime and PLC"
        if force and exists(self.runtime_build):
            rmtree(self.runtime_build)
            
        if not exists(self.runtime_build):
            os.makedirs(self.runtime_build)

        self.log.write("Building Beremiz runtime and PLC for Zephyr\n")
        
        # Collect optional config files and dts overlays
        extraconf_files = []
        dts_files = []
        for dirpath in [self.runtime_src, join(self.runtime_src, self.board.split("/")[0])]:
            for opt in self.options:
                extraconf_file = join(dirpath, f"{opt}.conf")
                if exists(extraconf_file):
                    extraconf_files.append(extraconf_file)
                dts_file = join(dirpath, f"{opt}.overlay")
                if exists(dts_file):
                    dts_files.append(dts_file)

        # Add user.conf if any
        if user_conf:
            user_conf_path = join(self.runtime_build, "user.conf")
            with open(user_conf_path, "w") as f:
                f.write("\n".join(user_conf))
            extraconf_files.append(user_conf_path)

        # Create overlay dts in build directory, based on user_dts content
        if user_dts:
            user_dts_path = join(self.runtime_build, "user.dts")
            with open(user_dts_path, "w") as f:
                f.write("\n".join(user_dts))
            dts_files.append(user_dts_path)

        WestCommand = ['-v'] if verbose_build else []
        
        WestCommand += [
            'build',
            '-b', self.board,
            '-d', self.runtime_build,
            '-p', 'always' if force else 'auto',
            self.runtime_src, '--',
            '-D', f'EXTRA_CONF_FILE={";".join(extraconf_files)}',
            '-D', f'PLC_C_FILES={";".join(plc_c_files)}',
            '-D', f'PLC_C_FLAGS={";".join(plc_c_flags)}']
        if user_c_flags:
            WestCommand += [
            '-D', f'USER_C_FLAGS={";".join(user_c_flags)}']
        if dts_files:
            WestCommand += [
            '-D', f'DTC_OVERLAY_FILE={";".join(dts_files)}']
        
        # Build with west
        res,*_ignore = self.RunWest(WestCommand, working_dir = self.runtime_src)
        if res != 0:
            raise ZephyrBuildException("Failed to build Beremiz runtime and PLC for Zephyr")

        produced_fnames = ["zephyr.elf"]
        if "programmable" in self.options:
            produced_fnames.append("softplc.llext")

        return [join(self.runtime_build, "zephyr", fname) for fname in produced_fnames]
