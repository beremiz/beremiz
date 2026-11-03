#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Conversion between PLCopen TC6 XML (plc.xml) and a tree of IEC 61131-3 text files (plc/)
"""

import os

from .common import ConversionError  # noqa: F401
from .tree import Session, TreeConflictError  # noqa: F401

_sessions = {}


def load(plc_dir):
    """ TC6 XML string of plc_dir, remembering its files for save """
    session = Session(plc_dir)
    xml = session.load()
    _sessions[session.directory] = session
    return xml


def save(xml, plc_dir):
    """ Update plc_dir from TC6 XML string, keeping text of unchanged declarations.
    Raise TreeConflictError if files changed since load """
    directory = os.path.abspath(plc_dir)
    session = _sessions.get(directory)
    if session is None:
        session = Session(plc_dir)
        if os.path.isdir(plc_dir):
            session.load()
        _sessions[directory] = session
    session.save(xml)


def tree_to_xml(plc_dir):
    """ TC6 XML string of plc_dir """
    return Session(plc_dir).load()


def xml_to_tree(xml, plc_dir):
    """ Update plc_dir from TC6 XML string """
    session = Session(plc_dir)
    if os.path.isdir(plc_dir):
        session.load()
    session.save(xml)
