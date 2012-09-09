#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os 

import wx

# Get the default language
langid = wx.LANGUAGE_DEFAULT

# Define locale for wx
locale = wx.Locale(langid)

def GetDomain(path):
    for name in os.listdir(path):
        filepath = os.path.join(path, name)
        basename, fileext = os.path.splitext(name)
        if os.path.isdir(filepath):
            result = GetDomain(filepath)
            if result is not None:
                return result
        elif fileext == ".mo":
            return basename
    return None

def AddCatalog(locale_dir):
    if os.path.exists(locale_dir) and os.path.isdir(locale_dir):
        domain = GetDomain(locale_dir)
        if domain is not None:
            locale.AddCatalogLookupPathPrefix(locale_dir)
            locale.AddCatalog(domain)
