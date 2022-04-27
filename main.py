# Written By: Samuel Long

# This is a fish tank monitor system deplayed on a Raspberry Pi. This system measures the temperature and water level inside the tank. It also
# offers automated feeding and lighting features. Data and events are stored in logfiles. On alert events, the user is notified via MMS messages
# about the current tank conditions. Daily, the user receives a summary of the tank data recorded in the past 24 hours.

from datetime import datetime, timedelta
from gpiozero import LED, Button, MCP3208, Servo, DistanceSensor
import RPi.GPIO as GPIO
import I2C_LCD_driver
from time import sleep
import time
import smtplib
import subprocess
import urllib.request
import requests
import os
import json
import math

GPIO.setmode(GPIO.BCM)
os.system('sudo pigpiod')  # Ensures pigpiod service is running.
sleep(5)
from gpiozero.pins.pigpio import PiGPIOFactory
factory = PiGPIOFactory()
light_threshold = 1300  # Light threshold: light levels equal or higher than this value are considered "Day", light levels below this level are considered "Night."
waterDist = [20, 'cm']  # Water distance data: maximum allowable distance, units.
temp_range = [68, 80, 'F']  # Temperature data: low temp, high temp, units.
daily_event_log = {}  # Stores each recorded event and the time it was recorded.
daily_temp_record = {}  # Stores temperature data points gathered for daily report.
daily_waterDist_record = {}  # Stores water level data points gathered for daily report.
phone = ''
send_to = '+18593545019@vzwpix.com'  # Number to which alerts and notifications will be sent.

KEY_MATRIX = [[1, 2, 3, 'A'],  # Matrix represeting the keypad, stored in rows (lists) and columns (keys inside lists).
              [4, 5, 6, 'B'],
              [7, 8, 9, 'C'],
              ['.', 0, '#', 'D']]
KEY_ROW = [23, 24, 25, 12]  # GPIO pins used for keypad rows.
KEY_COL = [18, 22, 27, 17]  # GPIO pins used for keypad columns.
for l in range(4):  # Output pins created and configured.
    GPIO.setup(KEY_COL[l], GPIO.OUT)
    GPIO.output(KEY_COL[l], 1)
for p in range(4):  # Input pins created and configured.
    GPIO.setup(KEY_ROW[p], GPIO.IN, pull_up_down=GPIO.PUD_UP)

button_alarmControl = Button(26, pull_up=True, bounce_time=0.25, hold_time=3)
button_featureControl = Button(16, pull_up=True, bounce_time=0.25, hold_time=3)
lcd = I2C_LCD_driver.lcd()  # LCD display object.
lcd.lcd_clear()  # Initially clear.
lcd_text = ''
temperature = MCP3208(channel=0, differential=False, max_voltage=3.3)  # Temperature sensor object.
light_sensor = MCP3208(channel=1, differential=False, max_voltage=3.3)  # Light sensor object.

light_switch = LED(19)  # Relay used to switch on and off the lighting.
light_switch.off()  # Initially off.
alarm_status = 'off'
light_setting = 'off'  # Light setting (off, on, or nighttime (light sensitive)).
light_status = 'off'  # Current light state.
feeder_setting = 'off'  # Feeder setting (off, on, and daytime (light sensitive)).
feeder_status = 'off'  # Current feeder state.
feeder_motor = Servo(5, pin_factory=factory)  # Servo motor to control feeding system.
feeder_motor.min()
feeder_interval = '30'  # Feeder interval in minutes.
distance_sensor = DistanceSensor(echo=6, trigger=13, max_distance=3)

working_dir = '/home/pi/Fish_Tank_Monitor/'  # System working directory.
log_dir = working_dir + 'Logs/'  # Directory for log storage.
if not os.path.exists(working_dir):  # Creates the working directory if it does not exist.
    os.makedirs(working_dir)
if not os.path.exists(log_dir):  # Creates the log directory if it does not exist.
    os.makedirs(log_dir)
os.chdir(working_dir)  # Changes to the working directory.

