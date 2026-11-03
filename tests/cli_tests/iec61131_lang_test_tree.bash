#!/bin/bash

# Run IEC61131 language test, with PLC program stored as IEC 61131-3 text files in plc/
# directory, through command line, and check for success in output

coproc setsid $BEREMIZPYTHONPATH $BEREMIZPATH/Beremiz_cli.py \
    -k \
    --project-home $BEREMIZPATH/tests/projects/iec61131_lang_test_tree \
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
