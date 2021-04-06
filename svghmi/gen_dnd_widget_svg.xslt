<?xml version="1.0"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:exsl="http://exslt.org/common" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:str="http://exslt.org/strings" xmlns:func="http://exslt.org/functions" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:cc="http://creativecommons.org/ns#" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:svg="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:ns="beremiz" version="1.0" extension-element-prefixes="ns func exsl regexp str dyn" exclude-result-prefixes="ns func exsl regexp str dyn">
  <xsl:output method="xml"/>
  <xsl:param name="hmi_path"/>
  <xsl:variable name="svg" select="/svg:svg"/>
  <xsl:variable name="hmi_elements" select="//svg:*[starts-with(@inkscape:label, 'HMI:')]"/>
  <xsl:variable name="subhmitree" select="ns:GetSubHMITree()"/>
  <xsl:variable name="indexed_hmitree" select="/.."/>
  <xsl:template mode="parselabel" match="*">
    <xsl:variable name="label" select="@inkscape:label"/>
    <xsl:variable name="id" select="@id"/>
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
    <xsl:if test="$type">
      <widget>
        <xsl:attribute name="id">
          <xsl:value-of select="$id"/>
        </xsl:attribute>
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
          <xsl:if test="string-length(.) &gt; 0">
            <path>
              <xsl:variable name="pathminmax" select="str:split(.,',')"/>
              <xsl:variable name="path" select="$pathminmax[1]"/>
              <xsl:variable name="pathminmaxcount" select="count($pathminmax)"/>
              <xsl:attribute name="value">
                <xsl:value-of select="$path"/>
              </xsl:attribute>
              <xsl:choose>
                <xsl:when test="$pathminmaxcount = 3">
                  <xsl:attribute name="min">
                    <xsl:value-of select="$pathminmax[2]"/>
                  </xsl:attribute>
                  <xsl:attribute name="max">
                    <xsl:value-of select="$pathminmax[3]"/>
                  </xsl:attribute>
                </xsl:when>
                <xsl:when test="$pathminmaxcount = 2">
                  <xsl:message terminate="yes">
                    <xsl:text>Widget id:</xsl:text>
                    <xsl:value-of select="$id"/>
                    <xsl:text> label:</xsl:text>
                    <xsl:value-of select="$label"/>
                    <xsl:text> has wrong syntax of path section </xsl:text>
                    <xsl:value-of select="$pathminmax"/>
                  </xsl:message>
                </xsl:when>
              </xsl:choose>
              <xsl:choose>
                <xsl:when test="regexp:test($path,'^\.[a-zA-Z0-9_]+$')">
                  <xsl:attribute name="type">
                    <xsl:text>PAGE_LOCAL</xsl:text>
                  </xsl:attribute>
                </xsl:when>
                <xsl:when test="regexp:test($path,'^[a-zA-Z0-9_]+$')">
                  <xsl:attribute name="type">
                    <xsl:text>HMI_LOCAL</xsl:text>
                  </xsl:attribute>
                </xsl:when>
                <xsl:otherwise>
                  <xsl:variable name="item" select="$indexed_hmitree/*[@hmipath = $path]"/>
                  <xsl:variable name="pathtype" select="local-name($item)"/>
                  <xsl:if test="$pathminmaxcount = 3 and not($pathtype = 'HMI_INT' or $pathtype = 'HMI_REAL')">
                    <xsl:message terminate="yes">
                      <xsl:text>Widget id:</xsl:text>
                      <xsl:value-of select="$id"/>
                      <xsl:text> label:</xsl:text>
                      <xsl:value-of select="$label"/>
                      <xsl:text> path section </xsl:text>
                      <xsl:value-of select="$pathminmax"/>
                      <xsl:text> use min and max on non mumeric value</xsl:text>
                    </xsl:message>
                  </xsl:if>
                  <xsl:if test="count($item) = 1">
                    <xsl:attribute name="index">
                      <xsl:value-of select="$item/@index"/>
                    </xsl:attribute>
                    <xsl:attribute name="type">
                      <xsl:value-of select="$pathtype"/>
                    </xsl:attribute>
                  </xsl:if>
                </xsl:otherwise>
              </xsl:choose>
            </path>
          </xsl:if>
        </xsl:for-each>
      </widget>
    </xsl:if>
  </xsl:template>
  <xsl:variable name="_parsed_widgets">
    <xsl:apply-templates mode="parselabel" select="$hmi_elements"/>
  </xsl:variable>
  <xsl:variable name="parsed_widgets" select="exsl:node-set($_parsed_widgets)"/>
  <xsl:variable name="selected_node_type" select="local-name($subhmitree)"/>
  <xsl:variable name="svg_widget" select="$parsed_widgets/widget[1]"/>
  <xsl:variable name="svg_widget_type" select="$svg_widget/@type"/>
  <xsl:variable name="svg_widget_path" select="$svg_widget/@path"/>
  <xsl:variable name="svg_widget_count" select="count($parsed_widgets/widget)"/>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="inline_svg" match="@*">
    <xsl:copy/>
  </xsl:template>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="inline_svg" match="@inkscape:label[starts-with(., 'HMI:')]">
    <xsl:copy/>
  </xsl:template>
  <xsl:template mode="inline_svg" match="node()">
    <xsl:copy>
      <xsl:apply-templates mode="inline_svg" select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
  <xsl:variable name="NODES_TYPES" select="str:split('HMI_ROOT HMI_NODE')"/>
  <xsl:variable name="HMI_NODES_COMPAT" select="str:split('Page Jump Foreach')"/>
  <xsl:template match="/">
    <xsl:comment>
      <xsl:text>Widget dropped in Inkscape from Beremiz</xsl:text>
    </xsl:comment>
    <xsl:choose>
      <xsl:when test="$svg_widget_count &lt; 1">
        <xsl:message terminate="yes">
          <xsl:text>No widget detected on selected SVG</xsl:text>
        </xsl:message>
      </xsl:when>
      <xsl:when test="$svg_widget_count &gt; 1">
        <xsl:message terminate="yes">
          <xsl:text>Multiple widget DnD not yet supported</xsl:text>
        </xsl:message>
      </xsl:when>
      <xsl:when test="$selected_node_type = $NODES_TYPES and                     not($svg_widget_type = $HMI_NODES_COMPAT)">
        <xsl:message terminate="yes">
          <xsl:text>Widget incompatible with selected HMI tree node</xsl:text>
        </xsl:message>
      </xsl:when>
    </xsl:choose>
    <xsl:variable name="testmsg">
      <msg>
        <xsl:value-of select="$hmi_path"/>
      </msg>
      <msg>
        <xsl:value-of select="$selected_node_type"/>
      </msg>
      <msg>
        <xsl:value-of select="$svg_widget_type"/>
      </msg>
    </xsl:variable>
    <xsl:value-of select="ns:GiveDetails($testmsg)"/>
    <xsl:apply-templates mode="inline_svg" select="/"/>
  </xsl:template>
</xsl:stylesheet>
