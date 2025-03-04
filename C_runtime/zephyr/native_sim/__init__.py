#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Zephyr Native Simulation Target

Possible configurations:

1. **NonProgrammable**:
    Simulate non-programmable PLCs. No dynamic loading, no RPC.

2. **Serial**: Programmable through eRPC over Serial:
    - `Device`: The default value is `/dev/ttyUSB0`.
    - `Baudrate`: The default value is `115200`.
    Use this configuration to simulate a programmable PLC using eRPC over a serial connection.
    To connect simulation to simulation, either:
        - use 2 USB-to-Serial adapters + null modem cable.
        - launch socat to create a virtual null modem cable. For example:
            `socat pty,link=/tmp/beremiz_runtime_tty,rawer pty,link=/tmp/beremiz_IDE_tty,rawer`
            - set simulation serial-port to "/tmp/beremiz_runtime_tty"
            - set IDE serial-port to "/tmp/beremiz_IDE_tty".

3. **USB**: This configuration includes optional attributes for:
    - `VendorID`: The default value is an empty string.
    - `ProductID`: The default value is an empty string.

4. **TCP**: This configuration includes an optional attribute for:
    - `Port`: The default value is an empty string.

"""


XSD_name = "NativeSimulation"
XSD = f"""
<xsd:element name="{XSD_name}">
    <xsd:complexType>
        <xsd:sequence>
            <xsd:element name="SimulationType">
                <xsd:complexType>
                    <xsd:annotation><xsd:documentation>Type of simulation</xsd:documentation></xsd:annotation>
                    <xsd:choice minOccurs="0">
                        <xsd:element name="NonProgrammable">
                            <xsd:annotation><xsd:documentation>
Simulate non-programmable PLCs. No dynamic loading, no eRPC.
                            </xsd:documentation></xsd:annotation>
                        </xsd:element>
                        <xsd:element name="Serial">
                            <xsd:complexType>
                                <xsd:annotation><xsd:documentation>Serial programming</xsd:documentation></xsd:annotation>
                                <xsd:attribute name="Device" type="xsd:string" use="optional" default="/dev/ttyUSB0">
                                    <xsd:annotation><xsd:documentation>
<![CDATA[Linux serial device opened by simulation to simulate an interrupt driven UART, typically /dev/ttyUSB0
To connect simulation to simulation, either:
    - use 2 USB-to-Serial adapters + null modem cable.
    - launch socat to create a virtual null modem cable. For example:
        - run "socat pty,link=/tmp/beremiz_runtime_tty,rawer pty,link=/tmp/beremiz_IDE_tty,rawer"
        - set simulation serial-port to "/tmp/beremiz_runtime_tty"
        - set IDE serial-port to "/tmp/beremiz_IDE_tty"]]>
                                    </xsd:documentation></xsd:annotation>
                                </xsd:attribute>
                                <xsd:attribute name="Baudrate" type="xsd:integer" use="optional" default="115200"/>
                            </xsd:complexType>
                        </xsd:element>    
                        <xsd:element name="USB">
                            <xsd:complexType>
                                <xsd:attribute name="VendorID" type="xsd:string" use="optional" default=""/>
                                <xsd:attribute name="ProductID" type="xsd:string" use="optional" default=""/>
                            </xsd:complexType>
                        </xsd:element>    
                        <xsd:element name="TCP">
                            <xsd:complexType>
                                <xsd:attribute name="Port" type="xsd:integer" use="optional" default="3000"/>
                            </xsd:complexType>
                        </xsd:element>    
                    </xsd:choice>
                </xsd:complexType>
            </xsd:element>    
        </xsd:sequence>
        <xsd:attribute name="SubBoardName" type="xsd:string" use="optional" default="native/64"/>
    </xsd:complexType>
</xsd:element>
"""

def GetBuildOptions(board_cfg):
    options = []
    board_name = "native_sim"
    c_flags = []
    user_dts = []
    user_conf = []
    
    sub_board_name = board_cfg.getSubBoardName().strip()
    if sub_board_name:
        board_name += "/" + sub_board_name
    
    simulation_type = board_cfg.getSimulationType().getcontent()
    simulation_type_name = simulation_type.getLocalTag()
    programmable = simulation_type_name != "NonProgrammable"
    
    if programmable:
        options.append("programmable")
        if simulation_type_name == "Serial":
            device = simulation_type.getDevice()
            baudrate = simulation_type.getBaudrate()
            user_dts.append(f"""
                beremiz_erpc_uart {{
                    current-speed = <{baudrate}>;
                    serial-port = "{device}";
                }};
            """)
            options.append("serial")
        elif simulation_type_name == "USB":
            vendor_id = simulation_type.getVendorID()
            product_id = simulation_type.getProductID()
            
            def validate_hex_id(id_value, id_name):
                if len(id_value) != 4 or not all(c in "0123456789abcdefABCDEF" for c in id_value):
                    raise ValueError(f"Invalid {id_name}: {id_value}")

            # Validate vendor_id and product_id
            validate_hex_id(vendor_id, "VendorID")
            validate_hex_id(product_id, "ProductID")
            
            user_dts.append(f"""
                beremiz_erpc_usb {{
                    vendor-id = <0x{vendor_id}>;
                    product-id = <0x{product_id}>;
                }};
            """)
            options.append("usb")
        elif simulation_type_name == "TCP":
            port = simulation_type.getPort()
            user_dts.append(f"""
            beremiz_erpc_tcp {{
                port = <{port}>;
            }};
            """)
            options.append("tcp")
        
    return board_name, options, c_flags, user_dts, user_conf