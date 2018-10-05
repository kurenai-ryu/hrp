#!/usr/bin/env python2
# # -*- coding: utf-8 -*-
import subprocess, platform
import logging
from socket import AF_INET, SOCK_STREAM, socket, timeout
from struct import pack, unpack
import codecs
import datetime

from .exception import *
from .util import crc16, _ord, LOGGER, log_call
from .const import *

from collections import namedtuple

TidReadParameter = namedtuple('TidReadParameter', 'fixed, size')
TagAddress = namedtuple('TagAddress', 'start, size')
MatchParameter = namedtuple('MatchParameter', 'area, start, length, content')

class HRP(object):
    """ clase para conexión Clou/Hopeland Hopeland Reader Protocol - HRP """
    @staticmethod
    def setLogLevel(level=logging.WARNING):
        LOGGER.setLevel(level)

    @staticmethod
    def setLogLevelDebug():
        LOGGER.setLevel(logging.DEBUG)

    def __init__(self, ip='192.168.1.116', port=9090, ommit_ping=False, timeout=10):
        """ init """
        self.__ommit_ping = ommit_ping
        self.address = (ip, port)
        self.timeout = timeout
        self.socket = None
        self.min_power = 0
        self.max_power = 0
        self.antennas = 0 # no antennas
        self.end_read_tag = False
        self.name = ""
        self.version = "-"
        self.deltalive = None
        self.region = 0 # GB1 = 920~925 ???
        self.auto = False # assumed
        self.channels = [] # empty

    @log_call(logging.INFO)
    def __test_ping(self):
        """
        Returns True if host responds to a ping request
        """
        LOGGER.info(" ping to %s", self.address[0])
        # Ping parameters as function of OS
        ping_str = "-n 1" if  platform.system().lower()=="windows" else "-c 1 -W 5"
        args = "ping " + " " + ping_str + " " + self.address[0] #ip
        need_sh = False if  platform.system().lower()=="windows" else True
        # Ping
        LOGGER.debug(args)
        return subprocess.call(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=need_sh) == 0
    @log_call()
    def _connect_tcp(self, timeout):
        """ connect_tcp """
        self.socket = socket(AF_INET, SOCK_STREAM)
        self.socket.settimeout(timeout)
        LOGGER.debug("begin tcp")
        res = self.socket.connect_ex(self.address)
        return res == 0

    @log_call()
    def _disconnect_tcp(self):
        """ disconnect_tcp"""
        if self.socket:
            LOGGER.debug("closing tcp")
            self.socket.close()
            self.socket = None

    @log_call()
    def _send_packet(self, mt=0, mid=0, payload=b""):
        """ send_packet"""
        # rs485 should be 0 because this is for tcp connection
        # if so, it needs a extra byte for address!!!
        # af should be 0 always, because we are sending the packet
        frame = pack(">BBBH",0xAA,mt, mid, len(payload))
        frame += payload #could be empty?
        LOGGER.debug(" p.frame %s", codecs.encode(frame, 'hex'))
        checksum = crc16(frame[1:])
        LOGGER.debug("   Checksum        %04x", checksum)
        frame += pack(">H", checksum) #big endian!!!
        #send!
        sent = self.socket.send(frame)
        LOGGER.debug("frame len: %i, sent: %i", len(frame), sent)
        #TODO: resend on missmatch?
        return sent

    @log_call()
    def _recieve_packet(self, mt=0, mid=0):
        """ recieve_packet"""
        try:
            header = self.socket.recv(5)
        except timeout:
            raise HDPFrameTimeoutError("header timed out!")
        #TODO: catch test of more bytes
        LOGGER.debug(" p.header %s", codecs.encode(header, 'hex'))
        fh, h_mt, h_mid, dlen = unpack(">BBBH", header)
        if fh != 0xAA:
            raise HDPFrameError("Inconsistent frame header")
        try:
            datac = self.socket.recv(dlen + 2) #data + Checksum
        except timeout:
            raise HDPFrameError("data[{}] timed out!".format(dlen+2))
        LOGGER.debug("     data + check   %s", codecs.encode(datac, 'hex'))
        #todo check checksum? datac[-2:]
        if mt != h_mt or mid != h_mid:
            raise HDPFrameError("Not corresponding response")
        self.__response = datac[:-2]

    @log_call(logging.INFO)
    def connect(self):
        """ connect"""
        if not self.__ommit_ping and not self.__test_ping():
            raise HDPNetworkError("can't reach reader (ping {})".format(self.address[0]))
        if not self._connect_tcp(self.timeout):
            raise HDPNetworkError("can't connect tcp reader ({})".format(self.address[0]))
        LOGGER.info("connecting...")
        self.reader_info()
        self.reader_ability()
        self.reader_band_region()
        self.reader_band_channels()
        self.reader_power()
        LOGGER.info("connected")

    @log_call(logging.INFO)
    def disconnect(self):
        """ connect"""
        #add extra commands...
        self._disconnect_tcp()

    def __shift_mandatory_int(self, size=1):
        """ mandatory is without pid"""
        val, = unpack(">I", self.__response[:size].rjust(4, b'\x00'))
        self.__response = self.__response[size:]
        return val

    def __shift_mandatory_fixed(self, size=1):
        """ mandatory is without pid"""
        val, = self.__response[:size]
        self.__response = self.__response[size:]
        return val

    def __shift_mandatory_var(self):
        """ mandatory  variable"""
        size, = unpack(">H", self.__response[:2])
        self.__response = self.__response[2:]
        val = self.__response[:size]
        self.__response = self.__response[size:]
        return val

    def __shift_mandatory_version(self):
        """ mandatory is without pid"""
        val = unpack(">HBB", self.__response[:4])
        self.__response = self.__response[4:]
        return val

    @log_call(logging.INFO)
    def reader_info(self):
        """ query reader info AA0100"""
        mt = MT_CONFIG
        mid = MID_CONFIG_QUERY_READER_INFORMATION
        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)
        #Mandatory fixed
        major, minor, patch = self.__shift_mandatory_version()
        self.version = "{}.{}.{}".format(major, minor, patch)
        LOGGER.info(" VERSION %s", self.version)
        self.name = str(self.__shift_mandatory_var().decode('utf-8'))
        LOGGER.info(" Reader name %s", self.name)
        live = self.__shift_mandatory_int(4)
        self.deltalive = datetime.timedelta(seconds=live)
        LOGGER.info(" Uptime: %s", self.deltalive)

    @log_call(logging.INFO)
    def reader_ability(self):
        """ query reader hability AA0200"""
        mt = MT_OPERATION
        mid = MID_OP_QUERY_READER_RFID_ABILITY
        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)
        #Mandatory fixed
        self.min_power = self.__shift_mandatory_int()
        self.max_power = self.__shift_mandatory_int()
        self.antennas = self.__shift_mandatory_int()
        LOGGER.info(" min_pow:%i, max_pow:%i", self.min_power, self.max_power)
        LOGGER.info(" antennas:%i", self.antennas)
        #parse FReq list?
        list = self.__shift_mandatory_var() # TODO: parse
        for fl in list:
            fl = _ord(fl)
            LOGGER.info(" supported bands: [%i] = %s", fl, RF_REGION[fl])
        #parse protocol list?
        protocols = self.__shift_mandatory_var()
        for fl in protocols:
            fl = _ord(fl)
            LOGGER.info(" supported protocols: [%i] = %s", fl, RF_PROTOCOL[fl])

    @log_call()
    def init_read_tag(self, antennas=1, match=None, tid=None, udata=None, rdata=None, password=None, monza=False, micron=False, em_sensor=False, edata=None):
        """ read tag command AA0210"""
        mt = MT_OPERATION
        mid = MID_OP_READ_EPC_TAG
        LOGGER.debug(" read antennas %i", antennas)
        params = pack(">BB", antennas, 1) #fixed inventory - continous read
        if match is not None:
            LOGGER.debug("adding match %i", match.area)
            params += pack(">BBHB", 1, match.area, match.start,len(match.content))
            params += match.content
        if tid is not None:
            LOGGER.debug(" adding tid %s", tid)
            # tid[0] 0-> variable up to [1], 1-> fixed read [1] words
            params += pack(">BBB", 2, tid.fixed, tid.size)
        if udata is not None:
            LOGGER.debug(" adding udata")
            params += pack(">BHB", 3, udata.start, udata.size)
        if rdata is not None:
            LOGGER.debug(" adding rdata")
            params += pack(">BHB", 4, rdata.start, rdata.size)
        if password is not None:
            LOGGER.debug(" adding password")
            params += pack(">BI", 5, password)
        if monza:
            LOGGER.debug(" adding monza qt")
            params += pack(">BB", 6, 1) #fixed 1
        if micron:
            LOGGER.debug(" adding RF micron")
            params += pack(">BB", 7, 1) #fixed 1
        if em_sensor:
            LOGGER.debug(" adding EM sensor data")
            params += pack(">BB", 8, 1) #fixed 1
        if edata is not None:
            LOGGER.debug(" adding epc data")
            params += pack(">BHB", 9, edata.start, edata.size)

        self._send_packet(mt, mid, params)
        self._recieve_packet(mt, mid)
        result = self.__shift_mandatory_int()
        LOGGER.info(" read_tag response (0:ok) is %s", result)
        return result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def read_tag(self, antennas=1, match=None, tid=None, udata=None, rdata=None, password=None, monza=False, micron=False, em_sensor=False, edata=None):
        if not self.init_read_tag(antennas, match, tid, udata, rdata, password, monza, micron, em_sensor, edata):
            LOGGER.warning("Can't read tags")
            return
        self.end_read_tag = False
        while not self.end_read_tag:
            LOGGER.debug(" waiting message...")
            try:
                self._recieve_packet(0x12, 0x00) #active data!
            except HDPFrameTimeoutError as e:
                LOGGER.debug(" timeout!")
                continue
            except (KeyboardInterrupt, SystemExit):
                LOGGER.info (" read_tag break!")
                break
            LOGGER.debug("read_tag rec %s", codecs.encode(self.__response, 'hex'))
            epc = self.__shift_mandatory_var()
            LOGGER.info (" EPC(%i) = %s", len(epc), codecs.encode(epc, 'hex'))
            tag_pc = self.__shift_mandatory_int(2)
            LOGGER.info (" TAGPC = 0x%x = %i", tag_pc, tag_pc)
            antenna = self.__shift_mandatory_int()
            LOGGER.info(" antenna = %i", antenna)
            extra = {'epc': epc, 'tag_pc':tag_pc, 'antenna':antenna}
            while len(self.__response):
                pid = self.__shift_mandatory_int()
                opt={
                    1: ('rssi', self.__shift_mandatory_int),
                    2: ('tag_result', self.__shift_mandatory_int),
                    3: ('tid', self.__shift_mandatory_var),
                    4: ('udata', self.__shift_mandatory_var),
                    5: ('rdata', self.__shift_mandatory_var),
                    6: ('sub_antenna', self.__shift_mandatory_int),
                    7: ('utc', self.__shift_mandatory_fixed, 8),
                    8: ('sequence', self.__shift_mandatory_int, 4),
                    9: ('frequency', self.__shift_mandatory_int, 4),
                    10: ('phase', self.__shift_mandatory_int),
                    11: ('em_sensor', self.__shift_mandatory_fixed, 8),
                    12: ('epc_data', self.__shift_mandatory_var),
                }
                val = opt.get(pid, None)
                if val is not None:
                    if len(val) > 2: #size!
                        temp = val[1](val[2])
                    else:
                        temp = val[1]()
                    LOGGER.debug(" (%i) %s = %s", pid, val[0], temp)
                    extra[val[0]] = temp
            tid = extra.get('tid')
            if tid:
                LOGGER.info(" TID(%i) = %s", len(tid), codecs.encode(tid, 'hex'))


        self.reader_stop()
        self._recieve_packet(0x12, 0x01) #tag read finish reason!

    @log_call(logging.INFO)
    def reader_stop(self):
        """ stop command AA02FF"""
        mt = MT_OPERATION
        mid = MID_OP_STOP_COMMAND
        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)
        self.result = self.__shift_mandatory_int()
        LOGGER.info(" stop response (0:ok) is %s", self.result)
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def reader_band_region(self, new_region=None):
        """ get or set band command AA0205"""
        if new_region is None: #read!
            mt = MT_OPERATION
            mid = MID_OP_QUERY_READER_RF_FREQUENCY_BAND
            payload= b""
        else:
            mt = MT_OPERATION
            mid = MID_OP_CONFIGURE_READER_RF_FREQUENCY_BAND
            payload = pack("B", new_region)
        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)
        self.result = self.__shift_mandatory_int()
        if new_region is None: #read
            LOGGER.info(" Region: %s", RF_REGION[self.result])
            self.region = self.result
            return self.result
        #if write
        LOGGER.info(" write band region response (0:ok) is %s", self.result)
        self.region = new_region
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def reader_band_channels(self, channel_list=None, auto=True):
        """ get or set band command AA0205"""
        chlist = RF_REGION_CHANNELS[self.region]
        if not channel_list: #read!
            mt = MT_OPERATION
            mid = MID_OP_QUERY_READER_WORKING_FREQUENCY
            payload= b""
        else:
            mt = MT_OPERATION
            mid = MID_OP_CONFIGURE_READER_WORKING_FREQUENCY
            chstring = b""
            for ch in channel_list:
                if ch >=len(chlist):
                    LOGGER.warn(" Invalid channel %i ommiting!", ch)
                else:
                    chstring += pack("B", ch)
            payload = pack(">BBH", int(auto), 1, len(chstring)) #pid=1

        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)

        if not channel_list: #read
            self.auto = bool(self.__shift_mandatory_int())
            channels = self.__shift_mandatory_var()

            LOGGER.info(" Range: %s", "full (automatic)" if self.auto else "fixed from list")
            self.channels = [ _ord(ch) for ch in channels ]
            for ch in self.channels:
                if ch >= len(chlist):
                    LOGGER.warn(" Invalid channel %i", ch)
                else:
                    LOGGER.info(" Channel: %i, %.2f MHz",ch,chlist[ch])
            LOGGER.debug(" end ch")
            return self.channels
        #if write
        self.result = self.__shift_mandatory_int()
        LOGGER.info(" write band region response (0:ok) is %s", self.result)
        self.region = new_region
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def reader_power(self, new_power=None, antennas=None):
        """ get or set reader power AA0202"""
        if new_power is None: #read!
            mt = MT_OPERATION
            mid = MID_OP_QUERY_READER_POWER

        else:
            mt = MT_OPERATION
            mid = MID_OP_CONFIGURE_READER_POWER
            payload = b""
            if antennas is None:
                antennas = self.antennas
            if type(antennas) is int and antennas < 4:
                antennas = range(1, antennas + 1)
            for ant in antennas:
                payload += pack(">BB",ant, new_power)
        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)
        if new_power is None: #read
            while len(self.__response):
                pid = self.__shift_mandatory_int()
                apow = self.__shift_mandatory_int()
                LOGGER.info(" Antenna#%i = %i dBm", pid, apow)
            return apow #TODO catch error
        #if write
        self.result = self.__shift_mandatory_int()
        LOGGER.info(" write antenna power response (0:ok) is %s", self.result)
        return self.result == 0 # 0 is ok!
