# wx2aprs
This project is meant to be used in conjunction with the database written to by the [WeatherStation](https://github.com/mjlocat/WeatherStation) project. It reads the weather history and formats an appropriate APRS message to be sent over the air.

## Prerequisites

* python3 and pip3
* A Linux system with the AX.25 stack configured properly
* The `beacon` program
* The [WeatherStation](https://github.com/mjlocat/WeatherStation) project running and writing weather data to a database

## Installation

* Install the Python requirements
  ``` shell
  pip3 install -r requirements.txt
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
  */5 * * * * source ~/.bashrc && cd ~/wx2aprs && MESSAGE=`python3 wx2aprs.py` && beacon -c N0CALL -d "APRS WIDE2-2" -s radio0 "${MESSAGE}"
  # ^- This should be the number        ^- Replace this with the directory of               ^- Replace with your        ^- Replace with the port
  #    of minutes between reports          this repository                                     callsign+ssid               defined in axports
  ```

## TODO

* Precipitation information (rain last hour, rain last 24 hours, rain since midnight)
* Barometric pressure
