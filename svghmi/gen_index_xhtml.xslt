<?xml version="1.0"?>
<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:svg="http://www.w3.org/2000/svg" xmlns:str="http://exslt.org/strings" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:exsl="http://exslt.org/common" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:ns="beremiz" xmlns:cc="http://creativecommons.org/ns#" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://purl.org/dc/elements/1.1/" extension-element-prefixes="ns func" version="1.0" exclude-result-prefixes="ns str regexp exsl func">
  <xsl:output method="xml" cdata-section-elements="xhtml:script"/>
  <xsl:variable name="geometry" select="ns:GetSVGGeometry()"/>
  <xsl:variable name="hmitree" select="ns:GetHMITree()"/>
  <xsl:variable name="hmi_elements" select="//svg:*[starts-with(@inkscape:label, 'HMI:')]"/>
  <xsl:variable name="hmi_geometry" select="$geometry[@Id = $hmi_elements/@id]"/>
  <xsl:variable name="hmi_pages" select="$hmi_elements[func:parselabel(@inkscape:label)/widget/@type = 'Page']"/>
  <xsl:variable name="default_page">
    <xsl:choose>
      <xsl:when test="count($hmi_pages) &gt; 1">
        <xsl:variable name="Home_page" select="$hmi_pages[func:parselabel(@inkscape:label)/widget/arg[1]/@value = 'Home']"/>
        <xsl:choose>
          <xsl:when test="$Home_page">
            <xsl:text>Home</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:message terminate="yes">No Home page defined!</xsl:message>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:when>
      <xsl:when test="count($hmi_pages) = 0">
        <xsl:message terminate="yes">No page defined!</xsl:message>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="func:parselabel($hmi_pages/@inkscape:label)/widget/arg[1]/@value"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:variable>
  <xsl:variable name="_categories">
    <noindex>
      <xsl:text>HMI_ROOT</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_LABEL</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_CLASS</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_PLC_STATUS</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_CURRENT_PAGE</xsl:text>
    </noindex>
  </xsl:variable>
  <xsl:variable name="categories" select="exsl:node-set($_categories)"/>
  <xsl:variable name="_indexed_hmitree">
    <xsl:apply-templates mode="index" select="$hmitree"/>
  </xsl:variable>
  <xsl:variable name="indexed_hmitree" select="exsl:node-set($_indexed_hmitree)"/>
  <xsl:template mode="index" match="*">
    <xsl:param name="index" select="0"/>
    <xsl:param name="parentpath" select="''"/>
    <xsl:variable name="content">
      <xsl:variable name="path">
        <xsl:choose>
          <xsl:when test="local-name() = 'HMI_ROOT'">
            <xsl:value-of select="$parentpath"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$parentpath"/>
            <xsl:text>/</xsl:text>
            <xsl:value-of select="@name"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:variable>
      <xsl:choose>
        <xsl:when test="not(local-name() = $categories/noindex)">
          <xsl:copy>
            <xsl:attribute name="index">
              <xsl:value-of select="$index"/>
            </xsl:attribute>
            <xsl:attribute name="hmipath">
              <xsl:value-of select="$path"/>
            </xsl:attribute>
            <xsl:for-each select="@*">
              <xsl:copy/>
            </xsl:for-each>
          </xsl:copy>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates mode="index" select="*[1]">
            <xsl:with-param name="index" select="$index"/>
            <xsl:with-param name="parentpath">
              <xsl:value-of select="$path"/>
            </xsl:with-param>
          </xsl:apply-templates>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:copy-of select="$content"/>
    <xsl:apply-templates mode="index" select="following-sibling::*[1]">
      <xsl:with-param name="index" select="$index + count(exsl:node-set($content)/*)"/>
      <xsl:with-param name="parentpath">
        <xsl:value-of select="$parentpath"/>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template mode="identity_svg" match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates mode="identity_svg" select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="/">
    <xsl:comment>
      <xsl:text>Made with SVGHMI. https://beremiz.org</xsl:text>
    </xsl:comment>
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head/>
      <body style="margin:0;">
        <xsl:copy>
          <xsl:comment>
            <xsl:apply-templates mode="testgeo" select="$hmi_geometry"/>
          </xsl:comment>
          <xsl:comment>
            <xsl:apply-templates mode="testtree" select="$hmitree"/>
          </xsl:comment>
          <xsl:comment>
            <xsl:apply-templates mode="testtree" select="$indexed_hmitree"/>
          </xsl:comment>
          <xsl:apply-templates mode="identity_svg" select="@* | node()"/>
        </xsl:copy>
        <script>
          <xsl:call-template name="scripts"/>
        </script>
      </body>
    </html>
  </xsl:template>
  <func:function name="func:parselabel">
    <xsl:param name="label"/>
    <xsl:variable name="description" select="substring-after($label,'HMI:')"/>
    <xsl:variable name="_args" select="substring-before($description,'@')"/>
    <xsl:variable name="args">
      <xsl:choose>
        <xsl:when test="$_args">
          <xsl:value-of select="$_args"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$description"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="_type" select="substring-before($args,':')"/>
    <xsl:variable name="type">
      <xsl:choose>
        <xsl:when test="$_type">
          <xsl:value-of select="$_type"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="$args"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="ast">
      <xsl:if test="$type">
        <widget>
          <xsl:attribute name="type">
            <xsl:value-of select="$type"/>
          </xsl:attribute>
          <xsl:for-each select="str:split(substring-after($args, ':'), ':')">
            <arg>
              <xsl:attribute name="value">
                <xsl:value-of select="."/>
              </xsl:attribute>
            </arg>
          </xsl:for-each>
          <xsl:variable name="paths" select="substring-after($description,'@')"/>
          <xsl:for-each select="str:split($paths, '@')">
            <path>
              <xsl:attribute name="value">
                <xsl:value-of select="."/>
              </xsl:attribute>
            </path>
          </xsl:for-each>
        </widget>
      </xsl:if>
    </xsl:variable>
    <func:result select="exsl:node-set($ast)"/>
  </func:function>
  <xsl:template name="scripts">
    <xsl:text>//(function(){
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var hmi_hash = [</xsl:text>
    <xsl:value-of select="$hmitree/@hash"/>
    <xsl:text>]; 
