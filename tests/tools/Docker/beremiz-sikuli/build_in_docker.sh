#!/bin/bash

set -e

CONTAINER=beremiz_sikuli_current

docker start $CONTAINER 
docker exec $CONTAINER bash -c "do_tests $1"
docker stop $CONTAINER

