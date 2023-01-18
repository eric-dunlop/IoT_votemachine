from time import sleep
from datetime import datetime
from smbus import SMBus
from gpiozero import LED, Button
import awssub as aws
from json import dumps, load
from uuid import uuid4


# light sensors are an iterable class that each knows what channel it is on and its value identifies the thing being voted for
class Light_sensor():
  _registry = []

  def __init__(self, channel, value):
    self._registry.append(self)
    self.channel = channel
    self.value = value
    self.zero = 0

  def __iter__(self):
    return iter(self._registry)

  # returns the current value on the sensor
  def read(self, bus):
    bus.write_byte(0x4b, 0x84 + self.channel)
    return bus.read_byte(0x4b)

  # sets a referance point to compare the current value against.
  def calibrate(self, bus):
    self.zero = self.read(bus)
    print(self.zero)

#===========================================================================


# calibrates all the sensors

def calibrate():
  for sens in Light_sensor._registry:
    sens.calibrate(bus)
  blue_led.value = 1
  print("calibration complete")
  aws.log(f"{str(datetime.now())[:19]} calibrated\n")

#===========================================================================
# on a read that looks like a vote or clear, it is checked again 0.7 sec later to prevent misreads

def double_check(result):
  sleep(.7)
  if result == [x for x in Light_sensor._registry if x.read(bus) < x.zero + 0x20]:
    yellow_led.value = 0
    green_led.value = 1
    return result[0].value
  else:
    return None

#===========================================================================
# function that waits for all sensors to be clear before it will allow a vote to be registered
# used to ensure the same ticket dosent get read multiple times.
# double check that the sensors are clear
# if not clear on check, calls wait_clear again

def wait_clear():
  global attempts
  attempts = 0
  reset = [0]

  while len(reset) != 3:
    reset = [x for x in Light_sensor._registry if x.read(bus) < x.zero + 0x20]
    sleep(0.1)
  
  if double_check(reset):
    attempts = 0
    for led in all_lights:
      led.value = 0
    # blue_led.value = 1

  else:
    wait_clear()

#===========================================================================
# bus, sensors, LED and button objects defined
bus = SMBus(1)
sens1 = Light_sensor(0x40, "Mac OS")
sens2 = Light_sensor(0x10, "Linux")
sens3 = Light_sensor(0x50, "Windows")

green_button = Button(18, pull_up = True)

red_led = LED(23)
yellow_led = LED(24)
green_led = LED(21)
blue_led = LED(16)
all_lights = [red_led, yellow_led, green_led, blue_led]

attempts = 0

# button to recalibrate in case of changing light conditions
green_button.when_released = calibrate

# calibrate all the sensors on start up
calibrate() 

while True:
  try:
    # makes a list of all the sensor objects that are exposed to light
    result = [x for x in Light_sensor._registry if x.read(bus) < x.zero + 0x20]
    # 1 sensor uncovered, register the vote
    if len(result) != 1:
      blue_led.value = 1

    else:
      blue_led.value = 0
      yellow_led.value = 1

      if double_check(result):
        print(f"vote for {result[0].value}")
        new_id = str(uuid4())
        curtime = str(datetime.now())[:19]
        payload = dumps({"time" : curtime,
                         "vote" : result[0].value,
                         "uuid" : new_id})

        aws.awsClient.publish(aws.publish_topic, payload, qos=aws.publish_qos)
        aws.log(f"{curtime} : vote for {result[0].value} -  {new_id}\n")
        wait_clear()

      yellow_led.value = 0
      attempts += 1

      # on 3rd failed attempt forces the sensors to be cleared to continue
      if attempts > 2:
        print("misread")
        aws.log(f"{str(datetime.now())[:19]} misread\n")
        red_led.value = 1
        wait_clear()
  
  except KeyboardInterrupt:
    for light in all_lights:
      light.value = 0
    aws.shut_down()