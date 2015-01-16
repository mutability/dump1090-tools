#!/usr/bin/env python

import csv, math, os, sys
import cairo, colorsys
from contextlib import closing

data = []
max_range = 0.0

with closing(open('polar_range.csv', 'r')) as f:
    r = csv.reader(f)
    r.next() # header
    for row in r:
        b_start = float(row[0])
        b_end = float(row[1])
        r_start = float(row[2])
        r_end = float(row[3])
        updates = float(row[4])
        airsec = float(row[5])
        if airsec > 2.0:
            rate = float(updates) / airsec
        else:
            rate = 0.0

        if rate > 0:
            data.append( ( (b_start-90) * math.pi / 180.0, (b_end-90) * math.pi / 180.0, r_start, r_end, rate) )
            max_range = max(max_range, r_end)

SIZE = 800

max_range = 400000.0
max_rate = 2.0
def color_for(x):
    if x < 0.1: intensity = 0
    else: intensity = (1.0 * x / max_rate) ** 0.8

    h = intensity * 0.5
    s = 1.0
    l = 0.3 + intensity*0.5
    r,g,b = colorsys.hls_to_rgb(h,l,s)
    return cairo.SolidPattern(r,g,b,1.0)

surface = cairo.ImageSurface(cairo.FORMAT_RGB24, SIZE, SIZE)
cc = cairo.Context(surface)

cc.translate(SIZE/2, SIZE/2)
cc.scale(SIZE/2 / max_range, SIZE/2 / max_range)

one_pixel = min( cc.device_to_user_distance(1.0, 1.0) )

cc.set_source_rgb(1.0,1.0,1.0)
cc.set_antialias(cairo.ANTIALIAS_DEFAULT);
cc.set_font_size(10 * one_pixel)
for r in xrange(0, int(max_range) + 100000, 100000):
    cc.new_path()
    cc.set_line_width(one_pixel)
    cc.arc(0, 0, r, 0, math.pi*2)
    cc.stroke()

    if r > 0:
        text = ' %.0f km' % (r/1000.0)
        t_xb,t_yb,t_w,t_h,t_xa,t_ya = cc.text_extents(text)
        cc.new_path()
        cc.set_line_width(2 * one_pixel)
        cc.move_to(t_xb, -r + t_yb)
        cc.show_text(text)

for i in xrange(16):
    a = 22.5*i
    acos = math.cos(a * math.pi / 180.0)
    asin = math.sin(a * math.pi / 180.0)

    cc.new_path()
    if i % 2 == 0:
        cc.set_line_width(one_pixel)
    else:
        cc.set_line_width(0.5 * one_pixel)
    cc.move_to(0.1 * max_range * acos, 0.1 * max_range * asin)
    cc.line_to(2 * max_range * acos, 2 * max_range * asin)
    cc.stroke()

cc.set_antialias(cairo.ANTIALIAS_NONE);
for s_start, s_end, r_start, r_end, rate in data:
    if rate == 0.0: continue

    cc.new_path()
    cc.move_to(r_end * math.cos(s_start), r_end * math.sin(s_start))
    cc.arc(0, 0, r_end, s_start, s_end)
    cc.arc_negative(0, 0, r_start, s_end, s_start)
    cc.close_path()
    cc.set_source(color_for(rate))
    cc.fill()

if len(sys.argv) > 1:
    cc.identity_matrix()
    cc.set_source_rgb(1.0,1.0,1.0)
    cc.set_antialias(cairo.ANTIALIAS_DEFAULT);
    cc.set_font_size(10)
    cc.set_line_width(1)

    text = sys.argv[1]
    t_xb,t_yb,t_w,t_h,t_xa,t_ya = cc.text_extents(text)
    cc.new_path()
    cc.move_to(5 - t_xb,5 - t_yb)
    cc.show_text(text)

surface.write_to_png("polar.png")
