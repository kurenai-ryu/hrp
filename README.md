# CLOU_READER

clou_reader es una librería para comunicación con antenas CLOU/Hopeland mediante el protocolo TCP.

------

clou_reader is an unofficial communication library for CLOU/Hopeland antennas via TCP.



## Instalación

* [INSTALL.md](INSTALL.md)



## Uso



ejemplo básico

```python
import sys
import traceback
import codecs
import logging

from hrp import HRP
from hrp.tag import TidReadParameter, TagAddress, MatchParameter
from hrp.exception import *

try:
    conn = HRP(ip='192.168.1.116', port=9090, ommit_ping=False, timeout=10)
    conn.setLogLevelDebug()
    print ("Connecting")
    conn.connect()
    filter_time, RSSI_threshold = conn.tag_filter()
    conn.tag_filter(100, 0)
    #conn.read_tag(tid=TidReadParameter(0, 10)) #test
    #conn.read_tag(edata=TagAddress(0x02, 6)) #test
    counter = 0
    for tag in conn.read_tag(antenna=0x01): #test generator
        if tag is None:
            print ("Time out, {}".format(counter))
            counter += 1
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
```

