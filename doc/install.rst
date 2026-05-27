Build and install
=================

Install latest release
----------------------

Windows installer and Snap package for Linux are available in `Github releases <https://github.com/beremiz/beremiz/releases>`_
and `Snapcraft's store <https://snapcraft.io/beremiz>`_

Developer setup
---------------

System prerequisites (Ubuntu 26.04)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install required system packages as root:

.. code-block:: bash

    sudo apt-get install \
      build-essential automake flex bison \
      libpython3.14-dev libssl-dev \
      python3.14 python3-wxgtk4.0 python3-venv \
      inkscape git

Prepare build directory
~~~~~~~~~~~~~~~~~~~~~~~

All commands hereafter assume that selected directory to contain all downloaded
source code and build results is ``~/Beremiz``.

.. code-block:: bash

    mkdir ~/Beremiz
    cd ~/Beremiz

Get source code (Git)
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    cd ~/Beremiz
    git clone https://github.com/beremiz/beremiz
    git clone https://github.com/beremiz/matiec

Python prerequisites (virtualenv)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # setup isolated python environment 
    # Note: --system-site-packages is for using distro's
    #       wxPython package instead of re-building it in venv.
    #       requirements.txt is expected to match latest ubuntu LTS
    python3 -m venv --system-site-packages ~/Beremiz/venv
    # install required python packages
    ~/Beremiz/venv/bin/pip install -r ~/Beremiz/beremiz/requirements.txt

Build MatIEC compiler
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    cd ~/Beremiz/matiec
    autoreconf -i
    ./configure
    make

Build Modbus library (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only needed for Modbus support.

.. code-block:: bash

    cd ~/Beremiz

    git clone https://github.com/beremiz/Modbus

    cd ~/Beremiz/Modbus
    make

Build CanFestival (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Only needed for CANopen support. Please read the CanFestival manual to choose a
CAN driver other than ``virtual``.

The static libraries are linked into the PLC's shared object, so the build must
be position-independent (``-DCMAKE_POSITION_INDEPENDENT_CODE=ON``).

.. code-block:: bash

    cd ~/Beremiz

    git clone https://github.com/beremiz/canfestival

    cd ~/Beremiz/canfestival
    mkdir build && cd build
    cmake .. -DCF_TARGET=unix \
             -DCF_CAN_DRIVER=virtual \
             -DCF_TIMERS_DRIVER=unix \
             -DCMAKE_POSITION_INDEPENDENT_CODE=ON
    make

The Beremiz CANopen extension picks up ``CF_TARGET`` / ``CF_CAN_DRIVER`` /
``CF_TIMERS_DRIVER`` from the resulting ``build/CMakeCache.txt`` and links
against ``build/src/libcanfestival.a`` and ``build/drivers/libcanfestival_<target>.a``,
so rebuilding with a different ``-DCF_CAN_DRIVER`` is enough to switch driver
(no Beremiz changes required).

Build BACnet (optional)
~~~~~~~~~~~~~~~~~~~~~~~

Only needed for BACnet support.

.. code-block:: bash

    cd ~/Beremiz
    svn checkout https://svn.code.sf.net/p/bacnet/code/trunk/bacnet-stack/ BACnet
    cd BACnet
    make MAKE_DEFINE='-fPIC' \
         MY_BACNET_DEFINES='-DPRINT_ENABLED=1 -DBACAPP_ALL -DBACFILE \
             -DINTRINSIC_REPORTING -DBACNET_TIME_MASTER \
             -DBACNET_PROPERTY_LISTS=1 -DBACNET_PROTOCOL_REVISION=16' \
         library

Launch Beremiz IDE
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    ~/Beremiz/venv/bin/python ~/Beremiz/beremiz/Beremiz.py

Run standalone Beremiz runtime
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Start standalone Beremiz service:

.. code-block:: bash

    mkdir ~/Beremiz/beremiz_runtime_workdir
    ~/Beremiz/venv/bin/python ~/Beremiz/beremiz/Beremiz_service.py \
        -p 61194 -i localhost -x 0 ~/Beremiz/beremiz_runtime_workdir

To connect IDE with runtime, enter target location URI in project's settings
(``project -> Config -> BeremizRoot/URI_location``) pointed to your running
Beremiz service, in this case::

    ERPC://127.0.0.1:61194

If project's URL is ``LOCAL://``, then IDE launches on demand a local instance
of Beremiz python runtime working on a temporary directory.

Build documentation
-------------------

Source code for documentation is stored in ``doc`` directory in project's
source tree. It's written in reStructuredText (ReST) and uses Sphinx to
generate documentation in different formats.

To build documentation you need following packages on Ubuntu/Debian:

.. code-block:: bash

    sudo apt-get install build-essential python-sphynx

Documentation in HTML
~~~~~~~~~~~~~~~~~~~~~

Build documentation:

.. code-block:: bash

    cd ~/Beremiz/doc
    make all

Result documentation is stored in directories ``doc/_build/dirhtml*``.

Documentation in PDF
~~~~~~~~~~~~~~~~~~~~

To build pdf documentation you have to install additional packages on
Ubuntu/Debian:

.. code-block:: bash

    sudo apt-get install textlive-latex-base texlive-latex-recommended \
         texlive-fonts-recommended texlive-latex-extra

Build documentation:

.. code-block:: bash

    cd ~/Beremiz/doc
    make latexpdf

Result documentation is stored in ``doc/_build/latex/Beremiz.pdf``.
