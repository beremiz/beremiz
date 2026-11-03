#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz IDE
#
# Copyright (C) 2026: Edouard TISSERANT
#
# See COPYING file for copyrights details.

"""
Tree of IEC 61131-3 text files (plc/ directory) <-> TC6 XML project

Files are .st (data types, configuration and ST POUs), .il, .fbd, .ld and .sfc
(POUs in that language). Other files are ignored. File and position of each
declaration are kept in TC6 XML, so that saving puts it back where it was.

A session remembers files as loaded : unchanged declarations are saved with
the text they had, and files changed on disk since are not overwritten.
"""

import hashlib
import os
import re
from dataclasses import dataclass

from lxml import etree

from . import iec_parser
from .canon import digest
from .common import ConversionError, INDENT, NSMAP, tc6, sub, elements, kids, localname
from .comments import set_location, location, set_gap, gap, set_block, block, significant
from .decl import Writer, Builder, DEFAULT_HEADER, SCALINGS

EXTENSIONS = {".st": "ST", ".il": "IL", ".fbd": "FBD", ".ld": "LD", ".sfc": "SFC"}
LANGUAGE_EXTENSIONS = {language: extension for extension, language in EXTENSIONS.items()}
# a tree without project header pragma gets a fixed date, so that its XML does not change
DEFAULT_CREATION = "1970-01-01T00:00:00"
DEFAULT_TYPES_FILE = "types.st"
DEFAULT_CONFIGURATION_FILE = "config.st"
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {"COM%d" % n for n in range(1, 10)} | \
    {"LPT%d" % n for n in range(1, 10)}
_HEADER_RE = re.compile(r"\{\s*TC6\b")


class TreeConflictError(ConversionError):
    """ Files changed on disk since they were loaded """


class TextCache:
    """ Text of units as loaded, by canonical digest of their XML """

    def __init__(self, entries=None):
        self.entries = entries or {}

    def add(self, element, unit_gap, text):
        self.entries.setdefault(digest(element), []).append((unit_gap, text))

    def take(self, element):
        texts = self.entries.get(digest(element))
        return texts.pop(0) if texts else None

    def copy(self):
        return TextCache({key: list(texts) for key, texts in self.entries.items()})


@dataclass
class SourceFile:
    digest: str
    newline: str = "\n"
    bom: bool = False


