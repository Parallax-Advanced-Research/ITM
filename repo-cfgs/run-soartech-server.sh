#/bin/bash
cd .deprepos/ta1-server-mvp
source venv/bin/activate
python -m itm_app > soartech-log.txt 2>&1
deactivate
