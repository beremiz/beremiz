#!/usr/bin/env python
# -*- coding: utf-8 -*-

# This file is part of Beremiz
#
# See COPYING file for copyrights details.

"""
Transport for the EtherCAT services the runtime exposes.

The runtime registers a single extended call, EXTENDED_CALL, and dispatches it
to a closed set of commands, see ETHERCAT_COMMANDS in runtime_etherlab.py.
Requests and answers are JSON objects and binary payloads are base64 encoded,
so that nothing the IDE sends can be turned into code on the runtime side.
"""


import base64
import json


EXTENDED_CALL = "EtherCAT"


class EtherCATError(Exception):
    """Raised when the runtime could not honour an EtherCAT request."""


def EncodeBinary(data):
    """Wrap binary data into a JSON compatible string."""
    return base64.b64encode(data).decode("ascii")


def DecodeBinary(text):
    """Unwrap what EncodeBinary produced."""
    return base64.b64decode(text.encode("ascii"))


def EncodeRequest(command, args):
    return json.dumps({"cmd": command, "args": list(args)}).encode("utf-8")


def DecodeRequest(payload):
    request = json.loads(payload.decode("utf-8"))
    return request["cmd"], request.get("args", [])


def EncodeAnswer(result):
    return json.dumps({"result": result}).encode("utf-8")


def EncodeError(message):
    return json.dumps({"error": message}).encode("utf-8")


def DecodeAnswer(payload):
    if not payload:
        raise EtherCATError("no answer from the runtime")
    answer = json.loads(payload.decode("utf-8"))
    if "error" in answer:
        raise EtherCATError(answer["error"])
    return answer["result"]


def CallEtherCAT(connector, command, *args):
    """
    Send a command to the EtherCAT service of the runtime.
    @param connector: connector to the runtime, None when not connected
    @param command: name of the command, key of ETHERCAT_COMMANDS
    @param args: arguments of the command, JSON compatible values only
    @return result of the command
    """
    if connector is None:
        raise EtherCATError("no runtime connected")
    return DecodeAnswer(
        connector.ExtendedCall(EXTENDED_CALL, EncodeRequest(command, args)))
