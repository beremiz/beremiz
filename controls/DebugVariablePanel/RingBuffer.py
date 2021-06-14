#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
# Copyright (C) 2021: Edouard TISSERANT
#
# See COPYING file for copyrights details.

# Based on Eelco Hoogendoorn stackoverflow answer about RingBuffer with numpy

import numpy as np


class RingBuffer(object):
    def __init__(self, width=None, size=65536, padding=None):
        self.size = size
        self.padding = size if padding is None else padding
        shape = (self.size+self.padding,)
        if width :
            shape += (width,)
        self.buffer = np.zeros(shape)
        self.counter = 0
        self.full = False

    def append(self, data):
        """this is an O(n) operation"""
        data = data[-self.padding:]
        n = len(data)
        if self.remaining < n: self.compact()
        self.buffer[self.counter+self.size:][:n] = data
        self.counter += n

    @property
    def count(self):
        return self.counter if not self.full else self.size

    @property
    def remaining(self):
        return self.padding-self.counter

    @property
    def view(self):
        """this is always an O(1) operation"""
        return self.buffer[self.counter:][:self.size]

    def compact(self):
        """
        note: only when this function is called, is an O(size) performance hit incurred,
        and this cost is amortized over the whole padding space
        """
        print 'compacting'
        self.buffer[:self.size] = self.view
        self.counter = 0
        self.full = True

