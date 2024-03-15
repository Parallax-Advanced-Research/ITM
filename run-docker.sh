#!/bin/bash
if [ -z "$TA3_ENDPOINT" ]
   then TA3_ENDPOINT="host-machine:8080"
fi

docker run --env PYTHONPATH=. -it tad python3 scripts/tad_tester.py --endpoint $TA3_ENDPOINT --keds $*
