#/bin/bash

if [[ ! -z $(which python3) ]]; then
    PYTHON="python3"
elif [[ ! -z $(which python) ]]; then
    PYTHON="python"
else
    echo "Python must be installed."
    exit 1
fi

cd .deprepos/adept_server
git checkout d1797a75a5832d46e4bb1a73b7bd600f7659a449
git pull
$PYTHON -m openapi_server
