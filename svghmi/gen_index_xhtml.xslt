<?xml version="1.0"?>
<xsl:stylesheet xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:svg="http://www.w3.org/2000/svg" xmlns="http://www.w3.org/1999/xhtml" xmlns:exsl="http://exslt.org/common" xmlns:ns="beremiz" xmlns:cc="http://creativecommons.org/ns#" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://purl.org/dc/elements/1.1/" extension-element-prefixes="ns" version="1.0" exclude-result-prefixes="ns">
  <xsl:output method="xml" cdata-section-elements="script"/>
  <xsl:variable name="geometry" select="ns:GetSVGGeometry()"/>
  <xsl:variable name="hmitree" select="ns:GetHMITree()"/>
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
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
          <xsl:text>(function(){
</xsl:text>
          <xsl:text>    var relative_URI = window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws');
</xsl:text>
          <xsl:text>    var ws = new WebSocket(relative_URI);
</xsl:text>
          <xsl:text>    ws.onmessage = function (evt) {
</xsl:text>
          <xsl:text>        var received_msg = evt.data;
</xsl:text>
          <xsl:text>        alert("Message is received..."+received_msg); 
</xsl:text>
          <xsl:text>    };
</xsl:text>
          <xsl:text>    ws.onopen = function (evt) {
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
