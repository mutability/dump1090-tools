Scripts for extracting stats from dump1090 in a form
suitable for feeding to mrtg.

Sample config:

````
Target[nw_dump1090_messages]: `/usr/local/bin/fetch-dump1090-message-count.sh http://rpi.lxi:8081`
Title[nw_dump1090_messages]: NW antenna dump1090 messages
MaxBytes[nw_dump1090_messages]: 5000
Options[nw_dump1090_messages]: noo, nopercent
YLegend[nw_dump1090_messages]: messages/s
ShortLegend[nw_dump1090_messages]:
LegendI[nw_dump1090_messages]: messages/second:
kMG[nw_dump1090_messages]:

Target[nw_dump1090_aircraft]: `/usr/local/bin/fetch-dump1090-aircraft-count.sh http://rpi.lxi:8081`
Title[nw_dump1090_aircraft]: NW antenna aircraft seen
MaxBytes[nw_dump1090_aircraft]: 500
Options[nw_dump1090_aircraft]: gauge, nopercent
YLegend[nw_dump1090_aircraft]: aircraft
ShortLegend[nw_dump1090_aircraft]:
LegendI[nw_dump1090_aircraft]: aircraft seen:
LegendO[nw_dump1090_aircraft]: aircraft with positions seen:
kMG[nw_dump1090_aircraft]:

Target[nw_dump1090_range]: `/usr/local/bin/fetch-dump1090-max-range.py http://rpi.lxi:8081`
Title[nw_dump1090_range]: NW antenna range
MaxBytes[nw_dump1090_range]: 300
Options[nw_dump1090_range]: noo, gauge, nopercent
YLegend[nw_dump1090_range]: range (NM)
ShortLegend[nw_dump1090_range]:
LegendI[nw_dump1090_range]: range (NM):
kMG[nw_dump1090_range]:
````
