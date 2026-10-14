#!/bin/bash

set -ex

# source directory containing beremiz, matiec, etc..
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && cd ../../../.. && pwd )"
echo "SOURCE direcory : $SRCDIR"

# absolute path to test directory. ~/test if not given as only argument
TESTDIR=${1:-~/test}
mkdir -p $TESTDIR
echo "TEST direcory : $TESTDIR"

UNAME=ubuntu
UHOME=/home/$UNAME

# define TESTDEBUG in env to enable dev-mode. This enables :
#   - IDE session port (make ide_session) and Chromium remote debugging port
#     (BEREMIZ_TEST_DEVTOOLS=9222) passthrough
DEBUGARGS="-p 8080:8080 -p 9222:9222"

echo "Creating docker container"
docker create \
       --name beremiz_playwright_current \
       -v $SRCDIR:$UHOME/src \
       -v $TESTDIR:$UHOME/test \
       `if [ "$TESTDEBUG" == "YES" ]; then echo $DEBUGARGS; fi` \
       -w $UHOME/test \
       -i -t beremiz_playwright /bin/bash

