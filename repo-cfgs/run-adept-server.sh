#/bin/bash
cd .deprepos/adept_server
source venv/bin/activate
python -m openapi_server --port 8081 > adept-log.txt 2>&1
deactivate
