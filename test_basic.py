#!/usr/bin/env python2
# # -*- coding: utf-8 -*-
import sys
import traceback
import codecs
import logging

from hrp import HRP
from hrp.hrp import TidReadParameter, TagAddress
from hrp.exception import *

try:
    conn = HRP(ip='192.168.1.116', port=9090, ommit_ping=False, timeout=10)
    conn.setLogLevelDebug()
    print ("Connecting")
    conn.connect()
    #conn.read_tag(tid=TidReadParameter(0, 10)) #test
    #conn.read_tag(rdata=TagAddress(0x00, 2)) #test
    conn.read_tag(micron=True) #test
except Exception as e:
    print ("Process terminate : {}".format(e))
    print ("Error: %s" % sys.exc_info()[0])
    print ('-'*60)
    traceback.print_exc(file=sys.stdout)
    print ('-'*60)
finally:
    print ("Disconnecting, bye!")
    try:
        conn.reader_stop()
    except Exception as e:
        print ("Can't stop reader")
    conn.disconnect()
