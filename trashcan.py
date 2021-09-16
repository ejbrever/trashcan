import argparse
import time

import RPi.GPIO as GPIO

from flask_login import current_user
from flask import Flask, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

parser = argparse.ArgumentParser(description='service')
parser.add_argument('--port', dest='port', type=int, help='port')
parser.add_argument('--host', dest='host', type=str, help='Host IP address')
parser.add_argument('--secret', dest='secret', type=str, help='Secret to run webhook')
args = parser.parse_args()

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address)

def openTrashCan():
    servo_pin = 19
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(servo_pin, GPIO.OUT)
    pwm = GPIO.PWM(servo_pin, 50) # 50 Hz (20 ms PWM period).
    pwm.start(2.0) # Initialize the servo to 0 degrees.
    time.sleep(0.3) # Wait for movement.
    pwm.ChangeDutyCycle(7.0) # Rotate to 90 degrees.
    time.sleep(1.0) # Wait for movement.
    pwm.start(2.0) # Initialize the servo to 0 degrees.
    pwm.ChangeDutyCycle(0.0)  # Turn off to prevent jitter.
    pwm.stop() # Stops the PWM.
    GPIO.cleanup()

@app.route('/webhook', methods=['POST', 'GET'])
@limiter.limit('3/minute')
def webhook():
    if request.method == 'GET':
        return 'GET not supported', 200

    if request.data != args.secret.encode('utf-8'):
        print('invalid secret, got %s, want %s' % (request.data, args.secret.encode('utf-8')))
        return 'invalid secret', 200

    print('opening the trash can')
    openTrashCan()
    return 'opened trash', 200


if __name__ == '__main__':
    app.run(port = args.port, host=args.host)
