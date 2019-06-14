import os
import os.path
import sys
sys.path.append('/Users/nuwan.senaratna/Dropbox/__CODING_PROJECTS_WORK/ColomboLabs/py/utils')

import datetime
import json
import math
import random
import requests
import time

from Cache import Cache

random.seed(1)

API_KEY = <API_KEY>
JS_API_KEY = <JS_API_KEY>
GOOGLE_MAPS_API_URL = 'https://maps.googleapis.com/maps/api/directions/json'

DEPARTURE_TIME_STR = '20190703 170000'
DEPARTURE_TIME = (int)(time.mktime(datetime.datetime.strptime(DEPARTURE_TIME_STR, "%Y%m%d  %H%M%S").timetuple()))

TRAFFIC_MODEL = 'pessimistic'
KEY_PREFIX = '%s_%s' % (DEPARTURE_TIME_STR, TRAFFIC_MODEL)

POINT_NEGOMBO =     [7.2003939, 79.8736949]
POINT_KALUTARA =    [6.5854076, 79.9606362]
POINT_COLOMBO =     [6.927044, 79.861236]
POINT_AVISSAWELLA = [6.9543317, 80.2045736]

POINT_TOWNHALL = [6.9157, 79.8636]
POINT_WTC = [6.936158, 79.842739]
POINT_PARLIAMENT = [6.8868, 79.9187]
POINT_E02_KADUWELA = [6.924035, 79.978809]
POINT_E03_KELANIBRIDGE = [6.956115, 79.883203]

POINT_KIRULA = [6.892504, 79.877055]
POINT_DEHIWALA = [6.851190, 79.866001]
POINT_UOC = [6.901598, 79.861842]

(MIN_LAT, MAX_LAT) = (6.77, 7.08)
(MIN_LON, MAX_LON) = (79.82, 80.08)
MID_LAT = (MAX_LAT + MIN_LAT) / 2.0
MID_LON = (MAX_LON + MIN_LON) / 2.0
SPAN_LAT = MAX_LAT - MIN_LAT
SPAN_LON = MAX_LON - MIN_LON

LAT_BOX_COUNT = 24
LON_BOX_COUNT = 16

BOX_SIZE_LAT = SPAN_LAT / LAT_BOX_COUNT
BOX_SIZE_LON = SPAN_LON / LON_BOX_COUNT

def get_travel_info(pointA, pointB):
    def point_to_loc(point):
        (lat, lon) = point
        return '%f,%f' % (lat, lon)

    start = point_to_loc(pointA)
    end = point_to_loc(pointB)
    # print(start, end)

    key = 'get_travel_info_%s_%s_%s' % (KEY_PREFIX, start, end)
    key = key.replace(' ', '')

    def fallback():
        params = {
            'origin': start,
            'destination': end,
            'key': API_KEY,
            'departure_time': DEPARTURE_TIME,
            'traffic_model': TRAFFIC_MODEL,
        }

        response = requests.get(GOOGLE_MAPS_API_URL, params=params)
        data_json = response.content
        data = json.loads(data_json)
        if (data['status'] == 'ZERO_RESULTS'):
            return None
        leg = data['routes'][0]['legs'][0]

        def loc_to_str(loc):
            return '%4.4f,%4.4f' % (loc['lat'], loc['lng'])

        return {
            'startLoc': start,
            'endLoc': end,

            'distance': leg['distance']['value'],
            'duration': leg['duration_in_traffic']['value'],

            'startAddress': leg['start_address'] if 'start_address' in leg else loc_to_str(leg['start_location']) ,
            'endAddress': leg['end_address'] if 'end_address' in leg else loc_to_str(leg['end_location']),

            'startLocation': leg['start_location'],
            'endLocation': leg['end_location'],
        }
    return Cache.get(key, fallback)

def get_random_point():
    return [
        random.random() * SPAN_LAT + MIN_LAT,
        random.random() * SPAN_LON + MIN_LON,
    ]

