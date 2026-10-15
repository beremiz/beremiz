#!/bin/bash

rm -f ./CLIOK ./PLCOK

# Start PLC with OPC-UA server
setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -k \
     --project-home $BEREMIZPATH/tests/projects/opcua_server clean build transfer run > >(
echo "Start PLC loop"
while read line; do
    # Wait for PLC to log value written by OPC-UA client
    echo "PLC>> $line"
    if [[ "$line" == *"OPCUA write Cmd=42"* ]]; then
        echo "Client could write value"
        touch ./PLCOK
    fi
done
echo "End PLC loop"
) &
PLC_PID=$!

# Run client : browse instance tree, read and write variables
$BEREMIZPYTHONPATH - > >(
    echo "Start CLI loop"
    while read line; do
        echo "CLI>> $line"
        if [[ "$line" == "CLIENT OK" ]]; then
            touch ./CLIOK
        fi
    done
    echo "End CLI loop"
) << EOF &

import sys
import os
import asyncio

from asyncua import Client, ua

host = os.environ.get("OPCUA_DEFAULT_HOST", "127.0.0.1")
url = "opc.tcp://"+host+":4840"

def check(cond, msg):
    if not cond:
        print("FAILED: " + msg)
        sys.exit(1)

async def main():
    client = Client(url)
    for retry in range(60):
        try:
            await client.connect()
            break
        except Exception:
            await asyncio.sleep(1)
    else:
        check(False, "cannot connect")

    try:
        ns = await client.get_namespace_index("urn:beremiz:plc")
        def node(path):
            return client.get_node(ua.NodeId(path, ns))

        # wait for node set to be populated
        inst = None
        for retry in range(30):
            try:
                inst = await client.nodes.objects.get_child(
                    ["%d:PLC" % ns, "%d:CONFIG" % ns, "%d:RESOURCE1" % ns, "%d:INSTANCE0" % ns])
                break
            except ua.UaError:
                await asyncio.sleep(1)
        check(inst is not None, "instance not found")
        names = [(await c.read_browse_name()).Name for c in await inst.get_children()]
        print("instance children:", names)
        for name in ["COUNTER", "ARR", "PT", "PTS", "CMD", "MSG", "DELAY"]:
            check(name in names, name + " not browsable")

        cnt = node("CONFIG.RESOURCE1.INSTANCE0.COUNTER.CNT")
        a = await cnt.read_value()
        await asyncio.sleep(0.5)
        b = await cnt.read_value()
        print("counter", a, b)
        check(b > a, "counter not running")

        check(await node("CONFIG.RESOURCE1.INSTANCE0.DELAY").read_value() == 1500, "TIME read")
        check(await node("CONFIG.RESOURCE1.INSTANCE0.PTS[1].X").read_value() == 1, "array of struct read")

        msg = node("CONFIG.RESOURCE1.INSTANCE0.MSG")
        await msg.write_value(ua.Variant("written", ua.VariantType.String))
        await asyncio.sleep(0.5)
        check(await msg.read_value() == "written", "STRING write")

        await node("CONFIG.RESOURCE1.INSTANCE0.CMD").write_value(ua.Variant(42, ua.VariantType.Int16))
        await asyncio.sleep(0.5)
        check(await node("CONFIG.RESOURCE1.INSTANCE0.ECHO").read_value() == 42, "PLC reaction to write")

        print("CLIENT OK")
    finally:
        await client.disconnect()

asyncio.run(main())
sys.stdout.flush()

EOF
CLIENT_PID=$!

echo all subprocess started, start polling results
res=110  # default to ETIMEDOUT
c=60
while ((c--)); do
    if [[ -a ./CLIOK && -a ./PLCOK ]]; then
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

exit $res