</xsl:text>
    <xsl:text>var hmi_widgets = {
</xsl:text>
    <xsl:for-each select="$hmi_elements">
      <xsl:variable name="widget" select="func:parselabel(@inkscape:label)/widget"/>
      <xsl:value-of select="@id"/>
      <xsl:text>: {
</xsl:text>
      <xsl:text>    type: "</xsl:text>
      <xsl:value-of select="$widget/@type"/>
      <xsl:text>",
</xsl:text>
      <xsl:text>    args: [
</xsl:text>
      <xsl:for-each select="$widget/arg">
        <xsl:text>        "</xsl:text>
        <xsl:value-of select="@value"/>
        <xsl:text>"</xsl:text>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>    ],
</xsl:text>
      <xsl:text>    indexes: [
</xsl:text>
      <xsl:for-each select="$widget/path">
        <xsl:variable name="hmipath" select="@value"/>
        <xsl:variable name="hmitree_match" select="$indexed_hmitree/*[@hmipath = $hmipath]"/>
        <xsl:if test="count($hmitree_match) = 0">
          <xsl:message terminate="yes">
            <xsl:text>No match for HMI </xsl:text>
            <xsl:value-of select="$hmipath"/>
            <xsl:text>;</xsl:text>
          </xsl:message>
        </xsl:if>
        <xsl:text>        </xsl:text>
        <xsl:value-of select="$hmitree_match/@index"/>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>    ],
</xsl:text>
      <xsl:text>    element: document.getElementById("</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>"),
</xsl:text>
      <xsl:apply-templates mode="widget_defs" select="$widget">
        <xsl:with-param name="hmi_element" select="."/>
      </xsl:apply-templates>
      <xsl:text>}</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var hmitree_types = [
</xsl:text>
    <xsl:for-each select="$indexed_hmitree/*">
      <xsl:text>/* </xsl:text>
      <xsl:value-of select="@index"/>
      <xsl:text>  </xsl:text>
      <xsl:value-of select="@hmipath"/>
      <xsl:text> */ "</xsl:text>
      <xsl:value-of select="substring(local-name(), 5)"/>
      <xsl:text>"</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>]
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var page_desc = {
</xsl:text>
    <xsl:for-each select="$hmi_pages">
      <xsl:variable name="desc" select="func:parselabel(@inkscape:label)/widget"/>
      <xsl:variable name="page" select="."/>
      <xsl:variable name="p" select="$hmi_geometry[@Id = $page/@id]"/>
      <xsl:variable name="page_ids" select="$hmi_geometry[@Id != $page/@id and &#10;                                @x &gt;= $p/@x and @y &gt;= $p/@y and &#10;                                @x+@w &lt;= $p/@x+$p/@w and @y+@h &lt;= $p/@y+$p/@h]/@Id"/>
      <xsl:variable name="page_elements" select="$hmi_elements[@id = $page_ids]"/>
      <xsl:text>    "</xsl:text>
      <xsl:value-of select="$desc/arg[1]/@value"/>
      <xsl:text>": {
</xsl:text>
      <xsl:text>        id: "</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>",
</xsl:text>
      <xsl:text>        widgets: [
</xsl:text>
      <xsl:for-each select="$page_ids">
        <xsl:text>            hmi_widgets.</xsl:text>
        <xsl:value-of select="."/>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>        ]
</xsl:text>
      <xsl:text>    }</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var default_page = "</xsl:text>
    <xsl:value-of select="$default_page"/>
    <xsl:text>";
</xsl:text>
    <xsl:text>// svghmi.js
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var cache = hmitree_types.map(_ignored =&gt; undefined);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function dispatch_value(index, value) {
</xsl:text>
    <xsl:text>    let widgets = subscribers[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    let oldval = cache[index];
</xsl:text>
    <xsl:text>    cache[index] = value;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    if(widgets.size &gt; 0) {
</xsl:text>
    <xsl:text>        for(let widget of widgets){
</xsl:text>
    <xsl:text>            let idxidx = widget.indexes.indexOf(index);
</xsl:text>
    <xsl:text>            if(idxidx == -1){
</xsl:text>
    <xsl:text>                throw new Error("Dispatching to widget not interested, should not happen.");
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>            let d = widget.dispatch;
</xsl:text>
    <xsl:text>            if(typeof(d) == "function" &amp;&amp; idxidx == 0){
</xsl:text>
    <xsl:text>                return d.call(widget, value, oldval);
</xsl:text>
    <xsl:text>            }else if(typeof(d) == "object" &amp;&amp; d.length &gt;= idxidx){
</xsl:text>
    <xsl:text>                return d[idxidx].call(widget, value, oldval);
</xsl:text>
    <xsl:text>            }/* else dispatch_0, ..., dispatch_n ? */
</xsl:text>
    <xsl:text>            /*else {
</xsl:text>
    <xsl:text>                throw new Error("Dunno how to dispatch to widget at index = " + index);
</xsl:text>
    <xsl:text>            }*/
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function init_widgets() {
</xsl:text>
    <xsl:text>    Object.keys(hmi_widgets).forEach(function(id) {
</xsl:text>
    <xsl:text>        let widget = hmi_widgets[id];
</xsl:text>
    <xsl:text>        let init = widget.init;
</xsl:text>
    <xsl:text>        if(typeof(init) == "function"){
</xsl:text>
    <xsl:text>            return init.call(widget);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    });
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// Open WebSocket to relative "/ws" address
</xsl:text>
    <xsl:text>var ws = new WebSocket(window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws'));
</xsl:text>
    <xsl:text>ws.binaryType = 'arraybuffer';
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>const dvgetters = {
</xsl:text>
    <xsl:text>    INT: [DataView.prototype.getInt16, 2],
</xsl:text>
    <xsl:text>    BOOL: [DataView.prototype.getInt8, 1]
</xsl:text>
    <xsl:text>    /* TODO */
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// Register message reception handler 
</xsl:text>
    <xsl:text>ws.onmessage = function (evt) {
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    let data = evt.data;
</xsl:text>
    <xsl:text>    let dv = new DataView(data);
</xsl:text>
    <xsl:text>    let i = 0;
</xsl:text>
    <xsl:text>    try {
</xsl:text>
    <xsl:text>        for(let hash_int of hmi_hash) {
</xsl:text>
    <xsl:text>            if(hash_int != dv.getUint8(i)){
</xsl:text>
    <xsl:text>                throw new Error("Hash doesn't match");
</xsl:text>
    <xsl:text>            };
</xsl:text>
    <xsl:text>            i++;
</xsl:text>
    <xsl:text>        };
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        while(i &lt; data.byteLength){
</xsl:text>
    <xsl:text>            let index = dv.getUint32(i, true);
</xsl:text>
    <xsl:text>            i += 4;
</xsl:text>
    <xsl:text>            let iectype = hmitree_types[index];
</xsl:text>
    <xsl:text>            if(iectype != undefined){
</xsl:text>
    <xsl:text>                let [dvgetter, bytesize] = dvgetters[iectype];
</xsl:text>
    <xsl:text>                let value = dvgetter.call(dv,i,true);
</xsl:text>
    <xsl:text>                dispatch_value(index, value);
</xsl:text>
    <xsl:text>                i += bytesize;
</xsl:text>
    <xsl:text>            } else {
</xsl:text>
    <xsl:text>                throw new Error("Unknown index "+index)
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        };
</xsl:text>
    <xsl:text>    } catch(err) {
</xsl:text>
    <xsl:text>        // 1003 is for "Unsupported Data"
</xsl:text>
    <xsl:text>        // ws.close(1003, err.message);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // TODO : remove debug alert ?
</xsl:text>
    <xsl:text>        alert("Error : "+err.message+"\nHMI will be reloaded.");
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // force reload ignoring cache
</xsl:text>
    <xsl:text>        location.reload(true);
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function send_blob(data) {
</xsl:text>
    <xsl:text>    if(data.length &gt; 0) {
</xsl:text>
    <xsl:text>        ws.send(new Blob([new Uint8Array(hmi_hash)].concat(data)));
</xsl:text>
    <xsl:text>    };
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>const typedarray_types = {
</xsl:text>
    <xsl:text>    INT: Int16Array,
</xsl:text>
    <xsl:text>    BOOL: Uint8Array
</xsl:text>
    <xsl:text>    /* TODO */
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function send_reset() {
</xsl:text>
    <xsl:text>    send_blob(new Uint8Array([1])); /* reset = 1 */
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// subscription state, as it should be in hmi server
</xsl:text>
    <xsl:text>// hmitree indexed array of integers
</xsl:text>
    <xsl:text>var subscriptions =  hmitree_types.map(_ignored =&gt; 0);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// subscription state as needed by widget now
</xsl:text>
    <xsl:text>// hmitree indexed array of Sets of widgets objects
</xsl:text>
    <xsl:text>var subscribers = hmitree_types.map(_ignored =&gt; new Set());
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function update_subscriptions() {
</xsl:text>
    <xsl:text>    let delta = [];
</xsl:text>
    <xsl:text>    for(let index = 0; index &lt; subscribers.length; index++){
</xsl:text>
    <xsl:text>        let widgets = subscribers[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // periods are in ms
</xsl:text>
    <xsl:text>        let previous_period = subscriptions[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        let new_period = 0;
</xsl:text>
    <xsl:text>        if(widgets.size &gt; 0) {
</xsl:text>
    <xsl:text>            let maxfreq = 0;
</xsl:text>
    <xsl:text>            for(let widget of widgets)
</xsl:text>
    <xsl:text>                if(maxfreq &lt; widget.frequency)
</xsl:text>
    <xsl:text>                    maxfreq = widget.frequency;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>            if(maxfreq != 0)
</xsl:text>
    <xsl:text>                new_period = 1000/maxfreq;
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        if(previous_period != new_period) {
</xsl:text>
    <xsl:text>            subscriptions[index] = new_period;
</xsl:text>
    <xsl:text>            delta.push(
</xsl:text>
    <xsl:text>                new Uint8Array([2]), /* subscribe = 2 */
</xsl:text>
    <xsl:text>                new Uint32Array([index]),
</xsl:text>
    <xsl:text>                new Uint16Array([new_period]));
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>    send_blob(delta);
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function send_hmi_value(index, value) {
</xsl:text>
    <xsl:text>    let iectype = hmitree_types[index];
</xsl:text>
    <xsl:text>    let jstype = typedarray_types[iectype];
</xsl:text>
    <xsl:text>    send_blob([
</xsl:text>
    <xsl:text>        new Uint8Array([0]),  /* setval = 0 */
</xsl:text>
    <xsl:text>        new Uint32Array([index]), 
</xsl:text>
    <xsl:text>        new jstype([value])]);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    cache[index] = value;
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function change_hmi_value(index, opstr) {
</xsl:text>
    <xsl:text>    let op = opstr[0];
</xsl:text>
    <xsl:text>    let given_val = opstr.slice(1);
</xsl:text>
    <xsl:text>    let old_val = cache[index]
</xsl:text>
    <xsl:text>    let new_val;
</xsl:text>
    <xsl:text>    switch(op){
</xsl:text>
    <xsl:text>      case "=":
</xsl:text>
    <xsl:text>        eval("new_val"+opstr);
</xsl:text>
    <xsl:text>        break;
</xsl:text>
    <xsl:text>      case "+":
</xsl:text>
    <xsl:text>      case "-":
</xsl:text>
    <xsl:text>      case "*":
</xsl:text>
    <xsl:text>      case "/":
</xsl:text>
    <xsl:text>        if(old_val != undefined)
</xsl:text>
    <xsl:text>            new_val = eval("old_val"+opstr);
</xsl:text>
    <xsl:text>        break;
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>    if(new_val != undefined &amp;&amp; old_val != new_val)
</xsl:text>
    <xsl:text>        send_hmi_value(index, new_val);
</xsl:text>
    <xsl:text>    return new_val;
</xsl:text>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var current_page;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function switch_page(page_name) {
</xsl:text>
    <xsl:text>    let old_desc = page_desc[current_page];
</xsl:text>
    <xsl:text>    let new_desc = page_desc[page_name];
</xsl:text>
    <xsl:text>    /* TODO hide / show widgets */
</xsl:text>
    <xsl:text>    /* TODO move viewport */
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    /* remove subsribers of previous page if any */
</xsl:text>
    <xsl:text>    if(old_desc) for(let widget of old_desc.widgets){
</xsl:text>
    <xsl:text>        for(let index of widget.indexes){
</xsl:text>
    <xsl:text>            subscribers[index].delete(widget);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>    /* add new subsribers if any */
</xsl:text>
    <xsl:text>    if(new_desc) for(let widget of new_desc.widgets){
</xsl:text>
    <xsl:text>        for(let index of widget.indexes){
</xsl:text>
    <xsl:text>            subscribers[index].add(widget);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    current_page = page_name;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    update_subscriptions();
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// Once connection established
</xsl:text>
    <xsl:text>ws.onopen = function (evt) {
</xsl:text>
    <xsl:text>    init_widgets();
</xsl:text>
    <xsl:text>    send_reset();
</xsl:text>
    <xsl:text>    // show main page
</xsl:text>
    <xsl:text>    switch_page(default_page);
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>ws.onclose = function (evt) {
</xsl:text>
    <xsl:text>    // TODO : add visible notification while waiting for reload
</xsl:text>
    <xsl:text>    console.log("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+" Reload in 10s.");
</xsl:text>
    <xsl:text>    // TODO : re-enable auto reload when not in debug
</xsl:text>
    <xsl:text>    //window.setTimeout(() =&gt; location.reload(true), 10000);
</xsl:text>
    <xsl:text>    alert("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+".");
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>//})();
</xsl:text>
  </xsl:template>
  <xsl:template mode="page_desc" match="*"/>
  <xsl:template mode="code_from_descs" match="*">
    <xsl:text>{
</xsl:text>
    <xsl:text>    var path, role, name, priv;
</xsl:text>
    <xsl:text>    var id = "</xsl:text>
    <xsl:value-of select="@id"/>
    <xsl:text>";
</xsl:text>
    <xsl:if test="@inkscape:label">
      <xsl:text>name = "</xsl:text>
      <xsl:value-of select="@inkscape:label"/>
      <xsl:text>";
</xsl:text>
    </xsl:if>
    <xsl:text>/* -------------- */
</xsl:text>
    <xsl:value-of select="substring-after(svg:desc, $mark)"/>
    <xsl:text>
</xsl:text>
    <xsl:text>    /* -------------- */
</xsl:text>
    <xsl:text>    res.push({
</xsl:text>
    <xsl:text>        path:path,
</xsl:text>
    <xsl:text>        role:role,
</xsl:text>
    <xsl:text>        name:name,
</xsl:text>
    <xsl:text>        priv:priv
</xsl:text>
    <xsl:text>    })
</xsl:text>
    <xsl:text>}
</xsl:text>
  </xsl:template>
  <xsl:template mode="testgeo" match="bbox">
    <xsl:text>ID: </xsl:text>
    <xsl:value-of select="@Id"/>
    <xsl:text> x: </xsl:text>
    <xsl:value-of select="@x"/>
    <xsl:text> y: </xsl:text>
    <xsl:value-of select="@y"/>
    <xsl:text> w: </xsl:text>
    <xsl:value-of select="@w"/>
    <xsl:text> h: </xsl:text>
    <xsl:value-of select="@h"/>
    <xsl:text>
</xsl:text>
  </xsl:template>
  <xsl:template mode="testtree" match="*">
    <xsl:param name="indent" select="''"/>
    <xsl:value-of select="$indent"/>
    <xsl:text> </xsl:text>
    <xsl:value-of select="local-name()"/>
    <xsl:text> </xsl:text>
    <xsl:for-each select="@*">
      <xsl:value-of select="local-name()"/>
      <xsl:text>=</xsl:text>
      <xsl:value-of select="."/>
      <xsl:text> </xsl:text>
    </xsl:for-each>
    <xsl:text>
</xsl:text>
    <xsl:apply-templates mode="testtree" select="*">
      <xsl:with-param name="indent">
        <xsl:value-of select="concat($indent,'&gt;')"/>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Display']">
    <xsl:param name="hmi_element"/>
    <xsl:text>frequency: 5,
</xsl:text>
    <xsl:text>dispatch: function(value) {
</xsl:text>
    <xsl:choose>
      <xsl:when test="$hmi_element[self::svg:text]">
        <xsl:text>  this.element.textContent = String(value);
</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message terminate="yes">
          <xsl:text>Display widget as a group not implemented</xsl:text>
        </xsl:message>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:text>},
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Meter']">
    <xsl:param name="hmi_element"/>
    <xsl:text>frequency: 10,
</xsl:text>
    <xsl:for-each select="str:split('value min max needle range')">
      <xsl:variable name="name" select="."/>
      <xsl:variable name="elt_id" select="$hmi_element//*[@inkscape:label=$name][1]/@id"/>
      <xsl:if test="not($elt_id)">
        <xsl:message terminate="yes">
          <xsl:text>Meter widget must have a </xsl:text>
          <xsl:value-of select="$name"/>
          <xsl:text> element</xsl:text>
        </xsl:message>
      </xsl:if>
      <xsl:value-of select="$name"/>
      <xsl:text>_elt: document.getElementById("</xsl:text>
      <xsl:value-of select="$elt_id"/>
      <xsl:text>"),
</xsl:text>
    </xsl:for-each>
    <xsl:text>dispatch: function(value) {
</xsl:text>
    <xsl:text>    this.value_elt.textContent = String(value);
</xsl:text>
    <xsl:text>    let [min,max,totallength] = this.range;
</xsl:text>
    <xsl:text>    let length = Math.max(0,Math.min(totallength,(Number(value)-min)*totallength/(max-min)));
</xsl:text>
    <xsl:text>    let tip = this.range_elt.getPointAtLength(length);
</xsl:text>
    <xsl:text>    this.needle_elt.setAttribute('d', "M "+this.origin.x+","+this.origin.y+" "+tip.x+","+tip.y);
</xsl:text>
    <xsl:text>},
</xsl:text>
    <xsl:text>origin: undefined,
</xsl:text>
    <xsl:text>range: undefined,
</xsl:text>
    <xsl:text>init: function() {
</xsl:text>
    <xsl:text>    this.range = [Number(this.min_elt.textContent), Number(this.max_elt.textContent), this.range_elt.getTotalLength()]
</xsl:text>
    <xsl:text>    this.origin = this.needle_elt.getPointAtLength(0);
</xsl:text>
    <xsl:text>},
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Input']">
    <xsl:param name="hmi_element"/>
    <xsl:text>frequency: 5,
</xsl:text>
    <xsl:variable name="value_elt_id" select="$hmi_element//*[self::svg:text][@inkscape:label='value'][1]/@id"/>
    <xsl:if test="not($value_elt_id)">
      <xsl:message terminate="yes">
        <xsl:text>Input widget must have a text element</xsl:text>
      </xsl:message>
    </xsl:if>
    <xsl:text>value_elt: document.getElementById("</xsl:text>
    <xsl:value-of select="$value_elt_id"/>
    <xsl:text>"),
</xsl:text>
    <xsl:text>dispatch: function(value) {
</xsl:text>
    <xsl:text>    this.value_elt.textContent = String(value);
</xsl:text>
    <xsl:text>},
</xsl:text>
    <xsl:variable name="edit_elt_id" select="$hmi_element/*[@inkscape:label='edit'][1]/@id"/>
    <xsl:text>init: function() {
</xsl:text>
    <xsl:if test="$edit_elt_id">
      <xsl:text>    document.getElementById("</xsl:text>
      <xsl:value-of select="$edit_elt_id"/>
      <xsl:text>").addEventListener(
</xsl:text>
      <xsl:text>        "click", 
</xsl:text>
      <xsl:text>        evt =&gt; alert('XXX TODO : Edit value'));
</xsl:text>
    </xsl:if>
    <xsl:for-each select="$hmi_element/*[regexp:test(@inkscape:label,'^[=+\-][0-9]+')]">
      <xsl:text>    document.getElementById("</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>").addEventListener(
</xsl:text>
      <xsl:text>        "click", 
</xsl:text>
      <xsl:text>        evt =&gt; {let new_val = change_hmi_value(this.indexes[0], "</xsl:text>
      <xsl:value-of select="@inkscape:label"/>
      <xsl:text>");
</xsl:text>
      <xsl:text>                this.value_elt.textContent = String(new_val);});
</xsl:text>
    </xsl:for-each>
    <xsl:text>},
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Button']"/>
  <xsl:template mode="widget_defs" match="widget[@type='Toggle']">
    <xsl:text>    frequency: 5,
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Change']">
    <xsl:text>    frequency: 5,
</xsl:text>
  </xsl:template>
</xsl:stylesheet>
