#!/usr/bin/env python

import math, csv, os, time, traceback
from contextlib import closing

WGS84_A = 6378137.0
WGS84_F =  1.0/298.257223563;
WGS84_B = WGS84_A * (1 - WGS84_F)
WGS84_ECC_SQ = 1 - WGS84_B * WGS84_B / (WGS84_A * WGS84_A)
WGS84_ECC = math.sqrt(WGS84_ECC_SQ)

ABSOLUTE_MAXIMUM_RANGE = 500000.0

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

# calculate range, bearing, elevation from C to L
def range_bearing_elevation(c,l):
    # rotate C onto X axis
    crx, cry, crz = latlngup_to_relxyz(c,c)
    # rotate L in the same way
    lrx, lry, lrz = latlngup_to_relxyz(c,l)

    # Now we have cartesian coordinates with C on
    # the X axis with ground plane YZ and north along +Z.

    dx, dy, dz = lrx-crx, lry-cry, lrz-crz
    rng = math.sqrt(dx*dx + dy*dy + dz*dz)
    bearing = (360 + 90 - rtod(math.atan2(dz,dy))) % 360
    elev = rtod(math.asin(dx / rng))

    return (rng, bearing, elev)    

class BinHisto:
    def __init__(self, n_bins, min_bin_value, max_bin_value):
        self.min_bin = min_bin_value
        self.bins = [0] * n_bins
        self.bins_unique = [0] * n_bins
        self.icao_seen = [set() for i in xrange(n_bins)]
        self.bin_size = float(max_bin_value - min_bin_value) / n_bins
        self.n = 0
        self.min_value = None
        self.max_value = None

    def bin_start(self, n):
        return self.min_bin + n * self.bin_size

    def bin_end(self, n):
        return self.bin_start(n+1)

    def bin_for(self, v):
        return int((v-self.min_bin) / self.bin_size)

    def bin_for_upper(self, v):
        return int(math.ceil((v-self.min_bin) / self.bin_size))

    def add(self,icao,v):
        i = self.bin_for(v)
        if i < 0 or i >= len(self.bins): return

        if icao not in self.icao_seen[i]:
            self.icao_seen[i].add(icao)
            self.bins_unique[i] += 1

        self.bins[i] += 1
        self.n += 1
        self.max_value = v if self.max_value is None else max(self.max_value, v)
        self.min_value = v if self.min_value is None else min(self.min_value, v)

    def reset_icao_history(self):
        for s in self.icao_seen:
            s.clear()

    def values(self):
        return ( (self.bin_start(i), self.bin_end(i), self.bins[i], self.bins_unique[i]) for i in xrange(len(self.bins)) )

    def write(self, filename):
        with closing(open(filename + '.new', 'w')) as w:
            c = csv.writer(w)
            c.writerow(['bin_start','bin_end','samples','unique'])
            for low, high, count, unique in self.values():
                if unique:
                    c.writerow(['%f' % low,
                                '%f' % high,
                                '%d' % count,
                                '%d' % unique])
        os.rename(filename + '.new', filename)

    def import_bin(self, low, high, count, unique):
        if count > 0:
            self.n += count
            self.min_value = min(self.min_value, low)
            self.max_value = max(self.max_value, high)

            firstbin = max(0, self.bin_for(low))
            lastbin = min(len(self.bins), self.bin_for_upper(high))

            for i in xrange(firstbin, lastbin):
                if low == high: break
                low_val = max(self.bin_start(i), low)
                high_val = min(self.bin_end(i), high)
                fraction = (high_val - low_val) / (high - low)
                frac_count = min(count, int(fraction * count + 0.5))
                frac_unique = min(unique, int(fraction * unique + 0.5))
                self.bins[i] += frac_count
                self.bins_unique[i] += frac_unique
                count -= frac_count
                unique -= frac_unique
                low = high_val

    def read(self, filename):
        with closing(open(filename, 'r')) as r:
            csvfile = csv.reader(r)
            csvfile.next() # skip header
            for row in csvfile:
                low = float(row[0])
                high = float(row[1])
                count = int(row[2])
                unique = int(row[3])

                self.import_bin(low, high, count, unique)

