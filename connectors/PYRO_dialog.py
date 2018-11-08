#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from __future__ import absolute_import

from itertools import repeat, islice, chain
import wx

from connectors.SchemeEditor import SchemeEditor


model = [('host',_("Host:")),
         ('port',_("Port:"))]

secure_model = model + [('ID',_("ID:"))]

models = [("LOCAL", []), ("PYRO",model), ("PYROS",secure_model)]

Schemes = list(zip(*models)[0])

ModelsDict = dict(models)

class PYRO_dialog(SchemeEditor):
    def __init__(self, scheme, *args, **kwargs):
        self.model = ModelsDict[scheme]
        SchemeEditor.__init__(self, scheme, *args, **kwargs)

    def SetLoc(self, loc):
        hostport, ID = list(islice(chain(loc.split("#"), repeat("")),2))
        host, port = list(islice(chain(hostport.split(":"), repeat("")),2))
        self.SetFields(locals())

    def GetLoc(self):
        if self.model:
            fields = self.GetFields()
            template = "{host}"
            if fields['port']:
                template += ":{port}" 

            return template.format(**fields)
        return ''

