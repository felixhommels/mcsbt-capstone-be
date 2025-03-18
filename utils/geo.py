from math import radians, sin, cos, atan2, sqrt

def compute_distance(start_latitude: float, start_longitude: float, end_latitude: float, end_longitude: float) -> float:
    # Using haversine formula
    R = 6371.0  # radius earth in km

    start_latitude, start_longitude, end_latitude, end_longitude = map(radians, [start_latitude, start_longitude, end_latitude, end_longitude])

    delta_longitude = end_longitude - start_longitude
    delta_latitude = end_latitude - start_latitude

    haversine_a = sin(delta_latitude / 2)**2 + cos(start_latitude) * cos(end_latitude) * sin(delta_longitude / 2)**2
    haversine_c = 2 * atan2(sqrt(haversine_a), sqrt(1 - haversine_a))

    distance = round(R * haversine_c, 2)

    return distance