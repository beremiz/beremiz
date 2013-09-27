<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ppx="http://www.plcopen.org/xml/tc6_0201"
    xmlns:ns="pou_vars_ns"
    extension-element-prefixes="ns"
    exclude-result-prefixes="ns">
  <xsl:template match="ppx:pou">
    <pou>
      <class><xsl:value-of select="@pouType"/></class>
      <type><xsl:value-of select="@name"/></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>True</xsl:text></debug>
      <variables>
        <xsl:apply-templates select="ppx:interface"/>
        <xsl:apply-templates select="ppx:actions/ppx:action | ppx:transitions/ppx:transition" mode="variable_list"/>
      </variables>
    </pou>
  </xsl:template>
  <xsl:template match="ppx:action">
    <action>
      <class/>
      <type><xsl:text>None</xsl:text></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>True</xsl:text></debug>
      <variables>
        <xsl:apply-templates select="ancestor::ppx:pou/child::ppx:interface"/>
      </variables>
    </action>
  </xsl:template>
  <xsl:template match="ppx:transition">
    <transition>
      <class/>
      <type><xsl:text>None</xsl:text></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>True</xsl:text></debug>
      <variables>
        <xsl:apply-templates select="ancestor::ppx:pou/child::ppx:interface"/>
      </variables>
    </transition>
  </xsl:template>
  <xsl:template match="ppx:configuration">
    <configuration>
      <class/>
      <type><xsl:text>None</xsl:text></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>False</xsl:text></debug>
      <variables>
        <xsl:apply-templates select="ppx:resource" mode="variable_list"/>
        <xsl:apply-templates select="ppx:globalVars"/>
      </variables>
    </configuration>
  </xsl:template>
  <xsl:template match="ppx:resource">
    <resource>
      <class/>
      <type><xsl:text>None</xsl:text></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>False</xsl:text></debug>
      <variables>
        <xsl:apply-templates select="ppx:pouInstance | ppx:task/ppx:pouInstance" mode="variable_list"/>
        <xsl:apply-templates select="ppx:globalVars"/>
      </variables>
    </resource>
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
	<xsl:for-each select="ppx:variable">
      <variable>
	    <name><xsl:value-of select="@name"/></name>
	    <class>
	      <xsl:apply-templates mode="var_class">
	        <xsl:with-param name="default_class">
	          <xsl:value-of select="$var_class"/>
	        </xsl:with-param>
	      </xsl:apply-templates>
	    </class>
	    <type><xsl:apply-templates mode="var_type"/></type>
	    <edit><xsl:apply-templates mode="var_edit"/></edit>
	    <debug><xsl:apply-templates mode="var_debug"/></debug>
      </variable>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="ppx:transition" mode="variable_list">
    <transition>
      <name><xsl:value-of select="@name"/></name>
      <class/>
      <type><xsl:text>None</xsl:text></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>True</xsl:text></debug>
    </transition>
  </xsl:template>
  <xsl:template match="ppx:action" mode="variable_list">
    <action>
	  <name><xsl:value-of select="@name"/></name>
	  <class/>
      <type><xsl:text>None</xsl:text></type>
	  <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>True</xsl:text></debug>
    </action>
  </xsl:template>
  <xsl:template match="ppx:resource" mode="variable_list">
    <resource>
      <name><xsl:value-of select="@name"/></name>
      <class/>
      <type><xsl:text>None</xsl:text></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>False</xsl:text></debug>
    </resource>
  </xsl:template>
  <xsl:template match="ppx:pouInstance" mode="variable_list">
    <program>
      <name><xsl:value-of select="@name"/></name>
      <class/>
      <type><xsl:value-of select="@typeName"/></type>
      <edit><xsl:text>True</xsl:text></edit>
      <debug><xsl:text>True</xsl:text></debug>
    </program>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:derived" mode="var_class">
    <xsl:param name="default_class"/>
    <ns:pou_class>
      <xsl:value-of select="$default_class"/>
    </ns:pou_class>
  </xsl:template>
  <xsl:template match="ppx:pou" mode="var_class">
    <xsl:param name="default_class"/>
    <xsl:value-of select="@pouType"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/*" mode="var_class">
    <xsl:param name="default_class"/>
    <xsl:value-of select="$default_class"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:derived" mode="var_type">
    <xsl:value-of select="@name"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:array" mode="var_type">
    <xsl:text>ARRAY [</xsl:text>
    <xsl:for-each select="ppx:dimension">
      <xsl:value-of select="@lower"/>
      <xsl:text>..</xsl:text>
      <xsl:value-of select="@upper"/>
    </xsl:for-each>
    <xsl:text>] OF </xsl:text>
    <xsl:apply-templates select="ppx:baseType" mode="var_type"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:string" mode="var_type">
    <xsl:text>STRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:wstring" mode="var_type">
    <xsl:text>WSTRING</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/*" mode="var_type">
    <xsl:value-of select="local-name()"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:derived" mode="var_edit">
    <ns:is_edited/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:array" mode="var_edit">
    <xsl:apply-templates select="ppx:baseType" mode="var_edit"/>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/*" mode="var_edit">
    <xsl:text>False</xsl:text>
  </xsl:template>
    <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:derived" mode="var_debug">
    <ns:is_debugged/>
  </xsl:template>
  <xsl:template match="ppx:pou" mode="var_debug">
    <xsl:text>True</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:array" mode="var_debug">
    <xsl:text>False</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/ppx:struct" mode="var_debug">
    <xsl:text>False</xsl:text>
  </xsl:template>
  <xsl:template match="*[self::ppx:type or self::ppx:baseType]/*" mode="var_debug">
    <xsl:text>True</xsl:text>
  </xsl:template>
  <xsl:template match="text()"/>
  <xsl:template match="text()" mode="var_class"/>
  <xsl:template match="text()" mode="var_type"/>
  <xsl:template match="text()" mode="var_edit"/>
  <xsl:template match="text()" mode="var_debug"/>
</xsl:stylesheet>