import argparse
import threading
import time

import RPi.GPIO as GPIO

from flask_login import current_user
from flask import Flask, request, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from MCP3008 import MCP3008

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
    time.sleep(2)  # Wait 2 second just so we don't trigger to often.


# Watch the distance IR sensor for movement.
class WatchForSwipe(object):
  """Thread to watch for a physical swipe to open the trashcan."""

  def __init__(self):
    thread = threading.Thread(target=self.run, args=())
    thread.daemon = True
    thread.start()
    self.adc = MCP3008()

  def __voltageFromChannel(self, ch):
    return self.adc.read(channel=ch) / 1023.0 * 3.3

  def __only_left_triggered(self):
    value1 = self.__voltageFromChannel(0)
    value2 = self.__voltageFromChannel(1)
    if value1 > 1 and value2 < 0.5:  # If the voltage > 1, something got close.
      return True
    return False

  def __only_right_triggered(self):
    value1 = self.__voltageFromChannel(0)
    value2 = self.__voltageFromChannel(1)
    if value2 > 1 and value1 < 0.5:
      return True
    return False

  def __both_triggered(self):
    value1 = self.__voltageFromChannel(0)
    value2 = self.__voltageFromChannel(1)
    if value1 > 1 and value2 > 1:
      return True
    return False

  def run(self):
    while True:
      if self.__only_left_triggered():
        for _ in range(10):
          time.sleep(0.05)
          if self.__only_right_triggered():
            print('opening the trash can from swipe')
            openTrashCan()
            break
          if self.__both_triggered():
            print('both sensors activated, so do nothing')
            break

      elif self.__only_right_triggered():
        for _ in range(10):
          time.sleep(0.05)
          if self.__only_left_triggered():
            print('opening the trash can from swipe')
            openTrashCan()
            break
          if self.__both_triggered():
            print('both sensors activated, so do nothing')
            break
      time.sleep(0.05)


WatchForSwipe()


@app.route('/webhook', methods=['POST', 'GET'])
@limiter.limit('3/minute')
def webhook():
    if request.method == 'GET':
        return 'GET not supported', 200

    if request.data != args.secret.encode('utf-8'):
        print('invalid secret, got %s, want %s' % (request.data, args.secret.encode('utf-8')))
        return 'invalid secret', 200

    print('opening the trash can from webhook')
    openTrashCan()
    return 'opened trash', 200


if __name__ == '__main__':
    app.run(port = args.port, host=args.host)
