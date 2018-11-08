#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from __future__ import absolute_import

from itertools import repeat, islice, chain
import wx

from connectors.SchemeEditor import SchemeEditor

Schemes = ["WAMP", "WAMPS"]

model = [('host',_("Host:")),
         ('port',_("Port:")),
         ('realm',_("Realm:")),
         ('ID',_("ID:"))]

class WAMP_dialog(SchemeEditor):
    def __init__(self, *args, **kwargs):
        self.model = model
        SchemeEditor.__init__(self, *args, **kwargs)

    def SetLoc(self, loc):
        hostport, realm, ID = list(islice(chain(loc.split("#"), repeat("")),3))
        host, port = list(islice(chain(hostport.split(":"), repeat("")),2))
        self.SetFields(locals())

    def GetLoc(self):
        fields = self.GetFields()

        #TODO : input validation test

        template = "{host}" + \
                   (":{port}" if fields['port'] else '') +\
                   "#{realm}#{ID}"

        return template.format(**fields)

