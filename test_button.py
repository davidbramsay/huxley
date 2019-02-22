import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)

while True:
	timer = 0
	input_state = GPIO.input(16)

	while not input_state:
		timer += 1
		input_state = GPIO.input(16)

	if timer:
		print 'Button Pressed ' + str(timer)
		timer=0
		time.sleep(0.2)

#150000 = long press

