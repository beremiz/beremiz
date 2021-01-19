#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2021: Edouard TISSERANT
#
# See COPYING file for copyrights details.

from __future__ import absolute_import
import sys
import subprocess
import time
import wx

def open_pofile(pofile):
    """ Opens PO file with POEdit """
    
    if sys.platform.startswith('win'):
        from six.moves import winreg
        poedit_cmd = None
        try:
            poedit_cmd = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE,
                                           'SOFTWARE\\Classes\\poedit\\shell\\open\\command')
            poedit_path = poedit_cmd.replace('"%1"', '').strip().replace('"', '')
        except OSError:
            poedit_path = None

    else:
        try:
            poedit_path = subprocess.check_output("command -v poedit", shell=True).strip()
        except subprocess.CalledProcessError:
            poedit_path = None

    if poedit_path is None:
        wx.MessageBox("POEdit is not found or installed !")
    else:
        subprocess.Popen([poedit_path,pofile])

locpfx = '#:svghmi.svg:'

pot_header = '''\
# SOME DESCRIPTIVE TITLE.
# Copyright (C) YEAR ORGANIZATION
# FIRST AUTHOR <EMAIL@ADDRESS>, YEAR.
#
msgid ""
msgstr ""
"Project-Id-Version: PACKAGE VERSION\\n"
"POT-Creation-Date: %(time)s\\n"
"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"
"Last-Translator: FULL NAME <EMAIL@ADDRESS>\\n"
"Language-Team: LANGUAGE <LL@li.org>\\n"
"MIME-Version: 1.0\\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Generated-By: SVGHMI 1.0\\n"

'''
escapes = []

def make_escapes(pass_iso8859):
    global escapes
    escapes = [chr(i) for i in range(256)]
    if pass_iso8859:
        # Allow iso-8859 characters to pass through so that e.g. 'msgid
        # "Höhe"' would result not result in 'msgid "H\366he"'.  Otherwise we
        # escape any character outside the 32..126 range.
        mod = 128
    else:
        mod = 256
    for i in range(mod):
        if not(32 <= i <= 126):
            escapes[i] = "\\%03o" % i
    escapes[ord('\\')] = '\\\\'
    escapes[ord('\t')] = '\\t'
    escapes[ord('\r')] = '\\r'
    escapes[ord('\n')] = '\\n'
    escapes[ord('\"')] = '\\"'

make_escapes(pass_iso8859 = True)

EMPTYSTRING = ''

def escape(s):
    global escapes
    s = list(s)
    for i in range(len(s)):
        s[i] = escapes[ord(s[i])]
    return EMPTYSTRING.join(s)

def normalize(s):
    # This converts the various Python string types into a format that is
    # appropriate for .po files, namely much closer to C style.
    lines = s.split('\n')
    if len(lines) == 1:
        s = '"' + escape(s) + '"'
    else:
        if not lines[-1]:
            del lines[-1]
            lines[-1] = lines[-1] + '\n'
        for i in range(len(lines)):
            lines[i] = escape(lines[i])
        lineterm = '\\n"\n"'
        s = '""\n"' + lineterm.join(lines) + '"'
    return s


class POTWriter:
    def __init__(self):
        self.__messages = {}

    def ImportMessages(self, msgs):
        for msg in msgs:
            self.addentry("\n".join([line.text.encode("utf-8") for line in msg]), msg.get("label"), msg.get("id"))

    def addentry(self, msg, label, svgid):
        entry = (label, svgid)
        print(entry)
        self.__messages.setdefault(msg, set()).add(entry)

    def write(self, fp):
        timestamp = time.strftime('%Y-%m-%d %H:%M+%Z')
        print >> fp, pot_header % {'time': timestamp}
        reverse = {}
        for k, v in self.__messages.items():
            keys = list(v)
            keys.sort()
            reverse.setdefault(tuple(keys), []).append((k, v))
        rkeys = reverse.keys()
        rkeys.sort()
        for rkey in rkeys:
            rentries = reverse[rkey]
            rentries.sort()
            for k, v in rentries:
                v = list(v)
                v.sort()
                locline = locpfx
                for label, svgid in v:
                    d = {'label': label, 'svgid': svgid}
                    s = _(' %(label)s:%(svgid)s') % d
                    if len(locline) + len(s) <= 78:
                        locline = locline + s
                    else:
                        print >> fp, locline
                        locline = locpfx + s
                if len(locline) > len(locpfx):
                    print >> fp, locline
                print >> fp, 'msgid', normalize(k)
                print >> fp, 'msgstr ""\n'


class POReader:
    def __init__(self):
        self.__messages = {}

    def add(msgid, msgstr, fuzzy):
        "Add a non-fuzzy translation to the dictionary."
        if not fuzzy and msgstr:
            self.__messages[msgid] = msgstr

    def read(self, fp):
        ID = 1
        STR = 2

        lines = fp.readlines()
        section = None
        fuzzy = 0

        # Parse the catalog
        lno = 0
        for l in lines:
            lno += 1
            # If we get a comment line after a msgstr, this is a new entry
            if l[0] == '#' and section == STR:
                self.add(msgid, msgstr, fuzzy)
                section = None
                fuzzy = 0
            # Record a fuzzy mark
            if l[:2] == '#,' and 'fuzzy' in l:
                fuzzy = 1
            # Skip comments
            if l[0] == '#':
                continue
            # Now we are in a msgid section, output previous section
            if l.startswith('msgid') and not l.startswith('msgid_plural'):
                if section == STR:
                    self.add(msgid, msgstr, fuzzy)
                section = ID
                l = l[5:]
                msgid = msgstr = ''
                is_plural = False
            # This is a message with plural forms
            elif l.startswith('msgid_plural'):
                if section != ID:
                    print >> sys.stderr, 'msgid_plural not preceded by msgid on %s:%d' %\
                        (infile, lno)
                    sys.exit(1)
                l = l[12:]
                msgid += '\0' # separator of singular and plural
                is_plural = True
            # Now we are in a msgstr section
            elif l.startswith('msgstr'):
                section = STR
                if l.startswith('msgstr['):
                    if not is_plural:
                        print >> sys.stderr, 'plural without msgid_plural on %s:%d' %\
                            (infile, lno)
                        sys.exit(1)
                    l = l.split(']', 1)[1]
                    if msgstr:
                        msgstr += '\0' # Separator of the various plural forms
                else:
                    if is_plural:
                        print >> sys.stderr, 'indexed msgstr required for plural on  %s:%d' %\
                            (infile, lno)
                        sys.exit(1)
                    l = l[6:]
            # Skip empty lines
            l = l.strip()
            if not l:
                continue
            l = ast.literal_eval(l)
            if section == ID:
                msgid += l
            elif section == STR:
                msgstr += l
            else:
                print >> sys.stderr, 'Syntax error on %s:%d' % (infile, lno), \
                      'before:'
                print >> sys.stderr, l
                sys.exit(1)
        # Add last entry
        if section == STR:
            self.add(msgid, msgstr, fuzzy)


