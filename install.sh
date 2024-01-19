#/bin/bash

# Get python references
PYTHON3_REF=$(which python3 | grep "/python3")
PYTHON_REF=$(which python | grep "/python")

error_msg(){
    echo "Need Python 3.10 or 3.11 installed"
}

python_ref(){
    local my_ref=$1
    echo $($my_ref -c 'import platform; major, minor, patch = platform.python_version_tuple(); print(major); print(minor);')
}

# Print success_msg/error_msg according to the provided minimum required versions
check_version(){
    local major=$1
    local minor=$2
    local python_ref=$3
    [[ $major -ge $PYTHON_MINIMUM_MAJOR && $minor -ge $PYTHON_MINIMUM_MINOR ]] && echo $python_ref || error_msg
}

# Logic
if [[ ! -z $PYTHON3_REF ]]; then
    version=($(python_ref python3))
    check_version ${version[0]} ${version[1]} $PYTHON3_REF
    PYTHON_EXEC="python3"
elif [[ ! -z $PYTHON_REF ]]; then
    # Didn't find python3, let's try python
    version=($(python_ref python))
    check_version ${version[0]} ${version[1]} $PYTHON_REF
    PYTHON_EXEC="python"
else
    # Python is not installed at all
    error_msg
    exit 1
fi

export PYTHON_EXEC

if [[ ! -z $(which pip3) ]]; then
    PIP=pip3
elif [[ ! -z $(which pip) ]]; then
    PIP=pip
else
    echo "Need pip installed."
    exit 1
fi

if [[ -z $(which git) ]]; then
    echo "Need git installed."
    exit 1
fi

$PYTHON_EXEC -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir .deprepos
cd .deprepos
echo "Installing TA3 client"
git clone git@github.com:NextCenturyCorporation/itm-evaluation-client.git
if [ $? != 0 ] ; then
  echo "Could not download evaluation client code, check internet connection."
  exit 1
fi

pip install -e itm-evaluation-client
deactivate

echo "Installing TA3 server"
../repo-cfgs/start.sh git@github.com:NextCenturyCorporation/itm-evaluation-server.git
if [ $? != 0 ] ; then
  exit 1
fi

echo "Installing ADEPT server"
../repo-cfgs/start.sh git@gitlab.com:itm-ta1-adept-shared/adept_server.git
if [ $? != 0 ] ; then
  exit 1
fi

echo "Installing SoarTech server"
../repo-cfgs/start.sh git@github.com:ITM-Soartech/ta1-server-mvp.git
if [ $? != 0 ] ; then
  exit 1
fi
