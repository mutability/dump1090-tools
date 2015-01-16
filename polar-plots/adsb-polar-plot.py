#!/usr/bin/env python

import csv, math, os
from contextlib import closing
from PIL import Image, ImageDraw, ImageFont

data = []
max_rate = 0.0
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
            data.append( (b_start, b_end, r_start, r_end, rate) )
            max_rate = max(max_rate, rate)

data.append( (0,0,0,0,0) )
data.sort(lambda x,y: cmp( (y[3],x[0],y[2]), (x[3],y[0],x[2]) ) )

for s_start, s_end, r_start, r_end, rate in data:
    if rate > 1.0:
        max_range = r_end
        break

max_range = 360000.0
max_rate = 2.0

def color_for(x):
    if x == 0.0:
        return 'black'
    else:
        if x < 0.1: intensity = 0
        else: intensity = (1.0 * x / max_rate) ** 0.8
        return "hsl(%d,%d%%,%d%%)" % (0 + int(0 + intensity * 180), 100, int(30 + intensity*50))    

SIZE = 800
SCALE = ((SIZE-10) / max_range / 2)
CENTER = SIZE/2
im = Image.new("RGB", (SIZE + 730,SIZE), "black")

draw = ImageDraw.Draw(im)

last_r_start = data[0][2]
last_r_end = data[0][3]
last_s_end = None
for s_start, s_end, r_start, r_end, rate in data:
    if r_end != last_r_end:
        # finish partial ring
        # if last_s_end is not None:
        #     bounds = (int(CENTER - last_r_end * SCALE),
        #               int(CENTER - last_r_end * SCALE),
        #               int(CENTER + last_r_end * SCALE),
        #               int(CENTER + last_r_end * SCALE))        
        #     draw.pieslice(bounds, int(last_s_end-90), int(360-90), fill = '#101010')
        
        # clear inner part
        bounds = (int(CENTER - last_r_start * SCALE),
                  int(CENTER - last_r_start * SCALE),
                  int(CENTER + last_r_start * SCALE),
                  int(CENTER + last_r_start * SCALE))        
        draw.ellipse(bounds, fill = '#101010')

        last_r_start = r_start
        last_r_end = r_end
        last_s_end = None

    # if last_s_end is not None and s_start != last_s_end:
    #     bounds = (int(CENTER - r_end * SCALE),
    #               int(CENTER - r_end * SCALE),
    #               int(CENTER + r_end * SCALE),
    #               int(CENTER + r_end * SCALE))        
    #     draw.pieslice(bounds, int(last_s_end-90), int(s_start-90), fill = '#101010')

    bounds = (int(CENTER - r_end * SCALE),
              int(CENTER - r_end * SCALE),
              int(CENTER + r_end * SCALE),
              int(CENTER + r_end * SCALE))        
    draw.pieslice(bounds, int(s_start - 90), int(s_end-90), fill = color_for(rate))
    last_s_end = s_end

font = ImageFont.load_default()
for r in xrange(0, int(max_range) + 100000, 100000):
    bounds = (int(CENTER - r * SCALE),
              int(CENTER - r * SCALE),
              int(CENTER + r * SCALE),
              int(CENTER + r * SCALE))
    draw.ellipse(bounds, outline="#FFFFFF")

    if r > 0:
        text = '%.0f km' % (r/1000.0)
        size = font.getsize(text)
        draw.text((CENTER + 5, CENTER - r * SCALE - 5 - size[1]), text, font=font, fill="#FFFFFF")

text1 = 'Rate: 0'
size1 = font.getsize(text1)
text2 = '%.1f updates/s/aircraft' % max_rate
size2 = font.getsize(text2)

draw.text((5, 5), text1)
draw.text((5 + size1[0] + 5 + 102 + 5, 5), text2)
draw.rectangle((5 + size1[0] + 5, 5, 5 + size1[0] + 5 + 101, 5 + size1[1]), outline='#FFFFFF')
for i in xrange(0,100):
    c = i * max_rate / 100
    draw.line((5 + size1[0] + 5 + 1 + i, 6, 5 + size1[0] + 5 + 1 + i, 4 + size1[1]), fill=color_for(c))

edata = []
min_elev = -5.0
max_elev = 0
with closing(open('polar_elev.csv', 'r')) as f:
    r = csv.reader(f)
    r.next() # header
    for row in r:
        b_start = float(row[0])
        b_end = float(row[1])
        e_start = float(row[2])
        e_end = float(row[3])
        count = float(row[4])
        unique = float(row[5])
        if unique > 0:
            rate = count / unique
        else:
            rate = 0.0

        if rate > 0:
            edata.append( (b_start, b_end, e_start, e_end, rate) )
            max_elev = max(e_end, max_elev)
            min_elev = min(e_start, min_elev)

min_elev = -5.0
max_elev = 90.0

ESCALE = -1.0 * SIZE / (max_elev - min_elev)
EZERO = int(-1.0 * max_elev * ESCALE)

draw.rectangle( (SIZE,0,SIZE+730,SIZE), fill='black' )

for i in xrange(0,361,30):
    draw.line( (SIZE+5+i*2,
                EZERO+int(ESCALE*min_elev),
                SIZE+5+i*2,
                EZERO+int(ESCALE*max_elev)),
               fill='#202020' )

i = 0.0
while i < max_elev:
    draw.line( (SIZE+5,
                EZERO+int(ESCALE*i),
                SIZE+725,
                EZERO+int(ESCALE*i)),
               fill='#202020' )
    i += 5.0

i = 0.0
while i > min_elev:
    draw.line( (SIZE+5,
                EZERO+int(ESCALE*i),
                SIZE+725,
                EZERO+int(ESCALE*i)),
               fill='#202020' )
    i -= 5.0

for bs, be, es, ee, rate in edata:
    x1 = int(bs)*2 + SIZE+5
    x2 = int(be)*2 + SIZE+5
    y1 = EZERO + int(ESCALE * es)
    y2 = EZERO + int(ESCALE * ee)
    
    draw.rectangle( (x1,y1,x2,y2), fill=color_for(rate) )

draw.line( (SIZE+5,EZERO,SIZE+725,EZERO), fill='white' )
for i in xrange(0,361,30):
    draw.line( (SIZE+5+i*2,EZERO,SIZE+5+i*2,EZERO+5), fill='white' )
    text = '%03d' % i
    size = font.getsize(text)
    draw.text((SIZE+5+i*2 - size[0]/2, EZERO+10), text)


del draw

#im.save("polar-new.png")
#os.rename("polar-new.png", "polar.png")
im.save("polar.png")