def get_point(p_lat, p_lon):
    return [
        p_lat * SPAN_LAT + MIN_LAT,
        p_lon * SPAN_LON + MIN_LON,
    ]

def get_travel_info_list(point_center_of_travel=POINT_WTC):
    n_sample_population = 200
    box_weighted_travel_time_map = {}

    startY = [
        3, 2, 3, 2, 2,
        2, 2, 1, 2, 1,
        1, 1, 1, 0, 2,
        2, 3, 2, 2, 2,
        2, 1, 2, 1,
    ]

    travel_info_list = []
    for x in range(0, LAT_BOX_COUNT):
        for y in range(startY[x], LON_BOX_COUNT):
            px = (x + 0.5) * 1.0 / LAT_BOX_COUNT
            py = (y + 0.5 + (x % 2) * 0.5) * 1.0 / LON_BOX_COUNT

            pointA = point_center_of_travel
            pointB = get_point(px, py)
            travel_info = get_travel_info(pointA, pointB)

            if travel_info == None:
                continue
            travel_info['lat'] = pointB[0]
            travel_info['lon'] = pointB[1]

            travel_info_list.append(travel_info)
            print('%d, %d) %s -> %s (%dmin)' % (x, y, travel_info['startAddress'], travel_info['endAddress'], travel_info['duration'] / 60.0))

    render_map(travel_info_list)

def render_box(travel_info):
    lat = travel_info['lat']
    lon = travel_info['lon']

    paths_list = []
    F = (0.94 + math.sqrt(3)) / 2
    for [i, j] in [[-2, 0], [-1, 2], [1, 2], [2, 0], [1, -2], [-1, -2]]:
            paths_list.append('{lat: %f, lng: %f},' % (lat  + F * BOX_SIZE_LAT * i / 4, lon + BOX_SIZE_LON * j / 4))
    paths = '\n'.join(paths_list)

    duration = travel_info['duration']
    duration_min = duration / 60.0
    if duration_min > 120:
        color = 'black'
    elif duration_min > 90:
        color = 'rgb(128, 0, 0)'
    elif duration_min > 60:
        color = 'rgb(255, 0, 0)'
    elif duration_min > 45:
        color = 'orange'
    elif duration_min > 30:
        color = 'yellow'
    elif duration_min > 15:
        color = 'green'
    else:
        color = 'blue'


    return '''
        new google.maps.Polygon({
          paths:  [
            %s
          ],
          strokeWeight: 0,
          fillColor: '%s',
          fillOpacity: 0.4,
        }).setMap(map);
    ''' % (paths, color)


def render_map(travel_info_list):

    rendered_box_list = list(map(
        lambda travel_info: render_box(travel_info),
        travel_info_list,
    ))
    rendered_box_list_str = '\n'.join(rendered_box_list)

    rendered_map = '''

<!DOCTYPE html>
<html>
  <head>
    <title>Simple Map</title>
    <meta name="viewport" content="initial-scale=1.0">
    <meta charset="utf-8">
    <style>
      /* Always set the map height explicitly to define the size of the div
       * element that contains the map. */
      #map {
        height: 100%%;
      }
      /* Optional: Makes the sample page fill the window. */
      html, body {
        height: 100%%;
        margin: 0;
        padding: 0;
      }
    </style>
  </head>
  <body>
    <div id="map"></div>
    <script>
      var map;
      function initMap() {
        map = new google.maps.Map(document.getElementById('map'), {
          center: {lat: %f, lng: %f},
          zoom: 13,
        });

        %s

      }
    </script>
    <script src="https://maps.googleapis.com/maps/api/js?key=%s&callback=initMap&libraries=visualization"
    async defer></script>
  </body>
</html>
    ''' % (MID_LAT, MID_LON, rendered_box_list_str, JS_API_KEY)
    fout = open('map.html', 'w')
    fout.write(rendered_map)
    fout.close()

if __name__ == '__main__':
    get_travel_info_list(POINT_WTC)
