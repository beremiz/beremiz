<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ppx="http://www.plcopen.org/xml/tc6_0201"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:ns="instance_tagname_ns"
    extension-element-prefixes="ns"
    exclude-result-prefixes="ns">
  <xsl:param name="instance_path"/>
  <xsl:template name="element_name">
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
    <xsl:param name="path"/>
    <xsl:choose>
      <xsl:when test="contains($path,'.')">
        <xsl:value-of select="substring-after($path,'.')"/>
      </xsl:when>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:project">
    <xsl:variable name="config_name">
      <xsl:call-template name="element_name">
        <xsl:with-param name="path" select="$instance_path"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:apply-templates select="ppx:instances/ppx:configurations/ppx:configuration[@name=$config_name]">
      <xsl:with-param name="element_path">
        <xsl:call-template name="next_path">
          <xsl:with-param name="path" select="$instance_path"/>
        </xsl:call-template>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:configuration">
    <xsl:param name="element_path"/>
    <xsl:choose>
      <xsl:when test="$element_path!=''">
        <xsl:variable name="child_name">
	      <xsl:call-template name="element_name">
	        <xsl:with-param name="path" select="$element_path"/>
	      </xsl:call-template>
	    </xsl:variable>
        <xsl:apply-templates select="ppx:resource[@name=$child_name] | ppx:globalVars/ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
          <xsl:with-param name="element_path">
            <xsl:call-template name="next_path">
		      <xsl:with-param name="path" select="$element_path"/>
		    </xsl:call-template>
		  </xsl:with-param>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <ns:config_tagname>
          <xsl:attribute name="name">
            <xsl:value-of select="@name"/>
          </xsl:attribute>
        </ns:config_tagname>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:resource">
    <xsl:param name="element_path"/>
    <xsl:choose>
      <xsl:when test="$element_path!=''">
	    <xsl:variable name="child_name">
	      <xsl:call-template name="element_name">
	        <xsl:with-param name="path" select="$element_path"/>
	      </xsl:call-template>
	    </xsl:variable>
        <xsl:apply-templates select="ppx:pouInstance[@name=$child_name] | ppx:task/ppx:pouInstance[@name=$child_name] | ppx:globalVars/ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
          <xsl:with-param name="element_path">
            <xsl:call-template name="next_path">
              <xsl:with-param name="path" select="$element_path"/>
            </xsl:call-template>
          </xsl:with-param>
        </xsl:apply-templates>
      </xsl:when>
      <xsl:otherwise>
        <ns:resource_tagname>
          <xsl:attribute name="name">
            <xsl:value-of select="@name"/>
          </xsl:attribute>
          <xsl:attribute name="config_name">
            <xsl:value-of select="ancestor::ppx:configuration/@name"/>
          </xsl:attribute>
        </ns:resource_tagname>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:pouInstance">
    <xsl:param name="element_path"/>
    <ns:instance_definition>
      <xsl:attribute name="name">
        <xsl:value-of select="@typeName"/>
      </xsl:attribute>
      <xsl:attribute name="path">
        <xsl:value-of select="$element_path"/>
      </xsl:attribute>
    </ns:instance_definition>
  </xsl:template>
  <xsl:template match="ppx:pou">
    <xsl:param name="element_path"/>
    <xsl:variable name="child_name">
      <xsl:call-template name="element_name">
        <xsl:with-param name="path" select="$element_path"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:apply-templates select="ppx:interface/*/ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="element_path">
        <xsl:call-template name="next_path">
          <xsl:with-param name="path" select="$element_path"/>
        </xsl:call-template>
      </xsl:with-param>
    </xsl:apply-templates>
    <xsl:apply-templates select="ppx:actions/ppx:action[@name=$child_name]"/>
    <xsl:apply-templates select="ppx:transitions/ppx:transition[@name=$child_name]"/>
  </xsl:template>
  <xsl:template match="ppx:action">
    <ns:action_tagname>
      <xsl:attribute name="name">
        <xsl:value-of select="@name"/>
      </xsl:attribute>
      <xsl:attribute name="pou_name">
        <xsl:value-of select="ancestor::ppx:pou/@name"/>
      </xsl:attribute>
    </ns:action_tagname>
  </xsl:template>
  <xsl:template match="ppx:transition">
    <ns:transition_tagname>
      <xsl:attribute name="name">
        <xsl:value-of select="@name"/>
      </xsl:attribute>
      <xsl:attribute name="pou_name">
        <xsl:value-of select="ancestor::ppx:pou/@name"/>
      </xsl:attribute>
    </ns:transition_tagname>
  </xsl:template>
  <xsl:template name="ppx:dataType">
    <xsl:param name="element_path"/>
    <xsl:apply-templates select="ppx:baseType/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="element_path" select="element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="ppx:derived">
    <xsl:param name="element_path"/>
    <ns:instance_definition>
      <xsl:attribute name="name">
        <xsl:value-of select="@name"/>
      </xsl:attribute>
      <xsl:attribute name="path">
        <xsl:value-of select="$element_path"/>
      </xsl:attribute>
    </ns:instance_definition>
  </xsl:template>
  <xsl:template match="array">
    <xsl:param name="element_path"/>
    <xsl:apply-templates select="ppx:baseType/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="element_path" select="element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="struct">
    <xsl:param name="element_path"/>
    <xsl:variable name="child_name">
      <xsl:call-template name="element_name">
        <xsl:with-param name="path" select="$element_path"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:variable name="next_child_path">
      <xsl:call-template name="next_path">
        <xsl:with-param name="path" select="$element_path"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:apply-templates select="ppx:variable[@name=$child_name]/ppx:type/*[self::ppx:derived or self::ppx:struct or self::ppx:array]">
      <xsl:with-param name="element_path" select="element_path"/>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template match="pou_instance">
    <xsl:choose>
      <xsl:when test="@pou_path!=''">
        <xsl:apply-templates>
          <xsl:with-param name="element_path" select="@pou_path"/>
        </xsl:apply-templates>        
      </xsl:when>
      <xsl:otherwise>
        <ns:pou_tagname>
          <xsl:attribute name="name">
            <xsl:value-of select="ppx:pou/@name"/>
          </xsl:attribute>
        </ns:pou_tagname>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="datatype_instance">
    <xsl:apply-templates>
      <xsl:with-param name="element_path" select="@datatype_path"/>
    </xsl:apply-templates>
  </xsl:template>
</xsl:stylesheet>