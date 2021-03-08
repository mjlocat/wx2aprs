from datetime import datetime
import math
import os
from dotenv import load_dotenv
import mysql.connector
from tzlocal import get_localzone
import pytz


def get_min_max_ts_period(timestamp):
    minutes_average = int(os.getenv("AVERAGE_MINUTES"))
    data = {
        'mints': timestamp - (minutes_average * 60),
        'maxts': timestamp
    }
    return data


def get_average_from_cursor(cursor):
    sum = 0
    count = 0
    row = cursor.fetchone()
    while row is not None:
        sum = sum + row[0]
        count = count + 1
        row = cursor.fetchone()

    if (count > 0):
        average = sum / count
        return math.trunc(average)

    return None


def get_wind_direction(cnx, timestamp):
    # TODO: This is only the most recent direction. Want to try to get the predomenent direction for the reporting period
    query = "SELECT winddirection FROM winddirection order by ts desc limit 1"
    dir_dict = {
        "N": 0,
        "NNE": 22,
        "NE": 45,
        "ENE": 67,
        "E": 90,
        "ESE": 112,
        "SE": 135,
        "SSE": 157,
        "S": 180,
        "SSW": 202,
        "SW": 225,
        "WSW": 247,
        "W": 270,
        "WNW": 292,
        "NW": 315,
        "NNW": 337
    }
    cursor = cnx.cursor()
    cursor.execute(query)
    row = cursor.fetchone()
    cursor.close()
    if row is not None:
        direction = dir_dict[row[0]]
        return "_{:03d}".format(direction)

    return "_..."


def get_wind_speed(cnx, timestamp):
    query = "SELECT windspeed FROM windspeed WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY windspeed, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = get_average_from_cursor(cursor)
    cursor.close()
    if average is not None:
        return "/{:03d}".format(average)

    return "/..."


def get_wind_gust(cnx, timestamp):
    query = "SELECT max(windspeed) FROM windspeed WHERE ts BETWEEN %(mints)s AND %(maxts)s"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)
    row = cursor.fetchone()
    cursor.close()
    if row is not None:
        max = math.floor(row[0])
        return "g{:03d}".format(max)

    return "g..."


def get_temperature(cnx, timestamp):
    query = "SELECT temperature FROM temperature WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY temperature, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = get_average_from_cursor(cursor)
    cursor.close()
    if average is not None:
        return "t{:03d}".format(average)

    return "t..."


def get_rain_hour(cnx, timestamp):
    return "r..."


def get_rain_24hour(cnx, timestamp):
    return "p..."


def get_rain_midnight(cnx, timestamp):
    return "P..."


def get_pressure(cnx, timestamp):
    # TODO: Not implemented until I get a barometric pressure sensor
    return "b....."


def get_humidity(cnx, timestamp):
    query = "SELECT humidity FROM humidity WHERE ts BETWEEN %(mints)s AND %(maxts)s GROUP BY humidity, ts"
    data = get_min_max_ts_period(timestamp)
    cursor = cnx.cursor()
    cursor.execute(query, data)

    average = get_average_from_cursor(cursor)
    cursor.close()
    if average is not None:
        if average == 100:
            return "h00"

        return "h{:02d}".format(average)

    return "h.."


def format_longitude():
    long_degrees = float(os.getenv('STATION_LONG_DEG'))
    degrees = abs(math.trunc(long_degrees))
    minutes = (abs(long_degrees) - degrees) * 60
    if long_degrees < 0:
        sign = "W"
    else:
        sign = "E"

    return "{}{:05.2f}{}".format(degrees, minutes, sign)


def format_latitude():
    lat_degrees = float(os.getenv('STATION_LAT_DEG'))
    degrees = abs(math.trunc(lat_degrees))
    minutes = (abs(lat_degrees) - degrees) * 60
    if lat_degrees < 0:
        sign = "S"
    else:
        sign = "N"

    return "{}{:05.2f}{}".format(degrees, minutes, sign)


def getEnvironment():
    load_dotenv()


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
    current_timestamp = now.timestamp()
    tz = get_localzone()
    utc = tz.localize(now).astimezone(pytz.utc)

    wind_direction = get_wind_direction(cnx, current_timestamp)
    wind_speed = get_wind_speed(cnx, current_timestamp)
    wind_gust = get_wind_gust(cnx, current_timestamp)
    temperature = get_temperature(cnx, current_timestamp)
    rain_hour = get_rain_hour(cnx, current_timestamp)
    rain_24hour = get_rain_24hour(cnx, current_timestamp)
    rain_midnight = get_rain_midnight(cnx, current_timestamp)
    pressure = get_pressure(cnx, current_timestamp)
    humidity = get_humidity(cnx, current_timestamp)
    lat_formatted = format_latitude()
    long_formatted = format_longitude()

    print("@%sz%s/%s%s%s%s%s%s%s%s%s%s" % (utc.strftime("%d%H%M"), lat_formatted, long_formatted, wind_direction,
                                           wind_speed, wind_gust, temperature, rain_hour, rain_24hour, rain_midnight, pressure, humidity))

    cnx.close()


if __name__ == "__main__":
    main()