# Alarm System setup steps.
def alarm_setup():
    global lcd_text, alarm_status, phone, temp_range, waterDist
    lcd.lcd_clear();
    lcd.lcd_display_string("..ALARM SETUP...", 1);
    sleep(3);
    lcd.lcd_clear()
    lcd.lcd_display_string("Alarm System:", 1);
    lcd_text = "1)on 2)off";
    alarm_status = user_input(2, 'none');
    lcd_text = '';
    lcd.lcd_clear();
    print("Alarm Status:", alarm_status)
    if alarm_status == '1':
        alarm_status = 'on'
        lcd.lcd_display_string("Phone #:", 1);
        sleep(0.5);
        phone = user_input(2, 'update');
        lcd.lcd_clear();
        print("Phone number is:", phone)
        lcd.lcd_display_string("Temp Units:", 1);
        sleep(0.5);
        lcd_text = "1)F 2)C";
        temp_unit = user_input(2, 'none');
        lcd_text = '';
        lcd.lcd_clear();
        print("Temperature Unit Key:", temp_unit)
        if temp_unit == '1':
            temp_range[2] = 'F'
        else:
            temp_range[2] = 'C'
        print('The unit is: ' + temp_range[2])
        lcd.lcd_display_string("Low Temp (" + temp_range[2] + '):', 1);
        sleep(0.5);
        temp_range[0] = int(user_input(2, 'update'));
        lcd.lcd_clear();
        print("Low Temperature:", temp_range[0])
        lcd.lcd_display_string("High Temp (" + temp_range[2] + '):', 1);
        sleep(0.5);
        temp_range[1] = int(user_input(2, 'update'));
        lcd.lcd_clear();
        print("High Temperature:", temp_range[1])
        lcd.lcd_display_string("Dist Units:", 1);
        sleep(0.5);
        lcd_text = "1)in 2)cm";
        dist_unit = user_input(2, 'none');
        lcd_text = '';
        lcd.lcd_clear();
        print("Distance Unit Key:", dist_unit)
        if dist_unit == '1':
            waterDist[1] = 'in'
        else:
            waterDist[1] = 'cm'
        print('The unit is: ' + waterDist[1])
        lcd.lcd_display_string("Measure Dist:", 1);
        sleep(0.5);
        lcd_text = "Enter if ready";
        dist_confirm = user_input(2, 'none');
        lcd_text = '';
        lcd.lcd_clear()
        lcd.lcd_display_string("Measure in 3", 1);
        sleep(1);
        lcd.lcd_display_string("Measure in 2", 1);
        sleep(1);
        lcd.lcd_display_string("Measure in 1", 1);
        sleep(1)
        lcd.lcd_display_string("Measuring...", 1);
        x, waterDist[0], x = average_values();
        lcd.lcd_clear()
        lcd.lcd_display_string("Measured:", 1);
        lcd.lcd_display_string(str(waterDist[0]) + str(waterDist[1]), 2);
        sleep(2);
        lcd.lcd_clear()
    else:
        alarm_status = 'off'
    lcd.lcd_display_string("ALARM SETUP", 1);
    lcd.lcd_display_string("COMPLETE!", 2);
    sleep(1)
    print("ALARM SETUP complete.")

# Features setup steps (feeding and lighting system).
def feature_setup():
    global lcd_text, feeder_setting, feeder_interval, light_setting
    lcd.lcd_clear();
    lcd.lcd_display_string("....FEATURES....", 1);
    sleep(2);
    lcd.lcd_clear()
    # Feeding system setup.
    lcd.lcd_display_string("Feeding System:", 1);
    sleep(0.5);
    lcd_text = "1)on 2)off";
    feeder_setting = user_input(2, 'none');
    lcd_text = '';
    lcd.lcd_clear();
    print("Feeder Status:", feeder_setting)
    if feeder_setting == '1':
        feeder_setting = 'on'
        lcd.lcd_display_string("Off at night?", 1);
        sleep(0.5);
        lcd_text = "1)yes 2)no";
        night_active = user_input(2, 'none');
        lcd_text = '';
        lcd.lcd_clear();
        print("Night Active Status:", night_active)
        if night_active == '1':
            feeder_setting = 'daytime'
        lcd.lcd_display_string("Interval (hours):", 1);
        sleep(0.5);
        feeder_interval = user_input(2, 'update');
        lcd.lcd_clear();
        print("Feeding interval is:", feeder_interval)
    else:
        feeder_setting = 'off'
        feeder_status = 'off'
    # Lighting system setup.
    lcd.lcd_display_string("Light System:", 1);
    sleep(0.5);
    lcd_text = "1)on 2)off";
    light_setting = user_input(2, 'none');
    lcd_text = '';
    lcd.lcd_clear();
    print("Light Status:", light_setting)
    if light_setting == '1':
        light_setting = 'on'
        lcd.lcd_display_string("Off in day?", 1);
        sleep(0.5);
        lcd_text = "1)yes 2)no";
        day_active = user_input(2, 'none');
        lcd_text = '';
        lcd.lcd_clear();
        print("Day Active Status:", day_active)
        if day_active == '1':
            light_setting = 'nighttime'
        else:
            light_switch.on()
    else:
        light_setting = 'off'
        light_status = 'off'
        light_switch.off()
    lcd.lcd_display_string("FEATURE SETUP", 1);
    lcd.lcd_display_string("COMPLETE!", 2);
    sleep(1);
    lcd.lcd_clear()
    print("FEATURES SETUP complete.")

