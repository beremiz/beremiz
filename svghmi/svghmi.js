(function(){
    var relative_URI = window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws');
    var ws = new WebSocket(relative_URI);
    ws.onmessage = function (evt) {
        var received_msg = evt.data;
        alert("Message is received..."+received_msg); 
    };
    ws.onopen = function (evt) {
        ws.send("test");
    };
})();
