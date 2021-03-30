#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2021: Edouard TISSERANT
#
# See COPYING file for copyrights details.

from __future__ import absolute_import
import os
import shutil
import hashlib
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
from svghmi.i18n import EtreeToMessages, SaveCatalog, ReadTranslations,\
                        MatchTranslations, TranslationToEtree, open_pofile
from svghmi.hmi_tree import HMI_TYPES, HMITreeNode, SPECIAL_NODES 
from svghmi.ui import SVGHMI_UI
from svghmi.fonts import GetFontTypeAndFamilyName, GetCSSFontFaceFromFontFile


ScriptDirectory = paths.AbsDir(__file__)


# module scope for HMITree root
# so that CTN can use HMITree deduced in Library
# note: this only works because library's Generate_C is
#       systematicaly invoked before CTN's CTNGenerate_C

hmi_tree_root = None

on_hmitree_update = None

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
            on_hmitree_update(hmi_tree_root)

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
        hmitree_backup_file = open(hmitree_backup_path, 'wb')
        hmitree_backup_file.write(etree.tostring(hmi_tree_root.etree()))
        hmitree_backup_file.close()

        return ((["svghmi"], [(gen_svghmi_c_path, IECCFLAGS)], True), "",
                ("runtime_00_svghmi.py", open(runtimefile_path, "rb")))
                #         ^
                # note the double zero after "runtime_", 
                # to ensure placement before other CTN generated code in execution order


def Register_SVGHMI_UI_for_HMI_tree_updates(ref):
    global on_hmitree_update
    def HMITreeUpdate(_hmi_tree_root):
        obj = ref()
        if obj is not None:
            obj.HMITreeUpdate(_hmi_tree_root)

    on_hmitree_update = HMITreeUpdate


class SVGHMIEditor(ConfTreeNodeEditor):
    CONFNODEEDITOR_TABS = [
        (_("HMI Tree"), "CreateSVGHMI_UI")]

    def CreateSVGHMI_UI(self, parent):
        global hmi_tree_root

        if hmi_tree_root is None:
            buildpath = self.Controler.GetCTRoot()._getBuildPath()
            hmitree_backup_path = os.path.join(buildpath, "hmitree.xml")
            if os.path.exists(hmitree_backup_path):
                hmitree_backup_file = open(hmitree_backup_path, 'rb')
                hmi_tree_root = HMITreeNode.from_etree(etree.parse(hmitree_backup_file).getroot())

        ret = SVGHMI_UI(parent, Register_SVGHMI_UI_for_HMI_tree_updates)

        on_hmitree_update(hmi_tree_root)

        return ret

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
            "bitmap":    "EditSVG",
            "name":    _("Inkscape"),
            "tooltip": _("Edit HMI"),
            "method":   "_StartInkscape"
        },
        {
            "bitmap":    "OpenPOT",
            "name":    _("New lang"),
            "tooltip": _("Open non translated message catalog (POT) to start new language"),
            "method":   "_OpenPOT"
        },
        {
            "bitmap":    "EditPO",
            "name":    _("Edit lang"),
            "tooltip": _("Edit existing message catalog (PO) for specific language"),
            "method":   "_EditPO"
        },
        {
            "bitmap":    "AddFont",
            "name":    _("Add Font"),
            "tooltip": _("Add TTF, OTH or WOFF font to be embedded in HMI"),
            "method":   "_AddFont"
        },
        {
            "bitmap":    "DelFont",
            "name":    _("Delete Font"),
            "tooltip": _("Remove font previously added to HMI"),
            "method":   "_DelFont"
        },
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

        build_path = self._getBuildPath()
        target_path = os.path.join(build_path, target_fname)
        hash_path = os.path.join(build_path, "svghmi.md5")

        self.GetCTRoot().logger.write("SVGHMI:\n")

        if os.path.exists(svgfile):

            hasher = hashlib.md5()
            hmi_tree_root._hash(hasher)
            with open(svgfile, 'rb') as afile:
                while True:
                    buf = afile.read(65536)
                    if len(buf) > 0:
                        hasher.update(buf)
                    else:
                        break
            digest = hasher.hexdigest()

            if os.path.exists(hash_path):
                with open(hash_path, 'rb') as digest_file:
                    last_digest = digest_file.read()
            else:
                last_digest = None
            
            if digest != last_digest:

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

                target_file = open(target_path, 'wb')
                result.write(target_file, encoding="utf-8")
                target_file.close()

                # print(str(result))
                # print(transform.xslt.error_log)
                # print(etree.tostring(result.xslt_profile,pretty_print=True))

                with open(hash_path, 'wb') as digest_file:
                    digest_file.write(digest)
            else:
                self.GetCTRoot().logger.write("    No changes - XSLT transformation skipped\n")

        else:
            target_file = open(target_path, 'wb')
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

    def _AddFont(self):
        pass

    def _DelFont(self):
        pass
        
    def CTNGlobalInstances(self):
        # view_name = self.BaseParams.getName()
        # return [ (view_name + "_" + name, iec_type, "") for name, iec_type in SPECIAL_NODES]
        # TODO : move to library level for multiple hmi
        return [(name, iec_type, "") for name, iec_type in SPECIAL_NODES]

    def GetIconName(self):
        return "SVGHMI"
