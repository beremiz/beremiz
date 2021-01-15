import time

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
"Content-Type: text/plain; charset=CHARSET\\n"
"Content-Transfer-Encoding: ENCODING\\n"
"Generated-By: SVGHMI 1.0\\n"

'''

class POTWriter:
    def __init__(self):
        self.__messages = {}

    def ImportMessages(self, msgs):    
        for msg in msgs:
            self.addentry("\n".join([line.text for line in msg]), msg.get("label"), msg.get("id"))

    def addentry(self, msg, label, svgid):
        entry = (label, svgid)
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
                v = v.keys()
                v.sort()
                locline = locpfx
                for label, svgid in v:
                    d = {'label': label, 'svgid': svgid}
                    s = _(' %(label)s:%(svgid)d') % d
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


