#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2019: Edouard TISSERANT
#
# See COPYING file for copyrights details.

from __future__ import absolute_import
import os
import shutil
from itertools import izip, imap
from pprint import pformat
import hashlib
import weakref
import shlex
import time

import wx

from lxml import etree
from lxml.etree import XSLTApplyError

import util.paths as paths
from POULibrary import POULibrary
from docutil import open_svg, get_inkscape_path

from util.ProcessLogger import ProcessLogger
from runtime.typemapping import DebugTypesSize
import targets
from editors.ConfTreeNodeEditor import ConfTreeNodeEditor
from XSLTransform import XSLTransform
from svghmi.i18n import EtreeToMessages, SaveCatalog, ReadTranslations, MatchTranslations, TranslationToEtree, open_pofile

HMI_TYPES_DESC = {
    "HMI_NODE":{},
    "HMI_STRING":{},
    "HMI_INT":{},
    "HMI_BOOL":{},
    "HMI_REAL":{}
}

HMI_TYPES = HMI_TYPES_DESC.keys()


ScriptDirectory = paths.AbsDir(__file__)

class HMITreeNode(object):
    def __init__(self, path, name, nodetype, iectype = None, vartype = None, cpath = None, hmiclass = None):
        self.path = path
        self.name = name
        self.nodetype = nodetype
        self.hmiclass = hmiclass

        if iectype is not None:
            self.iectype = iectype
            self.vartype = vartype
            self.cpath = cpath

        if nodetype in ["HMI_NODE"]:
            self.children = []

    def pprint(self, indent = 0):
        res = ">"*indent + pformat(self.__dict__, indent = indent, depth = 1) + "\n"
        if hasattr(self, "children"):
            res += "\n".join([child.pprint(indent = indent + 1)
                              for child in self.children])
            res += "\n"

        return res

    def place_node(self, node):
        best_child = None
        known_best_match = 0
        potential_siblings = {}
        for child in self.children:
            if child.path is not None:
                in_common = 0
                for child_path_item, node_path_item in izip(child.path, node.path):
                    if child_path_item == node_path_item:
                        in_common +=1
                    else:
                        break
                # Match can only be HMI_NODE, and the whole path of node
                # must match candidate node (except for name part)
                # since candidate would become child of that node
                if in_common > known_best_match and \
                   child.nodetype == "HMI_NODE" and \
                   in_common == len(child.path) - 1:
                    known_best_match = in_common
                    best_child = child
                else:
                    potential_siblings[child.path[
                        -2 if child.nodetype == "HMI_NODE" else -1]] = child
        if best_child is not None:
            if node.nodetype == "HMI_NODE" and best_child.path[:-1] == node.path[:-1]:
                return "Duplicate_HMI_NODE", best_child
            return best_child.place_node(node)
        else:
            candidate_name = node.path[-2 if node.nodetype == "HMI_NODE" else -1]
            if candidate_name in potential_siblings:
                return "Non_Unique", potential_siblings[candidate_name]

            if node.nodetype == "HMI_NODE" and len(self.children) > 0:
                prev = self.children[-1]
                if prev.path[:-1] == node.path[:-1]:
                    return "Late_HMI_NODE",prev

            self.children.append(node)
            return None

    def etree(self, add_hash=False):

        attribs = dict(name=self.name)
        if self.path is not None:
            attribs["path"] = ".".join(self.path)

        if self.hmiclass is not None:
            attribs["class"] = self.hmiclass

        if add_hash:
            attribs["hash"] = ",".join(map(str,self.hash()))

        res = etree.Element(self.nodetype, **attribs)

        if hasattr(self, "children"):
            for child_etree in imap(lambda c:c.etree(), self.children):
                res.append(child_etree)

        return res

    @classmethod
    def from_etree(cls, enode):
        """
        alternative constructor, restoring HMI Tree from XML backup
        note: all C-related information is gone, 
              this restore is only for tree display and widget picking
        """
        nodetype = enode.tag
        attributes = enode.attrib
        name = attributes["name"]
        path = attributes["path"].split('.') if "path" in attributes else None 
        hmiclass = attributes.get("class", None)
        # hash is computed on demand
        node = cls(path, name, nodetype, hmiclass=hmiclass)
        for child in enode.iterchildren():
            node.children.append(cls.from_etree(child))
        return node

    def traverse(self):
        yield self
        if hasattr(self, "children"):
            for c in self.children:
                for yoodl in c.traverse():
                    yield yoodl


    def hash(self):
        """ Produce a hash, any change in HMI tree structure change that hash """
        s = hashlib.new('md5')
        self._hash(s)
        # limit size to HMI_HASH_SIZE as in svghmi.c
        return map(ord,s.digest())[:8]

    def _hash(self, s):
        s.update(str((self.name,self.nodetype)))
        if hasattr(self, "children"):
            for c in self.children:
                c._hash(s)

