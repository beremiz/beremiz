Connect IDE to Runtime
======================


Connection is described by the *URI_location* in project's configuration.
    ``Open project tree root -> Config tab -> URI_location``

eRPC
----

`eRPC <https://github.com/embeddedrpc/erpc>`_ (Embedded RPC) is an open source
Remote Procedure Call (RPC) developed by NXP. 

In case of Beremiz, Runtime is the eRPC server and IDE is a client. Transport
can be either TCP/IP or Serial.

``URI_location`` for eRPC:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    * ``ERPC://host[:port]`` unencrypted connection. Default port is 3000.
        This connection is highly unsecure, and should never be used on
        untrusted network. It is intended to be used on peer to peer connection
        such as ethernet over USB, for initial pairing with IDE.
    * ``ERPCS://host[:port]`` SSL-PSK encrypted connection.
        Default port is 4000.
    * ``LOCAL://`` starts local runtime and connect with it through TCP/IP
        bound to Localhost using random port.

SSL-PSK setup:
^^^^^^^^^^^^^^

In order to provide practical secure communication in between runtime and IDE
TLS-PSK connection according to rfc4279.

Server (runtime)
""""""""""""""""
.. highlight:: ini

PSK ciphersuite avoids the need for public key operations and certificate
management. It is perfect for a performance-constrained environments with
limited CPU power as a PLC.

`Stunnel <https://www.stunnel.org/>`_ is used to wrap unencrypted eRPC server
into an TLS-PSK SSL socket. Hereafter is ``stunnel.conf``::

    [ERPCPSK]
    accept = 4000
    connect = 127.0.0.1:3000
    ciphers = PSK
    sslVersion = TLSv1.2
    PSKsecrets = psk.txt

.. highlight:: text

List PSK ciphers available in server's openssl::

    openssl ciphers -s -psk -tls1_2

Launch ``stunnel``::

    stunnel ./stunnel.conf

Client (IDE) 
""""""""""""

Compare client's available openssl PSK ciphers with Server's ciphers. At least
a few of them should match::

    openssl ciphers -s -psk -tls1_2

Use unencrypted peer-to-peer connection such as network over USB 
or simple Ethernet cable, connect an obtain PSK::

    ERPC://hostname[:port]

Then use Identity Management dialog in IDE to select matching ID and generate
``ERPCS`` URI::

    ERPCS://hostname[:port]#ID


WAMP
----

`WAMP <https://wamp-proto.org/>`_ is an open standard WebSocket subprotocol that provides two application messaging 
patterns in one unified protocol: Remote Procedure Calls + Publish & Subscribe.

Beremiz WAMP connector implementation uses python ``autobahn`` module, from the `crossbar.io <https://github.com/crossbario>`_ project.

Both IDE and runtime are WAMP clients that connect to ``crossbar`` server through HTTP.

``URI_location`` for WAMP:
	* ``WAMP://host[:port]#realm#ID`` Websocket over unencrypted HTTP transport.
	* ``WAMPS://host[:port]#realm#ID`` Websocket over secure HTTPS transport.


..
    TODO : 
        crossbar server setup with example config and minimal backend.
