#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from connectors.ERPC_URI import schemes_desc, per_scheme_model
from connectors.SchemeEditor import SchemeEditor

## Scheme list for the dialog's combobox

Schemes = list(zip(*schemes_desc))[0]


## Specialized SchemeEditor panel for ERPC 

class ERPC_dialog(SchemeEditor):
    def __init__(self, scheme, *args, **kwargs):
        self.model, self.EnableIDSelector, self.parser, self.builder = per_scheme_model[scheme]

        SchemeEditor.__init__(self, scheme, *args, **kwargs)

    def SetLoc(self, loc):
        self.SetFields(self.parser(loc))

    def GetLoc(self):
        return self.builder(self.GetFields())
