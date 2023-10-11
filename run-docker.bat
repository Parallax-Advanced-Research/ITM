@echo off
if "%TA3_ENDPOINT%"=="" set TA3_ENDPOINT="host.docker.internal:8080"

docker run --env PYTHONPATH=. -it tad python3 scripts/tad_tester.py --endpoint %TA3_ENDPOINT% %*
