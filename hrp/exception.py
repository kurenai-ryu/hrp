#!/usr/bin/env python2
# # -*- coding: utf-8 -*-

class HDPBaseError(Exception):
    pass

class HDPNetworkError(HDPBaseError):
    pass

class HDPFrameError(HDPBaseError):
    pass

class HDPFrameTimeoutError(HDPFrameError):
    pass
