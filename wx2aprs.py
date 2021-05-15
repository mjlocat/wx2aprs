from datetime import datetime, time
import math
import os
from dotenv import load_dotenv
import mysql.connector
from tzlocal import get_localzone
import pytz
from scipy.signal import medfilt
from numpy import mean

rainquery = "SELECT rain FROM rain WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY rain, ts ORDER BY ts"
window_size = 3 # default, will be overridden by environment settings further down

def get_min_max_ts_period(timestamp, minutes_back = None):
    if minutes_back is None:
        minutes_back = int(os.getenv("AVERAGE_MINUTES"))

    data = {
        'mints': timestamp - (minutes_back * 60),
        'maxts': timestamp
    }
    return data


def get_average_from_cursor(cursor):
    readings = []
    row = cursor.fetchone()
    while row is not None:
        readings.append(row[0])
        row = cursor.fetchone()

    if len(readings) < window_size:
        return None

    smooth_readings = medfilt(readings, window_size)
    return mean(smooth_readings)


def get_prevailing_wind_dir(cursor):
    # Algorithm based on information here: https://www.wxforum.net/index.php?topic=8660.0
    dir_dict = {
        "N": 0,
        "NNE": 22.5,
        "NE": 45,
        "ENE": 67.5,
        "E": 90,
        "ESE": 112.5,
        "SE": 135,
        "SSE": 157.5,
        "S": 180,
        "SSW": 202.5,
        "SW": 225,
        "WSW": 247.5,
        "W": 270,
        "WNW": 292.5,
        "NW": 315,
        "NNW": 337.5
    }
    s_ns = 0 # Sum of the North/South wind components
    s_ew = 0 # Sum of the East/West wind components
    row = cursor.fetchone()
    while row is not None:
        direction_degrees = dir_dict[row[0]]
        direction_radians = math.radians(direction_degrees)
        windspeed = row[1]
        c_ns = math.cos(direction_radians) * windspeed # North/South component
        c_ew = math.sin(direction_radians) * windspeed # East/West component
        s_ns = s_ns + c_ns
        s_ew = s_ew + c_ew
        row = cursor.fetchone()

    p_direction_radians = math.atan2(s_ew, s_ns)
    p_direction = math.degrees(p_direction_radians)
    if p_direction < 0:
        p_direction = p_direction + 360

    return p_direction


def get_wind_direction(cnx, timestamp):
    query = "SELECT d.winddirection, s.windspeed FROM winddirection d INNER JOIN windspeed s ON d.ts = s.ts WHERE d.ts BETWEEN %(mints)s AND %(maxts)s GROUP BY d.winddirection, s.windspeed, d.ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)
    direction = int(get_prevailing_wind_dir(cursor))
    cursor.close()
    if direction is not None:
        return "_{:03d}".format(direction)

    return "_..."


def get_wind_speed(cnx, timestamp):
    query = "SELECT windspeed FROM windspeed WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY windspeed, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = int(get_average_from_cursor(cursor))
    cursor.close()
    if average is not None:
        return "/{:03d}".format(average)

    return "/..."


def get_wind_gust(cnx, timestamp):
    readings = []
    query = "SELECT windspeed FROM windspeed WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY windspeed, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)
    row = cursor.fetchone()
    while row is not None:
        readings.append(row[0])
        row = cursor.fetchone()

    cursor.close()
    if len(readings) > 0:
        smooth_readings = medfilt(readings, window_size)
        gust = int(max(smooth_readings))
        return "g{:03d}".format(gust)

    return "g..."


def get_temperature(cnx, timestamp):
    query = "SELECT temperature FROM temperature WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY temperature, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = int(get_average_from_cursor(cursor))
    cursor.close()
    if average is not None:
        return "t{:03d}".format(average)

    return "t..."


def get_rain_over_period(cursor):
    readings = []
    row = cursor.fetchone()
    while row is not None:
        readings.append(row[0])
        row = cursor.fetchone()

    if len(readings) < window_size:
        return None

    smooth_readings = medfilt(readings, window_size)

    count = 0
    last = smooth_readings[0]
    for reading in smooth_readings:
        if last < reading:
            count = count + (reading - last)
            last = reading
        elif last > 900 and reading < 100:
            count = count + (100 + reading - last)
            last = reading
        elif last > reading:
            # Bad reading in there, bail out
            return None

    return int(count)