class PolarHisto:
    def __init__(self, n_sectors, n_bins, min_value, max_value):
        self.sector_size = 360.0 / n_sectors
        self.sectors = [BinHisto(n_bins, min_value, max_value) for i in xrange(n_sectors)]
        self.n = 0

    def sector_start(self,i):
        return self.sector_size * i

    def sector_end(self,i):
        return self.sector_size * (i+1)

    def sector_for(self,v):
        return int( (v % 360) / self.sector_size )

    def sector_for_upper(self,v):
        return int(math.ceil((v % 360) / self.sector_size))

    def reset_icao_history(self):
        for histo in self.sectors:
            histo.reset_icao_history()

    def add(self, icao, b, v):
        sector = self.sector_for(b)
        self.sectors[sector].add(icao, v)
        self.n += 1

    def values(self):
        return ( (self.sector_start(i), self.sector_end(i), self.sectors[i]) for i in xrange(len(self.sectors)) )

    def write(self, filename):
        with closing(open(filename + '.new', 'w')) as w:
            c = csv.writer(w)
            c.writerow(['bearing_start','bearing_end','bin_start','bin_end','samples','unique'])
            for b_low,b_high,histo in self.values():
                # make sure we write at least one value per sector,
                # it makes things a little easier when plotting
                first = True
                for h_low,h_high,count,unique in histo.values():
                    if unique or first:
                        c.writerow(['%f' % b_low,
                                    '%f' % b_high,
                                    '%f' % h_low,
                                    '%f' % h_high,
                                    '%d' % count,
                                    '%d' % unique])
                        first = False
        os.rename(filename + '.new', filename)

    def import_sector(self, b_low, b_high, h_low, h_high, count, unique):
        if count > 0:
            self.n += count

            firstsect = max(0, self.sector_for(b_low))
            lastsect = min(len(self.sectors), self.sector_for_upper(b_high))

            for i in xrange(firstsect, lastsect):
                if b_low == b_high: break

                low_val = max(self.sector_start(i), b_low)
                high_val = min(self.sector_end(i), b_high)
                fraction = (high_val - low_val) / (b_high - b_low)
                frac_count = min(count, int(fraction * count + 0.5))
                frac_unique = min(unique, int(fraction * unique + 0.5))
                self.sectors[i].import_bin(h_low, h_high, frac_count, frac_unique)
                count -= frac_count
                unique -= frac_unique
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

                if len(row) > 5:
                    count = int(row[4])
                    unique = int(row[5])
                else:
                    # older format with only count/unique stored
                    count = int( float(row[4]) * 10.0 )
                    unique = 10

                self.import_sector(b_low, b_high, h_low, h_high, count, unique)

def process_basestation_messages(home, f):
    count = 0
    range_histo = BinHisto(110, 0, 440000)
    polar_range_histo = PolarHisto(120, 100, 0, 400000)
    polar_elev_histo = PolarHisto(120, 400, -15.0, 90.0)

    try: range_histo.read('range.csv')
    except: traceback.print_exc()

    try: polar_range_histo.read('polar_range.csv')
    except: traceback.print_exc()

    try: polar_elev_histo.read('polar_elev.csv')
    except: traceback.print_exc()

    last_save = last_reset = time.time()

    c = csv.reader(f, delimiter=',')
    for row in c:
        if row[0] != 'MSG': continue
        if row[1] != '3': continue

        try:
            icao = row[4]
            ts = row[8] + ' ' + row[9]
            alt = ft_to_m(float(row[11]))
            lat = float(row[14])
            lng = float(row[15])
        except:
            continue

        r,b,e = range_bearing_elevation(home, (lat,lng,alt))
        if r > ABSOLUTE_MAXIMUM_RANGE:
            # bad data
            continue

        range_histo.add(icao, r)
        polar_range_histo.add(icao, b, r)
        polar_elev_histo.add(icao, b, e)

        now = time.time()
        if (now - last_save) > 30.0:
            range_histo.write('range.csv')
            polar_range_histo.write('polar_range.csv')
            polar_elev_histo.write('polar_elev.csv')
            last_save = now

        if (now - last_reset) > 5.0:
            range_histo.reset_icao_history()
            polar_range_histo.reset_icao_history()
            polar_elev_histo.reset_icao_history()
            last_reset = now

if __name__ == '__main__':
    import sys

    home = (52.2, 0.1, 20)
    process_basestation_messages(home, sys.stdin)

