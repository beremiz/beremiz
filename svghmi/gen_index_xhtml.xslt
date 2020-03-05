<?xml version="1.0"?>
<xsl:stylesheet xmlns:func="http://exslt.org/functions" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd" xmlns:svg="http://www.w3.org/2000/svg" xmlns:str="http://exslt.org/strings" xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:exsl="http://exslt.org/common" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:ns="beremiz" xmlns:cc="http://creativecommons.org/ns#" xmlns:regexp="http://exslt.org/regular-expressions" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:dc="http://purl.org/dc/elements/1.1/" extension-element-prefixes="ns func exsl regexp str dyn" version="1.0" exclude-result-prefixes="ns str regexp exsl func dyn">
  <xsl:output method="xml" cdata-section-elements="xhtml:script"/>
  <xsl:variable name="geometry" select="ns:GetSVGGeometry()"/>
  <xsl:variable name="hmitree" select="ns:GetHMITree()"/>
  <xsl:variable name="svg_root_id" select="/svg:svg/@id"/>
  <xsl:variable name="hmi_elements" select="//svg:*[starts-with(@inkscape:label, 'HMI:')]"/>
  <xsl:variable name="hmi_geometry" select="$geometry[@Id = $hmi_elements/@id]"/>
  <xsl:variable name="hmi_pages" select="$hmi_elements[func:parselabel(@inkscape:label)/widget/@type = 'Page']"/>
  <xsl:variable name="default_page">
    <xsl:choose>
      <xsl:when test="count($hmi_pages) &gt; 1">
        <xsl:variable name="Home_page" select="$hmi_pages[func:parselabel(@inkscape:label)/widget/arg[1]/@value = 'Home']"/>
        <xsl:choose>
          <xsl:when test="$Home_page">
            <xsl:text>Home</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:message terminate="yes">No Home page defined!</xsl:message>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:when>
      <xsl:when test="count($hmi_pages) = 0">
        <xsl:message terminate="yes">No page defined!</xsl:message>
      </xsl:when>
      <xsl:otherwise>
        <xsl:value-of select="func:parselabel($hmi_pages/@inkscape:label)/widget/arg[1]/@value"/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:variable>
  <xsl:variable name="_categories">
    <noindex>
      <xsl:text>HMI_ROOT</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_NODE</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_PLC_STATUS</xsl:text>
    </noindex>
    <noindex>
      <xsl:text>HMI_CURRENT_PAGE</xsl:text>
    </noindex>
  </xsl:variable>
  <xsl:variable name="categories" select="exsl:node-set($_categories)"/>
  <xsl:variable name="_indexed_hmitree">
    <xsl:apply-templates mode="index" select="$hmitree"/>
  </xsl:variable>
  <xsl:variable name="indexed_hmitree" select="exsl:node-set($_indexed_hmitree)"/>
  <func:function name="func:refered_elements">
    <xsl:param name="elems"/>
    <xsl:variable name="descend" select="$elems/descendant-or-self::svg:*"/>
    <xsl:variable name="clones" select="$descend[self::svg:use]"/>
    <xsl:variable name="originals" select="//svg:*[concat('#',@id) = $clones/@xlink:href]"/>
    <xsl:choose>
      <xsl:when test="$originals">
        <func:result select="$descend | func:refered_elements($originals)"/>
      </xsl:when>
      <xsl:otherwise>
        <func:result select="$descend"/>
      </xsl:otherwise>
    </xsl:choose>
  </func:function>
  <func:function name="func:intersect_1d">
    <xsl:param name="a0"/>
    <xsl:param name="a1"/>
    <xsl:param name="b0"/>
    <xsl:param name="b1"/>
    <xsl:variable name="d0" select="$a0 &gt;= $b0"/>
    <xsl:variable name="d1" select="$a1 &gt;= $b1"/>
    <xsl:choose>
      <xsl:when test="not($d0) and $d1">
        <func:result select="3"/>
      </xsl:when>
      <xsl:when test="$d0 and not($d1)">
        <func:result select="2"/>
      </xsl:when>
      <xsl:when test="$d0 and $d1 and $a0 &lt; $b1">
        <func:result select="1"/>
      </xsl:when>
      <xsl:when test="not($d0) and not($d1) and $b0 &lt; $a1">
        <func:result select="1"/>
      </xsl:when>
      <xsl:otherwise>
        <func:result select="0"/>
      </xsl:otherwise>
    </xsl:choose>
  </func:function>
  <func:function name="func:intersect">
    <xsl:param name="a"/>
    <xsl:param name="b"/>
    <xsl:variable name="x_intersect" select="func:intersect_1d($a/@x, $a/@x+$a/@w, $b/@x, $b/@x+$b/@w)"/>
    <xsl:choose>
      <xsl:when test="$x_intersect != 0">
        <xsl:variable name="y_intersect" select="func:intersect_1d($a/@y, $a/@y+$a/@h, $b/@y, $b/@y+$b/@h)"/>
        <func:result select="$x_intersect * $y_intersect"/>
      </xsl:when>
      <xsl:otherwise>
        <func:result select="0"/>
      </xsl:otherwise>
    </xsl:choose>
  </func:function>
  <func:function name="func:overlapping_geometry">
    <xsl:param name="elt"/>
    <xsl:variable name="groups" select="/svg:svg | //svg:g"/>
    <xsl:variable name="g" select="$geometry[@Id = $elt/@id]"/>
    <xsl:variable name="candidates" select="$geometry[@Id != $elt/@id]"/>
    <func:result select="$candidates[(@Id = $groups/@id and (func:intersect($g, .) = 9)) or &#10;                              (not(@Id = $groups/@id) and (func:intersect($g, .) &gt; 0 ))]"/>
  </func:function>
  <func:function name="func:all_related_elements">
    <xsl:param name="page"/>
    <xsl:variable name="page_overlapping_geometry" select="func:overlapping_geometry($page)"/>
    <xsl:variable name="page_overlapping_elements" select="//svg:*[@id = $page_overlapping_geometry/@Id]"/>
    <xsl:variable name="page_sub_elements" select="func:refered_elements($page | $page_overlapping_elements)"/>
    <func:result select="$page_sub_elements"/>
  </func:function>
  <func:function name="func:required_elements">
    <xsl:param name="pages"/>
    <xsl:choose>
      <xsl:when test="$pages">
        <func:result select="func:all_related_elements($pages[1])&#10;                          | func:required_elements($pages[position()!=1])"/>
      </xsl:when>
      <xsl:otherwise>
        <func:result select="/.."/>
      </xsl:otherwise>
    </xsl:choose>
  </func:function>
  <xsl:variable name="required_elements" select="//svg:defs/descendant-or-self::svg:*&#10;           | func:required_elements($hmi_pages)/ancestor-or-self::svg:*"/>
  <xsl:variable name="discardable_elements" select="//svg:*[not(@id = $required_elements/@id)]"/>
  <func:function name="func:sumarized_elements">
    <xsl:param name="elements"/>
    <xsl:variable name="short_list" select="$elements[not(ancestor::*/@id = $elements/@id)]"/>
    <xsl:variable name="filled_groups" select="$short_list/parent::svg:*[&#10;            not(descendant::*[&#10;                not(self::svg:g) and&#10;                not(@id = $discardable_elements/@id) and&#10;                not(@id = $short_list/descendant-or-self::*[not(self::svg:g)]/@id)&#10;            ])]"/>
    <xsl:variable name="groups_to_add" select="$filled_groups[not(ancestor::*/@id = $filled_groups/@id)]"/>
    <func:result select="$groups_to_add | $short_list[not(ancestor::svg:g/@id = $filled_groups/@id)]"/>
  </func:function>
  <func:function name="func:detachable_elements">
    <xsl:param name="pages"/>
    <xsl:choose>
      <xsl:when test="$pages">
        <func:result select="func:sumarized_elements(func:all_related_elements($pages[1]))&#10;                          | func:detachable_elements($pages[position()!=1])"/>
      </xsl:when>
      <xsl:otherwise>
        <func:result select="/.."/>
      </xsl:otherwise>
    </xsl:choose>
  </func:function>
  <xsl:variable name="detachable_elements" select="func:detachable_elements($hmi_pages)"/>
  <xsl:template mode="index" match="*">
    <xsl:param name="index" select="0"/>
    <xsl:param name="parentpath" select="''"/>
    <xsl:variable name="content">
      <xsl:variable name="path">
        <xsl:choose>
          <xsl:when test="local-name() = 'HMI_ROOT'">
            <xsl:value-of select="$parentpath"/>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="$parentpath"/>
            <xsl:text>/</xsl:text>
            <xsl:value-of select="@name"/>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:variable>
      <xsl:choose>
        <xsl:when test="not(local-name() = $categories/noindex)">
          <xsl:copy>
            <xsl:attribute name="index">
              <xsl:value-of select="$index"/>
            </xsl:attribute>
            <xsl:attribute name="hmipath">
              <xsl:value-of select="$path"/>
            </xsl:attribute>
            <xsl:for-each select="@*">
              <xsl:copy/>
            </xsl:for-each>
          </xsl:copy>
        </xsl:when>
        <xsl:otherwise>
          <xsl:apply-templates mode="index" select="*[1]">
            <xsl:with-param name="index" select="$index"/>
            <xsl:with-param name="parentpath">
              <xsl:value-of select="$path"/>
            </xsl:with-param>
          </xsl:apply-templates>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:copy-of select="$content"/>
    <xsl:apply-templates mode="index" select="following-sibling::*[1]">
      <xsl:with-param name="index" select="$index + count(exsl:node-set($content)/*)"/>
      <xsl:with-param name="parentpath">
        <xsl:value-of select="$parentpath"/>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template mode="inline_svg" match="@* | node()">
    <xsl:if test="not(@id = $discardable_elements/@id)">
      <xsl:copy>
        <xsl:apply-templates mode="inline_svg" select="@* | node()"/>
      </xsl:copy>
    </xsl:if>
  </xsl:template>
  <xsl:template mode="inline_svg" match="svg:svg/@width"/>
  <xsl:template mode="inline_svg" match="svg:svg/@height"/>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="inline_svg" match="svg:svg">
    <svg>
      <xsl:attribute name="preserveAspectRatio">
        <xsl:text>none</xsl:text>
      </xsl:attribute>
      <xsl:attribute name="height">
        <xsl:text>100vh</xsl:text>
      </xsl:attribute>
      <xsl:attribute name="width">
        <xsl:text>100vw</xsl:text>
      </xsl:attribute>
      <xsl:apply-templates mode="inline_svg" select="@* | node()"/>
    </svg>
  </xsl:template>
  <xsl:template mode="inline_svg" match="svg:svg[@viewBox!=concat('0 0 ', @width, ' ', @height)]">
    <xsl:message terminate="yes">
      <xsl:text>ViewBox settings other than X=0, Y=0 and Scale=1 are not supported</xsl:text>
    </xsl:message>
  </xsl:template>
  <xsl:template mode="inline_svg" match="sodipodi:namedview[@units!='px' or @inkscape:document-units!='px']">
    <xsl:message terminate="yes">
      <xsl:text>All units must be set to "px" in Inkscape's document properties</xsl:text>
    </xsl:message>
  </xsl:template>
  <xsl:variable name="to_unlink" select="$hmi_elements[not(@id = $hmi_pages)]//svg:use"/>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="inline_svg" match="svg:use">
    <xsl:choose>
      <xsl:when test="@id = $to_unlink/@id">
        <xsl:call-template name="unlink_clone"/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:copy>
          <xsl:apply-templates mode="inline_svg" select="@* | node()"/>
        </xsl:copy>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:variable name="_excluded_use_attrs">
    <name>
      <xsl:text>href</xsl:text>
    </name>
    <name>
      <xsl:text>width</xsl:text>
    </name>
    <name>
      <xsl:text>height</xsl:text>
    </name>
    <name>
      <xsl:text>x</xsl:text>
    </name>
    <name>
      <xsl:text>y</xsl:text>
    </name>
  </xsl:variable>
  <xsl:variable name="excluded_use_attrs" select="exsl:node-set($_excluded_use_attrs)"/>
  <xsl:template xmlns="http://www.w3.org/2000/svg" name="unlink_clone">
    <g>
      <xsl:for-each select="@*[not(local-name() = $excluded_use_attrs/name)]">
        <xsl:attribute name="{name()}">
          <xsl:value-of select="."/>
        </xsl:attribute>
      </xsl:for-each>
      <xsl:variable name="targetid" select="substring-after(@xlink:href,'#')"/>
      <xsl:apply-templates mode="unlink_clone" select="//svg:*[@id = $targetid]">
        <xsl:with-param name="seed" select="@id"/>
      </xsl:apply-templates>
    </g>
  </xsl:template>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="unlink_clone" match="@id">
    <xsl:param name="seed"/>
    <xsl:attribute name="id">
      <xsl:value-of select="$seed"/>
      <xsl:text>_</xsl:text>
      <xsl:value-of select="."/>
    </xsl:attribute>
  </xsl:template>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="unlink_clone" match="@*">
    <xsl:copy/>
  </xsl:template>
  <xsl:template xmlns="http://www.w3.org/2000/svg" mode="unlink_clone" match="svg:*">
    <xsl:param name="seed"/>
    <xsl:choose>
      <xsl:when test="@id = $hmi_elements/@id">
        <use>
          <xsl:attribute name="xlink:href">
            <xsl:value-of select="concat('#',@id)"/>
          </xsl:attribute>
        </use>
      </xsl:when>
      <xsl:otherwise>
        <xsl:copy>
          <xsl:apply-templates mode="unlink_clone" select="@* | node()">
            <xsl:with-param name="seed" select="$seed"/>
          </xsl:apply-templates>
        </xsl:copy>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:variable name="result_svg">
    <xsl:apply-templates mode="inline_svg" select="/"/>
  </xsl:variable>
  <xsl:variable name="result_svg_ns" select="exsl:node-set($result_svg)"/>
  <xsl:template match="/">
    <xsl:comment>
      <xsl:text>Made with SVGHMI. https://beremiz.org</xsl:text>
    </xsl:comment>
    <xsl:comment>
      <xsl:apply-templates mode="testgeo" select="$hmi_geometry"/>
    </xsl:comment>
    <xsl:comment>
      <xsl:apply-templates mode="testtree" select="$hmitree"/>
    </xsl:comment>
    <xsl:comment>
      <xsl:apply-templates mode="testtree" select="$indexed_hmitree"/>
    </xsl:comment>
    <xsl:comment>
      <xsl:text>Detachable :
