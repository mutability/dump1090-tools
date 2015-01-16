#!/usr/bin/env python

import json, math, sys
from urllib2 import urlopen
from contextlib import closing

def greatcircle(lat0, lon0, lat1, lon1):
    lat0 = lat0 * math.pi / 180.0;
    lon0 = lon0 * math.pi / 180.0;
    lat1 = lat1 * math.pi / 180.0;
    lon1 = lon1 * math.pi / 180.0;
    return 6371e3 * math.acos(math.sin(lat0) * math.sin(lat1) + math.cos(lat0) * math.cos(lat1) * math.cos(abs(lon0 - lon1)))

def get_max_range(baseurl):
    with closing(urlopen(baseurl + '/data/receiver.json', None, 5.0)) as f:
        receiver = json.load(f)

        if not (receiver.has_key('lat') and receiver.has_key('lon')):
            return None

        rlat = receiver['lat']
        rlon = receiver['lon']

        maxrange = None
        with closing(urlopen(baseurl + '/data/aircraft.json', None, 5.0)) as f:
            aircraft = json.load(f)
            for ac in aircraft['aircraft']:
                if ac.has_key('seen_pos') and ac['seen_pos'] < 300:
                    alat = ac['lat']
                    alon = ac['lon']
                    distance = greatcircle(rlat, rlon, alat, alon)
                    if maxrange is None or distance > maxrange:
                        maxrange = distance
                        
        return maxrange

if __name__ == '__main__':
    import sys
    baseurl = sys.argv[1]
    maxrange = get_max_range(baseurl)

    if maxrange is None: print 'UNKNOWN'
    else: print '%.1f' % (maxrange / 1852.0)
    print '0'
    print '0'
    print 'dump1090 at ' + baseurl
