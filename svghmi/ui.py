#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2021: Edouard TISSERANT
#
# See COPYING file for copyrights details.

from __future__ import absolute_import
import os
import hashlib
import weakref

import wx

from IDEFrame import EncodeFileSystemPath, DecodeFileSystemPath
from docutil import get_inkscape_path

from util.ProcessLogger import ProcessLogger

class HMITreeSelector(wx.TreeCtrl):
    def __init__(self, parent):
        global on_hmitree_update
        wx.TreeCtrl.__init__(self, parent, style=(
            wx.TR_MULTIPLE |
            wx.TR_HAS_BUTTONS |
            wx.SUNKEN_BORDER |
            wx.TR_LINES_AT_ROOT))

        self.MakeTree()

    def _recurseTree(self, current_hmitree_root, current_tc_root):
        for c in current_hmitree_root.children:
            if hasattr(c, "children"):
                display_name = ('{} (class={})'.format(c.name, c.hmiclass)) \
                               if c.hmiclass is not None else c.name
                tc_child = self.AppendItem(current_tc_root, display_name)
                self.SetPyData(tc_child, None) # TODO

                self._recurseTree(c,tc_child)
            else:
                display_name = '{} {}'.format(c.nodetype[4:], c.name)
                tc_child = self.AppendItem(current_tc_root, display_name)
                self.SetPyData(tc_child, None) # TODO

    def MakeTree(self, hmi_tree_root=None):

        self.Freeze()

        self.root = None
        self.DeleteAllItems()

        root_display_name = _("Please build to see HMI Tree") \
            if hmi_tree_root is None else "HMI"
        self.root = self.AddRoot(root_display_name)
        self.SetPyData(self.root, None)

        if hmi_tree_root is not None:
            self._recurseTree(hmi_tree_root, self.root)
            self.Expand(self.root)

        self.Thaw()

class WidgetPicker(wx.TreeCtrl):
    def __init__(self, parent, initialdir=None):
        wx.TreeCtrl.__init__(self, parent, style=(
            wx.TR_MULTIPLE |
            wx.TR_HAS_BUTTONS |
            wx.SUNKEN_BORDER |
            wx.TR_LINES_AT_ROOT))

        self.MakeTree(initialdir)

    def _recurseTree(self, current_dir, current_tc_root, dirlist):
        """
        recurse through subdirectories, but creates tree nodes 
        only when (sub)directory conbtains .svg file
        """
        res = []
        for f in sorted(os.listdir(current_dir)):
            p = os.path.join(current_dir,f)
            if os.path.isdir(p):

                r = self._recurseTree(p, current_tc_root, dirlist + [f])
                if len(r) > 0 :
                    res = r
                    dirlist = []
                    current_tc_root = res.pop()

            elif os.path.splitext(f)[1].upper() == ".SVG":
                if len(dirlist) > 0 :
                    res = []
                    for d in dirlist:
                        current_tc_root = self.AppendItem(current_tc_root, d)
                        res.append(current_tc_root)
                        self.SetPyData(current_tc_root, None)
                    dirlist = []
                    res.pop()
                tc_child = self.AppendItem(current_tc_root, f)
                self.SetPyData(tc_child, p)
        return res

    def MakeTree(self, lib_dir = None):

        self.Freeze()

        self.root = None
        self.DeleteAllItems()

        root_display_name = _("Please select widget library directory") \
            if lib_dir is None else os.path.basename(lib_dir)
        self.root = self.AddRoot(root_display_name)
        self.SetPyData(self.root, None)

        if lib_dir is not None:
            self._recurseTree(lib_dir, self.root, [])
            self.Expand(self.root)

        self.Thaw()

