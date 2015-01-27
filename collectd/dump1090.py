import collectd
import json, math
from contextlib import closing
from urllib2 import urlopen
import urlparse

def handle_config(root):
    for child in root.children:
        instance_name = None

        if child.key == 'Instance':
            instance_name = child.values[0]
            url = None
            for ch2 in child.children:
                if ch2.key == 'URL':
                    url = ch2.values[0]
            if not url:
                collectd.warning('No URL found in dump1090 Instance ' + instance_name)
            else:
                collectd.register_read(callback=handle_read,
                                       data=(instance_name, urlparse.urlparse(url).hostname, url),
                                       name='dump1090.' + instance_name)
                collectd.register_read(callback=handle_read_1min,
                                       data=(instance_name, urlparse.urlparse(url).hostname, url),
                                       name='dump1090.' + instance_name + '.1min',
                                       interval=60)

        else:
            collectd.warning('Ignored config entry: ' + child.key)
        
V=collectd.Values(host='', plugin='dump1090', time=0)

def handle_read(data):
    instance_name,host,url = data

    read_stats(instance_name, host, url)
    read_aircraft(instance_name, host, url)

def handle_read_1min(data):
    instance_name,host,url = data
    read_stats_1min(instance_name, host, url);
    
def read_stats_1min(instance_name, host, url):
    with closing(urlopen(url + '/data/stats.json', None, 5.0)) as stats_file:
        stats = json.load(stats_file)

    # Signal measurements - from the 1 min bucket
    if stats['last1min'].has_key('local'):
        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_dbfs',
                   type_instance='signal',
                   time=stats['last1min']['end'],
                   values = [stats['last1min']['local']['signal']],
                   interval = 60)

        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_dbfs',
                   type_instance='peak_signal',
                   time=stats['last1min']['end'],
                   values = [stats['last1min']['local']['peak_signal']],
                   interval = 60)
    
        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_messages',
                   type_instance='strong_signals',
                   time=stats['last1min']['end'],
                   values = [stats['last1min']['local']['strong_signals']],
                   interval = 60)


def read_stats(instance_name, host, url):
    with closing(urlopen(url + '/data/stats.json', None, 5.0)) as stats_file:
        stats = json.load(stats_file)

    # Local message counts
    if stats['total'].has_key('local'):
        counts = stats['total']['local']['accepted']
        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_messages',
                   type_instance='local_accepted',
                   time=stats['total']['end'],
                   values = [sum(counts)])
        for i in xrange(len(counts)):
            V.dispatch(plugin_instance = instance_name,
                       host=host,
                       type='dump1090_messages',
                       type_instance='local_accepted_%d' % i,
                       time=stats['total']['end'],
                       values = [counts[i]])

    # Remote message counts
    if stats['total'].has_key('remote'):
        counts = stats['total']['remote']['accepted']
        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_messages',
                   type_instance='remote_accepted',
                   time=stats['total']['end'],
                   values = [sum(counts)])
        for i in xrange(len(counts)):
            V.dispatch(plugin_instance = instance_name,
                       host=host,
                       type='dump1090_messages',
                       type_instance='remote_accepted_%d' % i,
                       time=stats['total']['end'],
                       values = [counts[i]])

    # CPU
    for k in stats['total']['cpu'].keys():
        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_cpu',
                   type_instance=k,
                   time=stats['total']['end'],
                   values = [stats['total']['cpu'][k]])

def greatcircle(lat0, lon0, lat1, lon1):
    lat0 = lat0 * math.pi / 180.0;
    lon0 = lon0 * math.pi / 180.0;
    lat1 = lat1 * math.pi / 180.0;
    lon1 = lon1 * math.pi / 180.0;
    return 6371e3 * math.acos(math.sin(lat0) * math.sin(lat1) + math.cos(lat0) * math.cos(lat1) * math.cos(abs(lon0 - lon1)))

def read_aircraft(instance_name, host, url):
    with closing(urlopen(url + '/data/receiver.json', None, 5.0)) as receiver_file:
        receiver = json.load(receiver_file)

    if receiver.has_key('lat'):
        rlat = float(receiver['lat'])
        rlon = float(receiver['lon'])
    else:
        rlat = rlon = None

    with closing(urlopen(url + '/data/aircraft.json', None, 5.0)) as aircraft_file:
        aircraft_data = json.load(aircraft_file)

    total = 0
    with_pos = 0
    max_range = 0
    for a in aircraft_data['aircraft']:
        if a['seen'] < 15: total += 1        
        if a.has_key('seen_pos') and a['seen_pos'] < 15:
            with_pos += 1
            if rlat is not None:
                distance = greatcircle(rlat, rlon, a['lat'], a['lon'])
                if distance > max_range: max_range = distance

    V.dispatch(plugin_instance = instance_name,
               host=host,
               type='dump1090_aircraft',
               type_instance='recent',
               time=aircraft_data['now'],
               values = [total, with_pos])

    if max_range > 0:
        V.dispatch(plugin_instance = instance_name,
                   host=host,
                   type='dump1090_range',
                   type_instance='max_range',
                   time=aircraft_data['now'],
                   values = [max_range])
        

collectd.register_config(callback=handle_config, name='dump1090')

