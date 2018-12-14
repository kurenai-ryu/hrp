#!/usr/bin/env python2
# -*- coding: utf-8 -*-

"""
Single read test

read_single_tag() returns a Tag instance if a tag was found or None otherwise
"""

import sys
import os
import traceback
import codecs

import time

#fix path to use local module
sys.path.insert(1,os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from hrp import HRP, const, exception
from hrp.tag import TidReadParameter, TagAddress, MatchParameter

try:
    conn = HRP(ip='192.168.1.116', port=9090, ommit_ping=False, timeout=10)
    conn.set_log_level_debug() # enable for debug information
    print ("Connecting")
    conn.connect()
    conn.stop() #always before reading tag!
    #conn.read_tag(tid=TidReadParameter(0, 10)) #test
    #conn.read_tag(edata=TagAddress(0x2D, 2)) #test
    tag = conn.read_single_tag(
            antennas=const.ANTENNA_1 | const.ANTENNA_2,
            #match=MatchParameter(const.MATCH_EPC, 32, codecs.decode('560179','hex')), # match EPC starting with 56 01 79
            #match=MatchParameter(const.MATCH_TID, 0, codecs.decode('e280b0a020','hex')), # match TID starting with e2 80 b0 a0 20
            tid=TidReadParameter(0, 6),
            #edata=TagAddress(0x02, 8)
        ) #test single read!
    if tag is None:
        print ("No tag found")
    else: #proper tag
        print (tag)
    print ("sleeping...")
    time.sleep(10)
except Exception as e:
    print ("Process terminate : {}".format(e))
    print ("Error: %s" % sys.exc_info()[0])
    print ('-'*60)
    traceback.print_exc(file=sys.stdout)
    print ('-'*60)
finally:
    print ("Disconnecting, bye!")
    conn.disconnect()