_conf_key = "SVGHMIWidgetLib"
_preview_height = 200
class WidgetLibBrowser(wx.Panel):
    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):

        wx.Panel.__init__(self, parent, id, pos, size)     

        self.bmp = None
        self.msg = None
        self.hmitree_node = None
        self.selected_SVG = None

        self.Config = wx.ConfigBase.Get()
        self.libdir = self.RecallLibDir()

        sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=3, vgap=0)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableRow(1)
        self.libbutton = wx.Button(self, -1, _("Select SVG widget library"))
        self.widgetpicker = WidgetPicker(self, self.libdir)
        self.preview = wx.Panel(self, size=(-1, _preview_height + 10))  #, style=wx.SIMPLE_BORDER)
        #self.preview.SetBackgroundColour(wx.WHITE)
        sizer.AddWindow(self.libbutton, flag=wx.GROW)
        sizer.AddWindow(self.widgetpicker, flag=wx.GROW)
        sizer.AddWindow(self.preview, flag=wx.GROW)
        sizer.Layout()
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Bind(wx.EVT_BUTTON, self.OnSelectLibDir, self.libbutton)
        self.preview.Bind(wx.EVT_PAINT, self.OnPaint)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnWidgetSelection, self.widgetpicker)

        self.msg = _("Drag selected Widget from here to Inkscape")

    def RecallLibDir(self):
        conf = self.Config.Read(_conf_key)
        if len(conf) == 0:
            return None
        else:
            return DecodeFileSystemPath(conf)

    def RememberLibDir(self, path):
        self.Config.Write(_conf_key,
                          EncodeFileSystemPath(path))
        self.Config.Flush()

    def DrawPreview(self):
        """
        Refresh preview panel 
        """
        # Init preview panel paint device context
        dc = wx.PaintDC(self.preview)
        dc.Clear()

        if self.bmp:
            # Get Preview panel size
            sz = self.preview.GetClientSize()
            w = self.bmp.GetWidth()
            dc.DrawBitmap(self.bmp, (sz.width - w)/2, 5)

        if self.msg:
            dc.SetFont(self.GetFont())
            dc.DrawText(self.msg, 25,25)


    def OnSelectLibDir(self, event):
        defaultpath = self.RecallLibDir()
        if defaultpath == None:
            defaultpath = os.path.expanduser("~")

        dialog = wx.DirDialog(self, _("Choose a widget library"), defaultpath,
                              style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if dialog.ShowModal() == wx.ID_OK:
            self.libdir = dialog.GetPath()
            self.RememberLibDir(self.libdir)
            self.widgetpicker.MakeTree(self.libdir)

        dialog.Destroy()

    def OnPaint(self, event):
        """
        Called when Preview panel needs to be redrawn
        @param event: wx.PaintEvent
        """
        self.DrawPreview()
        event.Skip()

    def GenThumbnail(self, svgpath, thumbpath):
        inkpath = get_inkscape_path()
        if inkpath is None:
            self.msg = _("Inkscape is not installed.")
            return False
        # TODO: spawn a thread, to decouple thumbnail gen
        status, result, _err_result = ProcessLogger(
            None,
            '"' + inkpath + '" "' + svgpath + '" -e "' + thumbpath +
            '" -D -h ' + str(_preview_height)).spin()
        if status != 0:
            self.msg = _("Inkscape couldn't generate thumbnail.")
            return False
        return True

    def OnWidgetSelection(self, event):
        """
        Called when tree item is selected
        @param event: wx.TreeEvent
        """
        item_pydata = self.widgetpicker.GetPyData(event.GetItem())
        if item_pydata is not None:
            svgpath = item_pydata
            dname = os.path.dirname(svgpath)
            fname = os.path.basename(svgpath)
            hasher = hashlib.new('md5')
            with open(svgpath, 'rb') as afile:
                while True:
                    buf = afile.read(65536)
                    if len(buf) > 0:
                        hasher.update(buf)
                    else:
                        break
            digest = hasher.hexdigest()
            thumbfname = os.path.splitext(fname)[0]+"_"+digest+".png"
            thumbdir = os.path.join(dname, ".svghmithumbs") 
            thumbpath = os.path.join(thumbdir, thumbfname) 

            self.msg = None
            have_thumb = os.path.exists(thumbpath)

            if not have_thumb:
                try:
                    if not os.path.exists(thumbdir):
                        os.mkdir(thumbdir)
                except IOError:
                    self.msg = _("Widget library must be writable")
                else:
                    have_thumb = self.GenThumbnail(svgpath, thumbpath)

            self.bmp = wx.Bitmap(thumbpath) if have_thumb else None

            self.selected_SVG = svgpath if have_thumb else None
            self.ValidateWidget()

            self.Refresh()
        event.Skip()

    def OnHMITreeNodeSelection(self, hmitree_node):
        self.hmitree_node = hmitree_node
        self.ValidateWidget()
        self.Refresh()

    def ValidateWidget(self):
        if self.selected_SVG is not None:
            if self.hmitree_node is not None:
                pass
        # XXX TODO: 
        #      - check SVG is valid for selected HMI tree item
        #      - prepare for D'n'D


class SVGHMI_UI(wx.SplitterWindow):

    def __init__(self, parent, register_for_HMI_tree_updates):
        wx.SplitterWindow.__init__(self, parent,
                                   style=wx.SUNKEN_BORDER | wx.SP_3D)

        self.SelectionTree = HMITreeSelector(self)
        self.Staging = WidgetLibBrowser(self)
        self.SplitVertically(self.SelectionTree, self.Staging, 300)
        register_for_HMI_tree_updates(weakref.ref(self))

    def HMITreeUpdate(self, hmi_tree_root):
            self.SelectionTree.MakeTree(hmi_tree_root)