def file_digest(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()


def new_project():
    project = etree.Element(tc6("project"), nsmap=NSMAP)
    sub(project, "fileHeader", {
        "companyName": DEFAULT_HEADER["companyName"],
        "productName": DEFAULT_HEADER["productName"],
        "productVersion": DEFAULT_HEADER["productVersion"],
        "creationDateTime": DEFAULT_CREATION})
    content_header = sub(project, "contentHeader", {"name": DEFAULT_HEADER["name"]})
    info = sub(content_header, "coordinateInfo")
    for language, _name in SCALINGS:
        sub(sub(info, language), "scaling", {"x": "0", "y": "0"})
    types = sub(project, "types")
    sub(types, "dataTypes")
    sub(types, "pous")
    sub(sub(project, "instances"), "configurations")
    return project


class Session:
    """ A plc/ directory, as loaded """

    def __init__(self, directory):
        self.directory = os.path.abspath(directory)
        self.files = {}
        self.cache = TextCache()

    # loading

    def walk(self):
        """ Relative paths of IEC files, with / separator, sorted """
        paths = []
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = sorted(d for d in dirs if not d.startswith("."))
            for name in sorted(files):
                if name.startswith((".", "#")) or name.endswith("~") or \
                   os.path.splitext(name)[1].lower() not in EXTENSIONS:
                    continue
                path = os.path.relpath(os.path.join(root, name), self.directory)
                paths.append(path.replace(os.sep, "/"))
        return paths

    def absolute(self, path):
        return os.path.join(self.directory, *path.split("/"))

    def read(self, path):
        with open(self.absolute(path), "rb") as f:
            data = f.read()
        info = SourceFile(hashlib.sha1(data).hexdigest())
        if data.startswith(b"\xef\xbb\xbf"):
            info.bom, data = True, data[3:]
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as e:
            raise ConversionError("not UTF-8 text: %s" % e, path)
        if "\r\n" in text:
            info.newline, text = "\r\n", text.replace("\r\n", "\n")
        return text, info

    def load(self):
        """ TC6 XML string of directory files """
        project = new_project()
        data_types = project.find(tc6("types") + "/" + tc6("dataTypes"))
        pous = project.find(tc6("types") + "/" + tc6("pous"))
        configurations = project.find(tc6("instances") + "/" + tc6("configurations"))
        files, units, header = {}, [], None
        for path in self.walk():
            text, files[path] = self.read(path)
            language = EXTENSIONS[os.path.splitext(path)[1].lower()]
            try:
                tree, trivia = iec_parser.parse(text, "TC6_%s_File" % language)
            except iec_parser.ParseError as e:
                raise ConversionError(str(e).split(": ", 1)[1], path, text, e.position)
            builder = Builder(text, path, trivia)
            for start, (kind, end) in sorted(trivia.items()):
                if kind == "Pragma" and _HEADER_RE.match(text, start):
                    if header is not None:
                        raise ConversionError("project header pragma is also in " + header,
                                              path, text, start)
                    header = path
                    self.header(builder, project, start, end)
                    set_location(project.find(tc6("contentHeader")), path, 0)
            try:
                self.build_file(builder, tree, language, data_types, pous, configurations)
            except ConversionError as e:
                raise e.locate(path)
            units.extend((element, unit_gap, text[start:end])
                         for element, unit_gap, start, end in builder.built_units)
        # units are cached once their XML is complete
        cache = TextCache()
        for element, unit_gap, text in units:
            cache.add(element, unit_gap, text)
        self.files, self.cache = files, cache
        return etree.tostring(project, pretty_print=True, xml_declaration=True,
                              encoding="utf-8").decode()

    def header(self, builder, project, start, end):
        content = builder.text[start + 1:end - 1]
        try:
            node, _trivia = iec_parser.parse(content, "TC6_Project_Pragma")
            builder.header(project, content, node)
        except (iec_parser.ParseError, ConversionError) as e:
            raise ConversionError("project header: %s" % e, builder.path, builder.text, start)
        builder.pragma(start, end)

    def build_file(self, builder, tree, language, data_types, pous, configurations):
        previous, index, last = 0, 0, None
        for item in kids(tree):
            if item[0] == "Data_Type_Decl":
                types = builder.data_types(data_types, item, previous)
                set_block(types[0], builder.trivia.gap(previous, item[1]))
                declarations = types
            elif item[0] == "TC6_Config_Decl":
                if len(configurations):
                    raise builder.error("there is more than one configuration", item)
                declarations = [builder.configuration(configurations, item, previous)]
            else:
                declarations = [builder.pou(pous, item, language, previous)]
            for declaration in declarations:
                set_location(declaration, builder.path, index)
                index += 1
            previous, last = item[2], declarations[-1]
        if last is not None:
            set_gap(last, "after", builder.trivia.gap(previous, len(builder.text)))

    # saving

    def target(self, element, language=None):
        """ File of top level declaration """
        path, _index = location(element)
        if path is not None:
            parts = path.split("/")
            valid = all(p not in ("", ".", "..") and not p.startswith(".") for p in parts) and \
                os.path.splitext(path)[1].lower() in EXTENSIONS
            if not valid:
                path = None
        name = localname(element)
        if name == "pou":
            extension = LANGUAGE_EXTENSIONS[language]
            if path is None:
                base = element.get("name")
                if base.upper() in _WINDOWS_RESERVED:
                    base += "_"
                path = base + extension
            elif os.path.splitext(path)[1].lower() != extension:
                path = os.path.splitext(path)[0] + extension
        elif path is None or not path.lower().endswith(".st"):
            path = DEFAULT_TYPES_FILE if name == "dataType" else DEFAULT_CONFIGURATION_FILE
        return path

    def conflicts(self, paths):
        """ Files of paths changed on disk since loaded """
        changed = []
        for path in sorted(set(paths) | set(self.files)):
            absolute = self.absolute(path)
            exists = os.path.isfile(absolute)
            if path in self.files:
                if not exists or file_digest(absolute) != self.files[path].digest:
                    changed.append(path)
            elif exists:
                changed.append(path)
        return changed

    def save(self, xml):
        """ Update directory files from TC6 XML string """
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
        writer = Writer(self.cache.copy())
        groups = {}
        declarations = elements(root.find(tc6("types") + "/" + tc6("dataTypes")), "dataType") + \
            elements(root.find(tc6("types") + "/" + tc6("pous")), "pou") + \
            elements(root.find(tc6("instances") + "/" + tc6("configurations")), "configuration")
        for order, element in enumerate(declarations):
            language = Writer.language(element) if localname(element) == "pou" else None
            path = self.target(element, language)
            _path, index = location(element)
            groups.setdefault(path, []).append(
                (index if index is not None else len(declarations) + order, order, element))
        # project header goes where it was, or with configuration unless it is default one
        header = writer.header(root)
        header_path, _index = location(root.find(tc6("contentHeader")))
        if header_path is None and header == writer.header(new_project()):
            header = header_path = None
        elif header_path is None or not header_path.lower().endswith(".st"):
            configuration = root.find(tc6("instances") + "/" + tc6("configurations") + "/" +
                                      tc6("configuration"))
            header_path = self.target(configuration) if configuration is not None \
                else DEFAULT_CONFIGURATION_FILE
        if header_path is not None:
            groups.setdefault(header_path, [])

        contents = {}
        for path, items in groups.items():
            try:
                contents[path] = self.file_text(writer, [e for _i, _o, e in sorted(items)],
                                                header if path == header_path else None)
            except ConversionError as e:
                raise e.locate(path)

        changed = self.conflicts(contents)
        if changed:
            raise TreeConflictError("files changed since loaded: " + ", ".join(changed))
        self.write(contents)
        self.load()

    def file_text(self, writer, declarations, header):
        text = header or ""
        in_types, last = None, None
        for element in declarations:
            default_gap = "\n\n" if text else ""
            if localname(element) == "dataType":
                marker = block(element)
                if in_types is None or marker is not None:
                    if in_types is not None:
                        text += writer.end(in_types, 0) + "END_TYPE"
                    text += (marker if significant(marker) else default_gap) + "TYPE"
                text += writer.unit(element, 1, writer.data_type, "\n" + INDENT) + ";"
                in_types = element
            else:
                if in_types is not None:
                    text += writer.end(in_types, 0) + "END_TYPE"
                    in_types = None
                generate = writer.pou if localname(element) == "pou" else writer.configuration
                text += writer.unit(element, 0, generate, default_gap)
            last = element
        if in_types is not None:
            text += writer.end(in_types, 0) + "END_TYPE"
        after = gap(last, "after") if last is not None else None
        return text + (after if significant(after) else "\n")

    def write(self, contents):
        """ Write changed files, through temporary files, then remove files left empty """
        written = []
        try:
            for path, content in sorted(contents.items()):
                info = self.files.get(path, SourceFile(""))
                data = ((b"\xef\xbb\xbf" if info.bom else b"") +
                        content.replace("\n", info.newline).encode("utf-8"))
                absolute = self.absolute(path)
                if os.path.isfile(absolute):
                    with open(absolute, "rb") as f:
                        if f.read() == data:
                            continue
                os.makedirs(os.path.dirname(absolute), exist_ok=True)
                temporary = os.path.join(os.path.dirname(absolute),
                                         "." + os.path.basename(absolute) + ".tc6tmp")
                with open(temporary, "wb") as f:
                    f.write(data)
                written.append((temporary, absolute))
            for temporary, absolute in written:
                os.replace(temporary, absolute)
        finally:
            for temporary, _absolute in written:
                if os.path.exists(temporary):
                    os.remove(temporary)
        for path in sorted(set(self.files) - set(contents)):
            absolute = self.absolute(path)
            if os.path.isfile(absolute):
                os.remove(absolute)
            directory = os.path.dirname(absolute)
            while directory != self.directory and not os.listdir(directory):
                os.rmdir(directory)
                directory = os.path.dirname(directory)
