" Here are base type definitions for plugins "

class PluggableTemplate:

    XSD = None
    
    def __init__(self, buspath):
        pass

    def TestModified(self):
        return False
        
    def ReqSave(self):
        return False

    def Generate_C(self, dirpath, locations):
        return [] # [filenames, ...]

    def BlockTypesFactory(self):
        return []

    def STLibraryFactory(self):
        return ""

    ViewClass = None
    View = None
    def ViewFactory(self):
        if self.ViewClass:
            if not self.View:
                def _onclose():
                    self.View = None
                self.View = self.ViewClass()
                self.View.OnPluggClose = _onclose
            return self.View
        return None


def _do_BaseParamsClasses():
    Classes = {}
    Types = {}
    GenerateClassesFromXSDstring("""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="BaseParams">
            <xsd:complexType>
              <xsd:attribute name="Enabled" type="xsd:string" use="required" />
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)
    CreateClasses(Classes, Types)
    
    PluginsBaseParamsClass = Classes["BaseParams"]

    Classes = {}
    Types = {}
    GenerateClassesFromXSDstring("""<?xml version="1.0" encoding="ISO-8859-1" ?>
        <xsd:schema xmlns:xsd="http://www.w3.org/2001/XMLSchema">
          <xsd:element name="BaseParams">
            <xsd:complexType>
              <xsd:attribute name="BusId" type="xsd:integer" use="required" />
              <xsd:attribute name="Name" type="xsd:string" use="required" />
            </xsd:complexType>
          </xsd:element>
        </xsd:schema>
    """)
    CreateClasses(Classes, Types)
    
    BusBaseParamsClass = Classes["BaseParams"]
    return PluginsBaseParamsClass, BusBaseParamsClass
    
PluginsBaseParamsClass, BusBaseParamsClass = _do_BaseParamsClasses()

