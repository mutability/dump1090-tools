#!/bin/sh

AC_TOTAL=`wget -q -O - "$1/data/aircraft.json" | jq '[.aircraft[] | select(.pos < 15)] | length'`
AC_POS=`wget -q -O - "$1/data/aircraft.json" | jq '[.aircraft[] | select(.seen_pos < 15)] | length'`

if [ -n "$AC_TOTAL" ]; then echo $AC_TOTAL; else echo UNKNOWN; fi
if [ -n "$AC_POS" ]; then echo $AC_POS; else echo UNKNOWN; fi
echo 0
echo "dump1090 at $1"
