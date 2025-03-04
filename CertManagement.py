#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

import os

def GetCertPath(project_path, CN):
    # find Certificate from project
    crtpath = os.path.join(project_path, 'cert', CN + '.crt')
    if not os.path.exists(crtpath):
        raise ValueError(
            'Error: Cert %s is missing!\n' % crtpath)
    return crtpath

