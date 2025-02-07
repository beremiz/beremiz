#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz Runtime
#
# Copyright (C) 2013: Laurent BESSARD
# Copyright (C) 2017: Andrey Skvortsov
# Copyright (C) 2025: Edouard Tisserant
#
# See COPYING file for copyrights details.

import csv
from collections import OrderedDict

csv_int_files = {}
cvs_int_changed = set()
csv_str_files = {}
cvs_str_changed = set()

class Entry():
    def __init__(self, *args):
        self.args = args
    def __call__(self):
        return self.args

def _CSV_int_Load(fname):
    global csv_int_files
    entry = csv_int_files.get(fname, None)
    if entry is None:
        data = list()
        csvfile = open(fname, 'rt', encoding='utf-8')

        try:
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
            csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)
            for row in reader:
                data.append(row)
        finally:
            csvfile.close()
        entry = Entry(fname, dialect, data)
        csv_int_files[fname] = entry
    return entry


def _CSV_str_Load(fname):
    global csv_str_files
    entry = csv_str_files.get(fname, None)
    if entry is None:
        data = []
        csvfile = open(fname, 'rt', encoding='utf-8')

        try:
            dialect = csv.Sniffer().sniff(csvfile.read(1024))
            csvfile.seek(0)
            reader = csv.reader(csvfile, dialect)
            first_row = reader.__next__()
            data.append(first_row)
            col_headers = OrderedDict([(name, index+1) for index, name 
                                        in enumerate(first_row[1:])])
            max_row_len = len(first_row)
            row_headers = OrderedDict()
            for index, row in enumerate(reader):
                row_headers[row[0]] = index+1
                data.append(row)
                max_row_len = max(max_row_len, len(row))
        finally:
            csvfile.close()
        entry = Entry(fname, dialect, col_headers, row_headers, max_row_len, data)
        csv_str_files[fname] = entry
    return entry


def _CSV_str_Create(fname):
    global csv_str_files
    data = [[]] # start with an empty row, acounting for header row
    dialect = None
    col_headers = OrderedDict()
    row_headers = OrderedDict()
    max_row_len = 1  # set to one initialy, accounting for header column
    entry = Entry(fname, dialect, col_headers, row_headers, max_row_len, data)
    csv_str_files[fname] = entry
    return entry


def _CSV_Save_data(fname, dialect, data):
    try:
        wfile = open(fname, 'wt')
        writer = csv.writer(wfile) if not(dialect) else csv.writer(wfile, dialect)
        for row in data:
            writer.writerow(row)
    finally:
        wfile.close()

def _CSV_int_Save(entry):
    fname, dialect, data = entry()
    _CSV_Save_data(fname, dialect, data)


def _CSV_str_Save(entry):
    fname, dialect, col_headers, row_headers, max_row_len, data = entry()
    _CSV_Save_data(fname, dialect, data)


_already_registered_cb = False
def _CSV_OnIdle_callback():
    global _already_registered_cb, cvs_int_changed, cvs_str_changed
    _already_registered_cb = False
    while len(cvs_int_changed):
        entry = cvs_int_changed.pop()
        _CSV_int_Save(entry)

    while len(cvs_str_changed):
        entry = cvs_str_changed.pop()
        _CSV_str_Save(entry)


def _CSV_register_OnIdle_callback():
    global _already_registered_cb
    if not _already_registered_cb:
        OnIdle.append(_CSV_OnIdle_callback)
        _already_registered_cb = True


def _CSV_int_modified(entry):
    global cvs_int_changed
    cvs_int_changed.add(entry)
    _CSV_register_OnIdle_callback()
    

def _CSV_str_modified(entry):
    global cvs_str_changed
    cvs_str_changed.add(entry)
    _CSV_register_OnIdle_callback()


