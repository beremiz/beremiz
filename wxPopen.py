#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of Beremiz, a Integrated Development Environment for
#programming IEC 61131-3 automates supporting plcopen standard and CanFestival. 
#
#Copyright (C) 2007: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

#
# based on wxPopen.py from boa-constructor
#

import time
from StringIO import StringIO

import wx

class ProcessRunnerMix:

    if wx.VERSION < (2, 6, 0):
        def Bind(self, event, function, id = None):
            if id is not None:
                event(self, id, function)
            else:
                event(self, function)
    
    def __init__(self, input, handler=None):
        if handler is None:
            handler = self
        self.handler = handler    
        handler.Bind(wx.EVT_MENU, self.OnIdle)
        handler.Bind(wx.EVT_END_PROCESS, self.OnProcessEnded, id=-1)
        
        input.reverse() # so we can pop
        self.input = input
        
        self.reset()

    def reset(self):
        self.process = None
        self.pid = -1
        self.output = []
        self.errors = []
        self.inputStream = None
        self.errorStream = None
        self.outputStream = None
        self.outputFunc = None
        self.errorsFunc = None
        self.finishedFunc = None
        self.finished = False
        self.responded = False

    def execute(self, cmd):
        self.process = wx.Process(self.handler)
        self.process.Redirect()

        self.pid = wx.Execute(cmd, wx.EXEC_NOHIDE, self.process)

        self.inputStream = self.process.GetOutputStream()
        self.errorStream = self.process.GetErrorStream()
        self.outputStream = self.process.GetInputStream()

        #self.OnIdle()
        wx.WakeUpIdle()
    
    def setCallbacks(self, output, errors, finished):
        self.outputFunc = output
        self.errorsFunc = errors
        self.finishedFunc = finished

    def detach(self):
        if self.process is not None:
            self.process.CloseOutput()
            self.process.Detach()
            self.process = None

    def kill(self):
        if self.process is not None:
            self.process.CloseOutput()
            if wx.Process_Kill(self.pid, wx.SIGTERM) != wx.KILL_OK:
                wx.Process_Kill(self.pid, wx.SIGKILL)
            self.process = None

    def updateStream(self, stream, data):
        if stream and stream.CanRead():
            if not self.responded:
                self.responded = True
            text = stream.read()
            data.append(text)
            return text
        else:
            return None

    def updateInpStream(self, stream, input):
        if stream and input:
            line = input.pop()
            stream.write(line)

    def updateErrStream(self, stream, data):
        return self.updateStream(stream, data)

    def updateOutStream(self, stream, data):
        return self.updateStream(stream, data)

    def OnIdle(self, event=None):
        if self.process is not None:
            self.updateInpStream(self.inputStream, self.input)
            e = self.updateErrStream(self.errorStream, self.errors)
            if e is not None and self.errorsFunc is not None:
                wx.CallAfter(self.errorsFunc, e)
            o = self.updateOutStream(self.outputStream, self.output)
            if o is not None and self.outputFunc is not None:
                wx.CallAfter(self.outputFunc, o)

            #wx.WakeUpIdle()
            #time.sleep(0.001)

    def OnProcessEnded(self, event):
        self.OnIdle()
        pid,exitcode = event.GetPid(), event.GetExitCode()
        if self.process:
            self.process.Destroy()
            self.process = None

        self.finished = True
        
        # XXX doesn't work ???
        #self.handler.Disconnect(-1, wx.EVT_IDLE)
        
        if self.finishedFunc:
            wx.CallAfter(self.finishedFunc, pid, exitcode)

class ProcessRunner(wx.EvtHandler, ProcessRunnerMix):
    def __init__(self, input):
        wx.EvtHandler.__init__(self)
        ProcessRunnerMix.__init__(self, input)

def wxPopen3(cmd, input, output, errors, finish, handler=None):
    p = ProcessRunnerMix(input, handler)
    p.setCallbacks(output, errors, finish)
    p.execute(cmd)
    return p
    
    