#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2013: Edouard TISSERANT and Laurent BESSARD
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

import wx

from plcopen.structures import TestIdentifier, IEC_KEYWORDS
from graphics.GraphicCommons import FREEDRAWING_MODE

#-------------------------------------------------------------------------------
#                    Dialog with preview for graphic block
#-------------------------------------------------------------------------------

"""
Class that implements a generic dialog containing a preview panel for displaying
graphic created by dialog
"""

class BlockPreviewDialog(wx.Dialog):

    def __init__(self, parent, controller, tagname, size, title):
        wx.Dialog.__init__(self, parent, size=size, title=title)
        
        self.Controller = controller
        self.TagName = tagname
        
        self.PreviewLabel = wx.StaticText(self, label=_('Preview:'))
        
        self.Preview = wx.Panel(self, style=wx.SIMPLE_BORDER)
        self.Preview.SetBackgroundColour(wx.WHITE)
        setattr(self.Preview, "GetDrawingMode", lambda:FREEDRAWING_MODE)
        setattr(self.Preview, "GetScaling", lambda:None)
        setattr(self.Preview, "GetBlockType", controller.GetBlockType)
        setattr(self.Preview, "IsOfType", controller.IsOfType)
        self.Preview.Bind(wx.EVT_PAINT, self.OnPaint)
        
        self.ButtonSizer = self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.CENTRE)
        self.Bind(wx.EVT_BUTTON, self.OnOK, 
                  self.ButtonSizer.GetAffirmativeButton())
        
        self.Block = None
        self.DefaultBlockName = None
        self.MinBlockSize = None
    
    def __del__(self):
        self.Controller = None
    
    def SetMinBlockSize(self, size):
        self.MinBlockSize = size
    
    def SetPreviewFont(self, font):
        self.Preview.SetFont(font)
    
    def TestBlockName(self, block_name):
        format = None
        uppercase_block_name = block_name.upper()
        if not TestIdentifier(block_name):
            format = _("\"%s\" is not a valid identifier!")
        elif uppercase_block_name in IEC_KEYWORDS:
            format = _("\"%s\" is a keyword. It can't be used!")
        elif uppercase_block_name in self.Controller.GetProjectPouNames():
            format = _("\"%s\" pou already exists!")
        elif ((self.DefaultBlockName is None or 
               self.DefaultBlockName.upper() != uppercase_block_name) and 
              uppercase_block_name in self.Controller.GetEditedElementVariables(
                                                                self.TagName)):
            format = _("\"%s\" element for this pou already exists!")
        
        if format is not None:
            self.ShowErrorMessage(format % block_name)
            return False
        
        return True
    
    def ShowErrorMessage(self, message):
        dialog = wx.MessageDialog(self, message, 
                                  _("Error"), 
                                  wx.OK|wx.ICON_ERROR)
        dialog.ShowModal()
        dialog.Destroy()
    
    def OnOK(self, event):
        self.EndModal(wx.ID_OK)
    
    def RefreshPreview(self):
        dc = wx.ClientDC(self.Preview)
        dc.SetFont(self.Preview.GetFont())
        dc.Clear()
        
        if self.Block is not None:
            min_width, min_height = self.Block.GetMinSize()
            width = max(self.MinBlockSize[0], min_width)
            height = max(self.MinBlockSize[1], min_height)
            self.Block.SetSize(width, height)
            clientsize = self.Preview.GetClientSize()
            x = (clientsize.width - width) / 2
            y = (clientsize.height - height) / 2
            self.Block.SetPosition(x, y)
            self.Block.Draw(dc)
    
    def OnPaint(self, event):
        self.RefreshPreview()
        event.Skip()
        