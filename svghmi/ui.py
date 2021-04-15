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
from tempfile import NamedTemporaryFile

import wx

from lxml import etree
from lxml.etree import XSLTApplyError
from XSLTransform import XSLTransform

import util.paths as paths
from IDEFrame import EncodeFileSystemPath, DecodeFileSystemPath
from docutil import get_inkscape_path

from util.ProcessLogger import ProcessLogger

ScriptDirectory = paths.AbsDir(__file__)

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
                self.SetPyData(tc_child, c)

                self._recurseTree(c,tc_child)
            else:
                display_name = '{} {}'.format(c.nodetype[4:], c.name)
                tc_child = self.AppendItem(current_tc_root, display_name)
                self.SetPyData(tc_child, c)

    def MakeTree(self, hmi_tree_root=None):

        self.Freeze()

        self.root = None
        self.DeleteAllItems()

        root_display_name = _("Please build to see HMI Tree") \
            if hmi_tree_root is None else "HMI"
        self.root = self.AddRoot(root_display_name)
        self.SetPyData(self.root, hmi_tree_root)

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

        sizer = wx.FlexGridSizer(cols=1, hgap=0, rows=4, vgap=0)
        sizer.AddGrowableCol(0)
        sizer.AddGrowableRow(1)
        self.libbutton = wx.Button(self, -1, _("Select SVG widget library"))
        self.widgetpicker = WidgetPicker(self, self.libdir)
        self.preview = wx.Panel(self, size=(-1, _preview_height + 10))
        self.comment = wx.TextCtrl(self, size=wx.Size(-1, 80),
                                   style=wx.TE_READONLY | wx.TE_MULTILINE)
        sizer.AddWindow(self.libbutton, flag=wx.GROW)
        sizer.AddWindow(self.widgetpicker, flag=wx.GROW)
        sizer.AddWindow(self.preview, flag=wx.GROW)
        sizer.AddWindow(self.comment, flag=wx.GROW)
        sizer.Layout()
        self.SetAutoLayout(True)
        self.SetSizer(sizer)
        sizer.Fit(self)
        self.Bind(wx.EVT_BUTTON, self.OnSelectLibDir, self.libbutton)
        self.preview.Bind(wx.EVT_PAINT, self.OnPaint)
        self.preview.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnWidgetSelection, self.widgetpicker)

        self.msg = _("Drag selected Widget from here to Inkscape")
        self.tempf = None 

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

        self.comment.SetValue(self.msg)


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

            have_thumb = os.path.exists(thumbpath)

            try:
                if not have_thumb:
                    if not os.path.exists(thumbdir):
                        os.mkdir(thumbdir)
                    have_thumb = self.GenThumbnail(svgpath, thumbpath)

                self.bmp = wx.Bitmap(thumbpath) if have_thumb else None

                self.selected_SVG = svgpath if have_thumb else None
                self.ValidateWidget()
            except IOError:
                self.msg = _("Widget library must be writable")

            self.Refresh()
        event.Skip()

    def OnHMITreeNodeSelection(self, hmitree_nodes):
        self.hmitree_node = hmitree_nodes[0] if len(hmitree_nodes) else None
        self.ValidateWidget()
        self.Refresh()

    def OnLeftDown(self, evt):
        if self.tempf is not None:
            filename = self.tempf.name
            data = wx.FileDataObject()
            data.AddFile(filename)
            dropSource = wx.DropSource(self)
            dropSource.SetData(data)
            dropSource.DoDragDrop(wx.Drag_AllowMove)

    def GiveDetails(self, _context, msgs):
        for msg in msgs:
            self.msg += msg.text + "\n"
        
    def GetSubHMITree(self, _context):
        return [self.hmitree_node.etree()]

    def ValidateWidget(self):
        self.msg = ""

        if self.tempf is not None:
            os.unlink(self.tempf.name)
            self.tempf = None

        try:
            if self.selected_SVG is None:
                raise Exception(_("No widget selected"))
            if self.hmitree_node is None:
                raise Exception(_("No HMI tree node selected"))

            transform = XSLTransform(
                os.path.join(ScriptDirectory, "gen_dnd_widget_svg.xslt"),
                [("GetSubHMITree", self.GetSubHMITree),
                 ("GiveDetails", self.GiveDetails)])

            svgdom = etree.parse(self.selected_SVG)

            result = transform.transform(
                svgdom, hmi_path = self.hmitree_node.hmi_path())

            for entry in transform.get_error_log():
                self.msg += "XSLT: " + entry.message + "\n" 

            self.tempf = NamedTemporaryFile(suffix='.svg', delete=False)
            result.write(self.tempf, encoding="utf-8")
            self.tempf.close()

        except Exception as e:
            self.msg += str(e)
        except XSLTApplyError as e:
            self.msg += "Widget transform error: " + e.message
                
    def __del__(self):
        if self.tempf is not None:
            os.unlink(self.tempf.name)

class SVGHMI_UI(wx.SplitterWindow):

    def __init__(self, parent, register_for_HMI_tree_updates):
        wx.SplitterWindow.__init__(self, parent,
                                   style=wx.SUNKEN_BORDER | wx.SP_3D)

        self.ordered_items = []

        self.SelectionTree = HMITreeSelector(self)
        self.Staging = WidgetLibBrowser(self)
        self.SplitVertically(self.SelectionTree, self.Staging, 300)
        register_for_HMI_tree_updates(weakref.ref(self))
        self.Bind(wx.EVT_TREE_SEL_CHANGED,
            self.OnHMITreeNodeSelection, self.SelectionTree)

    def OnHMITreeNodeSelection(self, event):
        items = self.SelectionTree.GetSelections()
        items_pydata = [self.SelectionTree.GetPyData(item) for item in items]

        # append new items to ordered item list
        for item_pydata in items_pydata:
            if item_pydata not in self.ordered_items:
                self.ordered_items.append(item_pydata)

        # filter out vanished items
        self.ordered_items = [
            item_pydata 
            for item_pydata in self.ordered_items 
            if item_pydata in items_pydata]

        self.Staging.OnHMITreeNodeSelection(items_pydata)

    def HMITreeUpdate(self, hmi_tree_root):
            self.SelectionTree.MakeTree(hmi_tree_root)

