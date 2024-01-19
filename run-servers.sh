#/bin/bash

repo-cfgs/update-server.sh itm-evaluation-client
repo-cfgs/update-server.sh itm-evaluation-server
repo-cfgs/update-server.sh ta1-server-mvp
repo-cfgs/update-server.sh adept_server

repo-cfgs/run-ta3-server.sh &
repo-cfgs/run-adept-server.sh &
repo-cfgs/run-soartech-server.sh &

