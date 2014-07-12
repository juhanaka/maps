

# cartesian_bounds = [min_x, max_x, min_y, max_y]
# geo_bounds = [min_long, max_long, min_lat, max_lat]
# point = [long, lat]
def convert_point_equirectangular(point, cartesian_bounds, geo_bounds):
    if point[0] > geo_bounds[0] or point[0] < geo_bounds[1] or\
            point[1] > geo_bounds[2] or point[1] < geo_bounds[3]:
        return None

    normalized_long = (point[0] - geo_bounds[0]) / (geo_bounds[1] - geo_bounds[0])
    x = normalized_long * (cartesian_bounds[1] - cartesian_bounds[0]) + cartesian_bounds[0]

    normalized_lat = (point[1] - geo_bounds[2]) / (geo_bounds[3] - geo_bounds[2])
    y = normalized_lat * (cartesian_bounds[3] - cartesian_bounds[2]) + cartesian_bounds[2]
    return [x, y]


PROJECTION_MAP = {
    'equirectangular': convert_point_equirectangular
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
