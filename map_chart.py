from __future__ import division
from lxml import etree
import math

DEFAULTS = {
    'cartesian_bounds': [0, 2000, 0, 1000],
    'geo_bounds': [-179, 179, -60, 89],
    'projection': 'equirectangular'
}


def test_bounds(point, geo_bounds):
    if point[0] < geo_bounds[0] or point[0] > geo_bounds[1] or\
            point[1] < geo_bounds[2] or point[1] > geo_bounds[3]:
        return False
    return True


# cartesian_bounds = [min_x, max_x, min_y, max_y]
# geo_bounds = [min_long, max_long, min_lat, max_lat]
# point = [long, lat]
def convert_point_equirectangular(point, cartesian_bounds, geo_bounds):
    if not test_bounds(point, geo_bounds):
        return None

    normalized_long = (point[0] - geo_bounds[0])\
        / (geo_bounds[1] - geo_bounds[0])
    x = normalized_long * \
        (cartesian_bounds[1] - cartesian_bounds[0]) + cartesian_bounds[0]

    normalized_lat = (point[1] - geo_bounds[2])\
        / (geo_bounds[3] - geo_bounds[2])

    # y=0 is at the top of the screen, so we need to flip the chart here
    y = cartesian_bounds[3] - normalized_lat *\
        (cartesian_bounds[3] - cartesian_bounds[2])
    return [x, y]


def convert_point_mercator(point, cartesian_bounds, geo_bounds):
    if not test_bounds(point, geo_bounds):
        return None

    normalized_long = (point[0] - geo_bounds[0])\
        / (geo_bounds[1] - geo_bounds[0])
    x = normalized_long *\
        (cartesian_bounds[1] - cartesian_bounds[0]) + cartesian_bounds[0]

    def convert_lat(lat):
        lat_radians = math.radians(lat)
        return math.log(math.tan(0.25 * math.pi + 0.5 * lat_radians))

    normalized_lat = (convert_lat(point[1]) - convert_lat(geo_bounds[2]))\
        / (convert_lat(geo_bounds[3]) - convert_lat(geo_bounds[2]))

    y = cartesian_bounds[3] - normalized_lat *\
        (cartesian_bounds[3] - cartesian_bounds[2])
    return [x, y]


PROJECTION_MAP = {
    'equirectangular': convert_point_equirectangular,
    'mercator': convert_point_mercator
}


def convert_linear_ring(linear_ring, cartesian_bounds, geo_bounds, projection):
    converted_ring = []
    point_conversion_func = PROJECTION_MAP.get(projection)
    if not point_conversion_func:
        raise Exception('Cannot find projection. {0}'.format(projection))
    for point in linear_ring:
        converted_point = point_conversion_func(point,
                                                cartesian_bounds,
                                                geo_bounds)
        if converted_point is not None:
            converted_ring.append(converted_point)
    return converted_ring


def convert_polygon(polygon, cartesian_bounds, geo_bounds, projection):
    converted_polygon = []
    for ring in polygon:
        converted_ring = convert_linear_ring(ring,
                                             cartesian_bounds,
                                             geo_bounds,
                                             projection)
        converted_polygon.append(converted_ring)
    return converted_polygon


def construct_polygon_element(polygon, parent, color,
                              cartesian_bounds, geo_bounds,
                              projection, _id):
    polygon_data = convert_polygon(polygon, cartesian_bounds,
                                   geo_bounds, projection)
    attrib = {}
    tag = 'path'

    d = 'M'
    for linear_ring in polygon_data:
        for point in linear_ring:
            d += '{0},{1} '.format(point[0], point[1])
    d += 'z'
    attrib['d'] = d
    attrib['fill'] = color
    attrib['id'] = _id
    return etree.SubElement(parent, tag, attrib)


def construct_map(geodict, colors,
                  cartesian_bounds=DEFAULTS['cartesian_bounds'],
                  geo_bounds=DEFAULTS['geo_bounds'],
                  projection=DEFAULTS['projection'],
                  key='iso_a2'):
    root = etree.Element("svg", preserveAspectRatio='xMinYMin')
    for feature in geodict['features']:
        if feature['properties']['iso_a2'] in colors:
            color = colors[feature['properties'][key]]
        else:
            color = '#000'

        _id = feature['properties'][key]
        if feature['geometry']['type'] == 'Polygon':
            construct_polygon_element(feature['geometry']['coordinates'],
                                      root, color,
                                      cartesian_bounds, geo_bounds,
                                      projection, _id)
        elif feature['geometry']['type'] == 'MultiPolygon':
            for polygon in feature['geometry']['coordinates']:
                construct_polygon_element(polygon,
                                          root, color,
                                          cartesian_bounds, geo_bounds,
                                          projection, _id)
    return root


def values_to_colors(values, light, dark):
    if not light[0] == '#' and dark[0] == '#':
        raise Exception('Please input only hex colors in format #FFFFFF')
    if not len(light) == 7 and len(dark) == 7:
        raise Exception('Please input only hex colors in format #FFFFFF')

    light = light.strip('#')
    dark = dark.strip('#')
    _min = min(values, key=values.get)
    _max = max(values, key=values.get)

    _min = values[_min]
    _max = values[_max]

    ret_dict = {}

    light_rgb = tuple(ord(c) for c in light.decode('hex'))
    dark_rgb = tuple(ord(c) for c in dark.decode('hex'))
    diff_rgb = []
    for i in range(len(light_rgb)):
        diff_rgb.append(light_rgb[i] - dark_rgb[i])

    for key in values:
        value = values[key]
        r = ((value - _min) / (_max - _min)) * diff_rgb[0] + dark_rgb[0]
        g = ((value - _min) / (_max - _min)) * diff_rgb[1] + dark_rgb[1]
        b = ((value - _min) / (_max - _min)) * diff_rgb[2] + dark_rgb[2]
        rgb = (r, g, b)
        rgb = map(int, rgb)
        ret_dict[key] = '#' + "".join(map(chr, rgb)).encode('hex')

    return ret_dict


def test_map(filein, fileout):
    import json
    import random
    import time
    import os

    with open(filein) as _filein:
        countries = json.load(_filein)

    data_dict = {}
    for feature in countries['features']:
        data_dict[feature['properties']['iso_a2']] = random.randint(0, 100)

    t1 = time.time()
    colors = values_to_colors(data_dict, '#FFFFFF', '#3366CC')

    _map = construct_map(countries, colors)
    t2 = time.time()
    with open(fileout, 'w') as _fileout:
        _fileout.write(etree.tostring(_map))

    print 'Constructed map in {0} seconds.'.format(t2-t1)
    size = os.path.getsize(fileout)
    print 'File size {0} KB'.format(size/1000)
    print 'Wrote to file {0}'.format(fileout)