# module scope for HMITree root
# so that CTN can use HMITree deduced in Library
# note: this only works because library's Generate_C is
#       systematicaly invoked before CTN's CTNGenerate_C

hmi_tree_root = None

on_hmitree_update = None

SPECIAL_NODES = [("HMI_ROOT", "HMI_NODE"),
                 ("heartbeat", "HMI_INT")]
                 # ("current_page", "HMI_STRING")])

class SVGHMILibrary(POULibrary):
    def GetLibraryPath(self):
         return paths.AbsNeighbourFile(__file__, "pous.xml")

    def Generate_C(self, buildpath, varlist, IECCFLAGS):
        global hmi_tree_root, on_hmitree_update

        """
        PLC Instance Tree:
          prog0
           +->v1 HMI_INT
           +->v2 HMI_INT
           +->fb0 (type mhoo)
           |   +->va HMI_NODE
           |   +->v3 HMI_INT
           |   +->v4 HMI_INT
           |
           +->fb1 (type mhoo)
           |   +->va HMI_NODE
           |   +->v3 HMI_INT
           |   +->v4 HMI_INT
           |
           +->fb2
               +->v5 HMI_IN

        HMI tree:
          hmi0
           +->v1
           +->v2
           +->fb0 class:va
           |   +-> v3
           |   +-> v4
           |
           +->fb1 class:va
           |   +-> v3
           |   +-> v4
           |
           +->v5

        """

        # Filter known HMI types
        hmi_types_instances = [v for v in varlist if v["derived"] in HMI_TYPES]

        hmi_tree_root = None

        # take first HMI_NODE (placed as special node), make it root
        for i,v in enumerate(hmi_types_instances):
            path = v["IEC_path"].split(".")
            derived = v["derived"]
            if derived == "HMI_NODE":
                hmi_tree_root = HMITreeNode(path, "", derived, v["type"], v["vartype"], v["C_path"])
                hmi_types_instances.pop(i)
                break

        if hmi_tree_root is None:
            self.FatalError("SVGHMI : Library is selected but not used. Please either deselect it in project config or add a SVGHMI node to project.")

        # deduce HMI tree from PLC HMI_* instances
        for v in hmi_types_instances:
            path = v["IEC_path"].split(".")
            # ignores variables starting with _TMP_
            if path[-1].startswith("_TMP_"):
                continue
            derived = v["derived"]
            kwargs={}
            if derived == "HMI_NODE":
                # TODO : make problem if HMI_NODE used in CONFIG or RESOURCE
                name = path[-2]
                kwargs['hmiclass'] = path[-1]
            else:
                name = path[-1]
            new_node = HMITreeNode(path, name, derived, v["type"], v["vartype"], v["C_path"], **kwargs)
            placement_result = hmi_tree_root.place_node(new_node)
            if placement_result is not None:
                cause, problematic_node = placement_result
                if cause == "Non_Unique":
                    message = _("HMI tree nodes paths are not unique.\nConflicting variable: {} {}").format(
                        ".".join(problematic_node.path),
                        ".".join(new_node.path))

                    last_FB = None 
                    for v in varlist:
                        if v["vartype"] == "FB":
                            last_FB = v 
                        if v["C_path"] == problematic_node:
                            break
                    if last_FB is not None:
                        failing_parent = last_FB["type"]
                        message += "\n"
                        message += _("Solution: Add HMI_NODE at beginning of {}").format(failing_parent)

                elif cause in ["Late_HMI_NODE", "Duplicate_HMI_NODE"]:
                    cause, problematic_node = placement_result
                    message = _("There must be only one occurrence of HMI_NODE before any HMI_* variable in POU.\nConflicting variable: {} {}").format(
                        ".".join(problematic_node.path),
                        ".".join(new_node.path))

                self.FatalError("SVGHMI : " + message)

        if on_hmitree_update is not None:
            on_hmitree_update()

        variable_decl_array = []
        extern_variables_declarations = []
        buf_index = 0
        item_count = 0
        found_heartbeat = False

        hearbeat_IEC_path = ['CONFIG', 'HEARTBEAT']

        for node in hmi_tree_root.traverse():
            if not found_heartbeat and node.path == hearbeat_IEC_path:
                hmi_tree_hearbeat_index = item_count
                found_heartbeat = True
                extern_variables_declarations += [
                    "#define heartbeat_index "+str(hmi_tree_hearbeat_index)
                ]
            if hasattr(node, "iectype"):
                sz = DebugTypesSize.get(node.iectype, 0)
                variable_decl_array += [
                    "{&(" + node.cpath + "), " + node.iectype + {
                        "EXT": "_P_ENUM",
                        "IN":  "_P_ENUM",
                        "MEM": "_O_ENUM",
                        "OUT": "_O_ENUM",
                        "VAR": "_ENUM"
                    }[node.vartype] + ", " +
                    str(buf_index) + ", 0, }"]
                buf_index += sz
                item_count += 1
                if len(node.path) == 1:
                    extern_variables_declarations += [
                        "extern __IEC_" + node.iectype + "_" +
                        "t" if node.vartype is "VAR" else "p"
                        + node.cpath + ";"]

        assert(found_heartbeat)

        # TODO : filter only requiered external declarations
        for v in varlist:
            if v["C_path"].find('.') < 0:
                extern_variables_declarations += [
                    "extern %(type)s %(C_path)s;" % v]

        # TODO check if programs need to be declared separately
        # "programs_declarations": "\n".join(["extern %(type)s %(C_path)s;" %
        #                                     p for p in self._ProgramList]),

        # C code to observe/access HMI tree variables
        svghmi_c_filepath = paths.AbsNeighbourFile(__file__, "svghmi.c")
        svghmi_c_file = open(svghmi_c_filepath, 'r')
        svghmi_c_code = svghmi_c_file.read()
        svghmi_c_file.close()
        svghmi_c_code = svghmi_c_code % {
            "variable_decl_array": ",\n".join(variable_decl_array),
            "extern_variables_declarations": "\n".join(extern_variables_declarations),
            "buffer_size": buf_index,
            "item_count": item_count,
            "var_access_code": targets.GetCode("var_access.c"),
            "PLC_ticktime": self.GetCTR().GetTicktime(),
            "hmi_hash_ints": ",".join(map(str,hmi_tree_root.hash()))
            }

        gen_svghmi_c_path = os.path.join(buildpath, "svghmi.c")
        gen_svghmi_c = open(gen_svghmi_c_path, 'w')
        gen_svghmi_c.write(svghmi_c_code)
        gen_svghmi_c.close()

        # Python based WebSocket HMITree Server
        svghmiserverfile = open(paths.AbsNeighbourFile(__file__, "svghmi_server.py"), 'r')
        svghmiservercode = svghmiserverfile.read()
        svghmiserverfile.close()

        runtimefile_path = os.path.join(buildpath, "runtime_00_svghmi.py")
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write(svghmiservercode)
        runtimefile.close()

        # Backup HMI Tree in XML form so that it can be loaded without building
        hmitree_backup_path = os.path.join(buildpath, "hmitree.xml")
        hmitree_backup_file = open(hmitree_backup_path, 'w')
        hmitree_backup_file.write(etree.tostring(hmi_tree_root.etree()))
        hmitree_backup_file.close()

        return ((["svghmi"], [(gen_svghmi_c_path, IECCFLAGS)], True), "",
                ("runtime_00_svghmi.py", open(runtimefile_path, "rb")))
                #         ^
                # note the double zero after "runtime_", 
                # to ensure placement before other CTN generated code in execution order