# Accepts keypad inputs from the user and returns the input string when "#" pressed. Optionally displays user input on LCD display.
# Identifies which key is pressed by looping through each column, setting the pins in the column to LOW, and checking which pin is active. 
def user_input(line, mode):
    global KEY_ROW, KEY_COL, lcd_text
    input_str = ''  # Stores the string input by the user.
    lcd.lcd_display_string(lcd_text, line)  # Displays input prompts.
    while True:
        for x in range(4):  # Loops through each column.
            GPIO.output(KEY_COL[x], 0)  # Sets pins in column to LOW.
            for i in range(4):  # Loops through each row in the column.
                if GPIO.input(KEY_ROW[i]) == 0:  # If pin is active, the key is pressed.
                    key_pressed = KEY_MATRIX[i][x]
                    if key_pressed == '#':  # If user inputs "#", returns the input string.
                        return input_str
                    if mode == 'update':  # Update mode -> adds to the input string.
                        input_str += str(key_pressed)
                    elif mode == 'replace':  # Replace mode -> replaces the input string (one character input).
                        input_str = str(key_pressed)
                    elif mode == 'none':  # None mode -> returns the input string immediately (one character input).
                        return str(key_pressed)
                    lcd.lcd_display_string(lcd_text + input_str, line)  # Updates the display with the user's new input.
                    while (GPIO.input(
                            KEY_ROW[i]) == 0):  # Loops while key is pressed to avoid multiple inputs being recorded.
                        sleep(0.05)
            GPIO.output(KEY_COL[x], 1)  # Sets pins in column back to HIGH.

# Main program function. Responsible for looping and executing other checks and functions as needed.
def main():
    global feeder_status, light_status
    last_record_date = floor_half_hour(
        datetime.now())  # Rounds backwards to the nearest half hour from the current time.
    last_feed_date = datetime.now()

    while True:
        # Event-based triggeres
        button_alarmControl.when_held = button_alarm_event
        button_featureControl.when_held = button_feature_event

        print("MAIN loop.")
        avg_temp, avg_waterDist, avg_lightLvl = average_values()  # Records an average of the values over a period of time.
        # print("Temp: " + str(avg_temp) + " Distance: " + str(avg_waterDist) + " Light Level: " + str(avg_lightLvl))
        lcd.lcd_clear()
        lcd.lcd_display_string('Temp: ' + str(avg_temp) + str(temp_range[2]), 1)
        lcd.lcd_display_string('Dist: ' + str(avg_waterDist) + str(waterDist[1]), 2)
        if avg_lightLvl >= light_threshold:  # If light level is considered "Day", night features = off, day features = on.
            if feeder_setting == 'daytime':
                feeder_status = 'on'
            if light_setting == 'nighttime' and light_status == 'on':  # Turn off light.
                light_switch.off()
                light_status = 'off'
        else:  # If light level is considered "Night", night features = on, day features = off.
            if feeder_setting == 'daytime':
                feeder_status = 'off'
            if light_setting == 'nighttime' and light_status == 'off':  # Turn on light.
                light_status = 'on'
                light_switch.on()

        time_from_last_feed = (datetime.now() - last_feed_date).total_seconds() / 3600

        if time_from_last_feed >= int(feeder_interval) and (feeder_setting == 'on' or feeder_status == 'on'):
            for i in range(2):
                feeder_motor.max()
                sleep(0.25)
                feeder_motor.min()
                sleep(0.25)
            last_feed_date = datetime.now()
        current_rounded_time = floor_half_hour(datetime.now())  # Round current time to last half 30-minute interval.
        if last_record_date != current_rounded_time:  # Checks if half an hour has passed since last log. If so, log the data and update the last_data_log value.
            record_data(current_rounded_time, avg_temp, avg_waterDist)  # Records data for this time.
            last_record_date = current_rounded_time
        if alarm_status == 'on':
            if not (temp_range[0] <= avg_temp <= temp_range[1]) or (avg_waterDist <= waterDist[
                0]):  # Checks if the average temp is NOT within the desired range OR if the average water level is NOT above the desired amount.
                lcd.lcd_clear()
                alarm(avg_temp, avg_waterDist)  # If one of the values is outside what is desired, initiate the alarm.
        sleep(60)  # Waits 60 seconds before restarting loop.

