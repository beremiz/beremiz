
class button:
    
    def __init__(self, parent, id, args):
        self.parent = parent
        self.id = id
        self.back_elt = getSVGElementById(args.back_id)
        self.sele_elt = getSVGElementById(args.sele_id)
        self.toggle = args.toggle
        self.active = args.active
        if args.state != undefined:
            self.state = args.state
        else:
            self.state = False
        self.dragging = False
        if self.toggle:
            self.up = not self.state
        else:
            self.up = True
        
        # Add event on each element of the button
        if self.active:
            self.back_elt.addEventListener("mouseup", self, False)
            self.back_elt.addEventListener("mousedown", self, False)
            self.back_elt.addEventListener("mouseover", self, False)
            self.back_elt.addEventListener("mouseout", self, False)
            
            self.sele_elt.addEventListener("mouseup", self, False)
            self.sele_elt.addEventListener("mousedown", self, False)
            self.sele_elt.addEventListener("mouseover", self, False)
            self.sele_elt.addEventListener("mouseout", self, False)
        
        blockSVGElementDrag(self.back_elt)
        blockSVGElementDrag(self.sele_elt)

        self.updateElements()

    # method to display the current state of interface
    def updateElements(self):
        if self.up:
            self.sele_elt.setAttribute("display", "none")
            self.back_elt.removeAttribute("display")
        else:
            self.sele_elt.removeAttribute("display")
            self.back_elt.setAttribute("display", "none")
            
    def updateValues(self, values):
        if values.state != self.state:
            self.state = values.state
            self.up = not self.state
            if self.toggle:
                updateAttr(self.id, 'state', self.state)
            self.updateElements()

    def handleEvent(self, evt):
        # Quand le bouton de la souris est presse
        if evt.type == "mousedown":
            evt.stopPropagation()
            setCurrentObject(self)
            
            self.dragging = True
            
            if self.toggle:
                self.up = self.state
            else:
                self.up = False
                self.state = True
                updateAttr(self.id, 'state', self.state)
            self.updateElements()
        
        if isCurrentObject(self) and self.dragging:
            # Quand le bouton est survole
            if evt.type == "mouseover" and self.toggle:
                self.up = self.state
                self.updateElements()
            
            # Quand le curseur quitte la zone du bouton
            elif evt.type == "mouseout" and self.toggle:       
                self.up = not self.state
                self.updateElements()
            
            # Quand le bouton de la souris est relache
            elif evt.type == "mouseup":
                evt.stopPropagation()
                if self.toggle and self.up == self.state:
                    self.state = not self.state
                    updateAttr(self.id, 'state', self.state)
                elif not self.toggle:
                    self.up = True
                    self.state = False
                    updateAttr(self.id, 'state', self.state)
                    self.updateElements()
                self.dragging = False

class textControl:
    
    def __init__(self, parent, id, args):
        self.parent = parent
        self.id = id
        self.back_elt = getSVGElementById(args.back_id)
        if args.text != undefined:
            self.text = args.text
        else:
            self.text = ""
        self.updateElements()
    
    def updateValues(self, values):
        if values.text != self.value:
            self.text = values.text
            updateAttr(self.id, 'text', self.text)
            self.updateElements()
    
    def updateElements(self):
        self.back_elt.firstChild.firstChild.textContent = self.text
    
    def handleEvent(self, evt):
        pass
    

