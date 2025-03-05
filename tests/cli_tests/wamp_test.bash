#!/bin/bash

rm -f ./CLI_OK ./PLC_OK ./PLC_CONNECTED

# Start runtime one first time to generate PLC PSK
$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_service.py -s psk.txt -n test_wamp_ID -x 0 &
PLC_PID=$!
res=110  # default to ETIMEDOUT
c=5
while ((c--)); do
    if [[ -a psk.txt ]]; then
        echo got PSK.
        res=0  # OK success
        break
    else
        echo waiting PSK.... $c
        sleep 1
    fi
done

kill $PLC_PID

if [ "$res" != "0" ] ; then
    echo timeout generating PSK.
    exit $res
fi

IFS=':' read -r PLC_wamp_ID PLC_wamp_secret < psk.txt

# Prepare test project
cp -a $BEREMIZPATH/tests/projects/wamp .

# Start CLI one first time to generate IDE PSK
IDE_PSK=$HOME/.local/share/beremiz/keystore/own/default.psk
rm -f $IDE_PSK
$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -k \
     --project-home wamp connect &
CLI_PID=$!
res=110  # default to ETIMEDOUT
c=5
while ((c--)); do
    if [[ -a $IDE_PSK ]]; then
        echo got IDE PSK.
        res=0  # OK success
        break
    else
        echo waiting IDE PSK.... $c
        sleep 1
    fi
done

kill $CLI_PID

if [ "$res" != "0" ] ; then
    echo timeout generating IDE PSK.
    exit $res
fi

IFS=':' read -r IDE_wamp_ID IDE_wamp_secret < $IDE_PSK

# Prepare crossbar server configuration
mkdir -p .crossbar

yes "" | openssl req -nodes -new -x509 -keyout ./.crossbar/server.key \
                 -addext "subjectAltName = DNS:localhost" \
                 -out ./.crossbar/server.crt

cat > .crossbar/config.json <<JsonEnd
{
    "version": 2,
    "workers": [
        {
            "type": "router",
            "id": "automation_router",
            "realms": [
                {
                    "name": "Automation",
                    "roles": [
                        {
                            "name": "authenticated",
                            "permissions": [
                                {
                                    "uri": "",
                                    "match": "prefix",
                                    "allow": {
                                        "call": true,
                                        "register": true,
                                        "publish": true,
                                        "subscribe": true
                                    },
                                    "disclose": {
                                        "caller": false,
                                        "publisher": false
                                    },
                                    "cache": true
                                }
                            ]
                        }
                    ]
                }
            ],
		    "transports": [
                {
                    "type": "web",
                    "endpoint": {
                        "type": "tcp",
                        "port": 8888,
                        "tls": {
                            "certificate": "server.crt",
                            "key": "server.key"
                        }
                    },
                    "paths": {
                        "ws": {
                            "type": "websocket",
                            "auth": {
                                "wampcra": {
                                    "type": "static",
                                    "users": {
                                        "${IDE_wamp_ID}": {
                                            "secret": "${IDE_wamp_secret}",
                                            "role": "authenticated"
                                        },
                                        "${PLC_wamp_ID}": {
                                            "secret": "${PLC_wamp_secret}",
                                            "role": "authenticated"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        }
    ]
}
JsonEnd
crossbar start &> crossbar_log.txt &
SERVER_PID=$!
res=110  # default to ETIMEDOUT
c=15
while ((c--)); do
    if [[ -a .crossbar/node.pid ]]; then
        echo found crossbar pid
        res=0  # OK success
        break
    else
        echo wait for crossbar to start.... $c
        sleep 1
    fi
done

if [ "$res" != "0" ] ; then
    kill $SERVER_PID
    echo timeout starting crossbar.
    exit $res
fi

# give more time to crossbar
sleep 3

# Prepare runtime Wamp config
cat > wampconf.json <<JsonEnd
{
    "ID": "${PLC_wamp_ID}", 
    "active": true, 
    "protocolOptions": {
        "autoPingInterval": 60, 
        "autoPingTimeout": 20

    }, 
    "realm": "Automation", 
    "url": "wss://localhost:8888/ws"
}
JsonEnd

# Re-use self-signed server cert for client
cp .crossbar/server.crt wampTrustStore.crt

# Start Beremiz runtime again, with wamp enabled
$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_service.py -c wampconf.json -s psk.txt -n test_wamp_ID -x 0 &> >(
    echo "Start PLC loop"
    while read line; do 
        # Wait for server to print modified value
        echo "PLC>> $line"
        if [[ "$line" =~ ^"WAMP session joined" ]]; then
            echo "PLC is connected"
            touch ./PLC_CONNECTED
        fi
        if [[ "$line" == "PLCobject : PLC started" ]]; then
            echo "PLC was programmed"
            touch ./PLC_OK
        fi
    done
    echo "End PLC loop"
) &
PLC_PID=$!

echo wait for runtime to come up
res=110  # default to ETIMEDOUT
c=30
while ((c--)); do
    if [[ -a ./PLC_CONNECTED ]]; then
        res=0  # OK success
        break
    else
        sleep 1
    fi
done

if [ "$res" != "0" ] ; then
    kill $SERVER_PID
    kill $PLC_PID
    echo timeout connecting PLC to crossbar.
    exit $res
fi

# Re-use self-signed server cert for client in test project
mkdir -p wamp/cert
cp .crossbar/server.crt wamp/cert/localhost.crt

# TODO: patch project's URI to connect to $BEREMIZ_LOCAL_HOST
#       used in tests instead of 127.0.0.1

# Use CLI to build transfer and start PLC
$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -k \
     --project-home wamp build transfer run &> >(
echo "Start CLI loop"
while read line; do 
    # Wait for PLC runtime to output expected value on stdout
    echo "CLI>> $line"
    if [[ "$line" == "PLC installed successfully." ]]; then
        echo "CLI did transfer PLC program"
        touch ./CLI_OK
    fi
done
echo "End CLI loop"
) &
CLI_PID=$!

echo all subprocess started, start polling results
res=110  # default to ETIMEDOUT
c=30
while ((c--)); do
    if [[ -a ./CLI_OK && -a ./PLC_OK ]]; then
        echo got results.
        res=0  # OK success
        break
    else
        echo waiting.... $c
        sleep 1
    fi
done

# Kill PLC and subprocess
echo will kill PLC:$PLC_PID, SERVER:$SERVER_PID and CLI:$CLI_PID
kill $PLC_PID 
kill $CLI_PID 
kill $SERVER_PID

exit $res