class HMITreeSelector(wx.TreeCtrl):
    def __init__(self, parent):
        global on_hmitree_update
        wx.TreeCtrl.__init__(self, parent, style=(
            wx.TR_MULTIPLE |
            wx.TR_HAS_BUTTONS |
            wx.SUNKEN_BORDER |
            wx.TR_LINES_AT_ROOT))

        on_hmitree_update = self.SVGHMIEditorUpdater()
        self.MakeTree()

    def _recurseTree(self, current_hmitree_root, current_tc_root):
        for c in current_hmitree_root.children:
            if hasattr(c, "children"):
                display_name = ('{} (class={})'.format(c.name, c.hmiclass)) \
                               if c.hmiclass is not None else c.name
                tc_child = self.AppendItem(current_tc_root, display_name)
                self.SetPyData(tc_child, None)

                self._recurseTree(c,tc_child)
            else:
                display_name = '{} {}'.format(c.nodetype[4:], c.name)
                tc_child = self.AppendItem(current_tc_root, display_name)
                self.SetPyData(tc_child, None)

    def MakeTree(self):
        global hmi_tree_root

        self.Freeze()

        self.root = None
        self.DeleteAllItems()

        root_display_name = _("Please build to see HMI Tree") if hmi_tree_root is None else "HMI"
        self.root = self.AddRoot(root_display_name)
        self.SetPyData(self.root, None)

        if hmi_tree_root is not None:
            self._recurseTree(hmi_tree_root, self.root)
            self.Expand(self.root)

        self.Thaw()

    def SVGHMIEditorUpdater(self):
        selfref = weakref.ref(self)
        def SVGHMIEditorUpdate():
            o = selfref()
            if o is not None:
                wx.CallAfter(o.MakeTree)
        return SVGHMIEditorUpdate

