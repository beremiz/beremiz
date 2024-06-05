#!/bin/bash

rm -f ./PLC_OK ./CLI_OK

# Run C runtime
$BEREMIZPATH/C_runtime/beremiz_runtime -v -t tcp -p 61131 -h localhost > >(
    echo "Start PLC stdout reader loop"
    while read line; do 
        # Wait for server to print modified value
        echo "PLC>> $line"
        if [[ "$line" == "C runtime OK #3" ]]; then
            echo "$line"
            touch ./PLC_OK
        fi
    done
    echo "End PLC stdout reader loop"
) &
PLC_PID=$!

# Start PLC with C runtime test
setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py -k \
     --project-home $BEREMIZPATH/tests/projects/c_runtime build transfer run > >(
echo "Start CLI loop"
while read line; do 
    # Wait for CLI to output expected PLC log message on stdout
    echo "CLI>> $line"
    if [[ $line =~ .*C\ runtime\ log\ OK\ #3$ ]]; then
        echo "$line"
        touch ./CLI_OK
    fi
done
echo "End CLI loop"
) &
CLI_PID=$!

echo all subprocess started, start polling results
res=110  # default to ETIMEDOUT
c=45
while ((c--)); do
    if [[ -a ./PLC_OK && -a ./CLI_OK ]]; then
        echo got results.
        res=0  # OK success
        break
    else
        echo waiting.... $c
        sleep 1
    fi
done

# Kill PLC and subprocess
echo will kill CLI:$CLI_PID and PLC:$PLC_PID
pkill -s $CLI_PID 
kill $PLC_PID

exit $res
