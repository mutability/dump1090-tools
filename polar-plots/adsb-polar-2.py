#!/usr/bin/env python

import math, csv, os, time, traceback
from contextlib import closing

WGS84_A = 6378137.0
WGS84_F =  1.0/298.257223563;
WGS84_B = WGS84_A * (1 - WGS84_F)
WGS84_ECC_SQ = 1 - WGS84_B * WGS84_B / (WGS84_A * WGS84_A)
WGS84_ECC = math.sqrt(WGS84_ECC_SQ)
MEAN_R = 6371009.0

ABSOLUTE_MAXIMUM_RANGE = 500000.0
ABSOLUTE_MINIMUM_ELEVATION = -5.0

def dtor(d):
    return d * math.pi / 180.0

def rtod(r):
    return r * 180.0 / math.pi

def ft_to_m(ft):
    return ft * 0.3048

def latlngup_to_ecef(l):
    "Converts L from WGS84 lat/long/up to ECEF"
    
    lat = dtor(l[0])
    lng = dtor(l[1])
    alt = l[2]

    slat = math.sin(lat)
    slng = math.sin(lng)
    clat = math.cos(lat)
    clng = math.cos(lng)

    d = math.sqrt(1 - (slat * slat * WGS84_ECC_SQ))
    rn = WGS84_A / d

    x = (rn + alt) * clat * clng
    y = (rn + alt) * clat * slng
    z = (rn * (1 - WGS84_ECC_SQ) + alt) * slat

    return (x,y,z)

def latlngup_to_relxyz(c,l):
    # this converts WGS84 (lat,lng,alt) to a rotated ECEF frame
    # where the earth center is still at the origin
    # but (clat,clng,calt) has been rotated to lie on the positive X axis

    clat,clng,calt = c
    llat,llng,lalt = l

    # rotate by -clng around Z to put C on the X/Z plane
    # (this is easy to do while still in WGS84 coordinates)
    llng = llng - clng

    # find angle between XY plane and C
    cx,cy,cz = latlngup_to_ecef((clat,0,calt))
    a = math.atan2(cz,cx)

    # convert L to (rotated around Z) ECEF
    lx,ly,lz = latlngup_to_ecef((llat,llng,lalt))

    # rotate by -a around Y to put C on the X axis
    asin = math.sin(-a)
    acos = math.cos(-a)
    rx = lx * acos - lz * asin
    rz = lx * asin + lz * acos

    return (rx, ly, rz)

