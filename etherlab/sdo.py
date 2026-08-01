#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
#
# See COPYING file for copyrights details.

"""
Description of an SDO entry, shared by the IDE and the runtime.

Entries travel between both sides as JSON objects, see etherlab/rpc.py.
"""


FIELDS = ("idx", "subIdx", "datatype", "size", "value")


class SDOEntry(object):
    def __init__(self, idx="", subIdx="", datatype="", size="", value=""):
        self.idx = idx
        self.subIdx = subIdx
        self.datatype = datatype
        self.size = size
        self.value = value

    def to_dict(self):
        return dict((field, getattr(self, field)) for field in FIELDS)

    @classmethod
    def from_dict(cls, description):
        return cls(**dict((field, description.get(field, ""))
                          for field in FIELDS))