class HMITreeView(wx.SplitterWindow):

    def __init__(self, parent):
        wx.SplitterWindow.__init__(self, parent,
                                   style=wx.SUNKEN_BORDER | wx.SP_3D)

        self.SelectionTree = HMITreeSelector(self)
        #self.Staging = wx.Panel(self)
        #self.SplitHorizontally(self.SelectionTree, self.Staging, 200)
        self.Initialize(self.SelectionTree)


class SVGHMIEditor(ConfTreeNodeEditor):
    CONFNODEEDITOR_TABS = [
        (_("HMI Tree"), "CreateHMITreeView")]

    def CreateHMITreeView(self, parent):
        #self.HMITreeView = HMITreeView(self)
        global hmi_tree_root

        if hmi_tree_root is None:
            buildpath = self.Controler.GetCTRoot()._getBuildPath()
            hmitree_backup_path = os.path.join(buildpath, "hmitree.xml")
            if os.path.exists(hmitree_backup_path):
                hmitree_backup_file = open(hmitree_backup_path, 'r')
                hmi_tree_root = HMITreeNode.from_etree(etree.parse(hmitree_backup_file).getroot())

        return HMITreeSelector(parent)

class SVGHMI(object):
    XSD = """<?xml version="1.0" encoding="utf-8" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="SVGHMI">
        <xsd:complexType>
          <xsd:attribute name="OnStart" type="xsd:string" use="optional"/>
          <xsd:attribute name="OnStop" type="xsd:string" use="optional"/>
          <xsd:attribute name="OnWatchdog" type="xsd:string" use="optional"/>
          <xsd:attribute name="WatchdogInitial" type="xsd:integer" use="optional"/>
          <xsd:attribute name="WatchdogInterval" type="xsd:integer" use="optional"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    EditorType = SVGHMIEditor

    ConfNodeMethods = [
        {
            "bitmap":    "ImportSVG",
            "name":    _("Import SVG"),
            "tooltip": _("Import SVG"),
            "method":   "_ImportSVG"
        },
        {
            "bitmap":    "EditSVG",  # should be something different
            "name":    _("Inkscape"),
            "tooltip": _("Edit HMI"),
            "method":   "_StartInkscape"
        },
        {
            "bitmap":    "OpenPOT",  # should be something different
            "name":    _("New lang"),
            "tooltip": _("Open non translated message catalog (POT) to start new language"),
            "method":   "_OpenPOT"
        },

        {
            "bitmap":    "EditPO",  # should be something different
            "name":    _("Edit lang"),
            "tooltip": _("Edit existing message catalog (PO) for specific language"),
            "method":   "_EditPO"
        },

        # TODO : HMITree button
        #        - can drag'n'drop variabes to Inkscape
    ]

    def _getSVGpath(self, project_path=None):
        if project_path is None:
            project_path = self.CTNPath()
        return os.path.join(project_path, "svghmi.svg")

    def _getPOTpath(self, project_path=None):
        if project_path is None:
            project_path = self.CTNPath()
        return os.path.join(project_path, "messages.pot")

    def OnCTNSave(self, from_project_path=None):
        if from_project_path is not None:
            shutil.copyfile(self._getSVGpath(from_project_path),
                            self._getSVGpath())
            shutil.copyfile(self._getPOTpath(from_project_path),
                            self._getPOTpath())
            # XXX TODO copy .PO files
        return True

    def GetSVGGeometry(self):
        self.ProgressStart("inkscape", "collecting SVG geometry (Inkscape)")
        # invoke inskscape -S, csv-parse output, produce elements
        InkscapeGeomColumns = ["Id", "x", "y", "w", "h"]

        inkpath = get_inkscape_path()

        if inkpath is None:
            self.FatalError("SVGHMI: inkscape is not installed.")

        svgpath = self._getSVGpath()
        status, result, _err_result = ProcessLogger(self.GetCTRoot().logger,
                                                     '"' + inkpath + '" -S "' + svgpath + '"',
                                                     no_stdout=True,
                                                     no_stderr=True).spin()
        if status != 0:
            self.FatalError("SVGHMI: inkscape couldn't extract geometry from given SVG.")

        res = []
        for line in result.split():
            strippedline = line.strip()
            attrs = dict(
                zip(InkscapeGeomColumns, line.strip().split(',')))

            res.append(etree.Element("bbox", **attrs))

        self.ProgressEnd("inkscape")
        return res

    def GetHMITree(self):
        global hmi_tree_root
        self.ProgressStart("hmitree", "getting HMI tree")
        res = [hmi_tree_root.etree(add_hash=True)]
        self.ProgressEnd("hmitree")
        return res

    def GetTranslations(self, _context, msgs):
        self.ProgressStart("i18n", "getting Translations")
        messages = EtreeToMessages(msgs)

        if len(messages) == 0:
            self.ProgressEnd("i18n")
            return

        SaveCatalog(self._getPOTpath(), messages)

        translations = ReadTranslations(self.CTNPath())
            
        langs,translated_messages = MatchTranslations(translations, messages, 
            errcallback=self.GetCTRoot().logger.write_warning)

        ret = TranslationToEtree(langs,translated_messages)

        self.ProgressEnd("i18n")

        return ret

    times_msgs = {}
    indent = 1
    def ProgressStart(self, k, m):
        self.times_msgs[k] = (time.time(), m)
        self.GetCTRoot().logger.write("    "*self.indent + "Start %s...\n"%m)
        self.indent = self.indent + 1

    def ProgressEnd(self, k):
        t = time.time()
        oldt, m = self.times_msgs[k]
        self.indent = self.indent - 1
        self.GetCTRoot().logger.write("    "*self.indent + "... finished in %.3fs\n"%(t - oldt))

    def CTNGenerate_C(self, buildpath, locations):

        location_str = "_".join(map(str, self.GetCurrentLocation()))
        view_name = self.BaseParams.getName()

        svgfile = self._getSVGpath()

        res = ([], "", False)

        target_fname = "svghmi_"+location_str+".xhtml"

        target_path = os.path.join(self._getBuildPath(), target_fname)
        target_file = open(target_path, 'wb')

        self.GetCTRoot().logger.write("SVGHMI:\n")

        if os.path.exists(svgfile):

            # TODO : move to __init__
            transform = XSLTransform(os.path.join(ScriptDirectory, "gen_index_xhtml.xslt"),
                          [("GetSVGGeometry", lambda *_ignored:self.GetSVGGeometry()),
                           ("GetHMITree", lambda *_ignored:self.GetHMITree()),
                           ("GetTranslations", self.GetTranslations),
                           ("ProgressStart", lambda _ign,k,m:self.ProgressStart(str(k),str(m))),
                           ("ProgressEnd", lambda _ign,k:self.ProgressEnd(str(k)))])

            self.ProgressStart("svg", "source SVG parsing")

            # load svg as a DOM with Etree
            svgdom = etree.parse(svgfile)

            self.ProgressEnd("svg")

            # call xslt transform on Inkscape's SVG to generate XHTML
            try: 
                self.ProgressStart("xslt", "XSLT transform")
                result = transform.transform(svgdom)  # , profile_run=True)
                self.ProgressEnd("xslt")
            except XSLTApplyError as e:
                self.FatalError("SVGHMI " + view_name  + ": " + e.message)
            finally:
                for entry in transform.get_error_log():
                    message = "SVGHMI: "+ entry.message + "\n" 
                    self.GetCTRoot().logger.write_warning(message)

            result.write(target_file, encoding="utf-8")
            # print(str(result))
            # print(transform.xslt.error_log)
            # print(etree.tostring(result.xslt_profile,pretty_print=True))

            # TODO
            #   - Errors on HMI semantics
            #   - ... maybe something to have a global view of what is declared in SVG.

        else:
            # TODO : use default svg that expose the HMI tree as-is
            target_file.write("""<!DOCTYPE html>
