#!/usr/bin/env python2
# # -*- coding: utf-8 -*-
import sys
import codecs
import logging

import datetime
import unittest
from mock import patch, Mock, MagicMock



try:
    unittest.TestCase.assertRaisesRegex
except AttributeError:
    unittest.TestCase.assertRaisesRegex = unittest.TestCase.assertRaisesRegexp

from hrp import HRP
from hrp.exception import HDPNetworkError



class HRPTest(unittest.TestCase):
    def setup(self):
        pass

    def tearDown(self):
        HRP.setLogLevel()# reset
        pass

    @patch('hrp.hrp.subprocess')
    def test_incorrect_ping(self, subprocess):
        #HRP.setLogLevel(logging.DEBUG)
        subprocess.call.return_value = 1
        conn = HRP('192.168.1.116')
        self.assertRaisesRegex(HDPNetworkError,"can't reach reader", conn.connect)

    @patch('hrp.hrp.socket')
    @patch('hrp.hrp.subprocess')
    def test_correct_ping(self, subprocess, socket):
        #HRP.setLogLevel(logging.DEBUG)
        subprocess.call.return_value = 0
        socket.return_value.connect_ex.return_value = 1
        conn = HRP('192.168.1.116')
        self.assertRaisesRegex(HDPNetworkError,"can't connect tcp reader", conn.connect)

    @patch('hrp.hrp.socket')
    @patch('hrp.hrp.subprocess')
    def test_correct_tcp(self, subprocess, socket):
        #HRP.setLogLevel(logging.DEBUG)
        subprocess.call.return_value = 0
        socket.return_value.connect_ex.return_value = 0
        socket.return_value.recv.side_effect = [
            codecs.decode('aa0100001b', 'hex'), #header: query_reader_info
            codecs.decode('000101100011434c3732303642325f3230313730363036000160424a14', 'hex'),
            codecs.decode('AA0200000E', 'hex'), #5 byte header query_reader_ability
            codecs.decode('0024040005000102030400020001527C', 'hex'),
        ]
        conn = HRP('192.168.1.116')
        conn.connect()
        subprocess.call.assert_called()
        socket.return_value.connect_ex.assert_called_with(('192.168.1.116', 9090))
        #don't check packets?

    @patch('hrp.hrp.socket')
    @patch('hrp.hrp.subprocess')
    def test_correct_connect(self, subprocess, socket):
        #HRP.setLogLevel(logging.DEBUG)
        subprocess.call.return_value = 0
        socket.return_value.connect_ex.return_value = 0
        socket.return_value.recv.side_effect = [
            codecs.decode('aa0100001b', 'hex'), #header: query_reader_info
            codecs.decode('000101100011434c3732303642325f3230313730363036000160424a14', 'hex'),
            codecs.decode('AA0200000E', 'hex'), #5 byte header query_reader_ability
            codecs.decode('0024040005000102030400020001527C', 'hex'),
        ]
        conn = HRP('192.168.1.116')
        conn.connect() # parsed reader_info & reader_ability
        self.assertEqual(conn.name, "CL7206B2_20170606", "incorrect name %s" % conn.name)
        self.assertEqual(conn.version, "1.1.16", "incorrect version %s" % conn.version)
        self.assertEqual(conn.deltalive, datetime.timedelta(seconds=90178), "incorrect live %s" % conn.deltalive)
        self.assertEqual(conn.min_power, 0, "incorrect min_pow %s" % conn.min_power)
        self.assertEqual(conn.max_power, 36, "incorrect max_pow %s" % conn.max_power)
        self.assertEqual(conn.antennas, 4, "incorrect antennas %s" % conn.antennas)

    @patch('hrp.hrp.socket')
    @patch('hrp.hrp.subprocess')
    def test_command_send(self, subprocess, socket):
        #HRP.setLogLevel(logging.DEBUG)
        subprocess.call.return_value = 0
        socket.return_value.connect_ex.return_value = 0
        socket.return_value.recv.side_effect = [
            codecs.decode('aa0100001b', 'hex'), #header: query_reader_info
            codecs.decode('000101100011434c3732303642325f3230313730363036000160424a14', 'hex'),
            codecs.decode('AA0200000E', 'hex'), #header: query_reader_ability
            codecs.decode('0024040005000102030400020001527C', 'hex'),
        ]
        conn = HRP('192.168.1.116')
        conn.connect()
        conn._send_packet(5,5) # TEST,swr detect,""
        socket.return_value.send.assert_called_with(codecs.decode("AA050500004444",'hex'))
        conn._send_packet(2, 255) # OP, stop command
        socket.return_value.send.assert_called_with(codecs.decode("AA02FF0000A40F",'hex'))

if __name__ == '__main__':
    unittest.main()
