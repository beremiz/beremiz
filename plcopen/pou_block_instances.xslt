<?xml version="1.0"?>
<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:dyn="http://exslt.org/dynamic" xmlns:str="http://exslt.org/strings" xmlns:math="http://exslt.org/math" xmlns:exsl="http://exslt.org/common" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:yml="http://fdik.org/yml" xmlns:set="http://exslt.org/sets" xmlns:ppx="http://www.plcopen.org/xml/tc6_0201" xmlns:ns="pou_block_instances_ns" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" extension-element-prefixes="ns" version="1.0" exclude-result-prefixes="ns">
  <xsl:output method="xml"/>
  <xsl:variable name="space" select="'                                                                                                                                                                                                        '"/>
  <xsl:param name="autoindent" select="4"/>
  <xsl:template match="text()">
    <xsl:param name="_indent" select="0"/>
  </xsl:template>
  <xsl:template match="ppx:pou[ppx:body]|ppx:transition[ppx:body]|ppx:action[ppx:body]">
    <xsl:param name="_indent" select="0"/>
    <xsl:apply-templates select="ppx:body/*[self::ppx:FBD or self::ppx:LD or self::ppx:SFC]/*">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template name="add_instance">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="type"/>
    <xsl:value-of select="ns:AddBlockInstance($type, @localId, ppx:position/@x, ppx:position/@y, @width, @height)"/>
  </xsl:template>
  <xsl:template name="execution_order">
    <xsl:param name="_indent" select="0"/>
    <xsl:choose>
      <xsl:when test="@executionOrderId">
        <xsl:value-of select="@executionOrderId"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:text>0</xsl:text>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template name="ConnectionInfos">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="type"/>
    <xsl:param name="negated"/>
    <xsl:param name="edge"/>
    <xsl:param name="formalParameter"/>
    <xsl:value-of select="ns:AddInstanceConnection($type, $formalParameter, $negated, $edge, ppx:relPosition/@x, ppx:relPosition/@y)"/>
  </xsl:template>
  <xsl:template match="ppx:position">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:AddLinkPoint(@x, @y)"/>
  </xsl:template>
  <xsl:template match="ppx:connection">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:AddConnectionLink(@refLocalId, @formalParameter)"/>
    <xsl:apply-templates select="ppx:position">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:connectionPointIn">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="negated"/>
    <xsl:param name="edge"/>
    <xsl:param name="formalParameter"/>
    <xsl:call-template name="ConnectionInfos">
      <xsl:with-param name="type">
        <xsl:text>input</xsl:text>
      </xsl:with-param>
      <xsl:with-param name="negated">
        <xsl:value-of select="$negated"/>
      </xsl:with-param>
      <xsl:with-param name="edge">
        <xsl:value-of select="$edge"/>
      </xsl:with-param>
      <xsl:with-param name="formalParameter">
        <xsl:value-of select="$formalParameter"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connection">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:connectionPointOut">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="negated"/>
    <xsl:param name="edge"/>
    <xsl:param name="formalParameter"/>
    <xsl:call-template name="ConnectionInfos">
      <xsl:with-param name="type">
        <xsl:text>output</xsl:text>
      </xsl:with-param>
      <xsl:with-param name="negated">
        <xsl:value-of select="$negated"/>
      </xsl:with-param>
      <xsl:with-param name="edge">
        <xsl:value-of select="$edge"/>
      </xsl:with-param>
      <xsl:with-param name="formalParameter">
        <xsl:value-of select="$formalParameter"/>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:connectionPointOutAction">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="ConnectionInfos">
      <xsl:with-param name="type">
        <xsl:text>output</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:comment">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:SetSpecificValues(ppx:content/xhtml:p/text())"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="local-name()"/>
      </xsl:with-param>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:block">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="execution_order">
      <xsl:call-template name="execution_order"/>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues(@instanceName, $execution_order)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="@typeName"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:for-each select="ppx:inputVariables/ppx:variable">
      <xsl:apply-templates select="ppx:connectionPointIn">
        <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        <xsl:with-param name="negated" select="@negated"/>
        <xsl:with-param name="edge" select="@edge"/>
        <xsl:with-param name="formalParameter" select="@formalParameter"/>
      </xsl:apply-templates>
    </xsl:for-each>
    <xsl:for-each select="ppx:outputVariables/ppx:variable">
      <xsl:apply-templates select="ppx:connectionPointOut">
        <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        <xsl:with-param name="negated" select="@negated"/>
        <xsl:with-param name="edge" select="@edge"/>
        <xsl:with-param name="formalParameter" select="@formalParameter"/>
      </xsl:apply-templates>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:derived">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="@name"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:string">
    <xsl:param name="_indent" select="0"/>
    <xsl:text>STRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:wstring">
    <xsl:param name="_indent" select="0"/>
    <xsl:text>WSTRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/*">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="local-name()"/>
  </xsl:template>
  <xsl:template name="VariableBlockInfos">
    <xsl:param name="_indent" select="0"/>
    <xsl:param name="type"/>
    <xsl:variable name="expression">
      <xsl:value-of select="ppx:expression/text()"/>
    </xsl:variable>
    <xsl:variable name="value_type">
      <xsl:choose>
        <xsl:when test="ancestor::ppx:transition[@name=$expression]">
          <xsl:text>BOOL</xsl:text>
        </xsl:when>
        <xsl:when test="ancestor::ppx:pou[@name=$expression]">
          <xsl:apply-templates select="ancestor::ppx:pou/child::ppx:interface/ppx:returnType">
            <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
          </xsl:apply-templates>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates select="ancestor::ppx:pou/child::ppx:interface/*/ppx:variable[@name=$expression]/ppx:type">
            <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
          </xsl:apply-templates>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="execution_order">
      <xsl:call-template name="execution_order"/>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues($expression, $value_type, $execution_order)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="$type"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="negated" select="@negatedIn"/>
      <xsl:with-param name="edge" select="@edgeIn"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:connectionPointOut">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="negated" select="@negatedOut"/>
      <xsl:with-param name="edge" select="@edgeOut"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:inVariable">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="VariableBlockInfos">
      <xsl:with-param name="type" select="'input'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:outVariable">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="VariableBlockInfos">
      <xsl:with-param name="type" select="'output'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:inOutVariable">
    <xsl:param name="_indent" select="0"/>
    <xsl:call-template name="VariableBlockInfos">
      <xsl:with-param name="type" select="'inout'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:connector|ppx:continuation">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:SetSpecificValues(@name)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="local-name()"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:connectionPointOut">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:leftPowerRail|ppx:rightPowerRail">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type" select="local-name()"/>
    <xsl:variable name="connectors">
      <xsl:choose>
        <xsl:when test="$type='leftPowerRail'">
          <xsl:value-of select="count(ppx:connectionPointOut)"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="count(ppx:connectionPointIn)"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues($connectors)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="$type"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:choose>
      <xsl:when test="$type='leftPowerRail'">
        <xsl:apply-templates select="ppx:connectionPointOut">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates select="ppx:connectionPointIn">
          <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
        </xsl:apply-templates>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:contact|ppx:coil">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type" select="local-name()"/>
    <xsl:variable name="storage">
      <xsl:choose>
        <xsl:when test="$type='coil'">
          <xsl:value-of select="@storage"/>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="execution_order">
      <xsl:call-template name="execution_order"/>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues(ppx:variable/text(), @negated, @edge, $storage, $execution_order)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="$type"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:connectionPointOut">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:step">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:SetSpecificValues(@name, @initialStep)"/>
    <xsl:apply-templates select="ppx:connectionPointOutAction">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="negated" select="@negated"/>
    </xsl:apply-templates>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="local-name()"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:connectionPointOut">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:transition">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="priority">
      <xsl:choose>
        <xsl:when test="@priority">
          <xsl:value-of select="@priority"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>0</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="condition_type">
      <xsl:choose>
        <xsl:when test="ppx:condition/ppx:connectionPointIn">
          <xsl:text>connection</xsl:text>
        </xsl:when>
        <xsl:when test="ppx:condition/ppx:reference">
          <xsl:text>reference</xsl:text>
        </xsl:when>
        <xsl:when test="ppx:condition/ppx:inline">
          <xsl:text>inline</xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="condition">
      <xsl:choose>
        <xsl:when test="ppx:condition/ppx:reference">
          <xsl:value-of select="ppx:condition/ppx:reference/@name"/>
        </xsl:when>
        <xsl:when test="ppx:condition/ppx:inline">
          <xsl:value-of select="ppx:condition/ppx:inline/ppx:ST/xhtml:p/text()"/>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues($priority, $condition_type, $condition)"/>
    <xsl:apply-templates select="ppx:condition/ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="negated" select="ppx:condition/@negated"/>
    </xsl:apply-templates>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="local-name()"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:connectionPointOut">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:selectionDivergence|ppx:selectionConvergence|ppx:simultaneousDivergence|ppx:simultaneousConvergence">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type">
      <xsl:value-of select="local-name()"/>
    </xsl:variable>
    <xsl:variable name="connectors">
      <xsl:choose>
        <xsl:when test="$type='selectionDivergence' or $type='simultaneousDivergence'">
          <xsl:value-of select="count(ppx:connectionPointOut)"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="count(ppx:connectionPointIn)"/>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues($connectors)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="$type"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:connectionPointOut">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:jumpStep">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type">
      <xsl:text>jump</xsl:text>
    </xsl:variable>
    <xsl:value-of select="ns:SetSpecificValues(@targetName)"/>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="$type"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:action">
    <xsl:param name="_indent" select="0"/>
    <xsl:variable name="type">
      <xsl:choose>
        <xsl:when test="ppx:reference">
          <xsl:text>reference</xsl:text>
        </xsl:when>
        <xsl:when test="ppx:inline">
          <xsl:text>inline</xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="value">
      <xsl:choose>
        <xsl:when test="ppx:reference">
          <xsl:value-of select="ppx:reference/@name"/>
        </xsl:when>
        <xsl:when test="ppx:inline">
          <xsl:value-of select="ppx:inline/ppx:ST/xhtml:p/text()"/>
        </xsl:when>
      </xsl:choose>
    </xsl:variable>
    <xsl:variable name="qualifier">
      <xsl:choose>
        <xsl:when test="@qualifier">
          <xsl:value-of select="@qualifier"/>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>N</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:value-of select="ns:AddAction($qualifier, $type, $value, @duration, @indicator)"/>
  </xsl:template>
  <xsl:template match="ppx:actionBlock">
    <xsl:param name="_indent" select="0"/>
    <xsl:value-of select="ns:SetSpecificValues()"/>
    <xsl:apply-templates select="ppx:action">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
    </xsl:apply-templates>
    <xsl:call-template name="add_instance">
      <xsl:with-param name="type">
        <xsl:value-of select="local-name()"/>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:apply-templates select="ppx:connectionPointIn">
      <xsl:with-param name="_indent" select="$_indent + (1) * $autoindent"/>
      <xsl:with-param name="negated" select="@negated"/>
    </xsl:apply-templates>
  </xsl:template>
</xsl:stylesheet>
