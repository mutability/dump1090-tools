#!/bin/sh

signal_graph() {
  rrdtool graph \
  "$1" \
  --start end-24h \
  --width 600 \
  --height 200 \
  --title "$3 signal" \
  --vertical-label "dBFS" \
  --upper-limit 0    \
  --lower-limit -50  \
  --rigid            \
  --units-exponent 0 \
  "DEF:signal=$2/dump1090_dbfs-signal.rrd:value:AVERAGE" \
  "DEF:peak=$2/dump1090_dbfs-peak_signal.rrd:value:AVERAGE" \
  "CDEF:us=signal,UN,-100,signal,IF" \
  "AREA:-100#00FF00:mean signal power" \
  "AREA:us#FFFFFF" \
  "LINE1:peak#0000FF:peak signal power"
}

local_rate_graph() {
  rrdtool graph \
  "$1" \
  --start end-24h \
  --width 600 \
  --height 200 \
  --title "$3 message rate" \
  --vertical-label "messages/second" \
  --lower-limit 0  \
  --units-exponent 0 \
  "DEF:messages=$2/dump1090_messages-local_accepted.rrd:value:AVERAGE" \
  "DEF:strong=$2/dump1090_messages-strong_signals.rrd:value:AVERAGE" \
  "AREA:strong#FF0000:messages over -3dBFS" \
  "LINE1:messages#0000FF:messages received"
}

remote_rate_graph() {
  rrdtool graph \
  "$1" \
  --start end-24h \
  --width 600 \
  --height 200 \
  --title "$3 message rate" \
  --vertical-label "messages/second" \
  --lower-limit 0  \
  --units-exponent 0 \
  "DEF:messages=$2/dump1090_messages-remote_accepted.rrd:value:AVERAGE" \
  "LINE1:messages#0000FF:messages received"
}

aircraft_graph() {
  rrdtool graph \
  "$1" \
  --start end-24h \
  --width 600 \
  --height 200 \
  --title "$3 aircraft seen" \
  --vertical-label "aircraft" \
  --lower-limit 0 \
  --units-exponent 0 \
  "DEF:all=$2/dump1090_aircraft-recent.rrd:total:AVERAGE" \
  "DEF:pos=$2/dump1090_aircraft-recent.rrd:positions:AVERAGE" \
  "AREA:all#00FF00:aircraft tracked" \
  "LINE1:pos#0000FF:aircraft with positions"
}

cpu_graph() {
  rrdtool graph \
  "$1" \
  --start end-24h \
  --width 600 \
  --height 200 \
  --title "$3 CPU" \
  --vertical-label "CPU %" \
  --lower-limit 0 \
  --upper-limit 100 \
  --rigid \
  "DEF:demod=$2/dump1090_cpu-demod.rrd:value:AVERAGE" \
  "CDEF:demodp=demod,10,/" \
  "DEF:reader=$2/dump1090_cpu-reader.rrd:value:AVERAGE" \
  "CDEF:readerp=reader,10,/" \
  "DEF:background=$2/dump1090_cpu-background.rrd:value:AVERAGE" \
  "CDEF:backgroundp=background,10,/" \
  "AREA:readerp#008000:USB" \
  "AREA:backgroundp#00C000:other:STACK" \
  "AREA:demodp#00FF00:demodulator:STACK"
}

common_graphs() {
  aircraft_graph /var/www/collectd/dump1090-$2-acs.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3"
  cpu_graph /var/www/collectd/dump1090-$2-cpu.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3"
}

# receiver_graphs host shortname longname
receiver_graphs() {
  common_graphs "$1" "$2" "$3"
  signal_graph /var/www/collectd/dump1090-$2-signal.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3"
  local_rate_graph /var/www/collectd/dump1090-$2-rate.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3"
}

hub_graphs() {
  common_graphs "$1" "$2" "$3"
  remote_rate_graph /var/www/collectd/dump1090-$2-rate.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3"
} 

receiver_graphs rpi.lxi northwest "Northwest antenna"
receiver_graphs twopi.lxi southeast "Southeast antenna"
hub_graphs rpi.lxi hub "Hub"
