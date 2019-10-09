<?xml version="1.0"?>
<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:svg="http://www.w3.org/2000/svg" xmlns:str="http://exslt.org/strings" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:exsl="http://exslt.org/common" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:ns="beremiz" xmlns:cc="http://creativecommons.org/ns#" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://purl.org/dc/elements/1.1/" extension-element-prefixes="ns func" version="1.0" exclude-result-prefixes="ns str regexp exsl func">
  <xsl:output method="xml" cdata-section-elements="script"/>
  <xsl:variable name="geometry" select="ns:GetSVGGeometry()"/>
  <xsl:variable name="hmitree" select="ns:GetHMITree()"/>
  <xsl:variable name="hmi_elements" select="//*[starts-with(@inkscape:label, 'HMI:')]"/>
  <xsl:variable name="hmi_geometry" select="$geometry[@Id = $hmi_elements/@id]"/>
  <xsl:variable name="hmi_pages" select="$hmi_elements[func:parselabel(@inkscape:label)/widget/@type = 'Page']"/>
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
    <xsl:text>var hmi_index = {
</xsl:text>
    <xsl:variable name="svg" select="/"/>
    <xsl:for-each select="$indexed_hmitree/*">
      <xsl:value-of select="@index"/>
      <xsl:text>: {
</xsl:text>
      <xsl:text>    name: "</xsl:text>
      <xsl:value-of select="@name"/>
      <xsl:text>",
</xsl:text>
      <xsl:text>    hmipath: "</xsl:text>
      <xsl:value-of select="@hmipath"/>
      <xsl:text>"
</xsl:text>
      <xsl:text>    ids: [
</xsl:text>
      <xsl:variable name="hmipath" select="@hmipath"/>
      <xsl:for-each select="$svg//*[substring-after(@inkscape:label,'@') = $hmipath]">
        <xsl:text>        "</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>"</xsl:text>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>    ]
</xsl:text>
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
    <xsl:text>var page_desc = {
</xsl:text>
    <xsl:for-each select="$hmi_pages">
      <xsl:variable name="desc" select="func:parselabel(@inkscape:label)/widget"/>
      <xsl:text>    "</xsl:text>
      <xsl:value-of select="$desc/arg[1]/@value"/>
      <xsl:text>": {
</xsl:text>
      <xsl:text>        id: "</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>"
</xsl:text>
      <xsl:text>        widgets: [
</xsl:text>
      <xsl:variable name="page" select="."/>
      <xsl:variable name="p" select="$hmi_geometry[@Id = $page/@id]"/>
      <xsl:for-each select="$hmi_geometry[@Id != $page/@id and &#10;                       @x &gt;= $p/@x and @y &gt;= $p/@y and @w &lt;= $p/@w and @h &lt;= $p/@h]">
        <xsl:text>            "</xsl:text>
        <xsl:value-of select="@Id"/>
        <xsl:text>"</xsl:text>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>        ]
</xsl:text>
    </xsl:for-each>
    <xsl:text>}
</xsl:text>
    <xsl:text>// svghmi.js
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>(function(){
</xsl:text>
    <xsl:text>    // Open WebSocket to relative "/ws" address
</xsl:text>
    <xsl:text>    var ws = new WebSocket(window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws'));
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    // Register message reception handler 
</xsl:text>
    <xsl:text>    ws.onmessage = function (evt) {
</xsl:text>
    <xsl:text>        // TODO : dispatch and cache hmi tree updates
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        var received_msg = evt.data;
</xsl:text>
    <xsl:text>        // TODO : check for hmitree hash header
</xsl:text>
    <xsl:text>        //        if not matching, reload page
</xsl:text>
    <xsl:text>        alert("Message is received..."+received_msg); 
</xsl:text>
    <xsl:text>    };
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    // Once connection established
</xsl:text>
    <xsl:text>    ws.onopen = function (evt) {
</xsl:text>
    <xsl:text>        // TODO : enable the HMI (was previously offline, or just starts)
</xsl:text>
    <xsl:text>        //        show main page
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // TODO : prefix with hmitree hash header
</xsl:text>
    <xsl:text>        ws.send("test");
</xsl:text>
    <xsl:text>    };
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    var pending_updates = {};
</xsl:text>
    <xsl:text>    
</xsl:text>
    <xsl:text>    // subscription state, as it should be in hmi server
</xsl:text>
    <xsl:text>    // expected {index:period}
</xsl:text>
    <xsl:text>    const subscriptions = new Map();
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    // subscription state as needed by widget now
</xsl:text>
    <xsl:text>    // expected {index:[widgets]};
</xsl:text>
    <xsl:text>    var subscribers = {};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    // return the diff in between curently subscribed and subscription
</xsl:text>
    <xsl:text>    function update_subscriptions() {
</xsl:text>
    <xsl:text>        let delta = [];
</xsl:text>
    <xsl:text>        Object.keys(subscribers).forEach(index =&gt; {
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>            let previous_period = subscriptions.get(index);
</xsl:text>
    <xsl:text>            delete subscriptions[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>            let new_period = Math.min(...widgets.map(widget =&gt; widget.period));
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>            if(previous_period != new_period) 
</xsl:text>
    <xsl:text>                delta.push({index: index, period: new_period});
</xsl:text>
    <xsl:text>        })
</xsl:text>
    <xsl:text>        return result;
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    function update_value(index, value) {
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    };
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    function switch_page(page_name) {
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    };
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>})();
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
</xsl:stylesheet>
