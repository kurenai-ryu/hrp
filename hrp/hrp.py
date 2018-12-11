#!/usr/bin/env python2
# # -*- coding: utf-8 -*-
import subprocess, platform
import logging
from socket import AF_INET, SOCK_STREAM, socket, timeout
from struct import pack, unpack
import codecs
import datetime

from .tag import TidReadParameter, TagAddress, MatchParameter
from .exception import *
from .util import crc16, _ord, LOGGER, log_call
from .tag import Tag
from .const import *


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
        self.band_region()
        self.band_channels()
        self.power()
        LOGGER.info("connected")

    @log_call(logging.INFO)
    def disconnect(self):
        """ connect"""
        #add extra commands...
        if self.socket:
            self.stop()
        self._disconnect_tcp()

    def __response_shift_int(self, size=1):
        """ mandatory is without pid"""
        val, = unpack(">I", self.__response[:size].rjust(4, b'\x00'))
        self.__response = self.__response[size:]
        return val

    def __response_shift_fixed(self, size=1):
        """ mandatory is without pid"""
        val, = self.__response[:size]
        self.__response = self.__response[size:]
        return val

    def __response_shift_var(self):
        """ mandatory  variable"""
        size, = unpack(">H", self.__response[:2])
        self.__response = self.__response[2:]
        val = self.__response[:size]
        self.__response = self.__response[size:]
        return val

    def __response_shift_version(self):
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
        major, minor, patch = self.__response_shift_version()
        self.version = "{}.{}.{}".format(major, minor, patch)
        LOGGER.info(" VERSION %s", self.version)
        self.name = str(self.__response_shift_var().decode('utf-8'))
        LOGGER.info(" Reader name %s", self.name)
        live = self.__response_shift_int(4)
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
        self.min_power = self.__response_shift_int()
        self.max_power = self.__response_shift_int()
        self.antennas = self.__response_shift_int()
        LOGGER.info(" min_pow:%i, max_pow:%i", self.min_power, self.max_power)
        LOGGER.info(" antennas:%i", self.antennas)
        #parse FReq list?
        list = self.__response_shift_var() # TODO: parse
        for fl in list:
            fl = _ord(fl)
            LOGGER.info(" supported bands: [%i] = %s", fl, RF_REGION[fl])
        #parse protocol list?
        protocols = self.__response_shift_var()
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
        if match is not None and type(match) is MatchParameter:
            LOGGER.debug("adding match %i", match.area)
            params += pack(">BBHB", 1, match.area, match.start,len(match.content))
            params += match.content
        if tid is not None and type(tid) is TidReadParameter:
            LOGGER.debug(" adding tid %s", tid)
            # tid[0] 0-> variable up to [1], 1-> fixed read [1] words
            params += pack(">BBB", 2, tid.fixed, tid.size)
        if udata is not None and type(udata) is TagAddress:
            LOGGER.debug(" adding udata")
            params += pack(">BHB", 3, udata.start, udata.size)
        if rdata is not None and type(rdata) is TagAddress:
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
        if edata is not None and type(edata) is TagAddress:
            LOGGER.debug(" adding epc data")
            params += pack(">BHB", 9, edata.start, edata.size)

        self._send_packet(mt, mid, params)
        self._recieve_packet(mt, mid)
        result = self.__response_shift_int()
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
                yield None
                continue
            except (KeyboardInterrupt, SystemExit):
                LOGGER.info (" read_tag break!")
                break
            LOGGER.debug("read_tag rec %s", codecs.encode(self.__response, 'hex'))
            epc = self.__response_shift_var()
            LOGGER.info (" EPC(%i) = %s", len(epc), codecs.encode(epc, 'hex'))
            tag_pc = self.__response_shift_int(2)
            LOGGER.info (" TAGPC = 0x%x %s", tag_pc, bin(tag_pc))
            antenna = self.__response_shift_int()
            LOGGER.info(" antenna = %i", antenna)
            tag = Tag(epc=epc, tag_pc=tag_pc, antenna=antenna)
            while len(self.__response):
                pid = self.__response_shift_int()
                opt={
                    1: ('rssi', self.__response_shift_int),
                    2: ('tag_result', self.__response_shift_int),
                    3: ('tid', self.__response_shift_var),
                    4: ('udata', self.__response_shift_var),
                    5: ('rdata', self.__response_shift_var),
                    6: ('sub_antenna', self.__response_shift_int),
                    7: ('utc', self.__response_shift_fixed, 8),
                    8: ('sequence', self.__response_shift_int, 4),
                    9: ('frequency', self.__response_shift_int, 4),
                    10: ('phase', self.__response_shift_int),
                    11: ('em_sensor', self.__response_shift_fixed, 8),
                    12: ('epc_data', self.__response_shift_var),
                }
                val = opt.get(pid, None)
                if val is not None:
                    if len(val) > 2: #size!
                        temp = val[1](val[2])
                    else:
                        temp = val[1]()
                    LOGGER.debug(" (%i) %s = %s", pid, val[0], temp)
                    tag.__dict__[val[0]] = temp
            if tag.tid:
                LOGGER.debug(" TID(%i) = %s", len(tag.tid), codecs.encode(tag.tid, 'hex'))
            yield tag

        self.stop()
        self._recieve_packet(0x12, 0x01) #tag read finish reason!

    @log_call(logging.INFO)
    def restart(self):
        """ restart command AA02FF"""
        mt = MT_CONFIG
        mid = MID_CONFIG_RESTART_READER
        self._send_packet(mt, mid)
        self._disconnect_tcp() # no more commands issued

    @log_call(logging.INFO)
    def stop(self):
        """ stop command AA02FF

        """
        mt = MT_OPERATION
        mid = MID_OP_STOP_COMMAND
        self._send_packet(mt, mid)
        self._recieve_packet(mt, mid)
        self.result = self.__response_shift_int()
        LOGGER.info(" stop response (0:ok) is %s", self.result)
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def band_region(self, new_region=None):
        """ get or set band command AA0205"""
        if new_region is None: #read!
            mt = MT_OPERATION
            mid = MID_OP_QUERY_READER_RF_FREQUENCY_BAND
            payload= b""
        else:
            mt = MT_OPERATION
            mid = MID_OP_CONFIGURE_READER_RF_FREQUENCY_BAND
            payload = pack("B", new_region)
        self._send_packet(mt, mid, payload)
        self._recieve_packet(mt, mid)
        self.result = self.__response_shift_int()
        if new_region is None: #read
            LOGGER.info(" Region: %s", RF_REGION[self.result])
            self.region = self.result
            return self.result
        #if write
        LOGGER.info(" write band region response (0:ok) is %s", self.result)
        self.region = new_region
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def band_channels(self, channel_list=None, auto=True):
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

        self._send_packet(mt, mid, payload)
        self._recieve_packet(mt, mid)

        if not channel_list: #read
            self.auto = bool(self.__response_shift_int())
            channels = self.__response_shift_var()

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
        self.result = self.__response_shift_int()
        LOGGER.info(" write band region response (0:ok) is %s", self.result)
        self.region = new_region
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def power(self, new_power=None, antennas=None):
        """ get or set reader power AA0202"""
        if new_power is None: #read!
            mt = MT_OPERATION
            mid = MID_OP_QUERY_READER_POWER
            payload= b""
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
                pid = self.__response_shift_int()
                apow = self.__response_shift_int()
                LOGGER.info(" Antenna#%i = %i dBm", pid, apow)
            return apow #TODO catch error
        #if write
        self.result = self.__response_shift_int()
        LOGGER.info(" write antenna power response (0:ok) is %s", self.result)
        return self.result == 0 # 0 is ok!

    @log_call(logging.INFO)
    def tag_filter(self, new_filter_time=None, new_RSSI_threshold=None):
        """ get or set reader tag upload params AA0209"""
        if new_filter_time is None and new_RSSI_threshold is None: #read!
            mt = MT_OPERATION
            mid = MID_OP_QUERY_TAG_UPLOAD_PARAMETERS
            payload= b""
        else:
            mt = MT_OPERATION
            mid = MID_OP_CONFIGURE_TAG_UPLOAD_PARAMETERS
            payload = b""
            if new_filter_time is not None:
                payload += pack(">BH",1, new_filter_time)
            if new_RSSI_threshold is not None:
                payload += pack(">BB",2, new_RSSI_threshold)
        self._send_packet(mt, mid, payload)
        self._recieve_packet(mt, mid)
        if new_filter_time is None: #read
            while len(self.__response):
                filter_time = self.__response_shift_int(2)
                RSSI_threshold = self.__response_shift_int()
                LOGGER.info(" filter %i x 10ms, RSSI th = %i dBm", filter_time, RSSI_threshold)
            return filter_time, RSSI_threshold
        #if write
        self.result = self.__response_shift_int()
        LOGGER.info(" write tag_filter response (0:ok) is %s", self.result)
        return self.result == 0 # 0 is ok!