# great circle distance from C to L, assuming spherical geometry (~0.3% error)
# from http://www.movable-type.co.uk/scripts/latlong.html ("haversine formula")
def gc_distance(c,l):
    # great circle distance (assumes spherical geometry!)
    lat1 = dtor(c[0])
    lat2 = dtor(l[0])
    delta_lat = lat2 - lat1
    delta_lon = dtor(c[1] - l[1])

    a = math.sin(delta_lat/2) * math.sin(delta_lat/2) + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon/2) * math.sin(delta_lon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return MEAN_R * c

def range_bearing_elevation_from(c):
    # build a function that calculates ranges, bearing, elevation from C
    clat,clng,calt = c

    # rotate by -clng to put C on the XZ plane
    # find angle between XY plane and C
    cx,cy,cz = latlngup_to_ecef((clat,0,calt))
    a = math.atan2(cz,cx)
    
    # rotate by -a around Y to put C on the X axis
    asin = math.sin(-a)
    acos = math.cos(-a)

    crx = cx * acos - cz * asin
    cry = cy                         # should be zero
    crz = cx * asin + cz * acos      # should be zero

    def rbe(l):
        # rotate L into our new reference frame
        llat,llng,lalt = l
        # rotate by -clng, convert to ECEF
        lx,ly,lz = latlngup_to_ecef((llat,llng - clng,lalt))

        # rotate by -a around Y
        lrx = lx * acos - lz * asin
        lry = ly
        lrz = lx * asin + lz * acos

        # Now we have cartesian coordinates with C on
        # the +X axis, ground plane YZ, north along +Z.

        dx, dy, dz = lrx-crx, lry-cry, lrz-crz
        slant = math.sqrt(dx*dx + dy*dy + dz*dz)             # true line-of-sight range
        bearing = (360 + 90 - rtod(math.atan2(dz,dy))) % 360 # bearing around X axis
        elev = rtod(math.asin(dx / slant))                   # elevation from horizon (YZ plane)
        horiz_range = math.sqrt(dy*dy + dz*dz)               # distance projected onto YZ (ground/horizon plane); something like ground distance if the Earth was flat
        return (slant, horiz_range, bearing, elev, (lrx,lry,lrz))

    return rbe

# calculate true range, bearing, elevation from C to L
def range_bearing_elevation(c,l):
    # rotate C onto X axis
    crx, cry, crz = latlngup_to_relxyz(c,c)
    # rotate L in the same way
    lrx, lry, lrz = latlngup_to_relxyz(c,l)

    # Now we have cartesian coordinates with C on
    # the +X axis, ground plane YZ, north along +Z.

    dx, dy, dz = lrx-crx, lry-cry, lrz-crz
    slant = math.sqrt(dx*dx + dy*dy + dz*dz)             # true line-of-sight range
    bearing = (360 + 90 - rtod(math.atan2(dz,dy))) % 360 # bearing around X axis
    elev = rtod(math.asin(dx / slant))                   # elevation from horizon (YZ plane)
    horiz_range = math.sqrt(dy*dy + dz*dz)               # distance projected onto YZ (ground/horizon plane); something like ground distance if the Earth was flat
    return (slant, horiz_range, bearing, elev, (lrx,lry,lrz))

class BinHisto:
    def __init__(self, n_bins, min_bin_value, max_bin_value):
        self.n_bins = n_bins
        self.min_bin = min_bin_value
        self.update_bins = [0] * n_bins
        self.airsec_bins = [0] * n_bins
        self.bin_size = float(max_bin_value - min_bin_value) / n_bins

    def bin_start(self, n):
        return self.min_bin + n * self.bin_size

    def bin_end(self, n):
        return self.bin_start(n+1)

    def bin_for(self, v):
        return int((v-self.min_bin) / self.bin_size)

    def add(self, v, add_updates, add_airsec):
        i = self.bin_for(v)
        if i < 0 or i >= self.n_bins: return
        self.update_bins[i] += add_updates
        self.airsec_bins[i] += add_airsec

    def values(self):
        return ( (self.bin_start(i), self.bin_end(i), self.update_bins[i], self.airsec_bins[i]) for i in xrange(self.n_bins) )

    def write(self, filename):
        with closing(open(filename + '.new', 'w')) as w:
            c = csv.writer(w)
            c.writerow(['bin_start','bin_end','updates','airsec'])
            for low, high, updates, airsec in self.values():
                if updates > 0 or airsec > 0:
                    c.writerow(['%.2f' % low,
                                '%.2f' % high,
                                '%.2f' % updates,
                                '%.2f' % airsec])
        os.rename(filename + '.new', filename)

    def import_bin(self, low, high, updates, airsec):
        firstbin = max(0, self.bin_for(low))
        lastbin = min(self.n_bins, self.bin_for(high) + 1)

        for i in xrange(firstbin, lastbin):
            if high-low < 1e-6: break
            low_val = max(self.bin_start(i), low)
            high_val = min(self.bin_end(i), high)
            fraction = (high_val - low_val) / (high - low)
            frac_updates = fraction * updates
            frac_airsec = fraction * airsec
            self.update_bins[i] += frac_updates
            self.airsec_bins[i] += frac_airsec
            updates -= frac_updates
            airsec -= frac_airsec
            low = high_val

    def read(self, filename):
        with closing(open(filename, 'r')) as r:
            csvfile = csv.reader(r)
            csvfile.next() # skip header
            for row in csvfile:
                low = float(row[0])
                high = float(row[1])
                updates = float(row[2])
                airsec = float(row[3])

                self.import_bin(low, high, updates, airsec)

class PolarHisto:
    def __init__(self, n_sectors, n_bins, min_value, max_value):
        self.n_sectors = n_sectors
        self.sector_size = 360.0 / n_sectors
        self.sectors = [BinHisto(n_bins, min_value, max_value) for i in xrange(n_sectors)]

    def sector_start(self,i):
        return self.sector_size * i

    def sector_end(self,i):
        return self.sector_size * (i+1)

    def sector_for(self,v):
        return int( (v % 360) / self.sector_size )

    def add(self, bearing, h, updates, airsec):
        sector = self.sector_for(bearing)
        self.sectors[sector].add(h, updates, airsec)

    def values(self):
        return ( (self.sector_start(i), self.sector_end(i), self.sectors[i]) for i in xrange(self.n_sectors) )

    def write(self, filename):
        with closing(open(filename + '.new', 'w')) as w:
            c = csv.writer(w)
            c.writerow(['bearing_start','bearing_end','bin_start','bin_end','updates','airsec'])
            for b_low,b_high,histo in self.values():
                for h_low,h_high,updates,airsec in histo.values():
                    if updates > 0 or airsec > 0:
                        c.writerow(['%.2f' % b_low,
                                    '%.2f' % b_high,
                                    '%.2f' % h_low,
                                    '%.2f' % h_high,
                                    '%.2f' % updates,
                                    '%.2f' % airsec])
        os.rename(filename + '.new', filename)

    def import_sector(self, b_low, b_high, h_low, h_high, updates, airsec):
        firstsect = max(0, self.sector_for(b_low))
        lastsect = min(self.n_sectors, self.sector_for(b_high) + 1)
        if lastsect <= firstsect: lastsect = self.n_sectors  # handle 360->0 wrap

        for i in xrange(firstsect, lastsect):
            if b_high - b_low < 1e-6: break
            
            low_val = max(self.sector_start(i), b_low)
            high_val = min(self.sector_end(i), b_high)
            fraction = (high_val - low_val) / (b_high - b_low)
            frac_updates = fraction * updates
            frac_airsec = fraction * airsec
            self.sectors[i].import_bin(h_low, h_high, frac_updates, frac_airsec)
            updates -= frac_updates
            airsec -= frac_airsec
            b_low = high_val

    def read(self, filename):
        with closing(open(filename, 'r')) as r:
            csvfile = csv.reader(r)
            csvfile.next() # skip header
            for row in csvfile:
                b_low = float(row[0])
                b_high = float(row[1])
                h_low = float(row[2])
                h_high = float(row[3])                
                updates = float(row[4])
                airsec = float(row[5])
                self.import_sector(b_low, b_high, h_low, h_high, updates, airsec)

class MultiPolarRangeHisto:
    def __init__(self, range_list):
        self.ranges = []
        for start_range, end_range, sector_res, range_res in range_list:
            assert end_range > start_range
            self.ranges.append( (start_range, end_range, PolarHisto(int(math.ceil(360.0/sector_res)),
                                                                    int(math.ceil((end_range - start_range) / range_res)),
                                                                    start_range,
                                                                    end_range)) )
            self.ranges.sort()

    def add(self, bearing, r, updates, airsec):
        for start_range, end_range, histo in self.ranges:
            if r >= start_range and r < end_range:
                histo.add(bearing, r, updates, airsec)
                return

    def write(self, filename):
        with closing(open(filename + '.new', 'w')) as w:
            c = csv.writer(w)
            c.writerow(['bearing_start','bearing_end','bin_start','bin_end','updates','airsec'])
            for sr,er,h in self.ranges:
                for b_low,b_high,histo in h.values():
                    for h_low,h_high,updates,airsec in histo.values():
                        if updates > 0 or airsec > 0:
                            c.writerow(['%.2f' % b_low,
                                        '%.2f' % b_high,
                                        '%.2f' % h_low,
                                        '%.2f' % h_high,
                                        '%.2f' % updates,
                                        '%.2f' % airsec])
        os.rename(filename + '.new', filename)

    def import_sector(self, b_low, b_high, h_low, h_high, updates, airsec):
        for sr,er,h in self.ranges:
            if h_low >= sr or h_high <= er:
                low_val = max(sr, h_low)
                high_val = min(er, h_high)
                fraction = (high_val - low_val) / (h_high - h_low)
                frac_updates = fraction * updates
                frac_airsec = fraction * airsec
                h.import_sector(b_low, b_high, low_val, high_val, frac_updates, frac_airsec)
                updates -= frac_updates
                airsec -= frac_airsec
                h_low = high_val

    def read(self, filename):
        with closing(open(filename, 'r')) as r:
            csvfile = csv.reader(r)
            csvfile.next() # skip header
            for row in csvfile:
                b_low = float(row[0])
                b_high = float(row[1])
                h_low = float(row[2])
                h_high = float(row[3])                
                updates = float(row[4])
                airsec = float(row[5])
                self.import_sector(b_low, b_high, h_low, h_high, updates, airsec)    

class aircraft(object):
    pass

def process_basestation_messages(home, f):
    count = 0
    #range_histo = BinHisto(220, 0, 440000)

    # this sets up approx 2km x 2km bins out to 400km
    # XX why don't I just use 2km x 2km square grid?
    polar_range_histo = MultiPolarRangeHisto([ (0, 40000, 2.86, 2000),
                                               (40000, 60000, 1.91, 2000),
                                               (60000, 80000, 1.43, 2000),
                                               (80000, 100000, 1.15, 2000),
                                               (100000, 150000, 0.76, 2000),
                                               (150000, 200000, 0.57, 2000),
                                               (200000, 250000, 0.46, 2000),
                                               (250000, 300000, 0.38, 2000),
                                               (300000, 350000, 0.33, 2000),
                                               (350000, 400000, 0.29, 2000) ])

    polar_elev_histo = MultiPolarRangeHisto([ (-15.0,  15.0, 1.00, 0.25),
                                              ( 15.0,  20.0, 1.20, 0.30),
                                              ( 20.0,  25.0, 1.40, 0.35),
                                              ( 25.0,  30.0, 1.60, 0.40),
                                              ( 30.0,  35.0, 1.80, 0.45),
                                              ( 35.0,  40.0, 2.00, 0.50),
                                              ( 40.0,  45.0, 2.20, 0.55),
                                              ( 45.0,  60.0, 2.40, 0.60),
                                              ( 60.0,  65.0, 2.60, 0.65),
                                              ( 65.0,  70.0, 2.80, 0.70),
                                              ( 70.0,  75.0, 3.00, 0.75),
                                              ( 75.0,  80.0, 3.20, 0.80),
                                              ( 80.0,  85.0, 3.40, 0.85),
                                              ( 85.0,  90.0, 3.60, 0.90) ])

    rbe_from_home = range_bearing_elevation_from(home)

    #try: range_histo.read('range.csv')
    #except: traceback.print_exc()

    try: polar_range_histo.read('polar_range.csv')
    except: traceback.print_exc()

    try: polar_elev_histo.read('polar_elev.csv')
    except: traceback.print_exc()

    current_aircraft = {}
    last_save = time.time()
    last_reset = 0
    recent_updates = 0

    c = csv.reader(f, delimiter=',')
    for row in c:
        if row[0] != 'MSG': continue
        if row[1] != '3': continue

        try:
            icao = row[4]
            alt_ft = float(row[11])
            alt_m = ft_to_m(alt_ft)
            lat = float(row[14])
            lng = float(row[15])            
        except:
            continue
        
        timestamp_string = row[8] + ' ' + row[9]
        base_timestamp, millis = timestamp_string.split('.')
        update_timestamp = time.mktime(time.strptime(base_timestamp, '%Y/%m/%d %H:%M:%S')) + int(millis)/1000.0

        tr,hr,b,e,l = rbe_from_home((lat,lng,alt_m))

        # horiz_range is approx equal to great circle distance for the small angles we will deal with:
        # difference is (tan(x)/x - 1) (about 1% at 10 degrees)
        # 
        # This seems to work well both at short range (where using line-of-sight distance would cause a zero-offset
        # due to altitude) and long range (where the signals are close to the horizon, and using great circle distance
        # would add an unwanted curvature effect)

        r = hr

        ac = current_aircraft.get(icao)
        if not ac:
            current_aircraft[icao] = ac = aircraft()
            aircraft.last = update_timestamp
            aircraft.range = r
            aircraft.bearing = b
            aircraft.elevation = e
            aircraft.position_xyz = l
            aircraft.position_llu = (lat,lng,alt_ft)
            aircraft.blacklist = None

        if r > ABSOLUTE_MAXIMUM_RANGE or e < ABSOLUTE_MINIMUM_ELEVATION:
            if not ac.blacklist:
                print "contact with improbable position, blacklisting: %s %s @ %.3f,%.3f,%.0f range %.1fkm elevation %.1f" % (timestamp_string, icao, lat, lng, alt_ft, r/1000.0, e)
            ac.blacklist = update_timestamp + 60

        elapsed = update_timestamp - ac.last
        if elapsed > 0:
            dx = l[0] - ac.position_xyz[0]
            dy = l[1] - ac.position_xyz[1]
            dz = l[2] - ac.position_xyz[2]
            moved = math.sqrt(dx*dx+dy*dy+dz*dz)
            if (elapsed > 4.0 or moved > 2000.0) and moved / elapsed > 500.0:   # 500m/s, about 970 knots
                if not ac.blacklist:
                    print "contact with improbable speed, blacklisting: %s %s @ %.3f,%.3f,%.0f -> %.3f,%.3f,%.0f moved %.1fkm at %.1fm/s" % (timestamp_string, icao, ac.position_llu[0], ac.position_llu[1], ac.position_llu[2], lat, lng, alt_ft, moved/1000.0, moved/elapsed)
                ac.blacklist = update_timestamp + 60

            if not ac.blacklist:
                #range_histo.add(ac.range, 1, elapsed)
                polar_range_histo.add(ac.bearing, ac.range, 1, elapsed)
                polar_elev_histo.add(ac.bearing, ac.elevation, 1, elapsed)

        if ac.blacklist and ac.blacklist < update_timestamp:
            print "un-blacklisting", timestamp_string, icao
            ac.blacklist = None

        ac.last = update_timestamp
        ac.range = r
        ac.bearing = b
        ac.elevation = e
        ac.position_xyz = l
        ac.position_llu = (lat,lng,alt_ft)
        recent_updates += 1
    
        if (update_timestamp - last_reset) > 30.0:
            last_reset = update_timestamp
            for icao, ac in current_aircraft.items():
                if (update_timestamp - ac.last) > 30.0:
                    # expire it.
                    # note that we still have to add 1 update to account for the initial update
                    # that hasn't been added yet.

                    if not ac.blacklist:
                        elapsed = 30.0 # always assume 30, even if we noticed it late
                        #range_histo.add(ac.range, 1, elapsed)
                        polar_range_histo.add(ac.bearing, ac.range, 1, elapsed)
                        polar_elev_histo.add(ac.bearing, ac.elevation, 1, elapsed)
                        
                    del current_aircraft[icao]

        now = time.time()
        if (now - last_save) > 30.0:
            print 'Active aircraft: %d   Update rate: %.1f/s' % (len(current_aircraft), recent_updates / (now - last_save))
            recent_updates = 0
            last_save = now

            #range_histo.write('range.csv')
            polar_range_histo.write('polar_range.csv')
            polar_elev_histo.write('polar_elev.csv')
            
    #range_histo.write('range.csv')
    polar_range_histo.write('polar_range.csv')
    polar_elev_histo.write('polar_elev.csv')

if __name__ == '__main__':
    import sys

    home = (52.2, 0.1, 20)
    process_basestation_messages(home, sys.stdin)

