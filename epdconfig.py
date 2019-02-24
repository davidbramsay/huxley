# /*****************************************************************************
# * | File        :	  EPD_1in54.py
# * | Author      :   Waveshare team
# * | Function    :   Hardware underlying interface
# * | Info        :
# *----------------
# * |	This version:   V2.0
# * | Date        :   2018-11-01
# * | Info        :
# * 1.Remove:
#   digital_write(self, pin, value)
#   digital_read(self, pin)
#   delay_ms(self, delaytime)
#   set_lut(self, lut)
#   self.lut = self.lut_full_update
# ******************************************************************************/
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#


import spidev
import RPi.GPIO as GPIO
import time

# Pin definition
PAGE_RST_PIN         = 17
PAGE_DC_PIN          = 25
PAGE_CS_PIN          = 8
PAGE_BUSY_PIN        = 24

COVER_RST_PIN         = 27
COVER_DC_PIN          = 22
COVER_CS_PIN          = 7
COVER_BUSY_PIN        = 23

# SPI device, bus = 0, device = 0
SPI = spidev.SpiDev(0, 0)

def digital_write(pin, value):
    GPIO.output(pin, value)

def digital_read(pin):
    return GPIO.input(pin)

def delay_ms(delaytime):
    time.sleep(delaytime / 1000.0)

def spi_writebyte(cs_pin, data):
    GPIO.output(cs_pin, GPIO.LOW)
    SPI.writebytes(data)
    GPIO.output(cs_pin, GPIO.HIGH)

def module_init(cover):
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    if cover:
        GPIO.setup(COVER_RST_PIN, GPIO.OUT)
        GPIO.setup(COVER_DC_PIN, GPIO.OUT)
        GPIO.setup(COVER_CS_PIN, GPIO.OUT)
        GPIO.setup(COVER_BUSY_PIN, GPIO.IN)
        GPIO.output(COVER_CS_PIN, GPIO.HIGH)
    else:
        GPIO.setup(PAGE_RST_PIN, GPIO.OUT)
        GPIO.setup(PAGE_DC_PIN, GPIO.OUT)
        GPIO.setup(PAGE_CS_PIN, GPIO.OUT)
        GPIO.setup(PAGE_BUSY_PIN, GPIO.IN)
        GPIO.output(PAGE_CS_PIN, GPIO.HIGH)

    SPI.max_speed_hz = 2000000
    SPI.mode = 0b00
    return 0;

### END OF FILE ###
