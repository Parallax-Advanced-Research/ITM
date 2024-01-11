#/bin/bash

if [[ ! -z $(which python3) ]]; then
    PYTHON="python3"
elif [[ ! -z $(which python) ]]; then
    PYTHON="python"
else
    echo "Python must be installed."
    exit 1
fi

cd .deprepos/itm-evaluation-server
git checkout a9f275ab69c77246cc74fe90cc72c27534c31c82
git pull
$PYTHON -m swagger_server
