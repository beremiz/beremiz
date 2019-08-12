<?xml version="1.0"?>
<xsl:stylesheet xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:svg="http://www.w3.org/2000/svg" xmlns:exsl="http://exslt.org/common" xmlns:ns="beremiz" xmlns:cc="http://creativecommons.org/ns#" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://purl.org/dc/elements/1.1/" extension-element-prefixes="ns" version="1.0" exclude-result-prefixes="ns">
  <xsl:output method="xml"/>
  <xsl:variable name="geometry" select="ns:GetSVGGeometry()"/>
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="/">
    <xsl:copy>
      <xsl:apply-templates mode="testgeo" select="$geometry"/>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:template mode="testgeo" match="bbox">
    <xsl:comment>
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
    </xsl:comment>
  </xsl:template>
</xsl:stylesheet>
