#/bin/bash
cd .deprepos/itm-evaluation-server
source venv/bin/activate
python -m swagger_server > ta3-log.txt 2>&1
deactivate
