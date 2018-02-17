#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of Beremiz.
# See COPYING file for copyrights details.

from __future__ import absolute_import
import os
from lxml import etree
import util.paths as paths
from plcopen.structures import StdBlckLibs

ScriptDirectory = paths.AbsDir(__file__)

class XSLTModelQuery(object):
    """ a class to handle XSLT queries on project and libs """
    def __init__(self, controller, xsltpath, ext = []):
        # arbitrary set debug to false, updated later
        self.debug = False

        # merge xslt extensions for library access to query specific ones
        xsltext = [
            ("GetProject", lambda *_ignored: 
                controller.GetProject(self.debug)),
            ("GetStdLibs", lambda *_ignored: 
                [lib for lib in StdBlckLibs.values()]),
            ("GetExtensions", lambda *_ignored: 
                [ctn["types"] for ctn in controller.ConfNodeTypes])
        ] + ext

        # parse and compile. "beremiz" arbitrary namespace for extensions 
        self.xslt = etree.XSLT(
            etree.parse(
                os.path.join(ScriptDirectory, xsltpath),
                etree.XMLParser()),
            extensions={ ("beremiz", name):call for name, call in xsltext})

    def _process_xslt(self, root, debug, **kwargs):
        self.debug = debug
        res = self.xslt(root,**{k:etree.XSLT.strparam(v) for k,v in kwargs.iteritems()})
        # print(self.xslt.error_log)
        return res
