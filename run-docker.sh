#!/bin/bash
if [ -z "$TA3_ENDPOINT" ]
   then TA3_ENDPOINT="host.docker.internal:8080"
fi

docker run --env PYTHONPATH=. -it tad python3 tad_tester.py --session_type eval --no-training --selector keds --assessor triage --ebd --endpoint $TA3_ENDPOINT $*
