#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zephyr ooPLC Target

Possible configurations:

1. **NonProgrammable**: This configuration is used for non-programmable PLCs.

2. **Serial**: Programmable through eRPC over Serial:
    - `Baudrate`: The default value is `115200`.

3. **USB**: This configuration includes optional attributes for:
    - `VendorID`: The default value is an empty string.
    - `ProductID`: The default value is an empty string.

"""


XSD_name = "ooPLC"
XSD = f"""
<xsd:element name="{XSD_name}">
    <xsd:complexType>
        <xsd:sequence>
            <xsd:element name="ooPLCType">
                <xsd:complexType>
                    <xsd:choice minOccurs="0">
                        <xsd:element name="NonProgrammable">
                            <xsd:annotation>
                                <xsd:documentation>Non-Programmable</xsd:documentation>
                            </xsd:annotation>
                        </xsd:element>
                        <xsd:element name="Serial">
                            <xsd:complexType>
                                <xsd:annotation><xsd:documentation>Serial ooPLC programming</xsd:documentation></xsd:annotation>
                                <xsd:attribute name="Baudrate" type="xsd:integer" use="optional" default="115200"/>
                            </xsd:complexType>
                        </xsd:element>
                        <xsd:element name="USB"/>
                    </xsd:choice>
                </xsd:complexType>
            </xsd:element>    
        </xsd:sequence>
    </xsd:complexType>
</xsd:element>
"""

def GetBuildOptions(target_cfg):
    options = []
    board_name = "ooplc"
    c_flags = []
    user_dts = []
    user_conf = []
    
    ooplc_type = target_cfg.getOoPLCType().getContent()
    ooplc_type_name = ooplc_type.getLocalTag()
    programmable = ooplc_type_name != "NonProgrammable"
    
    if programmable:
        options.append("programmable")
        if ooplc_type_name == "Serial":
            device = ooplc_type.getDevice()
            baudrate = ooplc_type.getBaudrate()
            user_dts.append(f"""
                beremiz_erpc_uart {{
                    current-speed = <{baudrate}>;
                }};
            """)
        elif ooplc_type_name == "USB":
            # TODO: Use the actual VendorID and ProductID from ooPLC
            vendor_id = "DEAD"
            product_id = "BEEF"
            
            user_dts.append(f"""
                beremiz_erpc_usb {{
                    vendor-id = <0x{vendor_id}>;
                    product-id = <0x{product_id}>;
                }};
            """)

    libraries = [("NativeSim", SimplePOULibraryFactory(paths.AbsNeighbourFile(__file__, "pous.xml")))]

    preamble = ''

    return board_name, options, c_flags, user_dts, user_conf, libraries, preamble