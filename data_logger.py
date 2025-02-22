#!/home/don/python/bin/python3

from datetime import datetime
from email.message import EmailMessage
import os
from pathlib import Path
import RPi.GPIO as GPIO
import subprocess
import smtplib
import sys
import time

sys.stdout = open('/home/don/compost/data_logger.log', 'at')
sys.stderr = open('/home/don/compost/data_logger.err', 'at')

omask = os.umask(0o000)

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)

channel_list = [20,21]
GPIO.setup(channel_list, GPIO.OUT)

ACTUATOR_EAST = 21
ACTUATOR_WEST = 20

class Data:
    def __init__(self, dt):
        self.sample_date = (str(dt.year) + '-' + \
                            str(dt.month).rjust(2, '0') + '-' + \
                            str(dt.day).rjust(2, '0') + ' ' + \
                            str(dt.hour).rjust(2, '0') + ':' + \
                            str(dt.minute).rjust(2, '0') + ':' + \
                            str(dt.second).rjust(2, '0'))
    def __str__(self):
        return ('Data(sample_date:   ' + str(self.sample_date)   + "\n" + \
                '     moisture:      ' + str(self.moisture)      + "\n" + \
                '     temp_east:     ' + str(self.temp_east)     + "\n" + \
                '     temp_west:     ' + str(self.temp_west)     + "\n" + \
                '     temp_moisture: ' + str(self.temp_moisture) + "\n" + \
                '     temp_rpi:      ' + str(self.temp_rpi)      + ")\n")
    def to_json(self):
        return ('{"sample_date": "'   + str(self.sample_date)    + '",' + \
                ' "moisture": "'      + str(self.moisture)       + '",' + \
                ' "temp_east": "'     + str(self.temp_east)  + '",' + \
                ' "temp_west": "'     + str(self.temp_west) + '",' + \
                ' "temp_rpi": "'      + str(self.temp_rpi)       + '"}\n')
    def to_tsv(self):
        return (str(self.sample_date)   + "\t" + \
                str(self.moisture)      + "\t" + \
                str(self.temp_east)     + "\t" + \
                str(self.temp_west)     + "\t" + \
                str(self.temp_rpi)      + "\n")
    
    moisture = 0
    sample_date = None
    temp_east = None
    temp_moisture = None
    temp_rpi = None
    temp_west = None

one_minute_before = (4, 9, 14, 19, 24, 29, 34, 39, 44, 49, 54, 59)
on_five_minutes = (0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55)
thermometers = ('28-43efd446911b', '28-2f7dd4467c28')
thermometer_dir = '/sys/bus/w1/devices/'

def rpi_temp():
    completed_process = subprocess.run(['/usr/bin/vcgencmd', ' measure_temp'], capture_output=True)
    #print(completed_process, flush=True);
    output = str(completed_process.stdout)
    #print(output, flush=True)
    equals_pos = output.find('=')
    #print(equals_pos, flush=True)
    tic_pos = output.find("'")
    #print(tic_pos, flush=True)
    c = float(output[equals_pos + 1:tic_pos])
    f = round((c * 9.0 / 5.0) + 32.0, 2)
    #print("RPi Temp: ", c, f, flush=True)
    return f

def ymd_path(dt):
    return '/home/don/data/' + str(dt.year) + '/' + str(dt.month).rjust(2, '0') + '/' + str(dt.day).rjust(2, '0')

def ymdh_filename(dt):
    return str(dt.year) + str(dt.month).rjust(2, '0') + str(dt.day).rjust(2, '0') + str(dt.hour).rjust(2, '0') + '.tsv'

def read_temp_raw(thermometer):
    device_file = thermometer_dir + thermometer + '/w1_slave'
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp(thermometer):
    lines = read_temp_raw(thermometer)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = round(float(temp_string) / 1000.0, 2)
        temp_f = round((temp_c * 9.0 / 5.0) + 32.0, 2)
        return temp_c, temp_f

def send_notification(body):
    message = EmailMessage()
    message.set_content(body)
    message['Subject'] = "raspberrypi-3-compost Alert"
    message['From'] = 'don@donaldbales.com'
    message['To'] = 'donaldbales@mac.com'
    # creates SMTP session
    connection = smtplib.SMTP('netsol-smtp-oxcs.hostingplatform.com', 587)
    # start TLS for security
    connection.starttls()
    # Authentication
    connection.login("don@donaldbales.com", os.getenv('EMAIL_PASSWORD', ''))
    # sending the mail
    connection.sendmail("don@donaldbales.com", "donaldbales@mac.com", message.as_string())
    # terminating the session
    connection.quit()
    return True

def write_data(dt, data):
    data_path = Path(ymd_path(dt))
    if (not data_path.exists()):
        result = data_path.mkdir(mode=0o777, parents=True)
        #print(result, flush=True)
    data_file = ymd_path(dt) + '/' + ymdh_filename(dt)
    file_object = open(data_file, 'a')
    file_object.write(data.to_tsv())
    file_object.close()

try:
    while True:
        dt = datetime.now()

        # Try to align to five minute, zero seconds
        while (dt.minute in one_minute_before and \
               dt.second >= 29):
            #print(str(dt.second), flush=True)
            time.sleep(1)
            dt = datetime.now()

        data = Data(dt)
        #print(str(data.sample_date), flush=True)
        data.temp_rpi = rpi_temp()
        for i in range(2):
            thermometer = thermometers[i]
            try:
                c, f = read_temp(thermometer)
            except Exception as error:
                c = None
                f = None
                print('Error reading thermometer ' + str(i) + ' ' + thermometer + ': ' + str(error), flush=True)
                print('Error reading thermometer ' + str(i) + ' ' + thermometer + ': ' + str(error), file=sys.stderr, flush=True)
            #print(thermometer, c, f, flush=True)
            match thermometer:
                case '28-43efd446911b':
                    data.temp_east = f
                case '28-2f7dd4467c28':
                    data.temp_west = f
        print(data.to_json(), flush=True)

        if (dt.minute in on_five_minutes and \
            dt.second <= 29):
            print('Writing data for ' + data.sample_date, flush=True)
            try: 
                write_data(dt, data)
            except Exception as error:
                print('Error writing data ' + data.to_json() + ': ' + str(error), flush=True)
                print('Error writing data ' + data.to_json() + ': ' + str(error), file=sys.stderr, flush=True)

        # Wait for 29 seconds
        time.sleep(29);

except KeyboardInterrupt:
    os.umask(omask)
    # Clean up the GPIO pins on exit
    GPIO.cleanup()
    #print("Program exited cleanly", flush=True)
