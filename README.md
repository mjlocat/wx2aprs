# wx2aprs
This project reads weather readings from an MQTT broker (topics under `house/wx/`) and formats an appropriate APRS message to be sent over the air. Averaging and smoothing are done upstream; the values are used as published.

## Prerequisites

* python3 and pip3
* A Linux system with the AX.25 stack configured properly
* The `beacon` program
* An MQTT broker publishing the weather topics (see below)

## Installation

* Install the Python requirements: You can install the Python requirements using pip3 for most cases. Debian 12 prefers you use the packages from the apt repositories instead
  * Install using pip3
    ``` shell
    pip3 install -r requirements.txt
    ```
  * Install using Debian packages repository
    ``` shell
    sh ./install-deps-debian.sh
    ```
* Create your `.env` file from the sample and update as specified
  ``` shell
  cp env.sample .env
  vi .env # Or nano .env
  ```
* Install a cronjob to send weather information every 5 minutes or more
  ``` shell
  crontab -e
  SHELL=/bin/bash
  */5 * * * * source ~/.bashrc && cd ~/wx2aprs && MESSAGE=`python3 wx2aprs.py` && /usr/sbin/beacon -c N0CALL -d "APRS WIDE2-2" -s radio0 "${MESSAGE}"
  # ^- This should be the number        ^- Replace this with the directory of                          ^- Replace with your        ^- Replace with the port
  #    of minutes between reports          this repository                                                callsign+ssid               defined in axports
  ```

## TODO

* Optional comment

## MQTT topics

Under the configured prefix (default `house/wx/`): `wind_dir_avg_5m`, `wind_speed_avg_5m`, `wind_speed_peak_5m`, `temperature_avg_5m`, `humidity_avg_5m`, `rain_1h`, `rain_24h`, `rain_today` (rain in inches). Pressure is not yet published, so it is reported as unavailable (`b.....`). Any missing topic is reported as dots in the APRS string.
