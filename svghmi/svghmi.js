// svghmi.js

(function(){
    // Open WebSocket to relative "/ws" address
    var ws = new WebSocket(window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws'));

    // Register message reception handler 
    ws.onmessage = function (evt) {
        // TODO : dispatch and cache hmi tree updates

        var received_msg = evt.data;
        alert("Message is received..."+received_msg); 
    };

    // Once connection established
    ws.onopen = function (evt) {
        // TODO : enable the HMI (was previously offline, or just starts)
        //        show main page

        ws.send("test");
    };
})();
