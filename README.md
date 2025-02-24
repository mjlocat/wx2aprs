# wx2aprs
This project is meant to be used in conjunction with the database written to by the [WeatherStation](https://github.com/mjlocat/WeatherStation) project. It reads the weather history and formats an appropriate APRS message to be sent over the air.

## Prerequisites

* python3 and pip3
* A Linux system with the AX.25 stack configured properly
* The `beacon` program
* The [WeatherStation](https://github.com/mjlocat/WeatherStation) project running and writing weather data to a database

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

## Notes

I've found that the readings I'm getting off the weather station have occasional erroneous values. Some examples I've found:

* Temperature reading of 164 degrees, skewing the 5 minute temperature average by 9 degrees
* Wind speed reading of 158 MPH, resulting in a bad 5 minute wind gust
* Rain reading jumping from 53 to 99 and back to 53, resulting in an inch of rain being recorded

To resolve this, we need to find a way to smooth out these erroneous values using a filter. The scipy signal module has a function called medfilt which will filter an array using the median value over a sliding window. After some testing, this seems to have done the trick. I'm using the default window size of 3 to start. If consecutive erroneous values come up, that window size will not be enough and will have to widen it to compensate. Had this happen with the rain sensor so extended the window size to 5 and added it as an environment variable.
