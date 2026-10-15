#!/bin/bash
#
# OPC-UA server across PLC logic hot-swap.
#
# Flow:
#  1. Start a Beremiz runtime on a random port.
#  2. Build + transfer + run opcua_server project (v1).
#  3. OPC-UA client connects, writes CMD, waits for PLC echo. Keeps session.
#  4. Build v2, adding NEWVAR variable (logic-only change), same build path
#     so that IOs .so, OPC-UA server included, is reused.
#  5. Transfer v2: hot-swap.
#  6. Client, still on same session, sees NEWVAR appear, and CMD still
#     readable with same NodeId and value carried over by hot-swap.

set -euo pipefail

RUNTIME_PORT=$(( RANDOM % 1000 + 61131 ))
RUNTIME_TMPDIR=$(mktemp -d)
TEST_TMPDIR=$(mktemp -d)

rm -f ./PLC_CONNECTED ./CLIENT_READY ./CLIENT_OK

cleanup() {
    if [[ "${CLI_PID:-0}" -gt 0 ]]; then
        pkill -9 -s "$CLI_PID" 2>/dev/null || true
    fi
    if [[ "${CLIENT_PID:-0}" -gt 0 ]]; then
        kill "$CLIENT_PID" 2>/dev/null || true
    fi
    if [[ "${RUNTIME_PID:-0}" -gt 0 ]]; then
        kill "$RUNTIME_PID" 2>/dev/null || true
    fi
    rm -rf "$RUNTIME_TMPDIR" "$TEST_TMPDIR"
}
trap cleanup EXIT

wait_for() {
    # wait_for <file> <seconds>
    local c=$2
    while ((c--)); do
        if [[ -a $1 ]]; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# --- Step 1: Start runtime on a random port ---
$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_service.py -p "$RUNTIME_PORT" -i 127.0.0.1 -x 0 "$RUNTIME_TMPDIR" &> >(
    while read line; do
        echo "PLC>> $line"
        if [[ "$line" == *"$RUNTIME_TMPDIR"* ]]; then
            touch ./PLC_CONNECTED
        fi
    done
) &
RUNTIME_PID=$!

if ! wait_for ./PLC_CONNECTED 30; then
    echo "FAILED: runtime did not come up"
    exit 110
fi

# --- Step 2: Prepare two project copies, build v1 ---
BUILD_DIR="$TEST_TMPDIR/build"
cp -a "$BEREMIZPATH/tests/projects/opcua_server" "$TEST_TMPDIR/v1"
cp -a "$BEREMIZPATH/tests/projects/opcua_server" "$TEST_TMPDIR/v2"
sed -i 's|<variable name="LOGGER0">|<variable name="NEWVAR"><type><INT/></type><initialValue><simpleValue value="7"/></initialValue></variable>\n            <variable name="LOGGER0">|' \
    "$TEST_TMPDIR/v2/plc.xml"

coproc CLI ( setsid "$BEREMIZPYTHONPATH" "$BEREMIZPATH/Beremiz_cli.py" -k \
        --uri "ERPC://127.0.0.1:$RUNTIME_PORT" \
        --project-home "$TEST_TMPDIR/v1" \
        --buildpath "$BUILD_DIR" \
        clean build transfer run )

# --- Step 3: Client, kept connected during whole test ---
$BEREMIZPYTHONPATH - > >(
    while read line; do
        echo "CLIENT>> $line"
        if [[ "$line" == "CLIENT READY" ]]; then
            touch ./CLIENT_READY
        fi
        if [[ "$line" == "CLIENT OK" ]]; then
            touch ./CLIENT_OK
        fi
    done
) << EOF &

import sys
import os
import asyncio

from asyncua import Client, ua

host = os.environ.get("OPCUA_DEFAULT_HOST", "127.0.0.1")
url = "opc.tcp://"+host+":4840"

async def read(node):
    try:
        return await node.read_value()
    except ua.UaError as e:
        return e

async def main():
    client = Client(url, timeout=10)
    for retry in range(120):
        try:
            await client.connect()
            break
        except Exception:
            await asyncio.sleep(1)
    else:
        print("FAILED: cannot connect")
        return

    ns = await client.get_namespace_index("urn:beremiz:plc")
    def node(name):
        return client.get_node(ua.NodeId("CONFIG.RESOURCE1.INSTANCE0." + name, ns))
    cmd, echo, newvar = node("CMD"), node("ECHO"), node("NEWVAR")

    while True:
        try:
            await cmd.write_value(ua.Variant(5, ua.VariantType.Int16))
            if await echo.read_value() == 5:
                break
        except ua.UaError:
            pass
        await asyncio.sleep(0.5)
    print("NEWVAR before swap:", await read(newvar))
    print("CLIENT READY")
    sys.stdout.flush()

    while True:
        await asyncio.sleep(0.5)
        value = await read(newvar)
        if value == 7:
            break
    value = await read(cmd)
    print("CMD after swap:", value)
    if value == 5:
        print("CLIENT OK")
    await client.disconnect()

asyncio.run(main())
sys.stdout.flush()

EOF
CLIENT_PID=$!

if ! wait_for ./CLIENT_READY 120; then
    echo "FAILED: client could not write v1 PLC"
    exit 110
fi
echo ">>> v1 running, client connected."

# --- Step 4: Disconnect v1 CLI so the server accepts the v2 connection ---
pkill -9 -s "${CLI_PID}" 2>/dev/null || true
CLI_PID=0
sleep 1

# --- Step 5: Build v2 + hot-swap transfer ---
coproc CLI ( setsid "$BEREMIZPYTHONPATH" "$BEREMIZPATH/Beremiz_cli.py" -k \
        --uri "ERPC://127.0.0.1:$RUNTIME_PORT" \
        --project-home "$TEST_TMPDIR/v2" \
        --buildpath "$BUILD_DIR" \
        build transfer )

saw_hotswap=0
while read -u "${CLI[0]}" -t 120 line; do
    echo "CLI2: $line"
    if [[ "$line" == *"Hot-swap:"* ]]; then
        saw_hotswap=1
        break
    fi
    if [[ "$line" == *"PLC stopped"* ]] || [[ "$line" == *"can't load PLC"* ]]; then
        echo "FAILED: no hot-swap"
        exit 1
    fi
done
if [[ $saw_hotswap -eq 0 ]]; then
    echo "FAILED: no 'Hot-swap:' confirmation"
    exit 1
fi

# --- Step 6: Client sees new node set ---
if ! wait_for ./CLIENT_OK 30; then
    echo "FAILED: client did not see v2 node set"
    exit 110
fi
echo ">>> OPC-UA server node set replaced on hot-swap."
exit 0
