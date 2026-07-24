#!/bin/bash

set -e

echo "Building docker image"
cp -f ../../../requirements_pinned.txt requirements_pinned.txt
export BUILDKIT_PROGRESS=plain
docker build \
    --build-arg UID=$(id -u) \
    --build-arg GID=$(id -g) \
    -t beremiz_sikuli .

