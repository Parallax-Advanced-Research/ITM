#/bin/bash

if [[ ! -z $(which python3) ]]; then
    PYTHON="python3"
elif [[ ! -z $(which python) ]]; then
    PYTHON="python"
else
    echo "Python must be installed."
    exit 1
fi

cd .deprepos/ta1-server-mvp
git checkout ddd3c0a33b9d3a27e55b128cb7930f83c5a68f46
git pull
$PYTHON -m itm_app
