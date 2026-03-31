#!/bin/bash

set -e

CONTAINER=beremiz_sikuli_current

docker stop $CONTAINER
docker start $CONTAINER 
docker exec -u root $CONTAINER bash -c "$1"
docker stop $CONTAINER

