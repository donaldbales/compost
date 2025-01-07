#!/home/don/python/bin/python3
# -*- coding: utf-8 -*-
#
# data_sender.py - Data sending program for garden data logging
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
import os
import sys
import time

def err(message):
  print(str(datetime.today()) + " data_sender: " + str(message), file=sys.stderr, flush=True)

def log(message):
  print(str(datetime.today()) + " data_sender: " + str(message), flush=True)

data_path = '/home/don/data'

log("starting...")
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
        filename_suffix = filename[-23:-19] 
        if (filename_suffix == '.tsv'):
          files.append(data_path + '/' + year + '/' + month + '/' + day + '/' + filename)
      for file in files:
        log('From: ' + file + ' to: ' + file[0:len(file) - 19])
        os.rename(file, file[0:len(file) - 19])
log("stopping.")
