#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2021: Edouard TISSERANT
#
# See COPYING file for copyrights details.

from __future__ import print_function
from base64 import b64encode

from fontTools import ttLib

def GetFontTypeAndFamilyName(filename):
    """
    Getting font family, format and MIME type
    """

    familyname = None
    formatname = None
    mimetype = None

    font = ttLib.TTFont(filename)
    # https://developer.apple.com/fonts/TrueType-Reference-Manual/RM06/Chap6name.html
    for name in font["name"].names:
        if name.nameID==1 and name.platformID in [0,3]:
            familyname = name.toUnicode()

    if font.flavor :
        # woff and woff2
        formatname = font.flavor
        mimetype = "font/" + formatname
    # conditions on sfntVersion was deduced from fontTools.ttLib.sfnt
    elif font.sfntVersion in ("\x00\x01\x00\x00", "true"):
        formatname = "truetype" 
        mimetype = "font/ttf"
    elif font.sfntVersion == "OTTO":
        formatname = "opentype"
        mimetype = "font/otf"

    return familyname,formatname,mimetype

def DataURIFromFile(filename, mimetype):
    with open(filename, "rb") as fp:
        data = fp.read()
    return "".join([
        "data:",
        mimetype,
        ";base64,",
        b64encode(data).strip()])

def GetCSSFontFaceFromFontFile(filename):
    familyname, formatname, mimetype = GetFontTypeAndFamilyName(filename)
    data_uri = DataURIFromFile(filename, mimetype)
    css_font_face = \
    """
    @font-face {{
          font-family: "{}";
          src: url("{}") format("{}")
    }}
    """.format(familyname, data_uri, formatname)
    return css_font_face


# tests
if __name__ == '__main__':
    print(GetCSSFontFaceFromFontFile("/usr/share/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf"))
    print(GetCSSFontFaceFromFontFile("/usr/share/fonts/opentype/urw-base35/NimbusSans-Regular.otf"))
    print(GetCSSFontFaceFromFontFile("/usr/share/yelp/mathjax/fonts/HTML-CSS/TeX/woff/MathJax_SansSerif-Regular.woff"))
