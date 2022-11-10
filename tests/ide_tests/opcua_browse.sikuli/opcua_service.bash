#!/bin/bash

echo "Instant OPC-UA server for test"

# Run server
exec $BEREMIZPYTHONPATH - << EOF

import sys
import time

from opcua import ua, Server

server = Server()
server.set_endpoint("opc.tcp://127.0.0.1:4840/freeopcua/server/")

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
