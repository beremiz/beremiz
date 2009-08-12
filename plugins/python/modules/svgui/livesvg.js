// import Nevow.Athena
// import Divmod.Base
function init() {
  Nevow.Athena.Widget.fromAthenaID(1).callRemote('HMIexec', 'initClient');
}

function updateAttr(id, param, value) {
  Nevow.Athena.Widget.fromAthenaID(1).callRemote('HMIexec', 'setattr', id, param, value);
}

var svguiWidgets={};

var currentObject = null;
function setCurrentObject(obj) {
	currentObject = obj;
}
function isCurrentObject(obj) {
	return currentObject == obj;
}

function getSVGElementById(id) {
	return document.getElementById(id);
}

function blockSVGElementDrag(element) {
	element.addEventListener("draggesture", function(event){event.stopPropagation()}, true);
}

LiveSVGPage.LiveSVGWidget = Nevow.Athena.Widget.subclass('LiveSVGPage.LiveSVGWidget');
LiveSVGPage.LiveSVGWidget.methods(
    function handleEvent(self, evt) {
        if (currentObject != null) {
            currentObject.handleEvent(evt);
        }
    },

    function receiveData(self, data){
        dataReceived = json_parse(data);
        newState = json_parse(dataReceived.kwargs).state
        svguiWidgets[dataReceived.back_id].updateState(newState);
        //console.log("OBJET : " + dataReceived.back_id + " STATE : " + newState);
    },
    
    function SvguiButton(self,elt_back, args){
        var btn = new svguilib.button(self, elt_back, args.sele_id, args.toggle, args.state, args.active);
        return btn;
    },
    
    function SvguiTextCtrl(self, elt_back, args){
        var txtCtrl = new svguilib.textControl(self, elt_back, args.state);
        return txtCtrl;
    },

    function init(self, arg1){
        //console.log("Object received : " + arg1);
        for (ind in arg1) {
            gad = json_parse(arg1[ind]);
            args = json_parse(gad.kwargs);
            gadget = self[gad.__class__](gad.back_id, args);
            svguiWidgets[gadget.back_elt.id]=gadget;
            //console.log('GADGET :' + gadget);
        }
        var elements = document.getElementsByTagName("svg");
        for (var i = 0; i < elements.length; i++) {
        	elements[i].addEventListener("mouseup", self, false);
        }
        //console.log("SVGUIWIDGETS : " + svguiWidgets);
    }
);

Divmod.Base.addLoadEvent(init);