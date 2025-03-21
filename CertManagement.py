#!/usr/bin/env python
# -*- coding: utf-8 -*-

# See COPYING file for copyrights details.


import os
import shutil
import time
import json
from zipfile import ZipFile
from cryptography import x509
from cryptography.x509.oid import ExtensionOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from util.paths import AppDataPath

# Certificate Management Data model :
# [[CN, Desc, LastConnect]]
COL_CN, COL_DESC, COL_LAST = list(range(3))
REPLACE, KEEP, CANCEL = list(range(3))

keystore_path = AppDataPath("keystore")

def _certpath():
    certpath = os.path.join(keystore_path, "cert")
    return certpath


def _mgtpath():
    return os.path.join(_certpath(), 'management.json')


def _ensureCertdir():
    certpath = _certpath()
    if not os.path.exists(certpath):
        os.makedirs(certpath)
    return certpath


def _default(CN):
    return [CN,
            '',  # default description
            None]  # last connection date


def _dataByCN(data):
    return {row[COL_CN]: row for row in data}


def _LoadData():
    """ load known metadata """
    if os.path.isdir(_certpath()):
        _path = _mgtpath()
        if os.path.exists(_path):
            return json.loads(open(_path).read())
    return []


def _get_host_name_from_certificate_file(file_path):
    with open(file_path, "rb") as cert_file:
        cert_data = cert_file.read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    # Support for legacy common name
    common_names = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if common_names:
        return common_names[0].value
    # Get the subjectAltName extension from the certificate
    ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    # Get the dNSName entries from the SAN extension
    SAN = ext.value.get_values_for_type(x509.DNSName)
    return SAN[0]
    # In case CN is not enough: fpr=cert.fingerprint(hash_algorithm).hex()


def GetData(log):
    loaded_data = _LoadData()
    if loaded_data:
        certpath = _certpath()
        cert_files = os.listdir(certpath)
        input_by_CN = _dataByCN(loaded_data)
        output = []
        # Go through all certificate files available an build data
        # out of data recoverd from json and list of certificates.
        # This implicitly filters out metadata from certificates 
        # whose file is missing
        for filename in cert_files:
            if filename.endswith('.crt'):
                try:
                    filepath = os.path.join(certpath, filename)
                    CN = _get_host_name_from_certificate_file(filepath)
                except:
                    log.write_error("Could not load certificate %s: %s"%(filepath,str(e)))
                else:    
                    if CN+".crt" == filename:
                        output.append(input_by_CN.get(CN, _default(CN)))
                    else:
                        log.write_error("Certificate %s is missnamed: should be %s.crt"%(filepath,CN))
        return output
    return []


def DeleteCert(CN):
    secret_path = os.path.join(_certpath(), CN+'.crt')
    os.remove(secret_path)


def SaveData(data):
    _ensureCertdir()
    with open(_mgtpath(), 'w') as f:
        f.write(json.dumps(data))


def _touchCN(CN):
    # here we directly use _LoadData, avoiding filtering that could be long
    data = _LoadData()
    idata = _dataByCN(data)
    dataForCN = idata.get(CN, None) if data else None

    _is_new_CN = dataForCN is None
    if _is_new_CN:
        dataForCN = _default(CN)

    # FIXME : could store time instead os a string and use DVC model's cmp
    # then date display could be smarter, etc - sortable sting hack for now
    dataForCN[COL_LAST] = time.strftime('%y/%m/%d-%H:%M:%S')

    if _is_new_CN:
        data.append(dataForCN)

    SaveData(data)

def GetCertPath(CN):
    # find Certificate from project
    crtpath = os.path.join(_certpath(), CN+'.crt')
    if not os.path.exists(crtpath):
        raise ValueError(
            "Error: Certificate for %s is missing!\n" % CN + \
            "Provide valid certicate in identity manager.")
    _touchCN(CN)
    return crtpath


def ImportCert(filepath, log, sircb):
    certpath = _ensureCertdir()
    try:
        CN = _get_host_name_from_certificate_file(filepath)
    except Exception as e:
        log.write_error("Could not load certificate %s: %s"%(filepath,str(e)))
        return False
    else:    
        data = _LoadData()
        idata = _dataByCN(data)
        dataForCN = idata.get(CN, None) if data else None
        new_filename = os.path.join(certpath, CN+".crt")
        if dataForCN:
           if sircb(dataForCN) != REPLACE:
                log.write_warning("New certificate %s for %s was discarded."%(filepath, CN))
                return False
        shutil.copyfile(filepath, new_filename)
        _touchCN(CN)
    return True


def GetClientCert():
    own_keystore = os.path.join(keystore_path, "own")
    if not os.path.exists(own_keystore):
        os.makedirs(own_keystore)
    return os.path.join(own_keystore, "client.crt")

def GetClientCertificateInfo():
    file_path = GetClientCert()
    if os.path.exists(file_path):
        info = ""
        try:
            with open(file_path, "rb") as cert_file:
                cert_data = cert_file.read()
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())

            # Support for legacy common name
            common_names = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
            for cn in common_names:
                info += "Common Name: %s\n"%cn.value
            try:
                ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
                SAN = ext.value.get_values_for_type(x509.DNSName)
                for SANEntry in SAN:
                    info += "SubjectAltName: %s\n"%SANEntry
            except x509.extensions.ExtensionNotFound:
                info += "No SubjectAltName\n"

            info += "Fingerprint: %s\n"%cert.fingerprint(hashes.SHA256()).hex()
            info += "Creation date: %s\n"%cert.not_valid_before.isoformat()
            info += "Expiration date: %s\n"%cert.not_valid_after.isoformat()
        except Exception as e:
            info += "Error while loading certificate: %s\n"%str(e)
            print(e.__class__)
        return info
    return "No client certificate available"

def ImportClientCert(filepath):
    certpath = GetClientCert()
    shutil.copyfile(filepath, certpath)

def RemoveClientCert():
    certpath = GetClientCert()
    if os.path.exists(certpath ):
        os.remove(certpath)
