#/bin/bash
DIR=$1
PORT=$2
NAME=$3
shift 3

cd .deprepos/$DIR
if (echo < /dev/tcp/localhost/$PORT) >/dev/null 2>&1 ; then
  echo "Port $PORT not available. $NAME server not started."
  exit 1
else
  echo "Port $PORT available. $NAME server starting."
fi
source venv/bin/activate
python $@ > ../$DIR-log.txt 2>&1 &
echo "$!" > ../$DIR.pid
deactivate