# Rounds down the time passed to the nearest 30-min interval by checking the minute.
def floor_half_hour(time):
    if time.minute < 30:
        return time.replace(minute=0, second=0, microsecond=0)
    else:
        return time.replace(minute=30, second=0, microsecond=0)

# Calculates temperature, water level, and light level values by averaging 100 points of data over 10 seconds.
def average_values():
    global light_switch
    sum_temp = 0
    sum_waterDist = 0
    sum_lightLvl = 0
    for i in range(100):  # Over 10 seconds, gathers 100 data points from each sensor.
        if temp_range[2] == 'F':
            sum_temp += (temperature.voltage * 180) + 32  # Converts voltage to F.
        else:
            sum_temp += (temperature.voltage * 100)  # Converts voltage to C.
        if waterDist[1] == 'cm':
            sum_waterDist += distance_sensor.distance * 100  # Distance in cm.
        else:
            sum_waterDist += distance_sensor.distance * 39.37  # Distance in in.
        sum_lightLvl += light_sensor.raw_value
        print(light_sensor.raw_value)
        sleep(0.1)
    return math.ceil(sum_temp) / 100, math.ceil(sum_waterDist) / 100, math.ceil(sum_lightLvl) / 100

# Generates/logs events and sends an MMS message to the tank owner.
def alarm(avg_temp, avg_waterDist):
    event = ''
    if (avg_waterDist > waterDist[0]):  # If the distance is greater than desired, record event.
        event = event + 'Water level is too LOW! '
        lcd.lcd_display_string('WTR LVL LOW!', 1)
    if (avg_temp > temp_range[1]):  # If the temperature is greater than desired, record event.
        event = event + 'Temperature is too HIGH! '
        lcd.lcd_display_string('TEMP TOO HIGH!', 2)
    elif (avg_temp < temp_range[0]):  # If the distance is lower than desired, record event.
        event = event + 'Temperature is too LOW! '
        lcd.lcd_display_string('TEMP TOO LOW!', 2)
    log_event(event)  # Logs recorded events to daily_event_log and to logfile.
    subject = 'FISH TANK ALERT!'
    body = """
ALARMS
-----------------
%s

Temperature
-----------------
Current: %.2f%s
Desired: %.2f%s - %.2f%s

Water Level
-----------------
Current: %.2f%s
Desired: <= %.2f%s""" % (
    event, avg_temp, temp_range[2], temp_range[0], temp_range[2], temp_range[1], temp_range[2], avg_waterDist,
    waterDist[1], waterDist[0], waterDist[1])
    send_text(send_to, subject, body)  # Sends alert message to the tank owner.

# Adds event to the dictionary of daily events and adds it to a log file.
def log_event(event):
    global daily_event_log
    currentTime = datetime.now().strftime("%Y:%m:%d:%H:%M:%S")  # Current time in hours, minutes, and seconds.
    daily_event_log[currentTime] = event  # Stores event to dictionary with the current time as the key.
    log_data_to_file(datetime.now().strftime("%Y:%m:%d"), 'events',
                     currentTime + ': ' + event + '\n')  # Logs event to event log file.

# Records sensor data for daily report using time in hours/minutes rounded to half-hour increments.
def record_data(time, avg_temp, avg_waterDist):
    global daily_temp_record, daily_waterDist_record
    time_str = time.strftime('%H:%M')  # Stores hours and minutes of time argument.
    if time_str == '00:00':  # If it is 12am (midnight), initiate the daily update (wipes daily records after completion).   CHANGE THIS VALUE BACK TO MIDNIGHT ('00:00')
        daily_update()
    daily_temp_record[time_str] = avg_temp  # Stores temperature record to dictionary with time as the key.
    daily_waterDist_record[time_str] = avg_waterDist  # Stores water distance record to dictionary with time as the key.
    log_data_to_file(datetime.now().strftime("%Y:%m:%d"), 'temp_record',
                     time_str + ': ' + str(avg_temp) + '\n')  # Saves avg_temp to log file.
    log_data_to_file(datetime.now().strftime("%Y:%m:%d"), 'waterDist_record',
                     time_str + ': ' + str(avg_waterDist) + '\n')  # Saves avg_waterDist to log file.

