// svghmi.js

function dispatch_value(index, value) {
    console.log("dispatch_value("+index+value+")");
};

// Open WebSocket to relative "/ws" address
var ws = new WebSocket(window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws'));
ws.binaryType = 'arraybuffer';

const dvgetters = {
    INT: [DataView.prototype.getInt16, 2],
    BOOL: [DataView.prototype.getInt8, 1]
    /* TODO */
};

// Register message reception handler 
ws.onmessage = function (evt) {

    let data = evt.data;
    let dv = new DataView(data);
    let i = 0;
    for(let hash_int of hmi_hash) {
        if(hash_int != dv.getUint8(i)){
            console.log("Recv non maching hash. Reload.");

            // 1003 is for "Unsupported Data"
            ws.close(1003,"Hash doesn't match");

            // TODO : remove debug alert ?
            alert("HMI will be reloaded.");

            // force reload ignoring cache
            location.reload(true);
        };
        i++;
    };

    while(i < data.length){
        let index = dv.getUint32(i);
        i += 4;
        let iectype = hmitree_types[index];
        let [dvgetter, bytesize] = dvgetters[iectypes];
        value = dvgetter.call(dv,i);
        dispatch_value(index, value);
        i += bytesize;
    };
};


function send_blob(data) {
    if(data.length > 0) {
        ws.send(new Blob([
            new Uint8Array(hmi_hash), 
            data]));
    };
};

const typedarray_types = {
    INT: Int16Array,
    BOOL: Uint8Array
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

function update_subscriptions() {
    let delta = [];
    for(let index = 0; index < subscribers.length; index++){
        let widgets = subscribers[index];

        // periods are in ms
        let previous_period = subscriptions[index];

        let new_period;
        if(widgets.size > 0) {
            let maxfreq = 0;
            for(let widget of widgets)
                if(maxfreq < widgets.frequency)
                    maxfreq = widgets.frequency;

            new_period = 1000/maxfreq;
        } else {
            new_period = 0;
        }

        if(previous_period != new_period) {
            subscriptions[index] = new_period;
            delta.push([
                new Uint8Array([2]), /* subscribe = 2 */
                new Uint32Array([index]), 
                new Uint16Array([new_period])]);
        }
        
    }
    send_blob(delta);
};

function update_value(index, value) {
    iectype = hmitree_types[index];
    jstype = typedarray_types[iectypes];
    send_blob([
        new Uint8Array([0]),  /* setval = 0 */
        new jstype([value])
        ]);

};

var current_page;

function switch_page(page_name) {
    let old_desc = page_desc[current_page];
    let new_desc = page_desc[page_name];
    /* TODO hide / show widgets */
    /* TODO move viewport */

    /* remove subsribers of previous page if any */
    if(old_desc) for(let widget of old_desc.widgets){
        for(let index of widget.indexes){
            subscribers[index].delete(widget);
        }
    }
    /* add new subsribers if any */
    if(new_desc) for(let widget of new_desc.widgets){
        for(let index of widget.indexes){
            subscribers[index].add(widget);
        }
    }

    current_page = page_name;

    update_subscriptions();
};


// Once connection established
ws.onopen = function (evt) {
    send_reset();
    // show main page
    switch_page(default_page);

};

