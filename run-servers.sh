#/bin/bash

cd .deprepos/itm-evaluation-client
git checkout e9fe3673056ab1cb7aabfb64ef3055d0ef088ac1
git pull
cd ../..

./run-ta3-server.sh &
./run-adept-server.sh &
./run-soartech-server.sh &