<html>
<body>
<h1> No SVG file provided </h1>
</body>
</html>
""")

        target_file.close()

        res += ((target_fname, open(target_path, "rb")),)

        svghmi_cmds = {}
        for thing in ["Start", "Stop", "Watchdog"]:
             given_command = self.GetParamsAttributes("SVGHMI.On"+thing)["value"]
             svghmi_cmds[thing] = (
                "Popen(" +
                repr(shlex.split(given_command.format(port="8008", name=view_name))) +
                ")") if given_command else "pass # no command given"

        runtimefile_path = os.path.join(buildpath, "runtime_%s_svghmi_.py" % location_str)
        runtimefile = open(runtimefile_path, 'w')
        runtimefile.write("""
# TODO : multiple watchdog (one for each svghmi instance)
def svghmi_watchdog_trigger():
    {svghmi_cmds[Watchdog]}

svghmi_watchdog = None

def _runtime_{location}_svghmi_start():
    global svghmi_watchdog
    svghmi_root.putChild(
        '{view_name}',
        NoCacheFile('{xhtml}',
        defaultType='application/xhtml+xml'))

    {svghmi_cmds[Start]}

    svghmi_watchdog = Watchdog(
        {watchdog_initial}, 
        {watchdog_interval}, 
        svghmi_watchdog_trigger)

