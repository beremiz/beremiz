<?xml version="1.0"?>
<xsl:stylesheet xmlns:svg="http://www.w3.org/2000/svg" xmlns:ns="beremiz" xmlns:cc="http://creativecommons.org/ns#" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://www.w3.org/1999/xhtml" xmlns:str="http://exslt.org/strings" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:exsl="http://exslt.org/common" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" exclude-result-prefixes="ns" extension-element-prefixes="ns" version="1.0">
  <xsl:output method="xml" cdata-section-elements="script"/>
  <xsl:variable name="geometry" select="ns:GetSVGGeometry()"/>
  <xsl:variable name="hmitree" select="ns:GetHMITree()"/>
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:variable name="mark">
    <xsl:text>=HMI=
</xsl:text>
  </xsl:variable>
  <xsl:template match="/">
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head/>
      <body style="margin:0;">
        <xsl:copy>
          <xsl:comment>
            <xsl:apply-templates mode="testgeo" select="$geometry"/>
          </xsl:comment>
          <xsl:comment>
            <xsl:apply-templates mode="testtree" select="$hmitree"/>
          </xsl:comment>
          <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
        <script>
          <xsl:text>function evaluate_js_from_descriptions() {
</xsl:text>
          <xsl:text>    var Page;
</xsl:text>
          <xsl:text>    var Input;
</xsl:text>
          <xsl:text>    var Display;
</xsl:text>
          <xsl:text>    var res = [];
</xsl:text>
          <xsl:variable name="midmark">
            <xsl:text>
</xsl:text>
            <xsl:value-of select="$mark"/>
          </xsl:variable>
          <xsl:apply-templates mode="code_from_descs" select="//*[contains(child::svg:desc, $midmark) or                                starts-with(child::svg:desc, $mark)]"/>
          <xsl:text>    return res;
</xsl:text>
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
          <xsl:text>})();
</xsl:text>
        </script>
      </body>
    </html>
  </xsl:template>
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
    <xsl:value-of select="@name"/>
    <xsl:text> </xsl:text>
    <xsl:value-of select="@type"/>
    <xsl:text> </xsl:text>
    <xsl:value-of select="@path"/>
    <xsl:text>
</xsl:text>
    <xsl:apply-templates mode="testtree" select="*">
      <xsl:with-param name="indent">
        <xsl:value-of select="concat($indent,'&gt;')"/>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
</xsl:stylesheet>
