#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.

import weakref
from zeroconf import ServiceBrowser, Zeroconf, get_all_addresses
import threading

service_type = '_Beremiz._tcp.local.'

class ZeroConfListenerClass:
    def __init__(self, dialog):
        self.dialog = weakref.ref(dialog)

        self.IfacesMonitorState = None
        self.IfacesMonitorTimer = None
        self.Browser = None
        self.ZeroConfInstance = None
        self.PublishedServices = set()

        self.start()

    def __del__(self):
        self.stop()

    def start(self):
        self.ZeroConfInstance = Zeroconf()
        self.Browser = ServiceBrowser(self.ZeroConfInstance, service_type, self)
        # Start the ifaces_monitor timer thread
        self.IfacesMonitorTimer = threading.Timer(1.0, self.ifaces_monitor)
        self.IfacesMonitorTimer.start()

    def stop(self):
        if self.IfacesMonitorTimer is not None:
            self.IfacesMonitorTimer.cancel()
            self.IfacesMonitorTimer = None

        if self.Browser is not None:
            self.Browser.cancel()
            self.Browser = None

        if  self.ZeroConfInstance is not None:
            self.ZeroConfInstance.close()
            self.ZeroConfInstance = None

    def update_service(self, zeroconf, _type, name):
        self.remove_service(zeroconf, _type, name)
        self.add_service(zeroconf, _type, name)

    def add_service(self, zeroconf, _type, name):
        dialog = self.dialog()
        if not dialog:
            return

        info = self.ZeroConfInstance.get_service_info(_type, name)
        if info is None:
            return

        typename = info.properties.get(b"protocol", None).decode()
        ip = str(info.parsed_addresses()[0])
        port = info.port
        dialog.addService(typename, ip, port, name)
        self.PublishedServices.add(name)

    def remove_service(self, zeroconf, _type, name):
        dialog = self.dialog()
        if not dialog:
            return
        
        if name in self.PublishedServices:
            dialog.removeService(name)
            self.PublishedServices.discard(name)

    def ifaces_monitor(self):
        dialog = self.dialog()
        if not dialog:
            return

        NewState = get_all_addresses()
        OldState = self.IfacesMonitorState
        self.IfacesMonitorState = NewState
        do_restart = False
        
        if OldState is not None:
            # detect if a new address appeared
            for addr in NewState:
                if addr not in OldState:
                    do_restart = True
                    break
                else:
                    OldState.remove(addr)
            # detect if an address disappeared
            if len(OldState) > 0:
                do_restart = True

            
        if do_restart:
            self.stop()
            
            while self.PublishedServices:
                dialog.removeService(self.PublishedServices.pop())
        
            self.start()
        else:
            # Restart the ifaces_monitor timer thread
            self.IfacesMonitorTimer = threading.Timer(1.0, self.ifaces_monitor)
            self.IfacesMonitorTimer.start()
