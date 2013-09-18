<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ppx="http://www.plcopen.org/xml/tc6_0201"
    xmlns:ns="instances_ns"
    extension-element-prefixes="ns"
    exclude-result-prefixes="ns">
  <xsl:param name="instance_type"/>
  <xsl:template match="ppx:project">
   <instances>
     <xsl:apply-templates select="ppx:instances/ppx:configurations/ppx:configuration"/>
   </instances>
  </xsl:template>
  <xsl:template match="ppx:configuration">
    <xsl:apply-templates select="ppx:globalVars/ppx:variable[ppx:type/ppx:derived]">
      <xsl:with-param name="parent_path" select="@name"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:resource">
      <xsl:with-param name="parent_path" select="@name"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:resource">
    <xsl:param name="parent_path"/>
    <xsl:variable name="resource_path">
      <xsl:value-of select="$parent_path"/>
      <xsl:text>.</xsl:text>
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:apply-templates select="ppx:globalVars/ppx:variable[ppx:type/ppx:derived]">
      <xsl:with-param name="parent_path" select="$resource_path"/>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:pouInstance | ppx:task/ppx:pouInstance">
      <xsl:with-param name="parent_path" select="$resource_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:pouInstance">
    <xsl:param name="parent_path"/>
    <xsl:variable name="pou_instance_path">
      <xsl:value-of select="$parent_path"/>
      <xsl:text>.</xsl:text>
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="@typeName=$instance_type">
        <instance>
          <xsl:attribute name="path">
            <xsl:value-of select="$pou_instance_path"/>
          </xsl:attribute>
        </instance>
      </xsl:when>
      <xsl:otherwise>
        <ns:instance_definition>
          <xsl:attribute name="name">
            <xsl:value-of select="@typeName"/>
          </xsl:attribute>
          <xsl:attribute name="path">
            <xsl:value-of select="$pou_instance_path"/>
          </xsl:attribute>
        </ns:instance_definition>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:pou">
    <xsl:param name="instance_path"/>
    <xsl:apply-templates select="ppx:interface/*/ppx:variable[ppx:type/ppx:derived]">
      <xsl:with-param name="parent_path" select="$instance_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:dataType">
    <xsl:param name="instance_path"/>
    <xsl:apply-templates select="ppx:baseType/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="parent_path" select="$instance_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:variable">
    <xsl:param name="parent_path"/>
    <xsl:variable name="variable_path">
      <xsl:value-of select="$parent_path"/>
      <xsl:text>.</xsl:text>
      <xsl:value-of select="@name"/>
    </xsl:variable>
    <xsl:apply-templates select="ppx:type/ppx:derived">
      <xsl:with-param name="variable_path" select="$variable_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:derived">
    <xsl:param name="variable_path"/>
    <xsl:choose>
      <xsl:when test="@name=$instance_type">
        <instance>
          <xsl:attribute name="path">
            <xsl:value-of select="$variable_path"/>
          </xsl:attribute>
        </instance>
      </xsl:when>
      <xsl:otherwise>
        <ns:instance_definition>
          <xsl:attribute name="name">
            <xsl:value-of select="@name"/>
          </xsl:attribute>
          <xsl:attribute name="path">
            <xsl:value-of select="$variable_path"/>
          </xsl:attribute>
        </ns:instance_definition>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template name="ppx:struct">
    <xsl:param name="variable_path"/>
    <xsl:for-each select="ppx:variable[ppx:type/ppx:derived or ppx:type/ppx:struct or ppx:type/ppx:array]">
      <xsl:variable name="element_path">
        <xsl:value-of select="$variable_path"/>
        <xsl:text>.</xsl:text>
        <xsl:value-of select="@name"/>
      </xsl:variable>
      <xsl:apply-templates select="ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
        <xsl:with-param name="variable_path" select="$element_path"/>
      </xsl:apply-templates>
    </xsl:for-each>
  </xsl:template>
  <xsl:template name="ppx:array">
    <xsl:param name="variable_path"/>
    <xsl:apply-templates select="ppx:baseType/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="variable_path" select="$variable_path"/>
    </xsl:apply-templates> 
  </xsl:template>
  <xsl:template match="pou_instance">
    <xsl:apply-templates>
      <xsl:with-param name="instance_path" select="@pou_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="datatype_instance">
    <xsl:apply-templates>
      <xsl:with-param name="instance_path" select="@datatype_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="text()"/>
</xsl:stylesheet>