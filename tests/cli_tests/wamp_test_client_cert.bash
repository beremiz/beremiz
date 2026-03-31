#!/bin/bash

#set -x

rm -f ./CLI_OK ./PLC_OK ./PLC_CONNECTED

export BEREMIZ_APPDATA=`pwd`/AppData
mkdir -p $BEREMIZ_APPDATA
KEYSTORE=$BEREMIZ_APPDATA/keystore

PLC_wamp_ID="PLC_1234"
IDE_wamp_ID="IDE_1234"

# Set BEREMIZ_LOCAL_HOST to localhost if not already set
: ${BEREMIZ_LOCAL_HOST:=localhost}

URI="WAMPS-CRT://${BEREMIZ_LOCAL_HOST}:8888/ws#Automation#${PLC_wamp_ID}"

# Array of client IDs
client_cns=(${IDE_wamp_ID} ${PLC_wamp_ID})

# Create base directory for the certificates and keys
mkdir -p certs/server certs/clients

openssl req -nodes -new -x509 -keyout certs/server/server.key \
                 -subj "/C=FR/L=Paris/O=Beremiz/OU=server/CN=${BEREMIZ_LOCAL_HOST}" \
                 -addext "subjectAltName=DNS:${BEREMIZ_LOCAL_HOST}" \
                 -out certs/server/server.crt

# Declare an associative array to store client certificate SHA1 fingerprints
declare -A client_fingerprints

# Loop through each client CN and generate keys and certificates
for cn in "${client_cns[@]}"; do

    # Generate client cert to be signed
    openssl req -nodes -newkey rsa:2048 -keyout certs/clients/${cn}.key \
            -subj "/C=FR/L=Paris/O=Beremiz/OU=client/CN=${cn}" \
            -addext "subjectAltName=DNS:${cn}" \
            -out certs/clients/${cn}.csr

    # Sign the client cert
    openssl x509 -req -in certs/clients/${cn}.csr \
            -CA certs/server/server.crt \
            -CAkey certs/server/server.key \
            -out certs/clients/${cn}.crt \
            # -extfile <(printf "subjectAltName=DNS:${cn}")

    # Get the SHA1 fingerprint of the client certificate
    fingerprint=$(openssl x509 -in certs/clients/${cn}.crt -noout -fingerprint -sha1 | sed 's/.*=//')
    client_fingerprints["${cn}"]="${fingerprint}"

    # Create a PEM file containing the client certificate and private key
    cat "certs/clients/${cn}.crt" "certs/clients/${cn}.key" > "certs/clients/${cn}.pem"

done

# Prepare crossbar server configuration
mkdir -p .crossbar
cp certs/server/server.crt ./.crossbar/ca.crt # In our test server is CA
cp certs/server/server.key ./.crossbar/server.key
cp certs/server/server.crt ./.crossbar/server.crt

# Crossbar need a Python Authenticator component to decide if Client Cert is OK
cat > authenticator.py <<PythonEnd
from twisted.internet.defer import inlineCallbacks

from autobahn.twisted.wamp import ApplicationSession
from autobahn.wamp.exception import ApplicationError


class AutomationAuthenticator(ApplicationSession):

   # our "database" of accepted client certificate fingerprints
   ACCEPTED_CERTS = {
PythonEnd

for client in "${!client_fingerprints[@]}"; do
    echo "      '${client_fingerprints[$client]}':'${client}'," >> authenticator.py
done

cat >> authenticator.py <<PythonEnd
   }
   @inlineCallbacks
   def onJoin(self, details):

      def authenticate(realm, authid, details):
         client_cert = details['transport'].get('peer_cert', None)

         if not client_cert:
            raise ApplicationError("automation.no_cert", "no client certificate presented")

         sha1 = client_cert['sha1']

         subject_cn = client_cert['subject']['cn']

         if sha1 not in self.ACCEPTED_CERTS:
            print("AutomationAuthenticator.authenticate: client denied.")
            raise ApplicationError("automation.invalid_cert", "certificate with SHA1 {} denied".format(sha1))
         else:
            print("AutomationAuthenticator.authenticate: client accepted.")
            return {
               'authid': subject_cn,
               'role': 'authenticated'
            }

      try:
         yield self.register(authenticate, 'automation.authenticate')
         print("AutomationAuthenticator: dynamic authenticator registered.")
      except Exception as e:
         print("AutomationAuthenticator: could not register dynamic authenticator - {}".format(e))
PythonEnd

# Crossbar configuration that uses Python Authenticator component
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
                                    "uri": "*",
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
                        },
                        {
                            "name": "authenticator",
                            "permissions": [
                                {
                                    "uri": "automation.authenticate",
                                    "match": "exact",
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
                            "key": "server.key",
                            "ca_certificates": [
                                "ca.crt"
                            ]
                        }
                    },
                    "paths": {
                        "ws": {
                            "type": "websocket",
                            "auth": {
                                "tls": {
                                    "type": "dynamic",
									"authenticator": "automation.authenticate"
                                }
                            }
                        }
                    }
                }
            ],
            "components": [
                {
                    "type": "class",
                    "classname": "authenticator.AutomationAuthenticator",
                    "realm": "Automation",
                    "role": "authenticator"
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
    "authentication": "ClientCertificate",
    "verifyHostname": true,
    "url": "wss://${BEREMIZ_LOCAL_HOST}:8888/ws"
}
JsonEnd


# Re-use self-signed server cert for client
cp .crossbar/server.crt wampTrustStore.crt
cp certs/clients/${PLC_wamp_ID}.pem wampClientCert.pem

# Start Beremiz runtime again, with wamp enabled
$BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_service.py -c wampconf.json -s psk.txt -n test_wamp_ID -x 0 &> >(
    echo "Start PLC loop"
    while read line; do
        # Wait for server to print modified value
        echo "PLC>> $line"
        if [[ "$line" =~ "WAMP session joined" ]]; then
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


# Prepare test project
cp -a $BEREMIZPATH/tests/projects/wamp .
sed -i "s,TEST_URI,${URI},g" wamp/beremiz.xml


# Re-use self-signed server cert for client in test project
IDE_CERT=$KEYSTORE/cert
mkdir -p $IDE_CERT
cp .crossbar/server.crt $IDE_CERT/${BEREMIZ_LOCAL_HOST}.crt

IDE_CLIENT_CERT=$KEYSTORE/own/client.crt
mkdir -p $KEYSTORE/own
rm -f $IDE_CLIENT_CERT
cp certs/clients/${IDE_wamp_ID}.pem $IDE_CLIENT_CERT

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
