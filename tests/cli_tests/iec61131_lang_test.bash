#!/bin/bash

# Run IEC61131 language test through command line, and check for success in output

coproc setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py \
    -k \
    --project-home $BEREMIZPATH/tests/projects/iec61131_lang_test \
    --config TargetType.CFLAGS string "-DBEREMIZ_TEST_CYCLES=1000" \
    clean build transfer run;

cli=$COPROC_PID

# Kills the CLI and the runtime when they didn't end by themselves.
trap 'pkill -9 -s $cli' EXIT

while read -t 5 -u ${COPROC[0]} line; do 
    echo "$line"
    if [[ "$line" == *ALL\ TESTS\ OK* ]]; then
        wait $cli
        exit 0
    fi
done

exit 42
