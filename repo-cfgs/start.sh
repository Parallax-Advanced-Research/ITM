#/bin/bash
git clone $1
if [ $? != 0 ]; then
  echo "Could not get $1, exiting."
  exit 1
fi
DIR=`echo "$1" | sed 's/^.*\/\(.*\).git/\1/'`
cd $DIR
$PYTHON_EXEC -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cd ..
deactivate