# Logs data to files using date and type of data. Date determines the folder in which the logs are stored; type determines the name of the log file.
def log_data_to_file(date, type, data):
    log_path = log_dir + date + '/'
    if not os.path.exists(log_path):  # If log folder for the current date does not exist, create it.
        os.mkdir(log_path)
    with open(log_path + type,
              'a') as file:  # Opens target log file in append mode (file is created if it does not exist).
        file.write(data)  # Data is written to the file.

# Compiles data into a graph and sends it and a message to the tank owner.
def daily_update():
    global daily_temp_record, daily_waterDist_record, daily_event_log
    data = ""
    labels = ""
    daily_waterDist_change = ""
    distance_to_waterDist = ""
    if len(daily_temp_record) > 0:
        for record in daily_temp_record:  # Loops through recorded data to populate strings in CSV format to be used by external graphing API.
            data += str(daily_temp_record[record]) + ','
            labels += str(record) + ','
        if data[
            -1] == ',':  # If there is a trailing comma, removes the comma from both data and labels (if trailing comma in data, can assume also in labels).
            data = data[:-1]
            labels = labels[:-1]
        daily_waterDist_change = int(list(daily_waterDist_record.items())[0][1]) - int(
            list(daily_waterDist_record.items())[len(daily_waterDist_record) - 1][
                1])  # Water level difference from start to end of day.
        distance_to_waterDist = int(list(daily_waterDist_record.items())[len(daily_waterDist_record) - 1][1]) - \
                                waterDist[0]
    # In the area "Features", we will list the features, their setting and their status.
    message = """\tDaily Tank Summary: %s
Water Level
------------
Change (since last update): %smm
Distance to minimum allowable level: %smm

Features
------------
LED : %s, %s
Feeder : %s, %s
Event(s):
""" % (datetime.now().strftime("%Y:%m:%d"), str(daily_waterDist_change), str(distance_to_waterDist), light_setting,
       light_status, feeder_setting, feeder_status)
    # Adds events to the end of the messsage. If daily_event_log is empty, displays no events have occured.
    if len(daily_event_log) > 0:
        for event in daily_event_log:
            message += "\t" + event + ' | ' + daily_event_log[event]
        message += ""
    else:
        message += "\tNo events logged."
    title = "Daily Temperature Graph"

    resp = requests.post('https://textbelt.com/sms-chart', {
        'phone': '+18593545019',
        'message': message,
        'data': data,
        'title': title,
        'labels': labels,
        'key': 'textbelt',
    })
    try:
        print(resp.json())
    except:
        print("Failed to parse JSON response.")
    print("The daily update has been triggered.")
    yesterdayDate = (datetime.today() - timedelta(days=1)).strftime("%Y:%m:%d")
    log_data_to_file(yesterdayDate, 'summary', json.dumps(message))  # Logs event to event log file.
    log_data_to_file(yesterdayDate, 'summary', json.dumps(daily_temp_record))  # Logs event to event log file.
    daily_waterDist_record = {}
    daily_temp_record = {}
    daily_event_log = {}

# Responsible for creating and sending text message.
def send_text(send_to, subject, body):
    gmail_user = "thisisanemailnotmyname@gmail.com"
    gmail_password = "PooperScooper12"
    while True:
        try:
            urllib.request.urlopen("http://www.google.com").close()
        except urllib.request.URLError:
            print("Network not up yet.")
            sleep(30)
        else:
            print("Network connected.")
            break

    sent_from = gmail_user
    ip = subprocess.getoutput('hostname -I')
    hostname = subprocess.getoutput('hostname')
    print(ip)
    tostr = ", ".join(send_to)

    email_text = """\
%s""" % (body)
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        message = 'subject: {}\n\n{}'.format(subject, email_text)
        server.sendmail(sent_from, send_to, message)
        server.close()
        print("Notification MMS sent!")
    except:
        print("Failed to send MMS notification!")

def button_alarm_event():
    alarm_setup()

def button_feature_event():
    feature_setup()


#### PROGRAM EXECUTION BEGINS HERE ####
alarm_setup()
feature_setup()
main()