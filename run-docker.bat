@echo off
if "%1" NEQ "" set TA3_ENDPOINT=%1
if "%TA3_ENDPOINT%"=="" set TA3_ENDPOINT="127.0.0.1:8080"

docker run --env PYTHONPATH=. -it tad python3 scripts/tad_tester.py --endpoint %TA3_ENDPOINT%
