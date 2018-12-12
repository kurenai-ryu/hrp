#!/usr/bin/env python2
# # -*- coding: utf-8 -*-

"""
HRP Exception types
"""

class HRPBaseError(Exception):
    """Base Error for HRP"""
    pass

class HRPNetworkError(HRPBaseError):
    """Network Error for HRP"""
    pass

class HRPFrameError(HRPBaseError):
    """Frame Error for HRP"""
    pass

class HRPFrameTimeoutError(HRPFrameError):
    """Timeout while waiting"""
    pass
