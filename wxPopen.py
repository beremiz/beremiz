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


import time
import wx
import subprocess, ctypes
import threading
import os
from signal import SIGTERM

    
class outputThread(threading.Thread):
    """
    Thread is used to print the output of a command to the stdout
    """
    def __init__(self, Proc, fd, callback=None, endcallback=None):
        threading.Thread.__init__(self)
        self.killed = False
        self.finished = False
        self.retval = None
        self.Proc = Proc
        self.callback = callback
        self.endcallback = endcallback
        self.fd = fd

    def run(self):
        outchunk = None
        self.retval = None
        while outchunk != '' and not self.killed :
            outchunk = self.fd.readline()
            if self.callback : self.callback(outchunk)
        while self.retval is None and not self.killed :
            self.retval = self.Proc.poll()
            outchunk = self.fd.readline()
            if self.callback : self.callback(outchunk)
        while outchunk != '' and not self.killed :
            outchunk = self.fd.readline()
        if self.endcallback:
            try:
            	err = self.Proc.wait()
            except:
                err = self.retval
            self.finished = True
            wx.CallAfter(self.endcallback, self.Proc.pid, err)

class ProcessLogger:
    def __init__(self, logger, Command, finish_callback=None, no_stdout=False, no_stderr=False, no_gui=True):
        self.logger = logger
        self.Command_str = Command
        self.Command = []
        for i,word in enumerate(Command.replace("'",'"').split('"')):
            if i % 2 == 0:
                word = word.strip()
                if len(word) > 0:
                    self.Command.extend(word.split())
            else:
                self.Command.append(word)
        
        self.finish_callback = finish_callback
        self.no_stdout = no_stdout
        self.no_stderr = no_stderr
        self.startupinfo = None
        self.errlen = 0
        self.outlen = 0
        self.exitcode = None
        self.outdata = ""
        self.errdata = ""
        self.finished = False
        
        popenargs= {
               "cwd":os.getcwd(),
               "stdin":subprocess.PIPE, 
               "stdout":subprocess.PIPE, 
               "stderr":subprocess.PIPE}
        if no_gui == True and wx.Platform == '__WXMSW__':
            self.startupinfo = subprocess.STARTUPINFO()
            self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            popenargs["startupinfo"] = self.startupinfo
        elif wx.Platform == '__WXGTK__':
            popenargs["shell"] = False  #True
        
        self.Proc = subprocess.Popen( self.Command, **popenargs )

        self.outt = outputThread(
                      self.Proc,
                      self.Proc.stdout,
                      self.output,
                      self.finish)

        self.outt.start()

        self.errt = outputThread(
                      self.Proc,
                      self.Proc.stderr,
                      self.errors)
#
        self.errt.start()	

    def output(self,v):
        self.outdata += v
        self.outlen += 1
        if not self.no_stdout:
            wx.CallAfter(self.logger.write,v)

    def errors(self,v):
        self.errdata += v
        self.errlen += 1
        if not self.no_stderr:
            wx.CallAfter(self.logger.write_warning,v)

    def finish(self, pid,ecode):
        self.finished = True
        self.exitcode = ecode
        if self.exitcode != 0:
            self.logger.write(self.Command_str + "\n")
            self.logger.write_warning("exited with status %s (pid %s)\n"%(str(ecode),str(pid)))
        if self.finish_callback is not None:
            self.finish_callback(self,ecode,pid)

    def kill(self,signal=SIGTERM):
        self.outt.killed = True
        self.errt.killed = True
        if wx.Platform == '__WXMSW__':
            PROCESS_TERMINATE = 1
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, self.Proc.pid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)
        else:
            try:
                os.kill(self.Proc.pid, signal)
            except:
                pass

    def spin(self, timeout=None, out_limit=None, err_limit=None, keyword = None, kill_it = True):
        count = 0
        while not self.finished:
            if err_limit and self.errlen > err_limit:
                break
            if out_limit and self.outlen > out_limit:
                break
            if timeout:
                if count > timeout:
                    break
                count += 1
            if keyword and self.outdata.find(keyword)!=-1:
                    break
            wx.Yield()
            time.sleep(0.01)

        if not self.outt.finished and kill_it:
            self.kill()

        return [self.exitcode, self.outdata, self.errdata]

