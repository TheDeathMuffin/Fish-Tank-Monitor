from datetime import datetime, timedelta
from time import sleep
import smtplib
import subprocess
import urllib.request
import requests

#
#
#
#

max_water_dist = 2               # maximum allowable distance from water level to sensor
temp_range = [68,80,'F']        # low temp, high temp, units
daily_event_log = {}            # This dictionary stores each recorded alarm event and the time it was recorded.
daily_temp_record = {}          # List stores data points gathered for daily report
daily_waterDist_record = {}      # List stores data point gathered for daily report
send_to = ['9378251843@tmomail.net']        # Number to which alerts and notifications will be sent.


# Main program function. Responsible for looping and executing other checks and functions as needed.
def main():
    last_record_date = floor_half_hour(datetime.now())          # Rounds backwards to the nearest half hour from the current time.


    while True:     # Sensor data is checked on every loop.

        avg_temp, avg_waterDist = average_values()                   # Records an average of the values over a period of time.
        current_rounded_time = floor_half_hour(datetime.now())       # Round current time to last half 30-minute interval.
        if last_record_date != current_rounded_time:                 # Checks if half an hour has passed since last log. If so, log the data and update the last_data_log value.
            record_data(current_rounded_time, avg_temp, avg_waterDist)      # Records data for this time.
            last_record_date = current_rounded_time
        if not (temp_range[0] <= avg_temp <= temp_range[1]) or (avg_waterDist <= max_water_dist):       # Checks if the average temp is NOT within the desired range OR if the average water level is NOT above the desired amount.
            alarm(avg_temp, avg_waterDist)              # If one of the values is outside what is desired, initiate the alarm.



    sleep(60)       # Waits 60 seconds before restarting loop.


# Rounds down to the nearest 30-min interval.
def floor_half_hour(time):
    if time.minute < 30:
        return time.replace(minute=0,second=0,microsecond=0)
    else:
        return time.replace(minute=30, second=0, microsecond=0)

# Calculates temperature and water level by averaging sensor data.
def average_values():
    total_temp = 0
    total_waterDist = 0
    for i in range(100):      # Over 10 seconds, gathers 100 data points from each sensor.
        total_temp += #GET TEMP HERE
        total_waterDist += #GET WATERDIST HERE
        sleep(0.1)
    return total_temp/100, total_waterDist/100

# Alarm system.
def alarm(avg_temp, avg_waterDist):
    event = ''
    if (avg_waterDist > max_water_dist):        # Executes if distance to water is greater than desired.
        # LIGHT APPROPRIATE LED
        event = event + 'Water level is too low. '      # Specifies event.
    if (avg_temp > temp_range[1]):              # Executes if temperature is higher than desired.
        # LIGHT APPROPRIATE LED
        event = event + 'Temperature is too high.'      # Specifies event.
    elif (avg_temp < temp_range[0]):            # Executes if temperature is lower than desired.
        # LIGHT APPROPRIATE LED
        event = event + 'Temperature is too low.'       # Specifies event.
    log_event(event)
    subject = 'FISH TANK ALERT!'
    body = """/
Alarms Activated:
%s    

Current Conditions:
\tTemperature: %s
\tWater Distance: %s

Desired Conditions:
\tTemperature: %s%s - %s%s
\tWater Distance: %s
    """ % (event, avg_temp, avg_waterDist, temp_range[0], temp_range[2], temp_range[1], temp_range[2], max_water_dist)
    send_text(send_to, subject, body)               # Sends the text message.

# Event logger.
def log_event(event):
    currentTime = datetime.now().strftime("%Y:%M:%d:%H:%M:%S")       # Stores current time in hours, minutes, and seconds as a string.
    daily_event_log[currentTime] = event         # Event key is the time the event occurred, value is the event itself.
    print(currentTime + ': ' + event)            # Prints time and event to console.

# Records sensor data for daily report using time in hours/minutes rounded to half-hour increments. Since we are using
# only hours and minutes, the previous day's record data will be overwritten, eliminating the need to empty the
# dictionaries each day.
def record_data(time, avg_temp, avg_waterDist):
    daily_temp_record[time.strftime('%H:%M')] = avg_temp
    daily_waterDist_record[time.strftime('%H:%M')] = avg_waterDist
    print('Record recorded for the time: ' + time)

# Compiles data into a graph and sends it and a message to the tank owner.
# NEED TO PLACE THIS FUNCTION CALL IN THE CODE STILL.
def daily_update():
    #PROBLEM\NOTE: This only lets us graph one set of data (either temperature or water distance (CONSIDER NOT REPORTING WATER LEVEL GRAPHICALLY, JUST USE DATA))
    data = # NEED TO COMPILE TEMPERATURES HERE (in string separated by commas  (e.g.     '12,67,56,34,23'))
    labels = # NEED TO COMPILE TIMES HERE --> think about the first day after turning on the machine. It may not have records for all hours, so you should clear the logged data at the end of this function.
    message = """\     
     
     """           # NEED TO SET MESSAGE HERE
    title = 'Daily Tank Summary:' + datetime.now().strftime("%Y:%M:d")
    resp = requests.post('https://textbelt.com/sms-chart', {
        'phone': str(send_to),
        'message': message,
        'data': data,
        'title': title,
        'labels': labels,
        'key': 'textbelt',      # I THINK THIS WILL BE A CUSTOM KEY THEY GIVE
    })
    print(resp.json())


# Responsible for creating and sending text message.
def send_text(send_to, subject, body):
    gmail_user = "khatrisujata025@gmail.com"
    gmail_password = "Suzata123$"
    while True:
        try:
           urllib.request.urlopen("http://www.google.com").close()
        except urllib.request.URLError:
            print("Network not up yet")
            sleep(30)
        else:
            print("Network connected")
            break

    # Get the IP address, hostname and create the email message parameters.
    #subject = '!!!!MOTION  DECTECTED!!!'
    sent_from = gmail_user
    ip = subprocess.getoutput('hostname -I')
    hostname = subprocess.getoutput('hostname')
    print(ip)
    tostr = ", ".join(send_to)

    email_text = """\
From: %s
To: %s
Subject: %s

%s
    """ % (sent_from, tostr, subject, body)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        message = 'subject: {}\n\n{}'.format(subject, email_text)
        server.sendmail(sent_from, send_to, message)
        server.close()
        print("Text Succesfully Sent!")
    except:
        print("Something went wrong")



#### PROGRAM EXECUTION BEGINS HERE ####
main()
