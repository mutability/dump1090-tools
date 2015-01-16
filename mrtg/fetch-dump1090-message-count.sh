#!/bin/sh

COUNTER=`wget -q -O - "$1/data/aircraft.json" | jq '.messages'`

if [ -n "$COUNTER" ]; then echo $COUNTER; else echo UNKNOWN; fi
echo 0
echo 0
echo "dump1090 at $1"
