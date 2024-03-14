#!/bin/bash
# Basically the same as what the CI script runs, but designed to be run locally before pushing

PYTHON=python3

# Start in ITM root dir
cd "$(dirname ${BASH_SOURCE[0]})/.."

# If we're in an active venv, remove it from the path (`deactivate` got lost
# when we started a new bash process, so we can't use that.)
VENV_DIR=$(grep '^VIRTUAL_ENV="' < venv/bin/activate | sed -r 's/^VIRTUAL_ENV="(.*)"$/\1/')
if grep '|' <<< "$VENV_DIR"; then
	echo -e "Parts of this script assume that the venv path will not contain a '|'.\nAnd yet it does. Aborting rather than trying to guess why." > /dev/stderr
	exit 1
fi
PATH=$(sed "s|$VENV_DIR/bin:||" <<< "$PATH")
	
# If the servers are already running, kill them.
function kill_servers_and_die() {
	"$PYTHON" stop-servers.py || true
	exit 1
}

###echo -e "\x1b[94m# Setup\x1b[0m"
"$PYTHON" stop-servers.py || true
###"$PYTHON" install.py # Assumes that $HOME/.ssh/id_rsa has access to the TA1 repo
source venv/bin/activate

echo $PATH

# No header here. run_tests prints its own headers
###"$PYTHON" run_tests.py --nolint
###sleep 2 # give user a chance to see the final summary before flooding the screen with more stuff

echo -e "\x1b[94m# Integration Tests\x1b[0m"
trap kill_servers_and_die SIGINT # not really working. run-servers or tad_tester gets the SIGINT instead of this script.
"$PYTHON" run-servers.py
sleep 2 # TODO: stopgap to avoid a race condition. Correct fix is for run-servers to not exit until the servers are listening at their ports.
"$PYTHON" tad_tester.py --no-verbose --session_type soartech
trap - SIGINT
### sleep 2

### "$PYTHON" run_tests.py --notest

