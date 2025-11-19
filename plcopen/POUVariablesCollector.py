#!/usr/bin/env python
# -*- coding: utf-8 -*-
# This file is part of Beremiz.
# See COPYING file for copyrights details.


from . XSLTModelQuery import XSLTModelQuery, _StringValue, _BoolValue, _translate_args
from . types_enums import CLASS_TYPES, POU_TYPES, VAR_CLASS_INFOS
import re
import xml.etree.ElementTree as ET
from functools import reduce
from operator import mul
import numpy as np

def class_extraction(value):
    class_type = CLASS_TYPES.get(value)
    if class_type is not None:
        return class_type

    pou_type = POU_TYPES.get(value)
    if pou_type is not None:
        return pou_type

    var_type = VAR_CLASS_INFOS.get(value)
    if var_type is not None:
        return var_type[1]

    return None


class _VariablesTreeItemInfos(object):
    __slots__ = ["name", "var_class", "type", "edit", "debug", "variables", "missed", "arr_index_offsets", "external"]
    def __init__(self, *args):
        for attr, value in zip(self.__slots__, args):
            setattr(self, attr, value if value is not None else "")
        setattr(self, "missed", 0)
        setattr(self, "external", 0)
        setattr(self, "arr_index_offsets", [0])


    def add_child(self, name, var_class, var_type, edit, debug, arr_index_offsets = [0], is_ext=0):
        child = _VariablesTreeItemInfos(
            name, var_class, var_type, edit, debug, []
        )
        child.missed = 1
        child.arr_index_offsets = arr_index_offsets
        child.external = is_ext
        self.variables.append(child)
        return child

    def copy(self):
        return _VariablesTreeItemInfos(*[getattr(self, attr) for attr in self.__slots__])
    
    def toString(self):
        info_parts = (
            f"{slot}={getattr(self, slot, 'N/A')!r}"
            for slot in self.__slots__
        )
        return f"{self.__class__.__name__}(" + ", ".join(info_parts) + ")"


