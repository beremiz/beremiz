#!/bin/bash

# MQTT over TLS test.
#
# Test project contains two MQTT clients connected to the same broker, each one
# publishing what the other subscribes to. PLC program compares what it sends
# with what it receives, and logs "TEST OK" once all values did pass through.
#
# Broker is the one coming with Eclipse Paho testing utilities, started with the
# TLS enabled configuration provided asside it. CA certificate given to MQTT
# clients is taken from the same place, so that it always matches broker's
# certificate.

rm -f ./PLC_OK ./broker_log.txt

TESTDIR=`pwd`

# Set BEREMIZ_LOCAL_HOST to localhost if not already set
: ${BEREMIZ_LOCAL_HOST:=localhost}

# Set PAHOTESTINGPATH to Paho testing utilities path if not already set
: ${PAHOTESTINGPATH:=$HOME/paho.mqtt.testing}

BROKERDIR=$PAHOTESTINGPATH/interoperability

# Broker's listener authenticating server only, no client certificate expected
BROKER_URI=wss://${BEREMIZ_LOCAL_HOST}:18885

# Prepare test project, with CA certificate matching broker's certificate
cp -a $BEREMIZPATH/tests/projects/mqtt_ssl .
cp $BROKERDIR/tls_testing/ssl/test-root-ca.crt mqtt_ssl/project_files/

# Start broker, configuration file paths are relative to broker's directory
cd $BROKERDIR
$BEREMIZPYTHONPATH startbroker.py -c localhost_testing.conf &> $TESTDIR/broker_log.txt &
SERVER_PID=$!
cd $TESTDIR

echo wait for broker to come up
res=110  # default to ETIMEDOUT
c=15
while ((c--)); do
    if grep -q "Starting TCP listener" ./broker_log.txt; then
        echo broker is up.
        res=0  # OK success
        break
    else
        echo waiting for broker.... $c
        sleep 1
    fi
done

if [ "$res" != "0" ] ; then
    kill $SERVER_PID
    echo timeout starting broker.
    exit $res
fi

# Use CLI to build, transfer and start PLC
setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -v -k \
     --project-home mqtt_ssl \
     --config mqtt_0.MQTTClient.Broker_URI string $BROKER_URI \
     --config mqtt_1.MQTTClient.Broker_URI string $BROKER_URI \
     clean build transfer run &> >(
echo "Start PLC loop"
while read line; do
    # Wait for PLC program to report that all values did pass through broker
    echo "PLC>> $line"
    if [[ "$line" == *"TEST OK"* ]]; then
        echo "PLC could exchange all values through broker"
        touch ./PLC_OK
    fi
done
echo "End PLC loop"
) &
PLC_PID=$!

echo all subprocess started, start polling results
res=110  # default to ETIMEDOUT
c=60
while ((c--)); do
    if [[ -a ./PLC_OK ]]; then
        echo got results.
        res=0  # OK success
        break
    else
        echo waiting.... $c
        sleep 1
    fi
done

# Kill PLC and subprocess
echo will kill PLC:$PLC_PID and SERVER:$SERVER_PID
pkill -s $PLC_PID
kill $SERVER_PID

exit $res
