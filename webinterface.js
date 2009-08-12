// import Nevow.Athena

WebInterface.PLC = Nevow.Athena.Widget.subclass('WebInterface.PLC');
WebInterface.PLC.method(
	 'updateHMI',
	 function (self, data) {
	   d = self.callRemote('getPLCElement');
	   d.addCallback(
			 function liveElementReceived(le) {
				d2 = self.addChildWidgetFromWidgetInfo(le);
				d2.addCallback(
						function childAdded(widget) {
						var node = self.nodeById('content');
						node.replaceChild(widget.node, node.getElementsByTagName('div')[0]);
						});
				});
	   });