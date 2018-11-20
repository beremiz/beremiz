#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

from __future__ import absolute_import
import os
import time
import json

COL_ID,COL_URI,COL_DESC,COL_LAST = range(4)

def _pskpath(project_path):
    return os.path.join(project_path, 'psk')

def _mgtpath(project_path):
    return os.path.join(_pskpath(project_path), 'management.json')

def _default():
    return ['', # default description
            None, # last known URI
            None]  # last connection date

def _LoadData(project_path):
    if os.path.isdir(_pskpath(project_path)):
        _path = _mgtpath(project_path)
        # load known keys metadata
        # {ID:(Desc, LastKnownURI, LastConnect)}
        return json.loads(open(_path).read()) \
               if os.path.exists(_path) else {}
    return {}

def GetData(project_path):
    # [(ID, Desc, LastKnownURI, LastConnect)
    data = []
    loaded_data = _LoadData(project_path)
    # go through all secret files available an build data
    # out of data recoverd from json and list of secret.
    # this implicitly filters IDs out of metadata who's
    # secret is missing
    psk_files = os.listdir(_pskpath(project_path))
    for filename in psk_files:
       if filename.endswith('.secret'):
           ID = filename[:-7]  # strip filename extension
           meta = loaded_data.get(ID,_default())                  
           data.append([ID]+meta)
    return data


def DeleteID(project_path, ID):
    secret_path = os.path.join(_pskpath(project_path), ID+'.secret')
    os.remove(secret_path)

def _StoreData(project_path, data):
    pskpath = _pskpath(project_path)
    if not os.path.isdir(pskpath):
        os.mkdir(pskpath)
    with open(_mgtpath(project_path), 'w') as f:
        f.write(json.dumps(data))

def SaveData(project_path, data):
    to_store = {row[0]:row[1:] for row in data}
    _StoreData(project_path, to_store)

def UpdateID(project_path, ID, secret, URI):
    pskpath = _pskpath(project_path)
    if not os.path.exists(pskpath):
        os.mkdir(pskpath)

    secpath = os.path.join(pskpath, ID+'.secret')
    with open(secpath, 'w') as f:
        f.write(ID+":"+secret)

    data = _LoadData(project_path)
    dataForID = [ID] + (data.get(ID, _default()) if data else _default())
    dataForID[COL_URI] = URI
    # FIXME : could store time instead os a string and use DVC model's cmp 
    # then date display could be smarter, etc - sortable sting hack for now
    dataForID[COL_LAST] = time.strftime('%y/%M/%d-%H:%M:%S')
    data[ID] = dataForID[1:]
    _StoreData(project_path, data)
