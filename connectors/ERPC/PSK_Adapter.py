#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2019: Edouard TISSERANT
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


"""
The TLS-PSK adapter that handles SSL connections instead of regular sockets,
but using Pre Shared Keys instead of Certificates
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
        self._isServer = isServer
        self._sock = None

        if sslpsk is None:
             raise ImportError("sslpsk module is not available")

        raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw_sock.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
        raw_sock.connect((self._host, self._port))
        self._sock = sslpsk.wrap_socket(
                raw_sock, psk=psk, server_side=False,
                ciphers="PSK-AES256-CBC-SHA",  # available in openssl 1.0.2
                ssl_version=ssl.PROTOCOL_TLSv1)