class VariablesTreeInfosFactory(object):

    def __init__(self, disable_debug):
        self.Root = None
        self.usr_types = None
        self.temp_name = ''
        self.ext_names = None
        self.debug_allowed = not disable_debug

    def GetRoot(self):
        return self.Root

    def SetRoot(self, context, *args):
        self.Root = _VariablesTreeItemInfos(
            *([''] + _translate_args(
                [class_extraction, _StringValue] + [_BoolValue] * 2,
                args) + [[]]))
        
    def demux(self, datatype_name, nodename=''):
        datatype = self.GetDataType(datatype_name)
        basetype_content = datatype.baseType.getcontent()
        basetype_content_type = basetype_content.getLocalTag()
        if basetype_content_type == "enum":
            return None
        
        if basetype_content_type == "struct":
            for i, field in enumerate(basetype_content.getvariable()):
                field_type = field.type.getcontent()
                xml_string = field_type.tostring()
                field_type_type = field_type.getLocalTag()
                if field_type_type == "derived":
                    # not standart iec type
                    xml_string = field_type.tostring()
                    temp = nodename
                    nodename = nodename + '.' + field.getname()
                    next = field_type.getname()
                    sname = self.GetBaseName(nodename)
                    self.Root.add_child(nodename, 17 , next, 0, 0, is_ext=self.ext_names is not None and sname in self.ext_names)        
                    self.demux(next, nodename)
                    nodename = temp
                elif field_type_type == "array":
                    xml_string = field_type.tostring() #  <array xmlns:ns1="http://www.plcopen.org/xml/tc6_0201"><dimension lower="0" upper="2"/><baseType><INT/></baseType></array>
                    rt = ET.fromstring(xml_string)
                    # extract lower ,upper and basetype
                    lower_list = []
                    upper_list = []
                    for dim in rt.findall('dimension'):
                        lower_list.append(int(dim.attrib['lower']))
                        upper_list.append(int(dim.attrib['upper']))
                    sizes = []
                    arr_idx_offsets = []
                    idxs = ''
                    type = rt.find('baseType').find('*').tag
                    for start, end in zip(lower_list, upper_list):
                        sizes.append(end - start + 1)
                        arr_idx_offsets.append(start)
                        idxs += f'{start}..{end}, '

                    type_string = f'ARRAY [{idxs[:-2]}] OF {type}'
                    c = tuple(sizes)
                    array = np.zeros(c)
                    iter = np.nditer(array, flags=['multi_index'])

                    if type == 'derived': # array of obj
                        derived_elem = rt.find('.//derived')
                        if derived_elem is not None:
                            type = derived_elem.attrib['name']
                            # add array pointer (no debug ability)
                            array_head = self.Root.add_child(nodename+'.'+field.getname(), 17, type_string, 0, 0, is_ext=self.ext_names is not None and nodename in self.ext_names)
                            array_head.missed = 1 
                            for elem in iter:
                                idx = iter.multi_index # tuple (i,j,k,...)
                                index_str = ''.join(f'[{i + lower_list[d]}]' for d, i in enumerate(idx))
                                self.Root.add_child(array_head.name+index_str, 17 , type, 0, 0, arr_idx_offsets, is_ext=self.ext_names is not None and nodename in self.ext_names)
                                self.demux(type, array_head.name+index_str)
                    else: 
                        # add array pointer (no debug ability)
                        array_head = self.Root.add_child(nodename+'.'+field.getname(), 17, type_string, 0, 0, is_ext=self.ext_names is not None and nodename in self.ext_names)
                        array_head.missed = 1 
                        for elem in iter:
                            idx = iter.multi_index # tuple (i,j,k,...)
                            index_str = ''.join(f'[{i + lower_list[d]}]' for d, i in enumerate(idx))
                            self.Root.add_child(array_head.name+index_str, 17 , type, 0, self.debug_allowed, arr_idx_offsets, is_ext=self.ext_names is not None and nodename in self.ext_names)
                else:
                    # standart iec type
                    field_type_name = field_type_type.upper()
                    #name, var_class, var_type, edit, debug
                    sname = self.GetBaseName(nodename)
                    self.Root.add_child(nodename + '.' + field.getname(), 17 , field_type_name, 0, self.debug_allowed, is_ext=self.ext_names is not None and sname in self.ext_names)
   
    def GetBaseName(self, nodename):
        return re.split(r'[.\[]', nodename, 1)[0]

    def ArrParameter(self, var_type):
        """
        Parse IEC-style ARRAY declarations of arbitrary dimension:

        ARRAY [0..N] OF T            → ([N+1],              "T")
        ARRAY [0..N,0..M] OF T       → ([N+1, M+1],         "T")
        ARRAY [0..N,0..M,0..K] OF T  → ([N+1, M+1, K+1],    "T")

        Returns:
        (dims: List[(start_idx, end_idx)], base_type: str)
        """
        # 1) grab everything inside the [ ... ] and the base type
        pattern = re.compile(r'''
            ^ARRAY\s*            # literal ARRAY
            \[\s*(.*?)\s*\]\s*   #   capture “0..N, 0..M, …”
            OF\s+(.+)$           # literal “OF ” + the rest = base type
            ''', re.IGNORECASE | re.VERBOSE)
        m = pattern.match(var_type.strip())
        if not m:
            return ([], var_type)

        dims_str, base = m.group(1), m.group(2).strip()

        # 2) split on commas and parse each “a..b”
        dims = []
        for chunk in dims_str.split(','):
            rng = chunk.strip()
            r2 = re.match(r'(\d+)\s*\.\.\s*(\d+)$', rng)
            if not r2:
                raise ValueError(f"Cannot parse dimension “{rng}” in “{var_type}”")
            a, b = int(r2.group(1)), int(r2.group(2))
            if b < a:
                raise ValueError(f"Upper bound {b} < lower bound {a} in “{rng}”")
            dims.append( (a, b) )

        return (dims, base)
    
    def AddVariable(self, context, *args):
        if self.Root is None:
            return
        child_var = _VariablesTreeItemInfos(
            *(_translate_args(
                [_StringValue, class_extraction, _StringValue] +
                [_BoolValue] * 2, args) + [[]]))
        
        
        self.Root.variables.append(child_var)

        dims, type =  self.ArrParameter(child_var.type)
        sizes = []
        arr_idx_offsets = []
        for start, end in dims:
            sizes.append(end - start + 1)
            arr_idx_offsets.append(start)
         
        need_demux_arr = 0
        if sizes and type: 
            child_var.missed = 1
            if self.ext_names is not None and child_var.name in self.ext_names:
                child_var.external = 1  
            for usr_type in self.usr_types:
                type_name = usr_type.getname()
                if type_name == type:
                    need_demux_arr = 1

            c = tuple(sizes)
            array = np.zeros(c)
            iter = np.nditer(array, flags=['multi_index'])
            for elem in iter:
                idx = iter.multi_index # tuple (i,j,k,...)
                index_str = ''.join(f'[{i + dims[d][0]}]' for d, i in enumerate(idx))
                self.Root.add_child(child_var.name+index_str, 17 , type, 0, not need_demux_arr and self.debug_allowed, arr_idx_offsets, self.ext_names is not None and child_var.name in self.ext_names)
                if need_demux_arr:
                    self.demux(type, child_var.name+index_str)
                   
        # if is user type
        for usr_type in self.usr_types:
            type_name = usr_type.getname()
            # print(f'{type_name} :: {child_var.type}')
            if type_name == child_var.type:
                child_var.missed = 1
                if self.ext_names is not None and child_var.name in self.ext_names:
                    child_var.external = 1  
                self.demux(type_name, child_var.name)
                break

    def GetDataType(self, type_name):
        for type in self.usr_types:
            if type_name == type.getname():
                return type
            


class POUVariablesCollector(XSLTModelQuery):
    def __init__(self, controller):
        XSLTModelQuery.__init__(self,
                                controller,
                                "pou_variables.xslt",
                                [(name, self.FactoryCaller(name))
                                 for name in ["SetRoot", "AddVariable"]])

    def FactoryCaller(self, funcname):
        def CallFactory(*args):
            return getattr(self.factory, funcname)(*args)
        return CallFactory
    
    def GetNamesFromDerivedExternalVars(self, pou):
        pou_xml = pou.tostring()
        pou_xml = re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', pou_xml)  
        pou_xml = re.sub(r'(<\/?)[\w\d]+:', r'\1', pou_xml)       
        rt = ET.fromstring(pou_xml)
        res = []

        for extvar in rt.findall('.//externalVars'):
            for var in extvar.findall('variable'):
                var_name = var.get('name')
                # is external usertype
                if var.find('type/derived') is not None:
                    res.append(var_name)
                # is external array of usertype/iec
                if var.find('type/array/baseType') is not None:
                    res.append(var_name)
        r = 0
        return res


    def Collect(self, root, debug, user_types = None, disable_debug = False):
        self.factory = VariablesTreeInfosFactory(disable_debug)
        self.factory.usr_types = user_types
        if self.factory is not None and root.name != "config":
            if hasattr(root, 'getpouType'):
                if root.getpouType() == 'program':
                    self.factory.ext_names = self.GetNamesFromDerivedExternalVars(root)

        self._process_xslt(root, debug)
        res = self.factory.GetRoot()
        self.factory = None
        return res
