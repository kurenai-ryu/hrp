#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Basic loop example
1. starts connection
2. set 100ms filter_time
3. starts reading loop (it's a python generator read_tag())
4. break with Ctrl+C
5. stops reading and disconnect device
"""

import sys
import os
import traceback
import codecs


#fix path to use local module
sys.path.insert(1,os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from hrp import HRP, const, exception
from hrp.tag import TidReadParameter, TagAddress, MatchParameter

try:
    conn = HRP(ip='192.168.1.116', port=9090, ommit_ping=False, timeout=10)
    #conn.set_log_level_debug() # enable for debug information
    print ("Connecting")
    conn.connect()
    filter_time, RSSI_threshold = conn.tag_filter()
    conn.stop() #always before reading tag!
    conn.tag_filter(100, 0)
    print ("Connected! press Ctrl+C to break")
    #       tid=TidReadParameter(0, 6), #test read 6 word tid (12 bytes 24 chars)
    #       edata=TagAddress(0x02, 8), #test read exendend EPC with 8 words
    #       edata=TagAddress(0x02, 8), #test read exendend EPC with 8 words

    counter = 0
    for tag in conn.read_tag(
            antennas=const.ANTENNA_1 | const.ANTENNA_2,
            tid=TidReadParameter(0, 6),
            udata=TagAddress(0x28, 40),
            edata=TagAddress(0x08, 2)
        ): #test generator
        if tag is None:
            print ("Time out, {}".format(counter))
            counter += 1
            if counter > 10:
                conn.end_read_tag = True
        else: #proper tag
            print (tag)
    conn.tag_filter(filter_time, RSSI_threshold)
except Exception as e:
    print ("Process terminate : {}".format(e))
    print ("Error: %s" % sys.exc_info()[0])
    print ('-'*60)
    traceback.print_exc(file=sys.stdout)
    print ('-'*60)
finally:
    print ("Disconnecting, bye!")
    conn.disconnect()
