import RPi.GPIO as GPIO
import threading
import time
import smtplib

from datetime import datetime
from picamera import PiCamera

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

import sys, select

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

camera = PiCamera()
camera.rotation = 180

PIN_moveSensor = 4
PIN_redLED = 21
PIN_yellowLED = 16
PIN_buzzer = 12
PIN_greenLED = 23

from gpiozero import Servo
from time import sleep
from gpiozero.pins.pigpio import PiGPIOFactory
factory = PiGPIOFactory()
servo = Servo(18, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, pin_factory=factory)

BEAM_PIN = 20
GPIO.setup(BEAM_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.setup(PIN_moveSensor, GPIO.IN)
GPIO.setup(PIN_redLED, GPIO.OUT)
GPIO.setup(PIN_yellowLED, GPIO.OUT)
GPIO.setup(PIN_buzzer, GPIO.OUT)
GPIO.setup(PIN_greenLED, GPIO.OUT)

PWM_redLED = GPIO.PWM(PIN_redLED, 5)
PWM_redLED.start(0)

PWM_yellowLED = GPIO.PWM(PIN_yellowLED, 1)
PWM_yellowLED.start(0)

PWM_buzzer = GPIO.PWM(PIN_buzzer, 50)

insideZone = 'inside'
outsideZone = 'outside'
pinZone = 'wrong PIN'
photoName = ''
PIN = "1234"

print('Starting SECURITY SYSTEM')
time.sleep(1)
print('READY!!!\n')


def password(name):
    while True:
        temp = input('PIN: ')
        if (temp == PIN):
            print("PIN ok\nALARM off")
            break
        else:
            print("WRONG PIN!!!")


def sendEmail(whereMove):
    msg = MIMEMultipart()
    msg['From'] = 'XXX'
    msg['To'] = 'XXX'
    msg['Subject'] = '### ALARM ###' + whereMove
    message = 'ALARM'
    msg.attach(MIMEText(message))

    imageData = MIMEImage(open(photoName, 'rb').read(), 'jpg')
    imageData.add_header('Content-Disposition', 'attachment; filename="image.jpg"')
    msg.attach(imageData)

    mailserver = smtplib.SMTP('smtp.gmail.com', 587)
    mailserver.ehlo()
    mailserver.starttls()
    mailserver.ehlo()
    mailserver.login('XXX', 'XXX')

    mailserver.sendmail('XXX', 'XXX', msg.as_string())

    mailserver.quit()


def moveAndPhoto(where):
    global photoName
    photoName = '/home/pi/alarm_system/alarm-' + str(int(time.time())) + '.jpg'

    if (where == insideZone):
        servo.min()
        time.sleep(0.5)
        camera.capture(photoName)
        time.sleep(0.5)
        servo.mid()

    if (where == outsideZone):
        servo.max()
        time.sleep(0.5)
        camera.capture(photoName)
        time.sleep(0.5)
        servo.mid()

    if (where == pinZone):
        servo.mid()
        time.sleep(0.5)
        camera.capture(photoName)
        time.sleep(0.5)


def activeSensor():
    while True:
        if GPIO.input(PIN_moveSensor):
            moveAndPhoto(insideZone)

        if not GPIO.input(BEAM_PIN):
            moveAndPhoto(outsideZone)

def alarmStart(where):
    PWM_redLED.ChangeDutyCycle(50)
    print('\n#####ALARM#####\n')

    emilThread = threading.Thread(target=sendEmail(where), args=(2,))
    emilThread.start()

    passwordThread = threading.Thread(target=password, args=(1,))
    passwordThread.start()
    PWM_buzzer.start(80)

    while (passwordThread.is_alive()):
        PWM_buzzer.ChangeFrequency(466)
        time.sleep(0.1)
        PWM_buzzer.ChangeFrequency(330)
        time.sleep(0.2)

    PWM_buzzer.stop()
    PWM_redLED.ChangeDutyCycle(0)


def silentAlarm2(where):
    print('GLOBAL: -> ' + photoName)
    photoThread = threading.Thread(target=moveAndPhoto(where), args=(1,))
    photoThread.start()
    print('GLOBAL: -> ' + photoName)

    print('motion detected 10s')
    PWM_yellowLED.ChangeDutyCycle(50)

    i, o, e = select.select([sys.stdin], [], [], 10)

    if (i and sys.stdin.readline().strip()==PIN):
        print("PIN ok\nalarm deactivated")
        PWM_yellowLED.ChangeDutyCycle(0)

    else:
        print("Time 0s!\n")
        PWM_yellowLED.ChangeDutyCycle(0)
        alarmStart(where)


def break_beam_callback(channel):
    if GPIO.input(BEAM_PIN):
        print("beam unbroken")


def move_callback(channel):
    if GPIO.input(PIN_moveSensor):
        print("move unbroken")


def alarmActive():
    while True:
        if GPIO.input(PIN_moveSensor):
            print("move sensor")
            silentAlarm2(insideZone)
            break

        if not GPIO.input(BEAM_PIN):
            print("beam sensor")
            silentAlarm2(outsideZone)
            break


try:
    print('HELLO\nalarm deactivated')
    GPIO.output(PIN_greenLED, GPIO.HIGH)
    counter = 0
    while (True):
        tempPIN = input()

        if (tempPIN == PIN):
            print("PIN ok\nALARM activated")
            counter = 0
            GPIO.output(PIN_greenLED, GPIO.LOW)
            alarmActive()
            print('HELLO\nalarm deactivated')
            GPIO.output(PIN_greenLED, GPIO.HIGH)

        else:
            print("WRONG PIN!!!\n")
            counter += 1
            if (counter == 3):
                counter = 0
                print('ALARM')
                GPIO.output(PIN_greenLED, GPIO.LOW)
                moveAndPhoto(pinZone)
                alarmStart(pinZone)


except KeyboardInterrupt:
    PWM_redLED.stop()
    PWM_yellowLED.stop()
    PWM_buzzer.stop()
    servo.value = None;
    GPIO.cleanup()

finally:
    PWM_redLED.stop()
    PWM_yellowLED.stop()
    PWM_buzzer.stop()
    servo.value = None;
    GPIO.cleanup()
    sys.exit(0)