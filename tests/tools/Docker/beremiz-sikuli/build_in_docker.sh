#!/bin/bash

CONTAINER=beremiz_sikuli_current

docker start $CONTAINER 
docker exec -i -t $CONTAINER bash -i -c do_test $1
docker stop $CONTAINER

