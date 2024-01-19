#/bin/bash

repo-cfgs/update-server.sh itm-evaluation-client
repo-cfgs/update-server.sh itm-evaluation-server
repo-cfgs/update-server.sh ta1-server-mvp
repo-cfgs/update-server.sh adept_server

repo-cfgs/start-server.sh itm-evaluation-server 8080 TA3 -m swagger_server
repo-cfgs/start-server.sh ta1-server-mvp 8084 Soartech -m itm_app
repo-cfgs/start-server.sh adept_server 8081 BBN -m openapi_server --port 8081
