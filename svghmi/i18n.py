#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2021: Edouard TISSERANT
#
# See COPYING file for copyrights details.


from lxml import etree
import os
import sys
import subprocess
import time
import ast
import wx
import re
from email.parser import HeaderParser

import pycountry
from dialogs import MessageBoxOnce
from POULibrary import UserAddressedException

cmd_parser = re.compile(r'(?:"([^"]+)"\s*|([^\s]+)\s*)?')

def open_pofile(pofile):
    """ Opens PO file with POEdit """
    
    if sys.platform.startswith('win'):
        from six.moves import winreg
        poedit_cmd = None
        try:
            poedit_cmd = winreg.QueryValue(winreg.HKEY_LOCAL_MACHINE,
                                           'SOFTWARE\\Classes\\poedit\\shell\\open\\command')
            cmd = re.findall(cmd_parser, poedit_cmd)
            dblquote_value,smpl_value = cmd[0]
            poedit_path = dblquote_value+smpl_value
        except OSError:
            poedit_path = None

    else:
        if "SNAP" in os.environ:
            MessageBoxOnce("Launching POEdit with xdg-open",
                    "Confined app can't launch POEdit directly.\n"+
                        "Instead, PO/POT file is passed to xdg-open.\n"+
                        "Please select POEdit when proposed.\n\n"+
                    "Notes: \n"+
                    " - POEdit must be installed on you system.\n"+
                    " - If no choice is proposed, use file manager to change POT/PO file properties.\n",
                    "SVGHMII18SnapWarning")
            poedit_path = "xdg-open"
        else:
            try:
                poedit_path = subprocess.check_output("command -v poedit", shell=True).strip()
            except subprocess.CalledProcessError:
                poedit_path = None

    if poedit_path is None:
        wx.MessageBox("POEdit is not found or installed !")
    else:
        subprocess.Popen([poedit_path,pofile])

def EtreeToMessages(msgs):
    """ Converts XML tree from 'extract_i18n' templates into a list of tuples """
    messages = []

    for msg in msgs:
        messages.append((
            b"\n".join([line.text.encode() for line in msg]),
            msg.get("label").encode(), msg.get("id").encode()))

    return messages

def SaveCatalog(fname, messages):
    """ Save messages given as list of tupple (msg,label,id) in POT file """
    w = POTWriter()
    w.ImportMessages(messages)

    with open(fname, 'wb') as POT_file:
        w.write(POT_file)

def GetPoFiles(dirpath):
    po_files = [fname for fname in os.listdir(dirpath) if fname.endswith(".po")]
    po_files.sort()
    return [(po_fname[:-3],os.path.join(dirpath, po_fname)) for po_fname in po_files]

def ReadTranslations(dirpath):
    """ Read all PO files from a directory and return a list of (langcode, translation_dict) tuples """

    translations = []
    for translation_name, po_path in GetPoFiles(dirpath):
        r = POReader()
        r.read(po_path)
        translations.append((translation_name, r.get_messages()))
    return translations

def MatchTranslations(translations, messages, errcallback):
    """
    Matches translations against original message catalog,
    warn about inconsistancies,
    returns list of langs, and a list of (msgid, [translations]) tuples
    """
    translated_messages = []
    broken_lang = set()
    for msgid,label,svgid in messages:
        translated_message = []
        for langcode,translation in translations:
            msg = translation.pop(msgid, None)
            if msg is None:
                broken_lang.add(langcode)
                errcallback(_('{}: Missing translation for "{}" (label:{}, id:{})\n').format(langcode,msgid,label,svgid))
                translated_message.append(msgid)
            else:
                translated_message.append(msg)
        translated_messages.append((msgid,translated_message))
    langs = []
    for langcode,translation in translations:
        try:
            l,c = langcode.split("_")
            language_name = pycountry.languages.get(alpha_2 = l).name
            country_name = pycountry.countries.get(alpha_2 = c).name
            langname = "{} ({})".format(language_name, country_name)
        except:
            try:
                langname = pycountry.languages.get(alpha_2 = langcode).name
            except:
                langname = langcode

        langs.append((langname,langcode))

        broken = False
        for msgid, msg in translation.items():
            broken = True
            errcallback(_('{}: Unused translation "{}":"{}"\n').format(langcode,msgid,msg))
        if broken or langcode in broken_lang:
            errcallback(_('Translation for {} is outdated, please edit {}.po, click "Catalog -> Update from POT File..." and select messages.pot.\n').format(langcode,langcode))


    return langs,translated_messages


def TranslationToEtree(langs,translated_messages):

    result = etree.Element("translations")

    langsroot = etree.SubElement(result, "langs")
    for name, code in langs:
        langel = etree.SubElement(langsroot, "lang", {"code":code})
        langel.text = name

    msgsroot = etree.SubElement(result, "messages")
    for msgid, msgs in translated_messages:
        msgidel = etree.SubElement(msgsroot, "msgid")
        for msg in msgs:
            msgel = etree.SubElement(msgidel, "msg")
            for line in msg.split(b"\n"):
                lineel = etree.SubElement(msgel, "line")
                lineel.text = escape(line).decode()

    return result

# Code below is based on :
#  cpython/Tools/i18n/pygettext.py
#  cpython/Tools/i18n/msgfmt.py

locpfx = b'#:svghmi.svg:'

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
"Content-Type: text/plain; charset=UTF-8\\n"
"Content-Transfer-Encoding: 8bit\\n"
"Generated-By: SVGHMI 1.0\\n"


