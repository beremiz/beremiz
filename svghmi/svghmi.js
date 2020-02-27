// svghmi.js

var cache = hmitree_types.map(_ignored => undefined);

function dispatch_value_to_widget(widget, index, value, oldval) {
    try {
        let idxidx = widget.indexes.indexOf(index);
        let d = widget.dispatch;
        if(typeof(d) == "function" && idxidx == 0){
            d.call(widget, value, oldval);
        }else if(typeof(d) == "object" && d.length >= idxidx){
            d[idxidx].call(widget, value, oldval);
        }/* else dispatch_0, ..., dispatch_n ? */
        /*else {
            throw new Error("Dunno how to dispatch to widget at index = " + index);
        }*/
    } catch(err) {
        console.log(err);
    }
}

function dispatch_value(index, value) {
    let widgets = subscribers[index];

    let oldval = cache[index];
    cache[index] = value;

    if(widgets.size > 0) {
        for(let widget of widgets){
            dispatch_value_to_widget(widget, index, value, oldval);
        }
    }
};

function init_widgets() {
    Object.keys(hmi_widgets).forEach(function(id) {
        let widget = hmi_widgets[id];
        let init = widget.init;
        if(typeof(init) == "function"){
            try {
                init.call(widget);
            } catch(err) {
                console.log(err);
            }
        }
    });
};

