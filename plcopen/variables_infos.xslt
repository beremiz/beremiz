<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ppx="http://www.plcopen.org/xml/tc6_0201"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:ns="var_infos_ns"
    extension-element-prefixes="ns"
    exclude-result-prefixes="ns">
  <xsl:template match="ppx:returnType">
    <ReturnType>
      <Type><xsl:apply-templates/></Type>
      <Tree><xsl:apply-templates mode="var_tree"/></Tree>
    </ReturnType>
  </xsl:template>
  <xsl:template match="ppx:localVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'Local'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:globalVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'Global'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:externalVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'External'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:tempVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'Temp'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:inputVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'Input'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:outputVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'Output'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="ppx:inOutVars">
    <xsl:call-template name="variables_infos">
      <xsl:with-param name="var_class" select="'InOut'"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template name="variables_infos">
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
      <ns:add_variable>
        <Name><xsl:value-of select="@name"/></Name>
        <Class><xsl:value-of select="$var_class"/></Class>
        <Type><xsl:apply-templates select="ppx:type"/></Type>
        <Option><xsl:value-of select="$var_option"/></Option>
        <Location><xsl:value-of select="@address"/></Location>
        <Initial_Value><xsl:apply-templates select="ppx:initialValue"/></Initial_Value>
        <Edit/>
        <Tree><xsl:apply-templates select="ppx:type" mode="var_tree"/></Tree>
        <Documentation>
          <xsl:value-of select="ppx:documentation/xhtml:p/text()"/>
        </Documentation>
      </ns:add_variable>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:derived">
    <xsl:value-of select="@name"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:array">
    <array>
      <xsl:apply-templates select="ppx:baseType"/>
      <xsl:for-each select="ppx:dimension">
        <dimension>
          <xsl:attribute name="lower">
            <xsl:value-of select="@lower"/>
          </xsl:attribute>
          <xsl:attribute name="upper">
            <xsl:value-of select="@upper"/>
          </xsl:attribute>
        </dimension>
      </xsl:for-each>
    </array>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:string">
    <xsl:text>STRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:wstring">
    <xsl:text>WSTRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/*">
    <xsl:value-of select="local-name()"/>
  </xsl:template>
    <xsl:template match="ppx:initialValue">
    <xsl:apply-templates/>
  </xsl:template>
  <xsl:template match="ppx:value">
    <xsl:choose>
      <xsl:when test="@repetitionValue">
        <xsl:value-of select="@repetitionValue"/>
        <xsl:text>(</xsl:text>
        <xsl:apply-templates/>
        <xsl:text>)</xsl:text>
      </xsl:when>
      <xsl:when test="@member">
        <xsl:value-of select="@member"/>
        <xsl:text> := </xsl:text>
        <xsl:apply-templates/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:apply-templates/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="ppx:simpleValue">
    <xsl:value-of select="@value"/>
  </xsl:template>
  <xsl:template match="ppx:arrayValue">
    <xsl:text>[</xsl:text>
    <xsl:for-each select="ppx:value">
      <xsl:apply-templates select="."/>
      <xsl:choose>
        <xsl:when test="position()!=last()">
          <xsl:text>, </xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:for-each>
    <xsl:text>]</xsl:text>
  </xsl:template>
  <xsl:template match="ppx:structValue">
    <xsl:text>(</xsl:text>
    <xsl:for-each select="ppx:value">
      <xsl:apply-templates select="."/>
      <xsl:choose>
        <xsl:when test="position()!=last()">
          <xsl:text>, </xsl:text>
        </xsl:when>
      </xsl:choose>
    </xsl:for-each>
    <xsl:text>)</xsl:text>
  </xsl:template>
  <xsl:template match="ppx:pou" mode="var_tree">
    <xsl:apply-templates select="ppx:interface/*[self::ppx:inputVars or self::ppx:inOutVars or self::ppx:outputVars]/ppx:variable" mode="var_tree"/>
  </xsl:template>
  <xsl:template match="ppx:variable" mode="var_tree">
    <var>
      <xsl:attribute name="name">
        <xsl:value-of select="@name"/>
      </xsl:attribute>
      <xsl:apply-templates select="ppx:type" mode="var_tree"/>
    </var>
  </xsl:template>
  <xsl:template match="ppx:dataType">
    <xsl:apply-templates select="ppx:baseType" mode="var_tree"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:struct" mode="var_tree">
    <xsl:apply-templates select="ppx:variable" mode="var_tree"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:derived" mode="var_tree">
    <ns:var_tree/>
    <xsl:choose>
      <xsl:when test="count(./*) > 0">
        <xsl:apply-templates mode="var_tree"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="@name"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:array" mode="var_tree">
    <xsl:apply-templates select="ppx:baseType" mode="var_tree"/>
    <xsl:for-each select="ppx:dimension">
      <dimension>
        <xsl:attribute name="lower">
          <xsl:value-of select="@lower"/>
        </xsl:attribute>
        <xsl:attribute name="upper">
          <xsl:value-of select="@upper"/>
        </xsl:attribute>
      </dimension>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:string" mode="var_tree">
    <xsl:text>STRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/ppx:wstring" mode="var_tree">
    <xsl:text>WSTRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType or self::ppx:returnType]/*" mode="var_tree">
    <xsl:value-of select="local-name()"/>
  </xsl:template>
  <xsl:template match="text()"/>
  <xsl:template match="text()" mode="var_tree"/>
</xsl:stylesheet>