#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

import md5

class ConnectorBase(object):

    #chuncksize = 16384
    chuncksize = 1024*1024
    def BlobFromFile(self, filepath): 
        s = md5.new()
        blobID = s.digest()  # empty md5, to support empty blob
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(self.chuncksize) 
                if len(chunk) == 0: return blobID
                blobID = self.AppendChunkToBlob(chunk, blobID)
                s.update(chunk)
                if blobID != s.digest(): return None

