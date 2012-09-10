#!/usr/local/bin/bash

DIR=$(dirname $0)

while ! nc -z localhost 32000; do
	echo "Waiting... "
	sleep 1
done

export PYTHON_PATH=/home/jeffm/.python-2.5/site-packages
export PYTHONPATH=/home/jeffm/.python-2.5/site-packages
python $DIR/moo.py