def CSVRdInt(fname, rowidx, colidx):
    """
    Return value at row/column pointed by integer indexes
    Assumes data starts at first row and first column, no headers.
    """

    try:
        _fname, _dialect, data = _CSV_int_Load(fname)()
    except IOError:
        return "#FILE_NOT_FOUND"
    except csv.Error as e:
        return "#CSV_ERROR"

    try:
        row = data[rowidx]
        if not row and rowidx == len(data)-1:
            raise IndexError
    except IndexError:
        return "#ROW_NOT_FOUND"

    try:
        return row[colidx]
    except IndexError:
        return "#COL_NOT_FOUND"


def CSVRdStr(fname, rowname, colname):
    """
    Return value at row/column pointed by a pair of names as string
    Assumes first row is column headers and first column is row name.
    """

    if not rowname:
        return "#INVALID_ROW"
    if not colname:
        return "#INVALID_COLUMN"

    try:
        fname, dialect, col_headers, row_headers, max_row_len, data = _CSV_str_Load(fname)()
    except IOError:
        return "#FILE_NOT_FOUND"
    except csv.Error:
        return "#CSV_ERROR"

    try:
        rowidx = row_headers[rowname]
    except KeyError:
        return "#ROW_NOT_FOUND"

    try:
        colidx = col_headers[colname]
    except KeyError:
        return "#COL_NOT_FOUND"

    try:
        return data[rowidx][colidx]
    except IndexError:
        return "#COL_NOT_FOUND"


def CSVWrInt(fname, rowidx, colidx, content):
    """
    Update value at row/column pointed by integer indexes
    Assumes data starts at first row and first column, no headers.
    """

    try:
        entry = _CSV_int_Load(fname)
    except IOError:
        return "#FILE_NOT_FOUND"
    except csv.Error as e:
        return "#CSV_ERROR"

    fname, dialect, data = entry()
    try:
        if rowidx == len(data):
            row = []
            data.append(row)
        else:
            row = data[rowidx]
    except IndexError:
        return "#ROW_NOT_FOUND"

    try:
        if rowidx > 0 and colidx >= len(data[0]):
            raise IndexError
        if colidx >= len(row):
            row.extend([""] * (colidx - len(row)) + [content])
        else:
            row[colidx] = content
    except IndexError:
        return "#COL_NOT_FOUND"

    _CSV_int_modified(entry)

    return "OK"


def CSVWrStr(fname, rowname, colname, content):
    """
    Update value at row/column pointed by a pair of names as string.
    Assumes first row is column headers and first column is row name.
    """

    if not rowname:
        return "#INVALID_ROW"
    if not colname:
        return "#INVALID_COLUMN"

    try:
        entry = _CSV_str_Load(fname)
    except IOError:
        entry = _CSV_str_Create(fname)
    except csv.Error:
        return "#CSV_ERROR"

    fname, dialect, col_headers, row_headers, max_row_len, data = entry()
    try:
        rowidx = row_headers[rowname]
        row = data[rowidx]
    except KeyError:
        # create a new row with appropriate header
        row = [rowname]
        # put it at the end
        rowidx = len(data)
        data.append(row)
        row_headers[rowname] = rowidx

    try:
        colidx = col_headers[colname]
    except KeyError:
        # adjust col headers content
        first_row = data[0] 
        first_row += [""]*(max_row_len - len(first_row)) + [rowname]
        # create a new column
        colidx = col_headers[colname] = max_row_len
        max_row_len = max_row_len + 1

    try:
        row[colidx] = content
    except IndexError:
        # create a new cell
        row += [""]*(colidx - len(row)) + [content]

    _CSV_str_modified(entry)

    return "OK"


def CSVReload():
    global csv_int_files, csv_str_files, cvs_int_changed, cvs_str_changed

    # Force saving modified CSV files
    _CSV_OnIdle_callback()

    # Wipe data model
    csv_int_files.clear()
    csv_str_files.clear()
    cvs_int_changed.clear()
    cvs_str_changed.clear()

