# opcua/server.py

import os

import targets
from targets.Builder import PLC_SPLIT
from .client import Open62541LibraryPath, Open62541IncludePaths


class OPCUAServer(object):
    XSD = """<?xml version="1.0" encoding="ISO-8859-1" ?>
    <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
      <xsd:element name="OPCUAServer">
        <xsd:complexType>
          <xsd:sequence>
            <xsd:element name="Security" minOccurs="0">
              <xsd:annotation>
                <xsd:documentation>Cryptomaterial files are taken from project files directory</xsd:documentation>
              </xsd:annotation>
              <xsd:complexType>
                <xsd:attribute name="Certificate" type="xsd:string" use="optional" default="server_cert.der"/>
                <xsd:attribute name="PrivateKey" type="xsd:string" use="optional" default="server_key.pem"/>
                <xsd:attribute name="TrustList" type="xsd:string" use="optional" default=""/>
                <xsd:attribute name="AllowNonePolicy" type="xsd:boolean" use="optional" default="false"/>
              </xsd:complexType>
            </xsd:element>
            <xsd:element name="UserPassword" minOccurs="0">
              <xsd:complexType>
                <xsd:attribute name="User" type="xsd:string" use="optional"/>
                <xsd:attribute name="Password" type="xsd:string" use="optional"/>
              </xsd:complexType>
            </xsd:element>
          </xsd:sequence>
          <xsd:attribute name="Port" type="xsd:integer" use="optional" default="4840"/>
          <xsd:attribute name="Interface" type="xsd:string" use="optional" default=""/>
          <xsd:attribute name="Namespace" type="xsd:string" use="optional" default="urn:beremiz:plc"/>
          <xsd:attribute name="RootName" type="xsd:string" use="optional" default="PLC"/>
          <xsd:attribute name="ApplicationURI" type="xsd:string" use="optional" default="urn:beremiz:opcua:server"/>
          <xsd:attribute name="AccessLevel" use="optional" default="RW">
            <xsd:simpleType>
              <xsd:restriction base="xsd:string">
                <xsd:enumeration value="RO"/>
                <xsd:enumeration value="RW"/>
              </xsd:restriction>
            </xsd:simpleType>
          </xsd:attribute>
          <xsd:attribute name="AllowAnonymous" type="xsd:boolean" use="optional" default="true"/>
        </xsd:complexType>
      </xsd:element>
    </xsd:schema>
    """

    def SupportsTarget(self, target):
        # Instance tree is reached through logic lifecycle hooks of split builds
        return target.getPLCBuildType() == PLC_SPLIT

    def _ProjectFile(self, name):
        path = os.path.join(self.GetCTRoot()._getProjectFilesPath(), name)
        if not os.path.isfile(path):
            self.FatalError(_("OPC-UA server: missing file %s in project files\n") % name)
        with open(path, 'rb') as f:
            return f.read()

    def CTNGenerate_C(self, buildpath, locations):
        current_location = self.GetCurrentLocation()
        locstr = "_".join(map(str, current_location))
        c_path = os.path.join(buildpath, "opcua_server__%s.c" % locstr)

        def c_str(s):
            return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

        def c_bytes(name, data):
            return "static UA_Byte %s[] = {%s};" % (
                name, ",".join("0x%02x" % b for b in data) or "0")

        params = self.OPCUAServer
        crypto = []
        security = params.getSecurity()
        if security is not None:
            crypto.append(c_bytes("server_cert", self._ProjectFile(security.getCertificate())))
            crypto.append(c_bytes("server_key", self._ProjectFile(security.getPrivateKey())))
            trust = [name.strip() for name in security.getTrustList().split(",") if name.strip()]
            for i, name in enumerate(trust):
                crypto.append(c_bytes("trust_%d" % i, self._ProjectFile(name)))
            crypto.append("static UA_ByteString trust_list[] = {%s};" % ",".join(
                ["{sizeof(trust_%d), trust_%d}" % (i, i) for i in range(len(trust))] or ["{0, NULL}"]))
            crypto.append("#define OPCUA_SECURITY")
            crypto.append("#define OPCUA_TRUST_LIST_SIZE %d" % len(trust))
            crypto.append("#define OPCUA_ALLOW_NONE_POLICY %d" % security.getAllowNonePolicy())

        users = params.getUserPassword()
        if users is not None:
            crypto.append("#define OPCUA_USER %s" % c_str(users.getUser() or ""))
            crypto.append("#define OPCUA_PASSWORD %s" % c_str(users.getPassword() or ""))
        elif not params.getAllowAnonymous():
            self.GetCTRoot().logger.write_warning(
                _("OPC-UA server: anonymous access disabled and no user defined, nobody can connect\n"))

        with open(os.path.join(os.path.dirname(__file__), "opcua_server_template.c")) as f:
            template = f.read()

        c_code = template % {
            "locstr": locstr,
            "port": params.getPort(),
            "interface": c_str(params.getInterface()),
            "namespace": c_str(params.getNamespace()),
            "root_name": c_str(params.getRootName()),
            "application_uri": c_str(params.getApplicationURI()),
            "access_rw": int(params.getAccessLevel() == "RW"),
            "allow_anonymous": int(params.getAllowAnonymous()),
            "crypto": "\n".join(crypto),
            "var_access_code": targets.GetCode("var_access.c"),
        }

        with open(c_path, 'w') as c_file:
            c_file.write(c_code)

        LDFLAGS = ['"' + os.path.join(Open62541LibraryPath, "libopen62541.a") + '"', '-lcrypto']

        CFLAGS = ' '.join(['-I"' + path + '"' for path in Open62541IncludePaths])
        CFLAGS += ' "-I%s"' % os.path.abspath(self.GetCTRoot().GetIECLibPath())

        return [(c_path, CFLAGS)], LDFLAGS, True