</xsl:text>
      <xsl:for-each select="$detachable_elements">
        <xsl:value-of select="@id"/>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
    </xsl:comment>
    <xsl:comment>
      <xsl:text>Discardable :
</xsl:text>
      <xsl:for-each select="$discardable_elements">
        <xsl:value-of select="@id"/>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
    </xsl:comment>
    <xsl:comment>
      <xsl:text>Unlinked :
</xsl:text>
      <xsl:for-each select="$to_unlink">
        <xsl:value-of select="@id"/>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
    </xsl:comment>
    <html xmlns:svg="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.w3.org/1999/xhtml">
      <head/>
      <body style="margin:0;overflow:hidden;">
        <xsl:copy-of select="$result_svg"/>
        <script>
          <xsl:call-template name="scripts"/>
        </script>
      </body>
    </html>
  </xsl:template>
  <func:function name="func:parselabel">
    <xsl:param name="label"/>
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
    <xsl:variable name="ast">
      <xsl:if test="$type">
        <widget>
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
            <path>
              <xsl:attribute name="value">
                <xsl:value-of select="."/>
              </xsl:attribute>
            </path>
          </xsl:for-each>
        </widget>
      </xsl:if>
    </xsl:variable>
    <func:result select="exsl:node-set($ast)"/>
  </func:function>
  <xsl:template name="scripts">
    <xsl:text>//(function(){
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>id = idstr =&gt; document.getElementById(idstr);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var hmi_hash = [</xsl:text>
    <xsl:value-of select="$hmitree/@hash"/>
    <xsl:text>]; 
