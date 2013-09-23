<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:ns="entries_list_ns"
    extension-element-prefixes="ns"
    exclude-result-prefixes="ns">
  <xsl:param name="min_index"/>
  <xsl:param name="max_index"/>
  <xsl:template match="Device">
    <xsl:apply-templates select="Profile/Dictionary/Objects/Object"/>
    <xsl:for-each select="RxPdo">
      <xsl:call-template name="pdo_entries">
        <xsl:with-param name="direction" select="'Receive'"/>
      </xsl:call-template>
    </xsl:for-each>
    <xsl:for-each select="TxPdo">
      <xsl:call-template name="pdo_entries">
        <xsl:with-param name="direction" select="'Transmit'"/>
      </xsl:call-template>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="Object">
    <xsl:variable name="index">
      <xsl:value-of select="ns:HexDecValue(Index/text())"/>
    </xsl:variable>
    <xsl:variable name="entry_name">
      <xsl:value-of select="ns:EntryName(Name)"/>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="$index &gt;= $min_index and $index &lt;= $max_index">
        <xsl:variable name="datatype_name">
          <xsl:value-of select="Type/text()"/>
        </xsl:variable>
        <xsl:choose>
          <xsl:when test="ancestor::Dictionary/child::DataTypes/DataType[Name/text()=$datatype_name][SubItem]">
            <xsl:apply-templates select="ancestor::Dictionary/child::DataTypes/DataType[Name/text()=$datatype_name][SubItem]">
              <xsl:with-param name="index">
                <xsl:value-of select="$index"/>
              </xsl:with-param>
              <xsl:with-param name="entry_name">
                <xsl:value-of select="$entry_name"/>
              </xsl:with-param>
            </xsl:apply-templates>
          </xsl:when>
          <xsl:otherwise>
            <ns:add_entry>
              <Index><xsl:value-of select="$index"/></Index>
              <SubIndex><xsl:text>0</xsl:text></SubIndex>
              <Name><xsl:value-of select="$entry_name"/></Name>
              <Type><xsl:value-of select="$datatype_name"/></Type>
              <BitSize><xsl:value-of select="BitSize/text()"/></BitSize>
              <Access><xsl:value-of select="Flags/Access/text()"/></Access>
              <PDOMapping><xsl:value-of select="Flags/PdoMapping/text()"/></PDOMapping>
            </ns:add_entry>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:when>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="DataType">
    <xsl:param name="index"/>
    <xsl:param name="entry_name"/>
    <xsl:for-each select="SubItem">
      <xsl:variable name="subentry_names">
        <xsl:value-of select="DisplayName"/>
        <Default><xsl:value-of select="Name/text()"/></Default>
      </xsl:variable>
      <ns:add_entry>
        <Index><xsl:value-of select="$index"/></Index>
        <SubIndex><xsl:value-of select="ns:HexDecValue(SubIdx/text())"/></SubIndex>
        <Name>
          <xsl:value-of select="$entry_name"/>
          <xsl:text> - </xsl:text>
          <xsl:value-of select="ns:EntryName($subentry_names)"/>
        </Name>
        <Type><xsl:value-of select="Type/text()"/></Type>
        <BitSize><xsl:value-of select="BitSize/text()"/></BitSize>
        <Access><xsl:value-of select="Flags/Access/text()"/></Access>
        <PDOMapping><xsl:value-of select="Flags/PdoMapping/text()"/></PDOMapping>
      </ns:add_entry>
    </xsl:for-each>
  </xsl:template>
  <xsl:template name="pdo_entries">
    <xsl:param name="direction"/>
    <xsl:variable name="pdo_index">
      <xsl:value-of select="ns:HexDecValue(Index/text())"/>
    </xsl:variable>
    <xsl:variable name="pdo_name">
      <xsl:value-of select="ns:EntryName(Name)"/>
    </xsl:variable>
    <xsl:for-each select="Entry">
	  <xsl:variable name="index">
	    <xsl:value-of select="ns:HexDecValue(Index/text())"/>
	  </xsl:variable>
	  <xsl:choose>
	    <xsl:when test="$index &gt;= $min_index and $index &lt;= $max_index">
	      <ns:add_entry>
            <Index><xsl:value-of select="$index"/></Index>
            <SubIndex><xsl:value-of select="ns:HexDecValue(SubIndex/text())"/></SubIndex>
            <Name><xsl:value-of select="ns:EntryName(Name)"/></Name>
            <Type><xsl:value-of select="Type/text()"/></Type>
            <BitSize><xsl:value-of select="BitLen/text()"/></BitSize>
            <xsl:choose>
              <xsl:when test="$direction='Transmit'">
                <Access><xsl:text>ro</xsl:text></Access>
                <PDOMapping><xsl:text>T</xsl:text></PDOMapping>
              </xsl:when>
              <xsl:otherwise>
                <Access><xsl:text>wo</xsl:text></Access>
                <PDOMapping><xsl:text>R</xsl:text></PDOMapping>
              </xsl:otherwise>
            </xsl:choose>
            <PDO>
              <index><xsl:value-of select="$pdo_index"/></index>
              <name><xsl:value-of select="$pdo_name"/></name>
              <type><xsl:value-of select="$direction"/></type>
            </PDO>
          </ns:add_entry>
	    </xsl:when>
	  </xsl:choose>
    </xsl:for-each>
  </xsl:template>
  <xsl:template match="text()"/>
</xsl:stylesheet>