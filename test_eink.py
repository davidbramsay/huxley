#!/usr/bin/python
# -*- coding:utf-8 -*-

import epd7in5
import time
from PIL import Image,ImageDraw,ImageFont
import traceback
import os

try:

    title = "THIS TITLE 2"
    os.system('ssh pi@raspberrypi.local \'./papirus-fill.py "' + title + '"\'')

    '''
    epd_page = epd7in5.EPD(cover=False)
    epd_page.init()
    
    print "read bmp file"
    Himage = Image.open('test2.bmp')
    epd_page.display(epd_page.getbuffer(Himage))

    epd_page.sleep()
    '''

    epd_cover = epd7in5.EPD(cover=True)
    epd_cover.init()

    print "read bmp file"
    Himage = Image.open('test3.bmp')
    epd_cover.display(epd_cover.getbuffer(Himage))

    epd_cover.sleep()
        
except:
    print 'traceback.format_exc():\n%s' % traceback.format_exc()
    exit()

