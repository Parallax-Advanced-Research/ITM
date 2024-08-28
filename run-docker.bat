@echo off
if "%TA3_ENDPOINT%"=="" set TA3_ENDPOINT="host.docker.internal:8080"

docker run --env PYTHONPATH=. -it tad python3 tad_tester.py --session_type eval --no-training --selector keds --assessor triage --endpoint %TA3_ENDPOINT% -- %*
