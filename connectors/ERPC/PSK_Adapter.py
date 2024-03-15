#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Written by Edouard TISSERANT (C) 2024
# This file is part of Beremiz IDE
# See COPYING file for copyrights details.


"""
The TLS-PSK adapter that handles SSL connections instead of regular sockets,
but using Pre Shared Keys instead of Certificates

Corresponding stunnel.conf on PLC side:

    [ERPCPSK]
    accept = 4000
    connect = 127.0.0.1:3000
    ciphers = PSK
    sslVersion = TLSv1.2
    PSKsecrets = psk.txt

"""

import socket
import ssl

try:
    import sslpsk
except ImportError as e:
    sslpsk = None

from erpc.transport import TCPTransport

class SSLPSKClientTransport(TCPTransport):
    def __init__(self, host, port, psk):
        """ overrides TCPTransport's __init__ to wrap socket in SSl wrapper """
        super(TCPTransport, self).__init__()
        self._host = host
        self._port = port
        self._sock = None
        self._isServer = False

        if sslpsk is None:
             raise ImportError("sslpsk module is not available")

        self.sslpskctx = sslpsk.SSLPSKContext(ssl.PROTOCOL_TLSv1_2)
        self.sslpskctx.set_ciphers('PSK')
        self.sslpskctx.psk = psk
        
        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        raw_sock.connect((self._host, self._port))

        self._sock = self.sslpskctx.wrap_socket(raw_sock, server_side=False)