def get_rain_hour(cnx, timestamp):
    data = get_min_max_ts_period(timestamp, 60)
    cursor = cnx.cursor()
    cursor.execute(rainquery, data)
    rain = get_rain_over_period(cursor)
    cursor.close()
    if rain is not None:
        return "r{:03d}".format(rain)

    return "r..."


def get_rain_24hour(cnx, timestamp):
    data = get_min_max_ts_period(timestamp, 1440)
    cursor = cnx.cursor()
    cursor.execute(rainquery, data)
    rain = get_rain_over_period(cursor)
    cursor.close()
    if rain is not None:
        return "p{:03d}".format(rain)

    return "p..."


def get_rain_midnight(cnx, current_timestamp, midnight_timestamp):
    data = {
        'mints': midnight_timestamp,
        'maxts': current_timestamp
    }
    cursor = cnx.cursor()
    cursor.execute(rainquery, data)
    rain = get_rain_over_period(cursor)
    cursor.close()
    if rain is not None:
        return "P{:03d}".format(rain)

    return "P..."


def get_pressure(cnx, timestamp):
    query = "SELECT pressure FROM pressure WHERE ts BETWEEN %(mints)s and %(maxts)s GROUP BY pressure, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = get_average_from_cursor(cursor)
    cursor.close()
    if average is not None:
        tenths = int(average * 10)
        return "b{:05d}".format(tenths)

    return "b....."


def get_humidity(cnx, timestamp):
    query = "SELECT humidity FROM humidity WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY humidity, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = int(get_average_from_cursor(cursor))
    cursor.close()
    if average is not None:
        if average == 100:
            return "h00"

        return "h{:02d}".format(average)

    return "h.."


def format_longitude():
    long_degrees = float(os.getenv('STATION_LONG_DEG'))
    degrees = abs(int(long_degrees))
    minutes = (abs(long_degrees) - degrees) * 60
    if long_degrees < 0:
        sign = "W"
    else:
        sign = "E"

    return "{}{:05.2f}{}".format(degrees, minutes, sign)


def format_latitude():
    lat_degrees = float(os.getenv('STATION_LAT_DEG'))
    degrees = abs(int(lat_degrees))
    minutes = (abs(lat_degrees) - degrees) * 60
    if lat_degrees < 0:
        sign = "S"
    else:
        sign = "N"

    return "{}{:05.2f}{}".format(degrees, minutes, sign)


def getEnvironment():
    global window_size
    load_dotenv()
    window_size = int(os.getenv("WINDOW_SIZE"))


def main():
    getEnvironment()
    dbconfig = {
        'user': os.getenv('DBUSER'),
        'password': os.getenv('DBPASS'),
        'host': os.getenv('DBHOST'),
        'database': os.getenv('DBDATABASE')
    }
    cnx = mysql.connector.connect(**dbconfig)

    now = datetime.now()
    # now = datetime.fromtimestamp(1617352500)
    current_timestamp = now.timestamp()
    tz = get_localzone()
    utc = tz.localize(now).astimezone(pytz.utc)
    midnight_timestamp = datetime.combine(now, time.min).timestamp()

    wind_direction = get_wind_direction(cnx, current_timestamp)
    wind_speed = get_wind_speed(cnx, current_timestamp)
    wind_gust = get_wind_gust(cnx, current_timestamp)
    temperature = get_temperature(cnx, current_timestamp)
    rain_hour = get_rain_hour(cnx, current_timestamp)
    rain_24hour = get_rain_24hour(cnx, current_timestamp)
    rain_midnight = get_rain_midnight(cnx, current_timestamp, midnight_timestamp)
    pressure = get_pressure(cnx, current_timestamp)
    humidity = get_humidity(cnx, current_timestamp)
    lat_formatted = format_latitude()
    long_formatted = format_longitude()

    print("@%sz%s/%s%s%s%s%s%s%s%s%s%s" % (utc.strftime("%d%H%M"), lat_formatted, long_formatted, wind_direction,
                                           wind_speed, wind_gust, temperature, rain_hour, rain_24hour, rain_midnight, pressure, humidity))

    cnx.close()


if __name__ == "__main__":
    main()
