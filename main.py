from datetime import datetime, timedelta
from gpiozero import LED
from time import sleep
import smtplib
import subprocess
import urllib.request
import requests

#
#
#
#

max_waterDist = 2               # maximum allowable distance from water level to sensor
temp_range = [68,80,'F']        # low temp, high temp, units
daily_event_log = {}            # This dictionary stores each recorded alarm event and the time it was recorded.
daily_temp_record = {}          # List stores data points gathered for daily report
daily_waterDist_record = {}     # List stores data point gathered for daily report
send_to = ['9378251843@tmomail.net']        # Number to which alerts and notifications will be sent.

Light = LED()        # Relay object to control lighting system.
Light_setting = 'disabled'   # Holds light setting (has the states disabled, always on, or adaptive to light level).
Light_status = 'off'         # Holds light status (on or off).
Feeder =             # Servo motor to control feeding system.
Feeder_setting = 'disabled'  # Holds feeder setting (has the states disabled, always on, and not to feed at night).



# Main program function. Responsible for looping and executing other checks and functions as needed.
def main():
    last_record_date = floor_half_hour(datetime.now())          # Rounds backwards to the nearest half hour from the current time.


    while True:     # Sensor data is checked on every loop.

        avg_temp, avg_waterDist = average_values()                   # Records an average of the values over a period of time.
        current_rounded_time = floor_half_hour(datetime.now())       # Round current time to last half 30-minute interval.
        if last_record_date != current_rounded_time:                 # Checks if half an hour has passed since last log. If so, log the data and update the last_data_log value.
            record_data(current_rounded_time, avg_temp, avg_waterDist)      # Records data for this time.
            last_record_date = current_rounded_time
        if not (temp_range[0] <= avg_temp <= temp_range[1]) or (avg_waterDist <= max_waterDist):       # Checks if the average temp is NOT within the desired range OR if the average water level is NOT above the desired amount.
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
    if (avg_waterDist > max_waterDist):        # Executes if distance to water is greater than desired.
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
    """ % (event, avg_temp, avg_waterDist, temp_range[0], temp_range[2], temp_range[1], temp_range[2], max_waterDist)
    send_text(send_to, subject, body)               # Sends the text message.

# Event logger.
def log_event(event):
    currentTime = datetime.now().strftime("%Y:%M:%d:%H:%M:%S")       # Stores current time in hours, minutes, and seconds as a string.
    daily_event_log[currentTime] = event         # Event key is the time the event occurred, value is the event itself.
    print(currentTime + ': ' + event)            # Prints time and event to console.

# CONSIDER LOGGING THESE EITHER IN SEPARATE FILES OR IN A SINGLE FILE FOR THIS DAY!
# Records sensor data for daily report using time in hours/minutes rounded to half-hour increments.
def record_data(time, avg_temp, avg_waterDist):
    global daily_temp_record
    time_str = time.strftime('%H:%M')
    if time_str == '00:00':                 # If it is past 12am (midnight), initiate the daily update before recording the data.
        daily_update()
    daily_temp_record[time_str] = avg_temp      # daily_update() wipes these dictionaries, meaning these will be the first entries.
    daily_waterDist_record[time_str] = avg_waterDist
    print('Data recorded for the time: ' + time)



# Compiles data into a graph and sends it and a message to the tank owner.
def daily_update():
    global daily_temp_record, daily_event_log
    data = ''
    labels = ''
    for record in daily_temp_record:        # Loops through recorded data to populate strings in CSV format to be used by external graphing API.
        data += str(daily_temp_record[record]) + ','
        labels += str(record) + ','                     # MAKE SURE API INTERPRETS INTERVAL VALUES WELL.
    if data[-1] == ',':                     # If there is a trailing comma, removes the comma from both data and labels (if trailing comma in data, can assume also in labels).
        data = data[:-1]
        labels = labels[:-1]
    daily_waterDist_change = list(daily_waterDist_record.items())[0][1] - list(daily_waterDist_record.items())[len(daily_waterDist_record) - 1][1]      # Water level difference from start to end of day.
    distance_to_max_waterDist = list(daily_waterDist_record.items())[len(daily_waterDist_record) - 1][1] - max_waterDist

    # BE SURE TO VERIFY UNITS USED IN DATA DISPLAYED HERE. CONSIDER INDICATING IF WATER LEVEL HAS RISEN VS DECREASING (in case user fills tank throughout day)
    # In the area "Services", we will list the services, their status (for feeder, its cycle or if it is off; for LED, its cycle of if it is off), and if they are currently on (relevant to LED only).
    message = """     
\n\t Daily Tank Summary: %s

Water Level:
\tChange (since last update): %smm
\tDistance to minimum allowable level: %smm
     
Services:
\tLED : %s, %s
\tFeeder : %s

Event(s):
""" % (datetime.now().strftime("%Y:%M:d"), str(daily_waterDist_change), str(distance_to_max_waterDist), Light_setting, Light_status, Feeder_setting)
    # Adds events to end of message if there are any events.
    if len(daily_event_log) > 0:            #Checks if there are any events. If so, lists them in message. If not, notifies user.
        for event in daily_event_log:
            message += "\t" + event + ' | ' + daily_event_log[event]
    else:
        message += "\tNo events logged."

    title = '24-Hr Temperature Graph'
    resp = requests.post('https://textbelt.com/sms-chart', {
        'phone': str(send_to),
        'message': message,
        'data': data,
        'title': title,
        'labels': labels,
        'key': 'textbelt',      # I THINK THIS WILL BE A CUSTOM KEY THEY GIVE
    })
    print("This is the response: " + resp.json())
    print("The daily update has been sent.")
    daily_temp_record = {}      # CONSIDER WRITING DATA TO A LOG FILE BEFORE WIPING THE DATA. CONSIDER LOGGING WHEN DATA IS ACTUALLY RECORDED.
    daily_event_log = {}            # IF DECIDE TO LOG DATA, LOG EVENTS AT EVENT FUNCTION.

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