'''
escapes = []

def make_escapes():
    global escapes
    escapes = [b"\%03o" % i for i in range(128)]
    for i in range(32, 127):
        escapes[i] = bytes([i])
    escapes[ord('\\')] = b'\\\\'
    escapes[ord('\t')] = b'\\t'
    escapes[ord('\r')] = b'\\r'
    escapes[ord('\n')] = b'\\n'
    escapes[ord('\"')] = b'\\"'

make_escapes()

def escape(s):
    return b''.join([escapes[c] if c < 128 else bytes([c]) for c in s])

def normalize(s):
    # This converts the various Python string types into a format that is
    # appropriate for .po files, namely much closer to C style.
    lines = s.split(b'\n')
    if len(lines) == 1:
        s = b'"' + escape(s) + b'"'
    else:
        if not lines[-1]:
            del lines[-1]
            lines[-1] = lines[-1] + b'\n'
        for i in range(len(lines)):
            lines[i] = escape(lines[i])
        lineterm = b'\\n"\n"'
        s = b'""\n"' + lineterm.join(lines) + b'"'
    return s

class POTWriter:
    def __init__(self):
        self.__messages = {}

    def ImportMessages(self, msgs):
        for  msg, label, svgid in msgs:
            self.addentry(msg, label, svgid)

    def addentry(self, msg, label, svgid):
        entry = (label, svgid)
        self.__messages.setdefault(msg, set()).add(entry)

    def write(self, fp):
        timestamp = time.strftime('%Y-%m-%d %H:%M%z')
        header = pot_header % {'time': timestamp}
        fp.write(header.encode())
        reverse = {}
        for k, v in self.__messages.items():
            keys = list(v)
            keys.sort()
            reverse.setdefault(tuple(keys), []).append((k, v))
        rkeys = sorted(reverse.keys())
        for rkey in rkeys:
            rentries = reverse[rkey]
            rentries.sort()
            for k, v in rentries:
                v = list(v)
                v.sort()
                locline = locpfx
                for label, svgid in v:
                    d = {b'label': label, b'svgid': svgid}
                    s = b' %(label)s:%(svgid)s' % d
                    if len(locline) + len(s) <= 78:
                        locline = locline + s
                    else:
                        fp.write(locline + b'\n')
                        locline = locpfx + s
                if len(locline) > len(locpfx):
                    fp.write(locline + b'\n')
                fp.write(b'msgid ' + normalize(k) + b'\n')
                fp.write(b'msgstr ""\n\n')


class POReader:
    def __init__(self):
        self.__messages = {}

    def get_messages(self):
        return self.__messages

    def add(self, ctxt, msgid, msgstr, fuzzy):
        "Add a non-fuzzy translation to the dictionary."
        if not fuzzy and msgstr and msgid:
            if ctxt is None:
                self.__messages[msgid] = msgstr
            else:
                self.__messages[b"%b\x04%b" % (ctxt, id)] = str

    def read(self, infile):
        ID = 1
        STR = 2
        CTXT = 3


        with open(infile, 'rb') as f:
            lines = f.readlines()
            
        section = msgctxt = None
        fuzzy = 0

        # Start off assuming Latin-1, so everything decodes without failure,
        # until we know the exact encoding
        encoding = 'latin-1'

        # Parse the catalog
        lno = 0
        for l in lines:
            l = l.decode(encoding)
            lno += 1
            # If we get a comment line after a msgstr, this is a new entry
            if l[0] == '#' and section == STR:
                self.add(msgctxt, msgid, msgstr, fuzzy)
                section = msgctxt = None
                fuzzy = 0
            # Record a fuzzy mark
            if l[:2] == '#,' and 'fuzzy' in l:
                fuzzy = 1
            # Skip comments
            if l[0] == '#':
                continue
            # Now we are in a msgid or msgctxt section, output previous section
            if l.startswith('msgctxt'):
                if section == STR:
                    self.add(msgctxt, msgid, msgstr, fuzzy)
                section = CTXT
                l = l[7:]
                msgctxt = b''
            elif l.startswith('msgid') and not l.startswith('msgid_plural'):
                if section == STR:
                    self.add(msgctxt, msgid, msgstr, fuzzy)
                    if not msgid:
                        # See whether there is an encoding declaration
                        p = HeaderParser()
                        charset = p.parsestr(msgstr.decode(encoding)).get_content_charset()
                        if charset:
                            encoding = charset
                section = ID
                l = l[5:]
                msgid = msgstr = b''
                is_plural = False
            # This is a message with plural forms
            elif l.startswith('msgid_plural'):
                if section != ID:
                    raise UserAddressedException(
                        'msgid_plural not preceded by msgid on %s:%d' % (infile, lno))
                l = l[12:]
                msgid += b'\0' # separator of singular and plural
                is_plural = True
            # Now we are in a msgstr section
            elif l.startswith('msgstr'):
                section = STR
                if l.startswith('msgstr['):
                    if not is_plural:
                        raise UserAddressedException(
                            'plural without msgid_plural on %s:%d' % (infile, lno))
                    l = l.split(']', 1)[1]
                    if msgstr:
                        msgstr += b'\0' # Separator of the various plural forms
                else:
                    if is_plural:
                        raise UserAddressedException(
                            'indexed msgstr required for plural on  %s:%d' % (infile, lno))
                    l = l[6:]
            # Skip empty lines
            l = l.strip()
            if not l:
                continue
            l = ast.literal_eval(l)
            if section == CTXT:
                msgctxt += l.encode(encoding)
            elif section == ID:
                msgid += l.encode(encoding)
            elif section == STR:
                msgstr += l.encode(encoding)
            else:
                raise UserAddressedException(
                    'Syntax error on %s:%d' % (infile, lno) + 'before:\n %s'%l)
        # Add last entry
        if section == STR:
            self.add(msgctxt, msgid, msgstr, fuzzy)



