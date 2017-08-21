[![docs](https://readthedocs.org/projects/beremiz/badge/?version=latest)](https://beremiz.readthedocs.io)

# Beremiz #

Beremiz is an integrated development environment for machine automation. It is Free Software, conforming to IEC-61131 among other standards.

It relies on open standards to be independent of the targeted device, and let you turn any processor into a PLC. Beremiz includes tools to create HMI, and to connect your PLC programs to existing supervisions, databases, or fieldbuses.

With Beremiz, you conform to standards, avoid vendor lock, and contribute to the better future of Automation. 

See official [Beremiz website](http://www.beremiz.org/) for more information.

### Build on Linux ###

* Prerequisites
```
#!sh

* # Ubuntu/Debian :
sudo apt-get install build-essential bison flex autoconf
sudo apt-get install python-wxgtk3.0 pyro mercurial
sudo apt-get install python-numpy python-nevow python-matplotlib python-lxml
```
* Prepare
```
#!sh
mkdir ~/Beremiz
cd ~/Beremiz
```

* Get Source Code
```
#!sh
cd ~/Beremiz

hg clone https://bitbucket.org/skvorl/beremiz
hg clone https://bitbucket.org/mjsousa/matiec
```

* Build MatIEC compiler
```
#!sh
cd ~/Beremiz/matiec
autoreconf -i
./configure
make
```

* Build CanFestival (optional)
Only needed for CANopen support. Please read CanFestival manual to choose CAN interface other than 'virtual'.

```
#!sh
cd ~/Beremiz
hg clone http://dev.automforge.net/CanFestival-3

cd ~/Beremiz/CanFestival-3
./configure --can=virtual
make
```

* Launch Beremiz IDE

```
#!sh
cd ~/Beremiz/beremiz
python Beremiz.py
```

### Run standalone Beremiz service ###

* Start standalone Beremiz service
```
#!sh
cd ~/Beremiz
mkdir beremiz_workdir

cd ~/beremiz
python Beremiz_service.py -p 61194 -i localhost -x 0 -a 1 ~/Beremiz/beremiz_workdir
```

* Launch Beremiz IDE
```
#!sh
cd ~/Beremiz/beremiz
python Beremiz.py
```
* Open/Create PLC project in Beremiz IDE.
* 
Enter target location URI in project's settings (project->Config->BeremizRoot/URI_location) pointed to your running Beremiz service (For example, PYRO://127.0.0.1:61194).
Save project and connect to running Beremiz service.

### Documentation ###

 * See [Beremiz youtube channel](https://www.youtube.com/channel/UCcE4KYI0p1f6CmSwtzyg-ZA) to get quick information how to use Beremiz IDE.
 
 * [Official user manual](http://beremiz.readthedocs.io/) is built from sources in doc directory.
   Documentation does not cover all aspects of Beremiz use yet.
   Contribution are very welcome!
   
 * [User manual](http://www.sm1820.ru/files/beremiz/beremiz_manual.pdf) from INEUM (Russian).
   Be aware that it contains some information about functions available only in INEUM's fork of Beremiz.

 * [User manual](http://www.beremiz.org/LpcManager_UserManual.pdf) from Smarteh (English).
   Be aware that it contains some information about functions available only in Smarteh's fork of Beremiz.

 * Outdated short [user manual](https://www.scribd.com/document/76101511/Manual-Beremiz#scribd) from LOLI Tech (English).

 * See official [Beremiz website](http://www.beremiz.org/) for more information.

### Support and development ###

Main community support channel is [mailing list](https://sourceforge.net/p/beremiz/mailman/beremiz-devel/) (beremiz-devel@lists.sourceforge.net).

The list is moderated and requires subscription for posting to it.

To subscribe to the mailing list go [here](https://sourceforge.net/p/beremiz/mailman/beremiz-devel/).

Searchable archive using search engine of your choice is available [here](http://beremiz-devel.2374573.n4.nabble.com/).