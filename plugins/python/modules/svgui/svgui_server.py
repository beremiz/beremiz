#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

from nevow import rend, appserver, inevow, tags, loaders, athena
import simplejson as json

svgfile = '%(svgfile)s'

svguiWidgets={}

class SvguiWidget:
    
    def __init__(self, classname, back_id, **kwargs):
        self.classname = classname
        self.back_id = back_id
        self.attrs = kwargs.copy()
        self.lastattrs = kwargs.copy()
        self.inhibit = False
        self.changed = False

    def setattr(self, attrname, value):
        self.attrs[attrname] = value
        
    def getattr(self, attrname):
        return self.args.get(attrname, None)

    def update(self, **kwargs):
        for attrname, value in kwargs.iteritems():
            if self.lastattrs.get(attrname, None) != value:
                self.changed = True
                self.attrs[attrname] = value
                self.lastattrs[attrname] = value
        interface = website.getHMI()
        if interface is not None and self.changed and not self.inhibit:
            self.changed = False
            interface.sendData(self)
        
        return self.attrs["state"]

def convert_to_builtin_type(obj):
    # Convert objects to a dictionary of their representation
    d = { '__class__':obj.classname,
          'back_id':obj.back_id,
          'kwargs':json.dumps(obj.attrs),
          }
    return d

def dataToSend():
    gadgets = []
    for gadget in svguiWidgets.values():
        gadgets.append(unicode(json.dumps(gadget, default=convert_to_builtin_type, indent=2), 'ascii'))
    return gadgets


class SVGUI_HMI(athena.LiveElement):
    jsClass = u"LiveSVGPage.LiveSVGWidget"
    
    docFactory = loaders.stan(tags.div(render=tags.directive('liveElement'))[                                    
                                         tags.xml(loaders.xmlfile(os.path.join(WorkingDir, svgfile))),
                                         ])

    def sendData(self,data):
        objDefer = self.callRemote('receiveData',unicode(json.dumps(data, default=convert_to_builtin_type, indent=2), 'ascii'))

    def initClient(self):
        self.callRemote('init', dataToSend())
    
    def setattr(self, id, attrname, value):
        svguiWidgets[id].setattr(attrname, value)

def SVGUI(*args, **kwargs):
    classname, back_id = args
    gad = svguiWidgets.get(back_id, None)
    if gad is None:
        gad = SvguiWidget(classname, back_id, **kwargs)
        svguiWidgets[back_id] = gad
        gadget = [unicode(json.dumps(gad, default=convert_to_builtin_type, indent=2), 'ascii')]
        interface = website.getHMI()
        if interface is not None:
            interface.callRemote('init', gadget)

    return gad.update(**kwargs)
