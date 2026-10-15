#!/bin/bash
#
# OPC-UA server with encryption, user/password authentication
# and read-only access level.

rm -f ./CLIOK

TEST_TMPDIR=$(mktemp -d)
PROJECT=$TEST_TMPDIR/opcua_server_encrypted
cp -a $BEREMIZPATH/tests/projects/opcua_server $PROJECT

cat > $PROJECT/opcua_server_0@opcua_server/confnode.xml << EOF
<?xml version='1.0' encoding='utf-8'?>
<OPCUAServer xmlns:xsd="http://www.w3.org/2001/XMLSchema" Interface="127.0.0.1" AccessLevel="RO" AllowAnonymous="false">
  <Security Certificate="server_cert.der" PrivateKey="server_key.pem"/>
  <UserPassword User="operator" Password="secret"/>
</OPCUAServer>
EOF

# Server cryptomaterial goes to project files, applicationUri must match
mkdir -p $PROJECT/project_files
yes "" | openssl req -x509 -newkey rsa:2048 -keyout $PROJECT/project_files/server_key.pem \
        -out $TEST_TMPDIR/server_cert.pem -days 355 -nodes \
        -addext "subjectAltName = URI:urn:beremiz:opcua:server,IP:127.0.0.1"
openssl x509 -outform der -in $TEST_TMPDIR/server_cert.pem -out $PROJECT/project_files/server_cert.der

# Client cryptomaterial
yes "" | openssl req -x509 -newkey rsa:2048 -keyout $TEST_TMPDIR/client_key.pem \
        -out $TEST_TMPDIR/client_cert.pem -days 355 -nodes \
        -addext "subjectAltName = URI:urn:freeopcua:client"
openssl x509 -outform der -in $TEST_TMPDIR/client_cert.pem -out $TEST_TMPDIR/client_cert.der

# Start PLC with OPC-UA server
setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -k \
     --project-home $PROJECT clean build transfer run > >(
while read line; do
    echo "PLC>> $line"
done
) &
PLC_PID=$!

# Run client
$BEREMIZPYTHONPATH - > >(
    while read line; do
        echo "CLI>> $line"
        if [[ "$line" == "CLIENT OK" ]]; then
            touch ./CLIOK
        fi
    done
) << EOF &

import sys
import os
import asyncio

from asyncua import Client, ua

host = os.environ.get("OPCUA_DEFAULT_HOST", "127.0.0.1")
url = "opc.tcp://"+host+":4840"
security = "Basic256Sha256,SignAndEncrypt,$TEST_TMPDIR/client_cert.der,$TEST_TMPDIR/client_key.pem"

def check(cond, msg):
    if not cond:
        print("FAILED: " + msg)
        sys.exit(1)

async def try_connect(user, password):
    client = Client(url)
    client.application_uri = "urn:freeopcua:client"
    if user:
        client.set_user(user)
        client.set_password(password)
    try:
        # also connects, to get server certificate
        await client.set_security_string(security)
        await client.connect()
    except Exception as e:
        print("connection refused:", type(e).__name__, e)
        return None
    return client

async def main():
    for retry in range(60):
        client = await try_connect("operator", "secret")
        if client: break
        await asyncio.sleep(1)
    check(client is not None, "cannot connect with user/password")

    try:
        ns = await client.get_namespace_index("urn:beremiz:plc")
        cnt = client.get_node(ua.NodeId("CONFIG.RESOURCE1.INSTANCE0.COUNTER.CNT", ns))
        for retry in range(30):
            try:
                a = await cnt.read_value()
                break
            except ua.UaError:
                await asyncio.sleep(1)
        await asyncio.sleep(0.5)
        b = await cnt.read_value()
        print("counter", a, b)
        check(b > a, "counter not running")

        cmd = client.get_node(ua.NodeId("CONFIG.RESOURCE1.INSTANCE0.CMD", ns))
        try:
            await cmd.write_value(ua.Variant(42, ua.VariantType.Int16))
            check(False, "write accepted despite RO access level")
        except ua.UaStatusCodeError as e:
            print("write rejected:", type(e).__name__)
    finally:
        await client.disconnect()

    check(await try_connect(None, None) is None, "anonymous connection accepted")
    check(await try_connect("operator", "wrong") is None, "wrong password accepted")

    print("CLIENT OK")

asyncio.run(main())
sys.stdout.flush()

EOF
CLIENT_PID=$!

echo all subprocess started, start polling results
res=110  # default to ETIMEDOUT
c=90
while ((c--)); do
    if [[ -a ./CLIOK ]]; then
        echo got results.
        res=0  # OK success
        break
    else
        echo waiting.... $c
        sleep 1
    fi
done

# Kill PLC and subprocess
echo will kill PLC:$PLC_PID and CLIENT:$CLIENT_PID
pkill -s $PLC_PID
kill $CLIENT_PID
rm -rf $TEST_TMPDIR

exit $res
