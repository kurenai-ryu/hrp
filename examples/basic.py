#!/usr/bin/env python2
# -*- coding: utf-8 -*-
import sys
import os
import traceback
import codecs
import logging

#fix path to use local module
sys.path.insert(1,os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from hrp import HRP, const, exception
from hrp.tag import TidReadParameter, TagAddress, MatchParameter

try:
    conn = HRP(ip='192.168.1.116', port=9090, ommit_ping=False, timeout=10)
    conn.set_log_level_debug() # enable for debug information
    print ("Connecting")
    conn.connect()
    filter_time, RSSI_threshold = conn.tag_filter()
    conn.tag_filter(100, 0)
    print ("Connected! press Ctrl+C to break")
    #conn.read_tag(tid=TidReadParameter(0, 10)) #test
    #conn.read_tag(edata=TagAddress(0x2D, 2)) #test
    counter = 0
    for tag in conn.read_tag(
            antennas=const.ANTENNA_1 | const.ANTENNA_2,
            tid=TidReadParameter(0, 10),
            #edata=TagAddress(0x02, 8)
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
