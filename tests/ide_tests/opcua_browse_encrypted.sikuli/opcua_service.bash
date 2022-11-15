#!/bin/bash

echo "Instant encrypted OPC-UA server for test"

yes "" | openssl req -x509 -newkey rsa:2048 -keyout my_private_key.pem -out my_cert.pem \
        -days 355 -nodes -addext "subjectAltName = URI:urn:example.org:FreeOpcUa:python-opcua"
openssl x509 -outform der -in my_cert.pem -out my_cert.der

PROJECT_FILES_DIR=$BEREMIZPATH/tests/projects/opcua_browse_encrypted/project_files
mkdir $PROJECT_FILES_DIR
cp my_cert.der my_private_key.pem $PROJECT_FILES_DIR

echo "CERTS READY"

# Run server
exec $BEREMIZPYTHONPATH - << EOF

import sys
import time

from opcua import ua, Server

server = Server()
server.set_endpoint("opc.tcp://127.0.0.1:4840/freeopcua/server/")

server.set_security_policy([ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt])
server.load_certificate("my_cert.der")
server.load_private_key("my_private_key.pem")

uri = "http://beremiz.github.io"
idx = server.register_namespace(uri)

objects = server.get_objects_node()

testobj = objects.add_object(idx, "TestObject")
testvarout = testobj.add_variable(idx, "TestOut", 1.2)
testvar = testobj.add_variable(idx, "TestIn", 5.6)
testvar.set_writable()

server.start()

try:
    while True:
        time.sleep(1)
        inval=testvar.get_value()
        print inval
        testvarout.set_value(inval*2)
        sys.stdout.flush()
finally:
    server.stop()
EOF
