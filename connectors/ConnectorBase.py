#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

import md5

class ConnectorBase(object):

    #chuncksize = 16384
    chuncksize = 1024*1024
    def BlobFromFile(self, filepath, seed):
        s = md5.new()
        s.update(seed)
        blobID = self.SeedBlob(seed)
        with open(filepath, "rb") as f:
            while blobID == s.digest():
                chunk = f.read(self.chuncksize) 
                if len(chunk) == 0: return blobID
                blobID = self.AppendChunkToBlob(chunk, blobID)
                s.update(chunk)

