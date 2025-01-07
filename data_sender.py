#!/home/don/python/bin/python3
# -*- coding: utf-8 -*-
#
# data_sender.py - Data sending program for compost data logging
# Copyright (C) 2024  Donald J. Bales
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import urlopen, Request
import json
import os
import sys
import time

sys.stdout = open('/home/don/compost/data_sender.log', 'at')
sys.stderr = open('/home/don/compost/data_sender.err', 'at')

url = 'http://192.168.0.70:3000/compost_data'

def err(message):
  print(str(datetime.today()) + " data_sender: " + str(message), file=sys.stderr, flush=True)

def log(message):
  print(str(datetime.today()) + " data_sender: " + str(message), flush=True)

log("starting up")

# wait for a network connection
log("waiting for a network connection")
time.sleep(60)

data_path = '/home/don/data'

def dot_sent():
  dt = datetime.now()
  return ('.sent' + \
    str(dt.year) + \
    str(dt.month).rjust(2, '0') + \
    str(dt.day).rjust(2, '0') + \
    str(dt.hour).rjust(2, '0') + \
    str(dt.minute).rjust(2, '0') + \
    str(dt.second).rjust(2, '0'))

def to_yyyymmddhh(dt):
  return ( \
    str(dt.year) + \
    str(dt.month).rjust(2, '0') + \
    str(dt.day).rjust(2, '0') + \
    str(dt.hour).rjust(2, '0'))

def to_json(sample_date, moisture, temp_east, temp_west, temp_rpi):
  return ('{"sample_date": ' + to_nvl(sample_date) + ',' + \
          ' "moisture": '    + to_nvl(moisture)    + ',' + \
          ' "temp_east": '   + to_nvl(temp_air_east)   + ',' + \
          ' "temp_west": '   + to_nvl(temp_air_west)   + ',' + \
          ' "temp_rpi": '    + to_nvl(temp_rpi)    + '}\n')

def to_nvl(value):
  if (value == 'None'):
    return 'null'
  else:
    return '"' + str(value) + '"' 

while True:
  log("waking up")
  files = []
  dt = datetime.now()
  years = os.listdir(data_path)
  for year in years:
    months = os.listdir(data_path + '/' + year)
    for month in months:
      days = os.listdir(data_path + '/' + year + '/' + month)
      for day in days:
        filenames = os.listdir(data_path + '/' + year + '/' + month + '/' + day)
        for filename in filenames:
          filename_suffix = filename[-4:] 
          filename_time = int(filename[-14:-4])
          datetime_time = int(to_yyyymmddhh(dt))
          if (filename_suffix == '.tsv' and \
              filename_time   <  datetime_time):
            files.append(data_path + '/' + year + '/' + month + '/' + day + '/' + filename)
        for file in files:
          log(file)
          line_count = 0
          post_count = 0
          headers = { "Content-Type": "application/json" }
          with open(file, 'r') as lines:
            for line in lines:
              line_count = line_count + 1
              stripped = line.strip()
              tokens = stripped.split('\t')
              json_str = to_json(tokens[0], tokens[1], tokens[2], tokens[3], tokens[4])
              data = json_str.encode('utf-8');
              # method is POST by default if data is provided
              request = Request(url, data, headers)
              try:
                with urlopen(request, timeout=10) as response:
                  log('Response status: ' + str(response.status))
                  #log('Response body: \n' + str(response.read().decode("utf-8")))
                  if (str(response.status) == '201'):
                    post_count = post_count + 1
              except HTTPError as error:
                if (str(error.status) == '422'):
                  post_count = post_count + 1
                  log('Response error.status: ' + str(error.status))
                  log('Response error.reason: ' + str(error.reason))
                else:
                  err('Response error.status: ' + str(error.status))
                  err('Response error.reason: ' + str(error.reason))
              except URLError as error:
                err(error.reason)
              except TimeoutError:
                err("Request timed out")
          if (line_count == post_count):
            os.rename(file, file + dot_sent())
        files = []
        dt = datetime.now()
  log("going to sleep for 5 minutes")
  time.sleep(60 * 5)

log("shuting down")