</xsl:text>
    <xsl:text>var hmi_widgets = {
</xsl:text>
    <xsl:for-each select="$hmi_elements">
      <xsl:variable name="widget" select="func:parselabel(@inkscape:label)/widget"/>
      <xsl:variable name="eltid" select="@id"/>
      <xsl:text>  "</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>": {
</xsl:text>
      <xsl:text>    type: "</xsl:text>
      <xsl:value-of select="$widget/@type"/>
      <xsl:text>",
</xsl:text>
      <xsl:text>    args: [
</xsl:text>
      <xsl:for-each select="$widget/arg">
        <xsl:text>        "</xsl:text>
        <xsl:value-of select="@value"/>
        <xsl:text>"</xsl:text>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>    ],
</xsl:text>
      <xsl:text>    indexes: [
</xsl:text>
      <xsl:for-each select="$widget/path">
        <xsl:variable name="hmipath" select="@value"/>
        <xsl:variable name="hmitree_match" select="$indexed_hmitree/*[@hmipath = $hmipath]"/>
        <xsl:choose>
          <xsl:when test="count($hmitree_match) = 0">
            <xsl:message terminate="no">
              <xsl:text>Widget </xsl:text>
              <xsl:value-of select="$widget/@type"/>
              <xsl:text> id="</xsl:text>
              <xsl:value-of select="$eltid"/>
              <xsl:text>" : No match for path "</xsl:text>
              <xsl:value-of select="$hmipath"/>
              <xsl:text>" in HMI tree</xsl:text>
            </xsl:message>
          </xsl:when>
          <xsl:otherwise>
            <xsl:text>            </xsl:text>
            <xsl:value-of select="$hmitree_match/@index"/>
            <xsl:if test="position()!=last()">
              <xsl:text>,</xsl:text>
            </xsl:if>
            <xsl:text>
</xsl:text>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:for-each>
      <xsl:text>    ],
</xsl:text>
      <xsl:text>    element: id("</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>"),
</xsl:text>
      <xsl:apply-templates mode="widget_defs" select="$widget">
        <xsl:with-param name="hmi_element" select="."/>
      </xsl:apply-templates>
      <xsl:text>  }</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var heartbeat_index = </xsl:text>
    <xsl:value-of select="$indexed_hmitree/*[@hmipath = '/HEARTBEAT']/@index"/>
    <xsl:text>;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var hmitree_types = [
</xsl:text>
    <xsl:for-each select="$indexed_hmitree/*">
      <xsl:text>    /* </xsl:text>
      <xsl:value-of select="@index"/>
      <xsl:text>  </xsl:text>
      <xsl:value-of select="@hmipath"/>
      <xsl:text> */ "</xsl:text>
      <xsl:value-of select="substring(local-name(), 5)"/>
      <xsl:text>"</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>]
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var detachable_elements = {
</xsl:text>
    <xsl:for-each select="$detachable_elements">
      <xsl:text>    "</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>":[id("</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>"), id("</xsl:text>
      <xsl:value-of select="../@id"/>
      <xsl:text>")]</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var page_desc = {
</xsl:text>
    <xsl:for-each select="$hmi_pages">
      <xsl:variable name="desc" select="func:parselabel(@inkscape:label)/widget"/>
      <xsl:variable name="page" select="."/>
      <xsl:variable name="p" select="$geometry[@Id = $page/@id]"/>
      <xsl:variable name="page_all_elements" select="func:all_related_elements($page)"/>
      <xsl:variable name="all_page_ids" select="$page_all_elements[@id = $hmi_elements/@id and @id != $page/@id]/@id"/>
      <xsl:variable name="required_detachables" select="func:sumarized_elements($page_all_elements)"/>
      <xsl:text>  "</xsl:text>
      <xsl:value-of select="$desc/arg[1]/@value"/>
      <xsl:text>": {
</xsl:text>
      <xsl:text>    widget: hmi_widgets["</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>"],
</xsl:text>
      <xsl:text>    bbox: [</xsl:text>
      <xsl:value-of select="$p/@x"/>
      <xsl:text>, </xsl:text>
      <xsl:value-of select="$p/@y"/>
      <xsl:text>, </xsl:text>
      <xsl:value-of select="$p/@w"/>
      <xsl:text>, </xsl:text>
      <xsl:value-of select="$p/@h"/>
      <xsl:text>],
</xsl:text>
      <xsl:text>    widgets: [
</xsl:text>
      <xsl:for-each select="$all_page_ids">
        <xsl:text>        hmi_widgets["</xsl:text>
        <xsl:value-of select="."/>
        <xsl:text>"]</xsl:text>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>    ],
</xsl:text>
      <xsl:text>    required_detachables: {
</xsl:text>
      <xsl:for-each select="$required_detachables">
        <xsl:text>        "</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>": detachable_elements["</xsl:text>
        <xsl:value-of select="@id"/>
        <xsl:text>"]</xsl:text>
        <xsl:if test="position()!=last()">
          <xsl:text>,</xsl:text>
        </xsl:if>
        <xsl:text>
</xsl:text>
      </xsl:for-each>
      <xsl:text>    }
</xsl:text>
      <xsl:text>  }</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var default_page = "</xsl:text>
    <xsl:value-of select="$default_page"/>
    <xsl:text>";
</xsl:text>
    <xsl:text>var svg_root = id("</xsl:text>
    <xsl:value-of select="$svg_root_id"/>
    <xsl:text>");
</xsl:text>
    <xsl:text>// svghmi.js
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var cache = hmitree_types.map(_ignored =&gt; undefined);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function dispatch_value_to_widget(widget, index, value, oldval) {
</xsl:text>
    <xsl:text>    try {
</xsl:text>
    <xsl:text>        let idxidx = widget.indexes.indexOf(index);
</xsl:text>
    <xsl:text>        let d = widget.dispatch;
</xsl:text>
    <xsl:text>        if(typeof(d) == "function" &amp;&amp; idxidx == 0){
</xsl:text>
    <xsl:text>            d.call(widget, value, oldval);
</xsl:text>
    <xsl:text>        }else if(typeof(d) == "object" &amp;&amp; d.length &gt;= idxidx){
</xsl:text>
    <xsl:text>            d[idxidx].call(widget, value, oldval);
</xsl:text>
    <xsl:text>        }/* else dispatch_0, ..., dispatch_n ? */
</xsl:text>
    <xsl:text>        /*else {
</xsl:text>
    <xsl:text>            throw new Error("Dunno how to dispatch to widget at index = " + index);
</xsl:text>
    <xsl:text>        }*/
</xsl:text>
    <xsl:text>    } catch(err) {
</xsl:text>
    <xsl:text>        console.log(err);
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function dispatch_value(index, value) {
</xsl:text>
    <xsl:text>    let widgets = subscribers[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    let oldval = cache[index];
</xsl:text>
    <xsl:text>    cache[index] = value;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    if(widgets.size &gt; 0) {
</xsl:text>
    <xsl:text>        for(let widget of widgets){
</xsl:text>
    <xsl:text>            dispatch_value_to_widget(widget, index, value, oldval);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function init_widgets() {
</xsl:text>
    <xsl:text>    Object.keys(hmi_widgets).forEach(function(id) {
</xsl:text>
    <xsl:text>        let widget = hmi_widgets[id];
</xsl:text>
    <xsl:text>        let init = widget.init;
</xsl:text>
    <xsl:text>        if(typeof(init) == "function"){
</xsl:text>
    <xsl:text>            try {
</xsl:text>
    <xsl:text>                init.call(widget);
</xsl:text>
    <xsl:text>            } catch(err) {
</xsl:text>
    <xsl:text>                console.log(err);
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    });
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// Open WebSocket to relative "/ws" address
</xsl:text>
    <xsl:text>var ws = new WebSocket(window.location.href.replace(/^http(s?:\/\/[^\/]*)\/.*$/, 'ws$1/ws'));
</xsl:text>
    <xsl:text>ws.binaryType = 'arraybuffer';
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>const dvgetters = {
</xsl:text>
    <xsl:text>    INT: (dv,offset) =&gt; [dv.getInt16(offset, true), 2],
</xsl:text>
    <xsl:text>    BOOL: (dv,offset) =&gt; [dv.getInt8(offset, true), 1],
</xsl:text>
    <xsl:text>    STRING: (dv, offset) =&gt; {
</xsl:text>
    <xsl:text>        size = dv.getInt8(offset);
</xsl:text>
    <xsl:text>        return [
</xsl:text>
    <xsl:text>            String.fromCharCode.apply(null, new Uint8Array(
</xsl:text>
    <xsl:text>                dv.buffer, /* original buffer */
</xsl:text>
    <xsl:text>                offset + 1, /* string starts after size*/
</xsl:text>
    <xsl:text>                size /* size of string */
</xsl:text>
    <xsl:text>            )), size + 1]; /* total increment */
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// Register message reception handler
</xsl:text>
    <xsl:text>ws.onmessage = function (evt) {
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    let data = evt.data;
</xsl:text>
    <xsl:text>    let dv = new DataView(data);
</xsl:text>
    <xsl:text>    let i = 0;
</xsl:text>
    <xsl:text>    try {
</xsl:text>
    <xsl:text>        for(let hash_int of hmi_hash) {
</xsl:text>
    <xsl:text>            if(hash_int != dv.getUint8(i)){
</xsl:text>
    <xsl:text>                throw new Error("Hash doesn't match");
</xsl:text>
    <xsl:text>            };
</xsl:text>
    <xsl:text>            i++;
</xsl:text>
    <xsl:text>        };
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        while(i &lt; data.byteLength){
</xsl:text>
    <xsl:text>            let index = dv.getUint32(i, true);
</xsl:text>
    <xsl:text>            i += 4;
</xsl:text>
    <xsl:text>            let iectype = hmitree_types[index];
</xsl:text>
    <xsl:text>            if(iectype != undefined){
</xsl:text>
    <xsl:text>                let dvgetter = dvgetters[iectype];
</xsl:text>
    <xsl:text>                let [value, bytesize] = dvgetter(dv,i);
</xsl:text>
    <xsl:text>                dispatch_value(index, value);
</xsl:text>
    <xsl:text>                i += bytesize;
</xsl:text>
    <xsl:text>            } else {
</xsl:text>
    <xsl:text>                throw new Error("Unknown index "+index)
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        };
</xsl:text>
    <xsl:text>    } catch(err) {
</xsl:text>
    <xsl:text>        // 1003 is for "Unsupported Data"
</xsl:text>
    <xsl:text>        // ws.close(1003, err.message);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // TODO : remove debug alert ?
</xsl:text>
    <xsl:text>        alert("Error : "+err.message+"\nHMI will be reloaded.");
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // force reload ignoring cache
</xsl:text>
    <xsl:text>        location.reload(true);
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function send_blob(data) {
</xsl:text>
    <xsl:text>    if(data.length &gt; 0) {
</xsl:text>
    <xsl:text>        ws.send(new Blob([new Uint8Array(hmi_hash)].concat(data)));
</xsl:text>
    <xsl:text>    };
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>const typedarray_types = {
</xsl:text>
    <xsl:text>    INT: (number) =&gt; new Int16Array([number]),
</xsl:text>
    <xsl:text>    BOOL: (truth) =&gt; new Int16Array([truth]),
</xsl:text>
    <xsl:text>    STRING: (str) =&gt; {
</xsl:text>
    <xsl:text>        // beremiz default string max size is 128
</xsl:text>
    <xsl:text>        str = str.slice(0,128);
</xsl:text>
    <xsl:text>        binary = new Uint8Array(str.length + 1);
</xsl:text>
    <xsl:text>        binary[0] = str.length;
</xsl:text>
    <xsl:text>        for(var i = 0; i &lt; str.length; i++){
</xsl:text>
    <xsl:text>            binary[i+1] = str.charCodeAt(i);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>        return binary;
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>    /* TODO */
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function send_reset() {
</xsl:text>
    <xsl:text>    send_blob(new Uint8Array([1])); /* reset = 1 */
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// subscription state, as it should be in hmi server
</xsl:text>
    <xsl:text>// hmitree indexed array of integers
</xsl:text>
    <xsl:text>var subscriptions =  hmitree_types.map(_ignored =&gt; 0);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// subscription state as needed by widget now
</xsl:text>
    <xsl:text>// hmitree indexed array of Sets of widgets objects
</xsl:text>
    <xsl:text>var subscribers = hmitree_types.map(_ignored =&gt; new Set());
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// artificially subscribe the watchdog widget to "/heartbeat" hmi variable
</xsl:text>
    <xsl:text>// Since dispatch directly calls change_hmi_value,
</xsl:text>
    <xsl:text>// PLC will periodically send variable at given frequency
</xsl:text>
    <xsl:text>subscribers[heartbeat_index].add({
</xsl:text>
    <xsl:text>    /* type: "Watchdog", */
</xsl:text>
    <xsl:text>    frequency: 1,
</xsl:text>
    <xsl:text>    indexes: [heartbeat_index],
</xsl:text>
    <xsl:text>    dispatch: function(value) {
</xsl:text>
    <xsl:text>        // console.log("Heartbeat" + value);
</xsl:text>
    <xsl:text>        change_hmi_value(heartbeat_index, "+1");
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>});
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function update_subscriptions() {
</xsl:text>
    <xsl:text>    let delta = [];
</xsl:text>
    <xsl:text>    for(let index = 0; index &lt; subscribers.length; index++){
</xsl:text>
    <xsl:text>        let widgets = subscribers[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // periods are in ms
</xsl:text>
    <xsl:text>        let previous_period = subscriptions[index];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        // subscribing with a zero period is unsubscribing
</xsl:text>
    <xsl:text>        let new_period = 0;
</xsl:text>
    <xsl:text>        if(widgets.size &gt; 0) {
</xsl:text>
    <xsl:text>            let maxfreq = 0;
</xsl:text>
    <xsl:text>            for(let widget of widgets)
</xsl:text>
    <xsl:text>                if(maxfreq &lt; widget.frequency)
</xsl:text>
    <xsl:text>                    maxfreq = widget.frequency;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>            if(maxfreq != 0)
</xsl:text>
    <xsl:text>                new_period = 1000/maxfreq;
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>        if(previous_period != new_period) {
</xsl:text>
    <xsl:text>            subscriptions[index] = new_period;
</xsl:text>
    <xsl:text>            delta.push(
</xsl:text>
    <xsl:text>                new Uint8Array([2]), /* subscribe = 2 */
</xsl:text>
    <xsl:text>                new Uint32Array([index]),
</xsl:text>
    <xsl:text>                new Uint16Array([new_period]));
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>    send_blob(delta);
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function send_hmi_value(index, value) {
</xsl:text>
    <xsl:text>    let iectype = hmitree_types[index];
</xsl:text>
    <xsl:text>    let tobinary = typedarray_types[iectype];
</xsl:text>
    <xsl:text>    send_blob([
</xsl:text>
    <xsl:text>        new Uint8Array([0]),  /* setval = 0 */
</xsl:text>
    <xsl:text>        new Uint32Array([index]),
</xsl:text>
    <xsl:text>        tobinary(value)]);
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    cache[index] = value;
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function change_hmi_value(index, opstr) {
</xsl:text>
    <xsl:text>    let op = opstr[0];
</xsl:text>
    <xsl:text>    let given_val = opstr.slice(1);
</xsl:text>
    <xsl:text>    let old_val = cache[index]
</xsl:text>
    <xsl:text>    let new_val;
</xsl:text>
    <xsl:text>    switch(op){
</xsl:text>
    <xsl:text>      case "=":
</xsl:text>
    <xsl:text>        eval("new_val"+opstr);
</xsl:text>
    <xsl:text>        break;
</xsl:text>
    <xsl:text>      case "+":
</xsl:text>
    <xsl:text>      case "-":
</xsl:text>
    <xsl:text>      case "*":
</xsl:text>
    <xsl:text>      case "/":
</xsl:text>
    <xsl:text>        if(old_val != undefined)
</xsl:text>
    <xsl:text>            new_val = eval("old_val"+opstr);
</xsl:text>
    <xsl:text>        break;
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>    if(new_val != undefined &amp;&amp; old_val != new_val)
</xsl:text>
    <xsl:text>        send_hmi_value(index, new_val);
</xsl:text>
    <xsl:text>    return new_val;
</xsl:text>
    <xsl:text>}
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>var current_page;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function prepare_svg() {
</xsl:text>
    <xsl:text>    for(let eltid in detachable_elements){
</xsl:text>
    <xsl:text>        let [element,parent] = detachable_elements[eltid];
</xsl:text>
    <xsl:text>        parent.removeChild(element);
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>function switch_page(page_name) {
</xsl:text>
    <xsl:text>    let old_desc = page_desc[current_page];
</xsl:text>
    <xsl:text>    let new_desc = page_desc[page_name];
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    if(new_desc == undefined){
</xsl:text>
    <xsl:text>        /* TODO LOG ERROR */
</xsl:text>
    <xsl:text>        return;
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    if(old_desc){
</xsl:text>
    <xsl:text>        for(let widget of old_desc.widgets){
</xsl:text>
    <xsl:text>            /* remove subsribers */
</xsl:text>
    <xsl:text>            for(let index of widget.indexes){
</xsl:text>
    <xsl:text>                subscribers[index].delete(widget);
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>        for(let eltid in old_desc.required_detachables){
</xsl:text>
    <xsl:text>            if(!(eltid in new_desc.required_detachables)){
</xsl:text>
    <xsl:text>                let [element, parent] = old_desc.required_detachables[eltid];
</xsl:text>
    <xsl:text>                parent.removeChild(element);
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>        for(let eltid in new_desc.required_detachables){
</xsl:text>
    <xsl:text>            if(!(eltid in old_desc.required_detachables)){
</xsl:text>
    <xsl:text>                let [element, parent] = new_desc.required_detachables[eltid];
</xsl:text>
    <xsl:text>                parent.appendChild(element);
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }else{
</xsl:text>
    <xsl:text>        for(let eltid in new_desc.required_detachables){
</xsl:text>
    <xsl:text>            let [element, parent] = new_desc.required_detachables[eltid];
</xsl:text>
    <xsl:text>            parent.appendChild(element);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    for(let widget of new_desc.widgets){
</xsl:text>
    <xsl:text>        /* add widget's subsribers */
</xsl:text>
    <xsl:text>        for(let index of widget.indexes){
</xsl:text>
    <xsl:text>            subscribers[index].add(widget);
</xsl:text>
    <xsl:text>            /* dispatch current cache in newly opened page widgets */
</xsl:text>
    <xsl:text>            let cached_val = cache[index];
</xsl:text>
    <xsl:text>            if(cached_val != undefined)
</xsl:text>
    <xsl:text>                dispatch_value_to_widget(widget, index, cached_val, cached_val);
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    }
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    svg_root.setAttribute('viewBox',new_desc.bbox.join(" "));
</xsl:text>
    <xsl:text>    current_page = page_name;
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>    update_subscriptions();
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>// Once connection established
</xsl:text>
    <xsl:text>ws.onopen = function (evt) {
</xsl:text>
    <xsl:text>    init_widgets();
</xsl:text>
    <xsl:text>    send_reset();
</xsl:text>
    <xsl:text>    // show main page
</xsl:text>
    <xsl:text>    prepare_svg();
</xsl:text>
    <xsl:text>    switch_page(default_page);
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>ws.onclose = function (evt) {
</xsl:text>
    <xsl:text>    // TODO : add visible notification while waiting for reload
</xsl:text>
    <xsl:text>    console.log("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+" Reload in 10s.");
</xsl:text>
    <xsl:text>    // TODO : re-enable auto reload when not in debug
</xsl:text>
    <xsl:text>    //window.setTimeout(() =&gt; location.reload(true), 10000);
</xsl:text>
    <xsl:text>    alert("Connection closed. code:"+evt.code+" reason:"+evt.reason+" wasClean:"+evt.wasClean+".");
</xsl:text>
    <xsl:text>
</xsl:text>
    <xsl:text>};
</xsl:text>
    <xsl:text>//})();
</xsl:text>
  </xsl:template>
  <xsl:template mode="testgeo" match="bbox">
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
    <xsl:text>
</xsl:text>
  </xsl:template>
  <xsl:template mode="testtree" match="*">
    <xsl:param name="indent" select="''"/>
    <xsl:value-of select="$indent"/>
    <xsl:text> </xsl:text>
    <xsl:value-of select="local-name()"/>
    <xsl:for-each select="@*">
      <xsl:value-of select="local-name()"/>
      <xsl:text>=</xsl:text>
      <xsl:value-of select="."/>
    </xsl:for-each>
    <xsl:text>
</xsl:text>
    <xsl:apply-templates mode="testtree" select="*">
      <xsl:with-param name="indent">
        <xsl:value-of select="concat($indent,'&gt;')"/>
      </xsl:with-param>
    </xsl:apply-templates>
  </xsl:template>
  <xsl:template name="defs_by_labels">
    <xsl:param name="labels" select="''"/>
    <xsl:param name="mandatory" select="'yes'"/>
    <xsl:param name="hmi_element"/>
    <xsl:variable name="widget_type" select="@type"/>
    <xsl:for-each select="str:split($labels)">
      <xsl:variable name="name" select="."/>
      <xsl:variable name="elt_id" select="$result_svg_ns//*[@id = $hmi_element/@id]//*[@inkscape:label=$name][1]/@id"/>
      <xsl:choose>
        <xsl:when test="not($elt_id)">
          <xsl:if test="$mandatory='yes'">
            <xsl:message terminate="no">
              <xsl:value-of select="$widget_type"/>
              <xsl:text> widget must have a </xsl:text>
              <xsl:value-of select="$name"/>
              <xsl:text> element</xsl:text>
            </xsl:message>
          </xsl:if>
        </xsl:when>
        <xsl:otherwise>
          <xsl:text>    </xsl:text>
          <xsl:value-of select="$name"/>
          <xsl:text>_elt: id("</xsl:text>
          <xsl:value-of select="$elt_id"/>
          <xsl:text>"),
</xsl:text>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:for-each>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Display']">
    <xsl:param name="hmi_element"/>
    <xsl:text>    frequency: 5,
</xsl:text>
    <xsl:text>    dispatch: function(value) {
</xsl:text>
    <xsl:choose>
      <xsl:when test="$hmi_element[self::svg:text]">
        <xsl:text>      this.element.textContent = String(value);
</xsl:text>
      </xsl:when>
      <xsl:otherwise>
        <xsl:message terminate="no">
          <xsl:text>Display widget as a group not implemented</xsl:text>
        </xsl:message>
      </xsl:otherwise>
    </xsl:choose>
    <xsl:text>    },
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Meter']">
    <xsl:param name="hmi_element"/>
    <xsl:text>    frequency: 10,
</xsl:text>
    <xsl:call-template name="defs_by_labels">
      <xsl:with-param name="hmi_element" select="$hmi_element"/>
      <xsl:with-param name="labels">
        <xsl:text>needle range</xsl:text>
      </xsl:with-param>
    </xsl:call-template>
    <xsl:call-template name="defs_by_labels">
      <xsl:with-param name="hmi_element" select="$hmi_element"/>
      <xsl:with-param name="labels">
        <xsl:text>value min max</xsl:text>
      </xsl:with-param>
      <xsl:with-param name="mandatory" select="'no'"/>
    </xsl:call-template>
    <xsl:text>    dispatch: function(value) {
</xsl:text>
    <xsl:text>        if(this.value_elt)
</xsl:text>
    <xsl:text>            this.value_elt.textContent = String(value);
</xsl:text>
    <xsl:text>        let [min,max,totallength] = this.range;
</xsl:text>
    <xsl:text>        let length = Math.max(0,Math.min(totallength,(Number(value)-min)*totallength/(max-min)));
</xsl:text>
    <xsl:text>        let tip = this.range_elt.getPointAtLength(length);
</xsl:text>
    <xsl:text>        this.needle_elt.setAttribute('d', "M "+this.origin.x+","+this.origin.y+" "+tip.x+","+tip.y);
</xsl:text>
    <xsl:text>    },
</xsl:text>
    <xsl:text>    origin: undefined,
</xsl:text>
    <xsl:text>    range: undefined,
</xsl:text>
    <xsl:text>    init: function() {
</xsl:text>
    <xsl:text>        let min = this.min_elt ?
</xsl:text>
    <xsl:text>                    Number(this.min_elt.textContent) :
</xsl:text>
    <xsl:text>                    this.args.length &gt;= 1 ? this.args[0] : 0;
</xsl:text>
    <xsl:text>        let max = this.max_elt ?
</xsl:text>
    <xsl:text>                    Number(this.max_elt.textContent) :
</xsl:text>
    <xsl:text>                    this.args.length &gt;= 2 ? this.args[1] : 100;
</xsl:text>
    <xsl:text>        this.range = [min, max, this.range_elt.getTotalLength()]
</xsl:text>
    <xsl:text>        this.origin = this.needle_elt.getPointAtLength(0);
</xsl:text>
    <xsl:text>    },
</xsl:text>
  </xsl:template>
  <func:function name="func:escape_quotes">
    <xsl:param name="txt"/>
    <xsl:variable name="frst" select="substring-before($txt,'&quot;')"/>
    <xsl:variable name="frstln" select="string-length($frst)"/>
    <xsl:choose>
      <xsl:when test="$frstln &gt; 0 and string-length($txt) &gt; $frstln">
        <func:result select="concat($frst,'\&quot;',func:escape_quotes(substring-after($txt,'&quot;')))"/>
      </xsl:when>
      <xsl:otherwise>
        <func:result select="$txt"/>
      </xsl:otherwise>
    </xsl:choose>
  </func:function>
  <xsl:template mode="widget_defs" match="widget[@type='Input']">
    <xsl:param name="hmi_element"/>
    <xsl:variable name="value_elt">
      <xsl:call-template name="defs_by_labels">
        <xsl:with-param name="hmi_element" select="$hmi_element"/>
        <xsl:with-param name="labels">
          <xsl:text>value</xsl:text>
        </xsl:with-param>
        <xsl:with-param name="mandatory" select="'no'"/>
      </xsl:call-template>
    </xsl:variable>
    <xsl:value-of select="$value_elt"/>
    <xsl:if test="$value_elt">
      <xsl:text>    frequency: 5,
</xsl:text>
    </xsl:if>
    <xsl:text>    dispatch: function(value) {
</xsl:text>
    <xsl:if test="$value_elt">
      <xsl:text>        this.value_elt.textContent = String(value);
</xsl:text>
    </xsl:if>
    <xsl:text>    },
</xsl:text>
    <xsl:variable name="edit_elt_id" select="$hmi_element/*[@inkscape:label='edit'][1]/@id"/>
    <xsl:text>    init: function() {
</xsl:text>
    <xsl:if test="$edit_elt_id">
      <xsl:text>        id("</xsl:text>
      <xsl:value-of select="$edit_elt_id"/>
      <xsl:text>").addEventListener(
</xsl:text>
      <xsl:text>            "click", 
</xsl:text>
      <xsl:text>            evt =&gt; alert('XXX TODO : Edit value'));
</xsl:text>
    </xsl:if>
    <xsl:for-each select="$hmi_element/*[regexp:test(@inkscape:label,'^[=+\-].+')]">
      <xsl:text>        id("</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>").addEventListener(
</xsl:text>
      <xsl:text>            "click", 
</xsl:text>
      <xsl:text>            evt =&gt; {let new_val = change_hmi_value(this.indexes[0], "</xsl:text>
      <xsl:value-of select="func:escape_quotes(@inkscape:label)"/>
      <xsl:text>");
</xsl:text>
      <xsl:text>                    this.value_elt.textContent = String(new_val);});
</xsl:text>
    </xsl:for-each>
    <xsl:text>    },
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Button']"/>
  <xsl:template mode="widget_defs" match="widget[@type='Toggle']">
    <xsl:text>    frequency: 5,
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Switch']">
    <xsl:param name="hmi_element"/>
    <xsl:text>    frequency: 5,
</xsl:text>
    <xsl:text>    dispatch: function(value) {
</xsl:text>
    <xsl:text>        for(let choice of this.choices){
</xsl:text>
    <xsl:text>            if(value != choice.value){
</xsl:text>
    <xsl:text>                choice.elt.setAttribute("style", "display:none");
</xsl:text>
    <xsl:text>            } else {
</xsl:text>
    <xsl:text>                choice.elt.setAttribute("style", choice.style);
</xsl:text>
    <xsl:text>            }
</xsl:text>
    <xsl:text>        }
</xsl:text>
    <xsl:text>    },
</xsl:text>
    <xsl:text>    init: function() {
</xsl:text>
    <xsl:text>        // Hello Switch
</xsl:text>
    <xsl:text>    },
</xsl:text>
    <xsl:text>    choices: [
</xsl:text>
    <xsl:variable name="regex" select="'^(&quot;[^&quot;].*&quot;|\-?[0-9]+)(#.*)?$'"/>
    <xsl:for-each select="$hmi_element/*[regexp:test(@inkscape:label,$regex)]">
      <xsl:variable name="literal" select="regexp:match(@inkscape:label,$regex)[2]"/>
      <xsl:text>        {
</xsl:text>
      <xsl:text>            elt:id("</xsl:text>
      <xsl:value-of select="@id"/>
      <xsl:text>"),
</xsl:text>
      <xsl:text>            style:"</xsl:text>
      <xsl:value-of select="@style"/>
      <xsl:text>",
</xsl:text>
      <xsl:text>            value:</xsl:text>
      <xsl:value-of select="$literal"/>
      <xsl:text>
</xsl:text>
      <xsl:text>        }</xsl:text>
      <xsl:if test="position()!=last()">
        <xsl:text>,</xsl:text>
      </xsl:if>
      <xsl:text>
</xsl:text>
    </xsl:for-each>
    <xsl:text>    ],
</xsl:text>
  </xsl:template>
  <xsl:template mode="widget_defs" match="widget[@type='Jump']">
    <xsl:param name="hmi_element"/>
    <xsl:text>    on_click: function(evt) {
</xsl:text>
    <xsl:text>        console.log(evt);
</xsl:text>
    <xsl:text>        switch_page(this.args[0]);
</xsl:text>
    <xsl:text>    },
</xsl:text>
    <xsl:text>    init: function() {
</xsl:text>
    <xsl:text>        this.element.setAttribute("onclick", "hmi_widgets['</xsl:text>
    <xsl:value-of select="$hmi_element/@id"/>
    <xsl:text>'].on_click(evt)");
</xsl:text>
    <xsl:text>    },
</xsl:text>
  </xsl:template>
</xsl:stylesheet>
