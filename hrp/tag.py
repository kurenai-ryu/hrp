#!/usr/bin/env python2
# # -*- coding: utf-8 -*-
import codecs
from collections import namedtuple

RESULT_OK = 0
RESULT_NO_RESPONSE = 1
RESULT_CRC_ERROR = 2
RESULT_DATA_LOCKED = 3
RESULT_DATA_OVERFLOW = 4
RESULT_PASSWORD_ERROR = 5
RESULT_OTHER_TAG_ERROR = 6
RESULT_OTHER_READER_ERROR = 7

RESULT = {
0: "Read successful",
1: "Tag no response",
2: "CRC error",
3: "Data area is locked",
4: "Data area overflow",
5: "Access password error",
6: "Other tag error",
7: "Other reader error"
}

TidReadParameter = namedtuple('TidReadParameter', 'fixed, size')
TagAddress = namedtuple('TagAddress', 'start, size')
MatchParameter = namedtuple('MatchParameter', 'area, start, length, content')


class Tag(object):
    """ clase para manejo de tags """
    def __init__(self,
                 epc=None,
                 tag_pc=None,
                 antenna=0,
                 rssi=None,
                 tag_result=RESULT_OK,
                 tid=None,
                 udata=None,
                 rdata=None,
                 sub_antenna=None,
                 utc=None,
                 sequence=None,
                 frequency=None,
                 phase=None,
                 em_sensor=None,
                 epc_data=None
                 ):
        """ init """
        #fixed read
        self.epc = epc
        self.tag_pc = tag_pc
        self.antenna = antenna
        #optional
        self.rssi = rssi
        self.tag_result = tag_result
        self.tid = tid
        self.udata = udata
        self.rdata = rdata
        self.sub_antenna = sub_antenna
        self.utc = utc
        self.sequence = sequence
        self.frequency = frequency
        self.phase = phase
        self.em_sensor = em_sensor
        self.epc_data = epc_data

    def str_result(self):
        return RESULT.get(self.tag_result, "UNDEF_{}".format(self.tag_result))

    def str_epc(self):
        return "TAG: EPC({}) = {}, PC=0x{:04x}".format(
            len(self.epc),
            codecs.encode(self.epc, 'hex'),
            self.tag_pc
        )

    def str_tid(self):
        return "TID({}) = {}".format(
            len(self.tid),
            codecs.encode(self.tid, 'hex')) if self.tid else "No TID"

    def str_udata(self):
        return "UDATA({}) = {}".format(
            len(self.udata),
            codecs.encode(self.udata, 'hex')) if self.udata else "No User Data"

    def str_rdata(self):
        return "RDATA({}) = {}".format(
            len(self.rdata),
            codecs.encode(self.rdata, 'hex')) if self.rdata else "No Res Data"

    def str_epc_data(self):
        return "EPC_DATA({}) = {}".format(
            len(self.epc_data),
            codecs.encode(self.epc_data, 'hex')) if self.epc_data else "No EPC Data"

    def __repr__(self):
        """ representacion en cadena """
        cadena = self.str_epc()
        if self.antenna:
            cadena += ", ANT: {}".format(self.antenna)
        if self.rssi:
            cadena += ", RSSI: {}".format(self.rssi)
        if self.tid:
            cadena += ", {}".format(self.str_tid())
        if self.udata:
            cadena += ", {}".format(self.str_udata())
        if self.rdata:
            cadena += ", {}".format(self.str_rdata())
        if self.epc_data:
            cadena += ", {}".format(self.str_epc_data())

        cadena += ", RESULT: {}". format(self.str_result())

        return cadena
