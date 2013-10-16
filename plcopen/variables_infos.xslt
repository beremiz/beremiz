<?xml version="1.0"?>
<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:dyn="http://exslt.org/dynamic" xmlns:str="http://exslt.org/strings" xmlns:math="http://exslt.org/math" xmlns:exsl="http://exslt.org/common" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:yml="http://fdik.org/yml" xmlns:set="http://exslt.org/sets" xmlns:ppx="http://www.plcopen.org/xml/tc6_0201" xmlns:ns="var_infos_ns" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" extension-element-prefixes="ns" version="1.0" exclude-result-prefixes="ns">
  <xsl:output method="xml"/>
  <xsl:variable name="space" select="'                                                                                                                                                                                                        '"/>
  <xsl:param name="autoindent" select="4"/>
  <xsl:param name="tree"/>
  <xsl:template match="text()">
    <xsl:param name="_indent" select="0"/>
  </xsl:template>
  <xsl:variable name="project">
    <xsl:copy-of select="document('project')/project/*"/>
  </xsl:variable>
  <xsl:variable name="stdlib">
    <xsl:copy-of select="document('stdlib')/stdlib/*"/>
  </xsl:variable>
  <xsl:variable name="extensions">
    <xsl:copy-of select="document('extensions')/extensions/*"/>
  </xsl:variable>
  <xsl:template match="ppx:configuration">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates select="ppx:globalVars">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:resource">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates select="ppx:globalVars">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:pou">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates select="ppx:interface/*">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:returnType">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:AddTree()"/>
    <xsl:apply-templates mode="var_type" select=".">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template name="variables_infos">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="var_class"/>
    <xsl:variable name="var_option">
      <xsl:choose>
        <xsl:when test="@constant='true' or @constant='1'">
          <xsl:text>Constant</xsl:text>
        </xsl:when>
        <xsl:when test="@retain='true' or @retain='1'">
          <xsl:text>Retain</xsl:text>
        </xsl:when>
        <xsl:when test="@nonretain='true' or @nonretain='1'">
          <xsl:text>Non-Retain</xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:for-each select="ppx:variable">
      <xsl:variable name="initial_value">
        <xsl:apply-templates select="ppx:initialValue">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:variable>
      <xsl:variable name="edit">
        <xsl:choose>
          <xsl:when test="$var_class='Global' or $var_class='External'">
            <xsl:text>true</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:apply-templates mode="var_edit" select="ppx:type">
              <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
            </xsl:apply-templates>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:variable>
      <xsl:value-of select="ns:AddTree()"/>
      <xsl:apply-templates mode="var_type" select="ppx:type">
        <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      </xsl:apply-templates>
      <xsl:value-of select="ns:AddVariable(@name, $var_class, $var_option, @address, $initial_value, $edit, ppx:documentation/xhtml:p/text())"/>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="ppx:localVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>Local</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:globalVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>Global</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:externalVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>External</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:tempVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>Temp</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:inputVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>Input</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:outputVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>Output</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:inOutVars">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class">
        <xsl:text>InOut</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template mode="var_type" match="ppx:pou">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates mode="var_type" select="ppx:interface/*[self::ppx:inputVars or self::ppx:inOutVars or self::ppx:outputVars]/ppx:variable">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template mode="var_type" match="ppx:variable">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="name">
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:value-of select="ns:AddTree()"/>
    <xsl:apply-templates mode="var_type" select="ppx:type">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:value-of select="ns:AddVarToTree($name)"/>
  </xsl:template>
  <xsl:template mode="var_type" match="ppx:dataType">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates mode="var_type" select="ppx:baseType">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template mode="var_type" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:struct">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates mode="var_type" select="ppx:variable">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template mode="var_type" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:derived">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type_name">
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="$tree='True'">
        <xsl:apply-templates mode="var_type" select="exsl:node-set($project)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                         exsl:node-set($project)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name] |&#10;                         exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                         exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name] |&#10;                         exsl:node-set($extensions)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                         exsl:node-set($extensions)/ppx:project/ppx:types/ppx:dataTypes/ppx:dataType[@name=$type_name]">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:when>
    </xsl:choose>
    <xsl:value-of select="ns:SetType($type_name)"/>
  </xsl:template>
  <xsl:template mode="var_type" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:array">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates mode="var_type" select="ppx:baseType">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:for-each select="ppx:dimension">
      <xsl:variable name="lower">
        <xsl:value-of select="@lower"/>
      </xsl:variable>
      <xsl:variable name="upper">
        <xsl:value-of select="@upper"/>
      </xsl:variable>
      <xsl:value-of select="ns:AddDimension($lower, $upper)"/>
    </xsl:for-each>
  </xsl:template>
  <xsl:template mode="var_type" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:string">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="name">
      <xsl:text>STRING</xsl:text>
    </xsl:variable>
    <xsl:value-of select="ns:SetType($name)"/>
  </xsl:template>
  <xsl:template mode="var_type" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:wstring">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="name">
      <xsl:text>WSTRING</xsl:text>
    </xsl:variable>
    <xsl:value-of select="ns:SetType($name)"/>
  </xsl:template>
  <xsl:template mode="var_type" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/*">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="name">
      <xsl:value-of select="local-name()"/>
    </xsl:variable>
    <xsl:value-of select="ns:SetType($name)"/>
  </xsl:template>
  <xsl:template mode="var_edit" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:derived">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type_name">
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:variable name="pou_infos">
      <xsl:copy-of select="exsl:node-set($project)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                    exsl:node-set($stdlib)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name] |&#10;                    exsl:node-set($extensions)/ppx:project/ppx:types/ppx:pous/ppx:pou[@name=$type_name]"/>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="$pou_infos != ''">
        <xsl:text>false</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>true</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template mode="var_edit" match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/*">
    <xsl:param name="_indent" select="0"/>
    <xsl:text>true</xsl:text>
  </xsl:template>
  <xsl:template match="ppx:value">
    <xsl:param name="_indent" select="0"/>
    <xsl:choose>
      <xsl:when test="@repetitionValue">
        <xsl:value-of select="@repetitionValue"/>
        <xsl:text>(</xsl:text>
        <xsl:apply-templates>
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
        <xsl:text>)</xsl:text>
      </xsl:when>
      <xsl:when test="@member">
        <xsl:value-of select="@member"/>
        <xsl:text> := </xsl:text>
        <xsl:apply-templates>
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates>
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:simpleValue">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="@value"/>
  </xsl:template>
  <xsl:template name="complex_type_value">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="start_bracket"/>
    <xsl:param name="end_bracket"/>
    <xsl:value-of select="$start_bracket"/>
    <xsl:for-each select="ppx:value">
      <xsl:apply-templates select=".">
        <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      </xsl:apply-templates>
      <xsl:choose>
        <xsl:when test="position()!=last()">
          <xsl:text>, </xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:for-each>
    <xsl:value-of select="$end_bracket"/>
  </xsl:template>
  <xsl:template match="ppx:arrayValue">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="complex_type_value">
      <xsl:with-param name="start_bracket">
        <xsl:text>[</xsl:text>
      </xsl:with-param>
      <xsl:with-param name="end_bracket">
        <xsl:text>]</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:structValue">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="complex_type_value">
      <xsl:with-param name="start_bracket">
        <xsl:text>(</xsl:text>
      </xsl:with-param>
      <xsl:with-param name="end_bracket">
        <xsl:text>)</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
</xsl:stylesheet>
