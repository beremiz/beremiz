#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Convert PLC logic between TC6 XML (plc.xml) and a tree of IEC 61131-3 text files (plc/)
"""

import argparse
import os
import sys

from lxml import etree

from . import tree_to_xml, xml_to_tree, ConversionError
from .canon import difference


def read_xml(path):
    """ TC6 XML of plc.xml file or plc/ directory, legacy namespace updated as Beremiz does """
    if os.path.isdir(path):
        return tree_to_xml(path)
    with open(path, encoding="utf-8") as f:
        return f.read().replace("http://www.plcopen.org/xml/tc6.xsd",
                                "http://www.plcopen.org/xml/tc6_0201")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m tc6_tree_convert", description=__doc__.strip())
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("to-tree", help="update plc/ directory from plc.xml")
    command.add_argument("xml")
    command.add_argument("directory")
    command = commands.add_parser("to-xml", help="write plc.xml from plc/ directory")
    command.add_argument("directory")
    command.add_argument("xml")
    command = commands.add_parser("check", help="compare two projects, plc.xml or plc/")
    command.add_argument("first")
    command.add_argument("second")
    args = parser.parse_args(argv)

    try:
        if args.command == "to-tree":
            xml_to_tree(read_xml(args.xml), args.directory)
        elif args.command == "to-xml":
            with open(args.xml, "w", encoding="utf-8") as f:
                f.write(tree_to_xml(args.directory))
        else:
            difference_text = difference(etree.fromstring(read_xml(args.first).encode()),
                                         etree.fromstring(read_xml(args.second).encode()))
            if difference_text is not None:
                print(difference_text)
                return 1
    except ConversionError as e:
        print(e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
