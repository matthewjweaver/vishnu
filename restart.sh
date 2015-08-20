#!/bin/bash

DIR=$(dirname $0)

while ! nc -z ib.ice-nine.org 32000; do
	echo "Waiting... "
	sleep 1
done

cd $DIR
python $DIR/moo.py
