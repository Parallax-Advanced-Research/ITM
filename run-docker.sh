#!/bin/bash
if [ ! -z "$1" ]
   then TA3_ENDPOINT=$1
fi
if [ -z "$TA3_ENDPOINT" ]
   then TA3_ENDPOINT="host.docker.internal:8080"
fi

docker run --env PYTHONPATH=. -it tad python3 scripts/tad_tester.py --endpoint $TA3_ENDPOINT
