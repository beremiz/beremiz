#!/bin/sh

cleanup()
{
    find ./tests/tools -name '*.pyc' -delete
}

LC_ALL=ru_RU.utf-8

export DISPLAY=:42
Xvfb $DISPLAY -screen 0 1280x1024x24 &
sleep 1


cleanup

ret=0
DELAY=400
KILL_DELAY=$(($DELAY + 30))
timeout -k $KILL_DELAY $DELAY pytest --timeout=10 ./tests/tools
ret=$?

cleanup


pkill -9 Xvfb

exit $ret