def _runtime_{location}_svghmi_stop():
    global svghmi_watchdog
    if svghmi_watchdog is not None:
        svghmi_watchdog.cancel()
        svghmi_watchdog = None

    svghmi_root.delEntity('{view_name}')
    {svghmi_cmds[Stop]}

        """.format(location=location_str,
                   xhtml=target_fname,
                   view_name=view_name,
                   svghmi_cmds=svghmi_cmds,
                   watchdog_initial = self.GetParamsAttributes("SVGHMI.WatchdogInitial")["value"],
                   watchdog_interval = self.GetParamsAttributes("SVGHMI.WatchdogInterval")["value"],
                   ))

        runtimefile.close()

        res += (("runtime_%s_svghmi.py" % location_str, open(runtimefile_path, "rb")),)

        return res

    def _ImportSVG(self):
        dialog = wx.FileDialog(self.GetCTRoot().AppFrame, _("Choose a SVG file"), os.getcwd(), "",  _("SVG files (*.svg)|*.svg|All files|*.*"), wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            svgpath = dialog.GetPath()
            if os.path.isfile(svgpath):
                shutil.copy(svgpath, self._getSVGpath())
            else:
                self.GetCTRoot().logger.write_error(_("No such SVG file: %s\n") % svgpath)
        dialog.Destroy()

    def _StartInkscape(self):
        svgfile = self._getSVGpath()
        open_inkscape = True
        if not self.GetCTRoot().CheckProjectPathPerm():
            dialog = wx.MessageDialog(self.GetCTRoot().AppFrame,
                                      _("You don't have write permissions.\nOpen Inkscape anyway ?"),
                                      _("Open Inkscape"),
                                      wx.YES_NO | wx.ICON_QUESTION)
            open_inkscape = dialog.ShowModal() == wx.ID_YES
            dialog.Destroy()
        if open_inkscape:
            if not os.path.isfile(svgfile):
                svgfile = None
            open_svg(svgfile)

    def _StartPOEdit(self, POFile):
        open_poedit = True
        if not self.GetCTRoot().CheckProjectPathPerm():
            dialog = wx.MessageDialog(self.GetCTRoot().AppFrame,
                                      _("You don't have write permissions.\nOpen POEdit anyway ?"),
                                      _("Open POEdit"),
                                      wx.YES_NO | wx.ICON_QUESTION)
            open_poedit = dialog.ShowModal() == wx.ID_YES
            dialog.Destroy()
        if open_poedit:
            open_pofile(POFile)

    def _EditPO(self):
        """ Select a specific translation and edit it with POEdit """
        project_path = self.CTNPath()
        dialog = wx.FileDialog(self.GetCTRoot().AppFrame, _("Choose a PO file"), project_path, "",  _("PO files (*.po)|*.po"), wx.OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            POFile = dialog.GetPath()
            if os.path.isfile(POFile):
                if os.path.relpath(POFile, project_path) == os.path.basename(POFile):
                    self._StartPOEdit(POFile)
                else:
                    self.GetCTRoot().logger.write_error(_("PO file misplaced: %s is not in %s\n") % (POFile,project_path))
            else:
                self.GetCTRoot().logger.write_error(_("PO file does not exist: %s\n") % POFile)
        dialog.Destroy()

    def _OpenPOT(self):
        """ Start POEdit with untouched empty catalog """
        POFile = self._getPOTpath()
        if os.path.isfile(POFile):
            self._StartPOEdit(POFile)
        else:
            self.GetCTRoot().logger.write_error(_("POT file does not exist, add translatable text (label starting with '_') in Inkscape first\n"))

    def CTNGlobalInstances(self):
        # view_name = self.BaseParams.getName()
        # return [ (view_name + "_" + name, iec_type, "") for name, iec_type in SPECIAL_NODES]
        # TODO : move to library level for multiple hmi
        return [(name, iec_type, "") for name, iec_type in SPECIAL_NODES]

    def GetIconName(self):
        return "SVGHMI"
