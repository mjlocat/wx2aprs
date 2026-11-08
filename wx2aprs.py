from datetime import datetime, timezone
import os
import sys
import threading

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

# Topic suffixes under the topic prefix (default house/wx/). Aggregation and
# smoothing are done upstream, so each topic holds a ready-to-use value.
TOPICS = [
    "wind_dir_avg_5m",      # degrees
    "wind_speed_avg_5m",    # mph
    "wind_speed_peak_5m",   # mph
    "temperature_avg_5m",   # degrees F
    "rain_1h",              # inches
    "rain_24h",             # inches
    "rain_today",           # inches
    "humidity_avg_5m",      # percent
]


def fetch_readings(host, port, prefix, timeout):
    """Read the (retained) values from the broker. Missing topics are omitted."""
    readings = {}
    done = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        client.subscribe([(prefix + t, 0) for t in TOPICS])

    def on_message(client, userdata, msg):
        name = msg.topic[len(prefix):]
        try:
            readings[name] = float(msg.payload.decode().strip())
        except ValueError:
            return  # Unparseable payload, treat as missing
        if len(readings) == len(TOPICS):
            done.set()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host, port, keepalive=int(timeout) + 5)
    client.loop_start()
    done.wait(timeout)
    client.loop_stop()
    client.disconnect()
    return readings


def fmt(value, template, missing):
    if value is None:
        return missing
    return template.format(int(round(value)))


def get_wind_direction(r):
    v = r.get("wind_dir_avg_5m")
    return "_..." if v is None else "_{:03d}".format(int(round(v)) % 360)


def get_wind_speed(r):
    return fmt(r.get("wind_speed_avg_5m"), "/{:03d}", "/...")


def get_wind_gust(r):
    return fmt(r.get("wind_speed_peak_5m"), "g{:03d}", "g...")


def get_temperature(r):
    return fmt(r.get("temperature_avg_5m"), "t{:03d}", "t...")


def rain_hundredths(r, name):
    v = r.get(name)
    return None if v is None else v * 100


def get_rain_hour(r):
    return fmt(rain_hundredths(r, "rain_1h"), "r{:03d}", "r...")


def get_rain_24hour(r):
    return fmt(rain_hundredths(r, "rain_24h"), "p{:03d}", "p...")


def get_rain_midnight(r):
    return fmt(rain_hundredths(r, "rain_today"), "P{:03d}", "P...")


def get_pressure(r):
    # Pressure has not been moved to MQTT yet, so it is always unavailable.
    v = r.get("pressure")
    return "b....." if v is None else "b{:05d}".format(int(round(v * 10)))


def get_humidity(r):
    v = r.get("humidity_avg_5m")
    if v is None:
        return "h.."
    v = int(round(v))
    return "h00" if v >= 100 else "h{:02d}".format(v)


def format_coordinate(degrees_decimal, pos, neg, width):
    degrees = abs(int(degrees_decimal))
    minutes = (abs(degrees_decimal) - degrees) * 60
    sign = neg if degrees_decimal < 0 else pos
    return "{:0{w}d}{:05.2f}{}".format(degrees, minutes, sign, w=width)


def format_longitude():
    return format_coordinate(float(os.getenv("STATION_LONG_DEG")), "E", "W", 3)


def format_latitude():
    return format_coordinate(float(os.getenv("STATION_LAT_DEG")), "N", "S", 2)


def main():
    load_dotenv()
    prefix = os.getenv("MQTT_TOPIC_PREFIX", "house/wx/")
    if not prefix.endswith("/"):
        prefix += "/"
    readings = fetch_readings(
        os.getenv("MQTT_HOST", "master"),
        int(os.getenv("MQTT_PORT", "1883")),
        prefix,
        float(os.getenv("MQTT_TIMEOUT", "10")),
    )
    missing = [t for t in TOPICS if t not in readings]
    if missing:
        print("No data for: " + ", ".join(missing), file=sys.stderr)

    utc = datetime.now(timezone.utc)
    print("@%sz%s/%s%s%s%s%s%s%s%s%s%s" % (
        utc.strftime("%d%H%M"), format_latitude(), format_longitude(),
        get_wind_direction(readings), get_wind_speed(readings), get_wind_gust(readings),
        get_temperature(readings), get_rain_hour(readings), get_rain_24hour(readings),
        get_rain_midnight(readings), get_pressure(readings), get_humidity(readings)))


if __name__ == "__main__":
    main()
