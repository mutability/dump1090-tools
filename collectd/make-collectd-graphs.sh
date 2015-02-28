#!/bin/sh

renice -n 5 -p $$

signal_graph() {
  rrdtool graph \
  "$1" \
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
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
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
  --title "$3 message rate" \
  --vertical-label "messages/second" \
  --lower-limit 0  \
  --units-exponent 0 \
  --right-axis 360:0 \
  "DEF:messages=$2/dump1090_messages-local_accepted.rrd:value:AVERAGE" \
  "DEF:strong=$2/dump1090_messages-strong_signals.rrd:value:AVERAGE" \
  "DEF:positions=$2/dump1090_messages-positions.rrd:value:AVERAGE" \
  "CDEF:y2strong=strong,10,*" \
  "CDEF:y2positions=positions,10,*" \
  "LINE1:messages#0000FF:messages received" \
  "AREA:y2strong#FF0000:messages >-3dBFS / hr (RHS)" \
  "LINE1:y2positions#00c0FF:positions / hr (RHS)"
}

remote_rate_graph() {
  rrdtool graph \
  "$1" \
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
  --title "$3 message rate" \
  --vertical-label "messages/second" \
  --lower-limit 0  \
  --units-exponent 0 \
  --right-axis 360:0 \
  "DEF:messages=$2/dump1090_messages-remote_accepted.rrd:value:AVERAGE" \
  "DEF:positions=$2/dump1090_messages-positions.rrd:value:AVERAGE" \
  "CDEF:y2positions=positions,10,*" \
  "LINE1:messages#0000FF:messages received" \
  "LINE1:y2positions#00c0FF:position / hr (RHS)"
}

aircraft_graph() {
  rrdtool graph \
  "$1" \
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
  --title "$3 aircraft seen" \
  --vertical-label "aircraft" \
  --lower-limit 0 \
  --units-exponent 0 \
  "DEF:all=$2/dump1090_aircraft-recent.rrd:total:AVERAGE" \
  "DEF:pos=$2/dump1090_aircraft-recent.rrd:positions:AVERAGE" \
  "AREA:all#00FF00:aircraft tracked" \
  "LINE1:pos#0000FF:aircraft with positions"
}

tracks_graph() {
  rrdtool graph \
  "$1" \
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
  --title "$3 tracks seen" \
  --vertical-label "tracks/hour" \
  --lower-limit 0 \
  --units-exponent 0 \
  "DEF:all=$2/dump1090_tracks-all.rrd:value:AVERAGE" \
  "DEF:single=$2/dump1090_tracks-single_message.rrd:value:AVERAGE" \
  "CDEF:hall=all,3600,*,1000,MIN" \
  "CDEF:hsingle=single,3600,*,1000,MIN" \
  "AREA:hall#00FF00:unique tracks" \
  "AREA:hsingle#FF0000:tracks with single message"
}

cpu_graph() {
  rrdtool graph \
  "$1" \
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
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

machine_cpu_graph() {
  rrdtool graph \
  "$1" \
  --start end-$4 \
  --width 480 \
  --height 200 \
  --step "$5" \
  --title "$3 overall CPU" \
  --vertical-label "CPU / %" \
  --lower-limit 0 \
  --upper-limit 100 \
  --rigid \
  --units-exponent 0 \
  "DEF:idle=$2/cpu-idle.rrd:value:AVERAGE" \
  "DEF:interrupt=$2/cpu-interrupt.rrd:value:AVERAGE" \
  "DEF:nice=$2/cpu-nice.rrd:value:AVERAGE" \
  "DEF:softirq=$2/cpu-softirq.rrd:value:AVERAGE" \
  "DEF:steal=$2/cpu-steal.rrd:value:AVERAGE" \
  "DEF:system=$2/cpu-system.rrd:value:AVERAGE" \
  "DEF:user=$2/cpu-user.rrd:value:AVERAGE" \
  "DEF:wait=$2/cpu-wait.rrd:value:AVERAGE" \
  "CDEF:all=idle,interrupt,nice,softirq,steal,system,user,wait,+,+,+,+,+,+,+" \
  "CDEF:pinterrupt=100,interrupt,*,all,/" \
  "CDEF:pnice=100,nice,*,all,/" \
  "CDEF:psoftirq=100,softirq,*,all,/" \
  "CDEF:psteal=100,steal,*,all,/" \
  "CDEF:psystem=100,system,*,all,/" \
  "CDEF:puser=100,user,*,all,/" \
  "CDEF:pwait=100,wait,*,all,/" \
  "AREA:pinterrupt#000080:irq" \
  "AREA:psoftirq#0000C0:softirq:STACK" \
  "AREA:psteal#0000FF::STACK" \
  "AREA:pwait#C00000:io:STACK" \
  "AREA:psystem#FF0000:sys:STACK" \
  "AREA:puser#40FF40:user:STACK" \
  "AREA:pnice#008000:nice:STACK"
}

common_graphs() {
  aircraft_graph /var/www/collectd/dump1090-$2-acs-$4.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3" "$4" "$5"
  cpu_graph /var/www/collectd/dump1090-$2-cpu-$4.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3" "$4" "$5"
  tracks_graph /var/www/collectd/dump1090-$2-tracks-$4.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3" "$4" "$5"
}

# receiver_graphs host shortname longname period step
receiver_graphs() {
  common_graphs "$1" "$2" "$3" "$4" "$5"
  signal_graph /var/www/collectd/dump1090-$2-signal-$4.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3" "$4" "$5"
  local_rate_graph /var/www/collectd/dump1090-$2-rate-$4.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3" "$4" "$5"
}

hub_graphs() {
  common_graphs "$1" "$2" "$3" "$4" "$5"
  remote_rate_graph /var/www/collectd/dump1090-$2-rate-$4.png /var/lib/collectd/rrd/$1/dump1090-$2 "$3" "$4" "$5"
}

period="$1"
step="$2"

receiver_graphs rpi.lxi northwest "Northwest antenna" "$period" "$step"
receiver_graphs twopi.lxi southeast "Southeast antenna" "$period" "$step"
hub_graphs rpi.lxi hub "Hub" "$period" "$step"
machine_cpu_graph /var/www/collectd/machine-cpu-rpi-$period.png /var/lib/collectd/rrd/rpi.lxi/cpu-0 "rpi" "$period" "$step"
