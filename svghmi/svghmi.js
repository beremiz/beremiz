// svghmi.js

function dispatch_value(index, value) {
    let widgets = subscribers[index];

    // TODO : value cache
    
    if(widgets.size > 0) {
        for(let widget of widgets){
            let idxidx = widget.indexes.indexOf(index);
            if(idxidx == -1){
                throw new Error("Dispatching to widget not interested, should not happen.");
            }
            let d = widget.dispatch;
            if(typeof(d) == "function" && idxidx == 0){
                return d.call(widget,value);
            }else if(typeof(d) == "object" && d.length >= idxidx){
                d[idxidx].call(widget,value);
            }/* else dispatch_0, ..., dispatch_n ? */
            /*else {
                throw new Error("Dunno how to dispatch to widget at index = " + index);
            }*/
        }
    }
};

function init_widgets() {
    Object.keys(hmi_widgets).forEach(function(id) {
        let widget = hmi_widgets[id];
        let init = widget.init;
        if(typeof(init) == "function"){
            return init.call(widget);
        }
    });
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
                let [dvgetter, bytesize] = dvgetters[iectype];
                let value = dvgetter.call(dv,i,true);
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
    let jstype = typedarray_types[iectype];
    send_blob([
        new Uint8Array([0]),  /* setval = 0 */
        new Uint32Array([index]), 
        new jstype([value])]);

};

function change_hmi_value(index, opstr) {
    let op = opstr[0];
    if(op == "=")
        return send_hmi_value(index, Number(opstr.slice(1)));

    alert('Change '+opstr+" TODO !!! (index :"+index+")");
}

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
    init_widgets();
    send_reset();
    // show main page
    switch_page(default_page);
};

ws.onclose = function (evt) {
    // TODO : add visible notification while waiting for reload
    console.log("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+" Reload in 10s.");
    // TODO : re-enable auto reload when not in debug
    //window.setTimeout(() => location.reload(true), 10000);
    alert("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+".");

};
