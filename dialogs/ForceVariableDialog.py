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

import re
import datetime

import wx

#-------------------------------------------------------------------------------
#                                Helpers
#-------------------------------------------------------------------------------

LOCATIONDATATYPES = {"X" : ["BOOL"],
                     "B" : ["SINT", "USINT", "BYTE", "STRING"],
                     "W" : ["INT", "UINT", "WORD", "WSTRING"],
                     "D" : ["DINT", "UDINT", "REAL", "DWORD"],
                     "L" : ["LINT", "ULINT", "LREAL", "LWORD"]} 

def gen_get_function(f):
    def get_function(v):
        try:
            return f(v)
        except:
            return None
    return get_function

def gen_get_string(delimiter):
    STRING_MODEL = re.compile("%(delimiter)s([^%(delimiter)s]*)%(delimiter)s$" % {"delimiter": delimiter})
    def get_string(v):
        result = STRING_MODEL.match(v)
        if result is not None:
            return result.group(1)
        return None
    return get_string

getinteger = gen_get_function(int)
getfloat = gen_get_function(float)
getstring = gen_get_string("'")
getwstring = gen_get_string('"')

SECOND = 1000000
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE
DAY = 24 * HOUR

IEC_TIME_MODEL = re.compile("(?:(?:T|TIME)#)?(-)?(?:(%(float)s)D_?)?(?:(%(float)s)H_?)?(?:(%(float)s)M(?!S)_?)?(?:(%(float)s)S_?)?(?:(%(float)s)MS)?$" % {"float": "[0-9]+(?:\.[0-9]+)?"})
IEC_DATE_MODEL = re.compile("(?:(?:D|DATE)#)?([0-9]{4})-([0-9]{2})-([0-9]{2})$")
IEC_DATETIME_MODEL = re.compile("(?:(?:DT|DATE_AND_TIME)#)?([0-9]{4})-([0-9]{2})-([0-9]{2})-([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]+)?)$")
IEC_TIMEOFDAY_MODEL = re.compile("(?:(?:TOD|TIME_OF_DAY)#)?([0-9]{2}):([0-9]{2}):([0-9]{2}(?:\.[0-9]+)?)$")

def gettime(v):    
    result = IEC_TIME_MODEL.match(v.upper())
    if result is not None:
        negative, days, hours, minutes, seconds, milliseconds = result.groups()
        microseconds = 0
        not_null = False
        for value, factor in [(days, DAY),
                              (hours, HOUR),
                              (minutes, MINUTE),
                              (seconds, SECOND),
                              (milliseconds, 1000)]:
            if value is not None:
                microseconds += float(value) * factor
                not_null = True
        if not not_null:
            return None
        if negative is not None:
            microseconds = -microseconds
        return datetime.timedelta(microseconds=microseconds)
    
    else: 
        return None

def getdate(v):
    result = IEC_DATE_MODEL.match(v.upper())
    if result is not None:
        year, month, day = result.groups()
        try:
            date = datetime.datetime(int(year), int(month), int(day))
        except ValueError, e:
            return None
        base_date = datetime.datetime(1970, 1, 1)
        return date - base_date
    else: 
        return None

def getdatetime(v):
    result = IEC_DATETIME_MODEL.match(v.upper())
    if result is not None:
        year, month, day, hours, minutes, seconds = result.groups()
        try:
            date = datetime.datetime(int(year), int(month), int(day), int(hours), int(minutes), int(float(seconds)), int((float(seconds) * SECOND) % SECOND))
        except ValueError, e:
            return None
        base_date = datetime.datetime(1970, 1, 1)
        return date - base_date
    else: 
        return None

def gettimeofday(v):
    result = IEC_TIMEOFDAY_MODEL.match(v.upper())
    if result is not None:
        hours, minutes, seconds = result.groups()
        microseconds = 0
        for value, factor in [(hours, HOUR),
                              (minutes, MINUTE),
                              (seconds, SECOND)]:
            microseconds += float(value) * factor
        return datetime.timedelta(microseconds=microseconds)
    else:
        return None

GetTypeValue = {"BOOL": lambda x: {"TRUE": True, "FALSE": False, "0": False, "1": True}.get(x.upper(), None),
                "SINT": getinteger,
                "INT": getinteger,
                "DINT": getinteger,
                "LINT": getinteger,
                "USINT": getinteger,
                "UINT": getinteger,
                "UDINT": getinteger,
                "ULINT": getinteger,
                "BYTE": getinteger,
                "WORD": getinteger,
                "DWORD": getinteger,
                "LWORD": getinteger,
                "REAL": getfloat,
                "LREAL": getfloat,
                "STRING": getstring,
                "WSTRING": getwstring,
                "TIME": gettime,
                "DATE": getdate,
                "DT": getdatetime,
                "TOD": gettimeofday}

#-------------------------------------------------------------------------------
#                            Force Variable Dialog
#-------------------------------------------------------------------------------

class ForceVariableDialog(wx.TextEntryDialog):

    def __init__(self, parent, iec_type, defaultValue=""):
        wx.TextEntryDialog.__init__(self, parent, message = _("Forcing Variable Value"), 
                caption = _("Please enter value for a \"%s\" variable:") % iec_type, defaultValue = defaultValue, 
                style = wx.OK|wx.CANCEL|wx.CENTRE, pos = wx.DefaultPosition)
        
        self.IEC_Type = iec_type 
        
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
              self.GetSizer().GetItem(2).GetSizer().GetItem(1).GetSizer().GetAffirmativeButton())
        
    def OnOK(self, event):
        message = None
        value = self.GetSizer().GetItem(1).GetWindow().GetValue()
        if value == "":
            message = _("You must type a value!")
        elif GetTypeValue[self.IEC_Type](value) is None:
            message = _("Invalid value \"{a1}\" for \"{a2}\" variable!").format(a1 = value, a2 = self.IEC_Type)
        if message is not None:
            dialog = wx.MessageDialog(self, message, _("Error"), wx.OK|wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
        else:
            self.EndModal(wx.ID_OK)
        event.Skip()

    def GetValue(self):
        return GetTypeValue[self.IEC_Type](wx.TextEntryDialog.GetValue(self))
