<!---
[![docs](https://readthedocs.org/projects/beremiz/badge/?version=latest)](https://beremiz.readthedocs.io)
-->
[![CI Automated testing](https://github.com/beremiz/beremiz/actions/workflows/run_tests_in_docker.yml/badge.svg?branch=python3)](https://github.com/beremiz/beremiz/actions/workflows/run_tests_in_docker.yml)

# Beremiz #

Beremiz is an integrated development environment for machine automation. It is Free Software, conforming to IEC-61131 among other standards.

It relies on open standards to be independent of the targeted device, and let you turn any processor into a PLC. Beremiz includes tools to create HMI, and to connect your PLC programs to existing supervisions, databases, or fieldbuses.

With Beremiz, you conform to standards, avoid vendor lock, and contribute to the better future of Automation. 

Beremiz provides:

* Integrated Development Environment (IDE, GPLv2). GUI to configure, write, build and debug PLC programs and control PLC runtime.
* Command Line Interface (CLI, GPLv2). Build PLC and control PLC runtime in a terminal or from a script.
* Runtimes, running on target platform communicates with I/O and executes PLC program.
    * Python reference runtime implementation (LGPLv2).
    * C++ runtime for smaller targets (GPLv3).

See official [Beremiz website](https://beremiz.org/) for more information.

[Beremiz company](https://beremiz.fr/) develops and maintains the Beremiz Free Software project while also providing professional support services.

## Licensing ##

Beremiz IDE source code is licensed under the [GPLv2](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html) or later, see COPYING_for_IDE.

Beremiz Python runtime source code is licensed under the [LPGLv2](https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html) or later, see COPYING_for_Python_Runtime.

Beremiz C++ runtime source code is licensed under the [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html) or later, see COPYING_for_C_Runtime.

## Install latest release ##

Windows installer and Snap package for Linux are available in [Github releases](https://github.com/beremiz/beremiz/releases) and [Snapcraft's store](https://snapcraft.io/beremiz)

## Tutorials and examples ##

In IDE, find menu "File>Tutorials and examples" to quickly open examples that should run as-is.

There are more examples in `tests/projects` and `exemples` directories.

Some example and test are shown on [Beremiz youtube channel](https://www.youtube.com/channel/UCcE4KYI0p1f6CmSwtzyg-ZA).

## Development with Beremiz ##

Please use [GitHub's issues](https://github.com/beremiz/beremiz/issues) and [Pull Requests](https://github.com/beremiz/beremiz/pulls) to contribute.

See [doc/install.rst](doc/install.rst) for developer setup instructions (building Beremiz from source on Linux, MatIEC, optional Modbus/CanFestival/BACnet libraries, and running a standalone runtime).

## Documentation ##

 * See [Beremiz youtube channel](https://www.youtube.com/channel/UCcE4KYI0p1f6CmSwtzyg-ZA) to get quick information how to use Beremiz IDE.

 * [Official documentation](http://beremiz.readthedocs.io/) is built from sources in doc directory.
   Documentation does not cover all aspects of Beremiz use yet.
   Contribution are very welcome!
   
 * [User manual](http://www.sm1820.ru/files/beremiz/beremiz_manual.pdf) from INEUM (Russian).
   Be aware that it contains some information about functions available only in INEUM's fork of Beremiz.

 * [User manual](http://www.beremiz.org/LpcManager_UserManual.pdf) from Smarteh (English).
   Be aware that it contains some information about functions available only in Smarteh's fork of Beremiz.

 * Outdated short [user manual](https://www.scribd.com/document/76101511/Manual-Beremiz#scribd) from LOLI Tech (English).

 * See official [Beremiz website](http://www.beremiz.org/) for more information.

