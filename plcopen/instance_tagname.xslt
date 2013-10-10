<?xml version="1.0"?>
<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:dyn="http://exslt.org/dynamic" xmlns:str="http://exslt.org/strings" xmlns:math="http://exslt.org/math" xmlns:exsl="http://exslt.org/common" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:yml="http://fdik.org/yml" xmlns:set="http://exslt.org/sets" xmlns:ppx="http://www.plcopen.org/xml/tc6_0201" xmlns:ns="instance_tagname_ns" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" extension-element-prefixes="ns" version="1.0" exclude-result-prefixes="ns">
  <xsl:output method="xml"/>
  <xsl:variable name="space" select="'                                                                                                                                                                                                        '"/>
  <xsl:param name="autoindent" select="4"/>
  <xsl:param name="instance_path"/>
  <xsl:variable name="project">
    <xsl:copy-of select="document('project')/project/*"/>
  </xsl:variable>
  <xsl:variable name="stdlib">
    <xsl:copy-of select="document('stdlib')/stdlib/*"/>
  </xsl:variable>
  <xsl:variable name="extensions">
    <xsl:copy-of select="document('extensions')/extensions/*"/>
  </xsl:variable>
  <xsl:template name="element_name">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="path"/>
    <xsl:choose>
      <xsl:when test="contains($path,'.')">
        <xsl:value-of select="substring-before($path,'.')"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="$path"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template name="next_path">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="path"/>
    <xsl:choose>
      <xsl:when test="contains($path,'.')">
        <xsl:value-of select="substring-after($path,'.')"/>
      </xsl:when>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:project">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="config_name">
      <xsl:call-template name="element_name">
        <xsl:with-param name="path" select="$instance_path"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:apply-templates select="ppx:instances/ppx:configurations/ppx:configuration[@name=$config_name]">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="element_path">
        <xsl:call-template name="next_path">
          <xsl:with-param name="path" select="$instance_path"/>
        </xsl:call-template>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:configuration">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:choose>
      <xsl:when test="$element_path!=''">
        <xsl:variable name="child_name">
          <xsl:call-template name="element_name">
            <xsl:with-param name="path" select="$element_path"/>
          </xsl:call-template>
        </xsl:variable>
        <xsl:apply-templates select="ppx:resource[@name=$child_name] | ppx:globalVars/ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
          <xsl:with-param name="element_path">
            <xsl:call-template name="next_path">
              <xsl:with-param name="path" select="$element_path"/>
            </xsl:call-template>
          </xsl:with-param>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="ns:ConfigTagName(@name)"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:resource">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:choose>
      <xsl:when test="$element_path!=''">
        <xsl:variable name="child_name">
          <xsl:call-template name="element_name">
            <xsl:with-param name="path">
              <xsl:value-of select="$element_path"/>
            </xsl:with-param>
          </xsl:call-template>
        </xsl:variable>
        <xsl:apply-templates select="ppx:pouInstance[@name=$child_name] | ppx:task/ppx:pouInstance[@name=$child_name] | ppx:globalVars/ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
          <xsl:with-param name="element_path">
            <xsl:call-template name="next_path">
              <xsl:with-param name="path" select="$element_path"/>
            </xsl:call-template>
          </xsl:with-param>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="ns:ResourceTagName(ancestor::ppx:configuration/@name, @name)"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:pouInstance">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:variable name="type_name">
      <xsl:value-of select="@typeName"/>
    </xsl:variable>
    <xsl:apply-templates select="exsl:node-set($project)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                 exsl:node-set($project)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name] |&#10;                 exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                 exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name] |&#10;                 exsl:node-set($extensions)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                 exsl:node-set($extensions)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name]">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="element_path" select="$element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:pou">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:choose>
      <xsl:when test="$element_path!=''">
        <xsl:variable name="child_name">
          <xsl:call-template name="element_name">
            <xsl:with-param name="path" select="$element_path"/>
          </xsl:call-template>
        </xsl:variable>
        <xsl:apply-templates select="ppx:interface/*/ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
          <xsl:with-param name="element_path">
            <xsl:call-template name="next_path">
              <xsl:with-param name="path" select="$element_path"/>
            </xsl:call-template>
          </xsl:with-param>
        </xsl:apply-templates>
        <xsl:apply-templates select="ppx:actions/ppx:action[@name=$child_name] | ppx:transitions/ppx:transition[@name=$child_name]">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <xsl:variable name="name">
          <xsl:value-of select="@name"/>
        </xsl:variable>
        <xsl:value-of select="ns:PouTagName($name)"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:action">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:ActionTagName(ancestor::ppx:pou/@name, @name)"/>
  </xsl:template>
  <xsl:template match="ppx:transition">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:TransitionTagName(ancestor::ppx:pou/@name, @name)"/>
  </xsl:template>
  <xsl:template match="ppx:dataType">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:apply-templates select="ppx:baseType/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="element_path" select="$element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:derived">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:variable name="type_name">
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:apply-templates select="exsl:node-set($project)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                 exsl:node-set($project)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name] |&#10;                 exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                 exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name] |&#10;                 exsl:node-set($extensions)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                 exsl:node-set($extensions)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name]">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="element_path" select="$element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:array">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:apply-templates select="ppx:baseType/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="element_path" select="$element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:struct">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="element_path"/>
    <xsl:variable name="child_name">
      <xsl:call-template name="element_name">
        <xsl:with-param name="path" select="$element_path"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:apply-templates select="ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="element_path">
        <xsl:call-template name="next_path">
          <xsl:with-param name="path" select="$element_path"/>
        </xsl:call-template>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
</xsl:stylesheet>