// Open WebSocket to relative "/ws" address
var ws = new WebSocket(window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws'));
ws.binaryType = 'arraybuffer';

const dvgetters = {
    INT: (dv,offset) => [dv.getInt16(offset, true), 2],
    BOOL: (dv,offset) => [dv.getInt8(offset, true), 1],
    STRING: (dv, offset) => {
        size = dv.getInt8(offset);
        return [
            String.fromCharCode.apply(null, new Uint8Array(
                dv.buffer, /* original buffer */
                offset + 1, /* string starts after size*/
                size /* size of string */
            )), size + 1]; /* total increment */
    }
};

// Register message reception handler
ws.onmessage = function (evt) {

    let data = evt.data;
    let dv = new DataView(data);
    let i = 0;
    try {
        for(let hash_int of hmi_hash) {
            if(hash_int != dv.getUint8(i)){
                throw new Error("Hash doesn't match");
            };
            i++;
        };

        while(i < data.byteLength){
            let index = dv.getUint32(i, true);
            i += 4;
            let iectype = hmitree_types[index];
            if(iectype != undefined){
                let dvgetter = dvgetters[iectype];
                let [value, bytesize] = dvgetter(dv,i);
                dispatch_value(index, value);
                i += bytesize;
            } else {
                throw new Error("Unknown index "+index)
            }
        };
    } catch(err) {
        // 1003 is for "Unsupported Data"
        // ws.close(1003, err.message);

        // TODO : remove debug alert ?
        alert("Error : "+err.message+"\\\\nHMI will be reloaded.");

        // force reload ignoring cache
        location.reload(true);
    }
};


function send_blob(data) {
    if(data.length > 0) {
        ws.send(new Blob([new Uint8Array(hmi_hash)].concat(data)));
    };
};

const typedarray_types = {
    INT: (number) => new Int16Array([number]),
    BOOL: (truth) => new Int16Array([truth]),
    STRING: (str) => {
        // beremiz default string max size is 128
        str = str.slice(0,128);
        binary = new Uint8Array(str.length + 1);
        binary[0] = str.length;
        for(var i = 0; i < str.length; i++){
            binary[i+1] = str.charCodeAt(i);
        }
        return binary;
    }
    /* TODO */
};

function send_reset() {
    send_blob(new Uint8Array([1])); /* reset = 1 */
};

// subscription state, as it should be in hmi server
// hmitree indexed array of integers
var subscriptions =  hmitree_types.map(_ignored => 0);

// subscription state as needed by widget now
// hmitree indexed array of Sets of widgets objects
var subscribers = hmitree_types.map(_ignored => new Set());

// artificially subscribe the watchdog widget to "/heartbeat" hmi variable
// Since dispatch directly calls change_hmi_value,
// PLC will periodically send variable at given frequency
subscribers[heartbeat_index].add({
    /* type: "Watchdog", */
    frequency: 1,
    indexes: [heartbeat_index],
    dispatch: function(value) {
        // console.log("Heartbeat" + value);
        change_hmi_value(heartbeat_index, "+1");
    }
});

function update_subscriptions() {
    let delta = [];
    for(let index = 0; index < subscribers.length; index++){
        let widgets = subscribers[index];

        // periods are in ms
        let previous_period = subscriptions[index];

        // subscribing with a zero period is unsubscribing
        let new_period = 0;
        if(widgets.size > 0) {
            let maxfreq = 0;
            for(let widget of widgets)
                if(maxfreq < widget.frequency)
                    maxfreq = widget.frequency;

            if(maxfreq != 0)
                new_period = 1000/maxfreq;
        }

        if(previous_period != new_period) {
            subscriptions[index] = new_period;
            delta.push(
                new Uint8Array([2]), /* subscribe = 2 */
                new Uint32Array([index]),
                new Uint16Array([new_period]));
        }
    }
    send_blob(delta);
};

function send_hmi_value(index, value) {
    let iectype = hmitree_types[index];
    let tobinary = typedarray_types[iectype];
    send_blob([
        new Uint8Array([0]),  /* setval = 0 */
        new Uint32Array([index]),
        tobinary(value)]);

    cache[index] = value;
};

function change_hmi_value(index, opstr) {
    let op = opstr[0];
    let given_val = opstr.slice(1);
    let old_val = cache[index]
    let new_val;
    switch(op){
      case "=":
        eval("new_val"+opstr);
        break;
      case "+":
      case "-":
      case "*":
      case "/":
        if(old_val != undefined)
            new_val = eval("old_val"+opstr);
        break;
    }
    if(new_val != undefined && old_val != new_val)
        send_hmi_value(index, new_val);
    return new_val;
}

var current_page;

function prepare_svg() {
    /* set everybody hidden initially for better performance */
    for(let widget in hmi_widgets){
        if(widget.element != undefined)
            widget.element.style.display = "none";
    }
        /*for(let name in page_desc){
            if(name != new_desc){
                page_desc[name].widget.element.style.display = "none";
            }
        }*/
};

function switch_page(page_name) {
    let old_desc = page_desc[current_page];
    let new_desc = page_desc[page_name];

    if(new_desc == undefined){
        /* TODO LOG ERROR */
        return;
    }

    if(old_desc){
        for(let widget of old_desc.widgets){

            /* hide widget */
            if(widget.element != undefined)
                widget.element.style.display = "none";

            /* remove subsribers */
            for(let index of widget.indexes){
                subscribers[index].delete(widget);
            }
        }
        old_desc.widget.element.style.display = "none";
    }

    for(let widget of new_desc.widgets){

        /* unhide widget */
        if(widget.element != undefined)
            widget.element.style.display = "inline";

        /* add widget's subsribers */
        for(let index of widget.indexes){
            subscribers[index].add(widget);
            /* dispatch current cache in newly opened page widgets */
            let cached_val = cache[index];
            if(cached_val != undefined)
                dispatch_value_to_widget(widget, index, cached_val, cached_val);
        }
    }

    new_desc.widget.element.style.display = "inline";

    svg_root.setAttribute('viewBox',new_desc.bbox.join(" "));
    current_page = page_name;

    update_subscriptions();
};


// Once connection established
ws.onopen = function (evt) {
    init_widgets();
    send_reset();
    // show main page
    prepare_svg();
    switch_page(default_page);
};

ws.onclose = function (evt) {
    // TODO : add visible notification while waiting for reload
    console.log("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+" Reload in 10s.");
    // TODO : re-enable auto reload when not in debug
    //window.setTimeout(() => location.reload(true), 10000);
    alert("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+".");

};
