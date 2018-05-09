from __future__ import absolute_import
from os import listdir, path
import util.paths as paths

_base_path = paths.AbsDir(__file__)


def _GetLocalConnectorClassDialog(name):
    return lambda: getattr(__import__(name, globals(), locals()), name + "_connector_dialog")

def _GetLocalConnectorURITypes(name):
    return lambda: getattr(__import__(name, globals(), locals()), "URITypes", None)

connectors_dialog = {name:
                     {"function":_GetLocalConnectorClassDialog(name), "URITypes": _GetLocalConnectorURITypes(name)}
                     for name in listdir(_base_path)
                     if (path.isdir(path.join(_base_path, name)) and
                         not name.startswith("__"))}

def ConnectorDialog(type, confnodesroot):
    if type not in connectors_dialog:
        return None

    connectorclass = connectors_dialog[type]["function"]()
    return connectorclass(confnodesroot)

def GetConnectorFromURI(uri):
    typeOfConnector = None
    for t in connectors_dialog:
        connectorTypes = connectors_dialog[t]["URITypes"]()
        if connectorTypes and uri in connectorTypes:
            typeOfConnector = t
            break

    return typeOfConnector