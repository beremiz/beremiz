#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from itertools import repeat, islice, chain

## URI parsing functions

def split_as_dict(s, sep, labels):
    return dict(zip(labels, islice(chain(s.split(sep), repeat("")), len(labels))))

def parse_tcp(loc):
    return split_as_dict(loc, ":", ["host", "port"])

def parse_sslpsk(loc):
    locals().update(**split_as_dict(loc, "#", ["hostport", "ID"]))
    return dict(**parse_tcp(hostport), ID=ID) # type: ignore

def parse_serial(loc):
    return split_as_dict(loc, "@", ["device", "baudrate"])

def parse_usb(loc):
    return split_as_dict(loc, ":", ["VID", "PID", "serialnumber"])

## URI building functions

def build_tcp(fields):
    if fields['port']:
        return "{host}:{port}".format(**fields)
    return fields['host']

def build_sslpsk(fields):
    return "{hostport}#{ID}".format(hostport=build_tcp(fields), **fields)

def build_serial(fields):
    if fields['baudrate']:
        return "{device}@{baudrate}".format(**fields)
    return fields['device']

def build_usb(fields):
    if fields['serialnumber']:
        return "{VID}:{PID}:{serialnumber}".format(**fields)
    if fields['PID']:
        return "{VID}:{PID}".format(**fields)
    return fields['VID']
    
## Dialog fields definition

model_tcp = [('host', _("Host:")),
             ('port', _("Port:"))]

model_serial = [('device', _("Device:")),
                ('baudrate', _("Baud rate:"))]

model_usb = [('VID', _("Vendor ID:")),
             ('PID', _("Product ID:")),
             ('serialnumber', _("Serial number:"))]


## Schemes description

schemes_desc = [
#   ( scheme name ,  data model , use ID,   parser   ,    builder  )
    ("LOCAL",       [],           False, lambda x: {}, lambda x: ""),
    ("ERPC",        model_tcp,    False, parse_tcp,    build_tcp   ),
    ("ERPCS",       model_tcp,    True,  parse_sslpsk, build_sslpsk),
    ("ERPC-SERIAL", model_serial, False, parse_serial, build_serial),
    ("ERPC-USB",    model_usb,    False, parse_usb,    build_usb   )]

per_scheme_model = {sch: desc for sch, *desc in schemes_desc}

