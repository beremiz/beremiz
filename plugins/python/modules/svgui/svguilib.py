
class button:
    
    def __init__(self, parent, back_id, sele_id, toggle, state, active):
        self.parent = parent
        self.back_elt = getSVGElementById(back_id)
        self.sele_elt = getSVGElementById(sele_id)
        self.toggle = toggle
        self.state = state
        self.active = active
        self.dragging = False
        if toggle:
            self.up = not state
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
            self.sele_elt.setAttribute("visibility", "hidden")
            self.back_elt.setAttribute("visibility", "visible")
        else:
            self.sele_elt.setAttribute("visibility", "visible")
            self.back_elt.setAttribute("visibility", "hidden")
        
    def updateState(self, value):
        self.up = not value
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
                updateAttr(self.back_elt.id, 'state', self.state)
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
                    updateAttr(self.back_elt.id, 'state', self.state)
                elif not self.toggle:
                    self.up = True
                    self.state = False
                    updateAttr(self.back_elt.id, 'state', self.state)
                    self.updateElements()
                self.dragging = False
        
class textControl:
    
    def __init__(self, parent, back_id, state):
        self.parent = parent
        self.back_elt = getSVGElementById(back_id)
        self.state = state
        self.setValue(self.state)
    
    def handleEvent(self, evt):
        pass
    
    def getValue(self):
        return self.back_elt.firstChild.firstChild.textContent
    
    def setValue(self, value):
        self.back_elt.firstChild.firstChild.textContent = value
    
    def updateState(self, value):
        self.setValue(value)
    