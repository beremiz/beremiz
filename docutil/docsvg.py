#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


from __future__ import absolute_import
import wx
import subprocess

def get_inkscape_path():
    """ Return the Inkscape binary path """

    if wx.Platform == '__WXMSW__':
        from six.moves import winreg
        inkcmd = None
        try:
            inkcmd = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE,
                                           'Software\\Classes\\svgfile\\shell\\Inkscape\\command')
        except OSError:
            try:
                inkcmd = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE,
                                               'Software\\Classes\\inkscape.svg\\shell\\open\\command')
            except OSError:
                return None

        return inkcmd.replace('"%1"', '').strip().replace('"', '')

    else:
        try:
            return subprocess.check_output("command -v inkscape", shell=True).strip()
        except subprocess.CalledProcessError:
            return None

def open_svg(svgfile):
    """ Generic function to open SVG file """
    
    inkpath = get_inkscape_path()
    if inkpath is None:
        wx.MessageBox("Inkscape is not found or installed !")
    else:
        subprocess.Popen([inkpath,svgfile])
