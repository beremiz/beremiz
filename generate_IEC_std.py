#!/usr/bin/env python
# -*- coding: utf-8 -*-

#This file is part of PLCOpenEditor, a library implementing an IEC 61131-3 editor
#based on the plcopen standard. 
#
#Copyright (C) 2007-2011: Edouard TISSERANT and Laurent BESSARD
#
#See COPYING file for copyrights details.
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#General Public License for more details.
#
#You should have received a copy of the GNU General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""
 THIS CODE GENARATES C++ CODE FOR IEC2C COMPILER
"""

file_list = [
        ('absyntax_utils',      'function_type_decl','h'        ),
        ('absyntax_utils',      'get_function_type_decl','c'    ),
        ('absyntax_utils',      'search_type_code','c'          ),
        ('stage4/generate_c',   'st_code_gen','c'               ),
        ('stage4/generate_c',   'il_code_gen','c'               ),
        ('stage1_2',            'standard_function_names','c'   ),
        ('lib',                 'iec_std_lib_generated','h'     )
        ]

# Get definitions
from plcopen.structures import *

if len(sys.argv) != 2 :
    print "Usage: " + sys.argv[0] + " path_name\n -> create files in path_name"
    sys.exit(0)

#import pprint
#pp = pprint.PrettyPrinter(indent=4)

matiec_header = """/*
 * Copyright (C) 2007-2011: Edouard TISSERANT and Laurent BESSARD
 *
 * See COPYING and COPYING.LESSER files for copyright details.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program. If not, see <http://www.gnu.org/licenses/>.
 *
 */

/****
 * IEC 61131-3 standard function library
 * generated code, do not edit by hand
 */
 
 """

matiec_lesser_header = """/*
 * Copyright (C) 2007-2011: Edouard TISSERANT and Laurent BESSARD
 *
 * See COPYING and COPYING.LESSER files for copyright details.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 3 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 * 
 * You should have received a copy of the GNU Lesser General Public License 
 * along with this library. If not, see <http://www.gnu.org/licenses/>.
 *
 */

/****
 * IEC 61131-3 standard function library
 * generated code, do not edit by hand
 */

 """

def ANY_to_compiler_test_type_GEN(typename, paramname):
    """
    Convert ANY_XXX IEC type declaration into IEC2C's generated type test.
    This tests are defined in search_expression_type.cc 
    """
    return {"ANY" : "",
    "ANY_BIT" : "if(%(paramname)s_type_symbol == NULL || search_expression_type->is_binary_type(%(paramname)s_type_symbol))",
    "ANY_NBIT" : "if(%(paramname)s_type_symbol == NULL || search_expression_type->is_nbinary_type(%(paramname)s_type_symbol))",
    "ANY_NUM" : "if(%(paramname)s_type_symbol == NULL || search_expression_type->is_num_type(%(paramname)s_type_symbol))",
    "ANY_REAL" : "if(%(paramname)s_type_symbol == NULL || search_expression_type->is_real_type(%(paramname)s_type_symbol))",
    "ANY_INT" : "if(%(paramname)s_type_symbol == NULL || search_expression_type->is_integer_type(%(paramname)s_type_symbol))"
    }.get(typename,
        #"if (typeid(*last_type_symbol) == typeid(%(typename)s_type_name_c))")%{
        "if(%(paramname)s_type_symbol == NULL || search_expression_type->is_same_type(&search_constant_type_c::%(typename)s_type_name, last_type_symbol))")%{
                "paramname" : paramname, "typename": typename.lower()}

def recurse_and_indent(fdecls, indent, do_type_search_only = False, do_il = False):
    """
    This function generate visit(function_invocation) code for 
        - ST code generator
        - IL code generator
        - search_expression_type class for ST
        - search_expression_type class for IL
        
    Input data is a 
    "{fname : {IN[0]paramname : {IN[0]paramtype : {IN[1]paraname : {IN[1]paramtype : {... : {IN[N]paraname : {IN[N]paramtype : (fdecl,)}}}}}}"
    nested dictionary structure.
    """
    if type(fdecls) != type(tuple()):
        res = ""
        for Paramname, ParamTypes in fdecls.iteritems():
            if do_il:
                res += """
{"""
                if not do_type_search_only:
                    res += """
    symbol_c *%(input_name)s_param_name = (symbol_c *)(new identifier_c("%(input_name)s"));
    /* Get the value from a foo(<param_name> = <param_value>) style call */
    symbol_c *%(input_name)s_param_value = &this->default_variable_name;
"""%{"input_name":Paramname}
                res += """
    symbol_c *%(input_name)s_type_symbol = param_data_type;
    last_type_symbol = %(input_name)s_type_symbol;
"""%{"input_name":Paramname}
            else:
                res += """
{
    symbol_c *%(input_name)s_param_name = (symbol_c *)(new identifier_c("%(input_name)s"));
    /* Get the value from a foo(<param_name> = <param_value>) style call */
    symbol_c *%(input_name)s_param_value = function_call_param_iterator.search_f(%(input_name)s_param_name);
    symbol_c *%(input_name)s_type_symbol = NULL;
    
    /* Get the value from a foo(<param_value>) style call */
    if (%(input_name)s_param_value == NULL)
      %(input_name)s_param_value = function_call_param_iterator.next_nf();
    if (%(input_name)s_param_value != NULL) {
      %(input_name)s_type_symbol = search_expression_type->get_type(%(input_name)s_param_value);
      last_type_symbol = last_type_symbol && %(input_name)s_type_symbol && search_expression_type->is_same_type(%(input_name)s_type_symbol, last_type_symbol) ? search_expression_type->common_type(%(input_name)s_type_symbol, last_type_symbol) : %(input_name)s_type_symbol ;
    }
"""%{"input_name":Paramname}
                                
            for ParamType,NextParamDecl in ParamTypes.iteritems():
            
                res += """    
    %(type_test)s
    {
%(if_good_type_code)s
    }
"""%{
    "type_test":ANY_to_compiler_test_type_GEN(ParamType,Paramname), 
    "if_good_type_code":recurse_and_indent(NextParamDecl,indent,do_type_search_only).replace('\n','\n    ')}

            res += """    
    
    ERROR;
}
"""
        
        return res.replace('\n','\n'+indent)
    else:
        res = "\n"
        fdecl=fdecls[0]
        
        if not do_type_search_only:
            code_gen = eval(fdecl["python_eval_c_code_format"])
            
            if code_gen[1] is not None:
                res += "function_name = (symbol_c*)(new pragma_c(\"%s\"));\n"%code_gen[1]
            if fdecl["extensible"]:
                res += """
if (nb_param < %(min_nb_param)d)
  nb_param = %(min_nb_param)d;
char* nb_param_str = new char[10];
sprintf(nb_param_str, "%%d", nb_param);
symbol_c * nb_param_name = (symbol_c *)(new identifier_c("nb_param"));
ADD_PARAM_LIST(nb_param_name, (symbol_c*)(new integer_c((const char *)nb_param_str)), (symbol_c*)(new int_type_name_c()), function_param_iterator_c::direction_in)
"""%{"min_nb_param" : len(fdecl["inputs"])}
            for paramname,paramtype,unused in fdecl["inputs"]:
                res += """
if (%(input_name)s_type_symbol == NULL)
  %(input_name)s_type_symbol = last_type_symbol;
ADD_PARAM_LIST(%(input_name)s_param_name, %(input_name)s_param_value, %(input_name)s_type_symbol, function_param_iterator_c::direction_in)
"""%{"input_name" : paramname}
            if fdecl["extensible"]:
                res += """
int base_num = %d;
symbol_c *param_value = NULL;
symbol_c *param_name = NULL;
do{
    char my_name[10];
    sprintf(my_name, "IN%%d", base_num++);
    param_name = (symbol_c*)(new identifier_c(my_name));
    
    /* Get the value from a foo(<param_name> = <param_value>) style call */
    param_value = function_call_param_iterator.search_f(param_name);
    
    /* Get the value from a foo(<param_value>) style call */
    if (param_value == NULL)
      param_value = function_call_param_iterator.next_nf();
    if (param_value != NULL){
        symbol_c *current_type_symbol = search_expression_type->get_type(param_value);
        last_type_symbol = last_type_symbol && search_expression_type->is_same_type(current_type_symbol, last_type_symbol) ? search_expression_type->common_type(current_type_symbol, last_type_symbol) : current_type_symbol ;
    
        /*Function specific CODE */
        ADD_PARAM_LIST(param_name, param_value, current_type_symbol, function_param_iterator_c::direction_in)
    }
    
}while(param_value != NULL);
"""%(fdecl["baseinputnumber"] + 2)
        
        result_type_rule = fdecl["return_type_rule"]
        res += {
            "copy_input" : "symbol_c * return_type_symbol = last_type_symbol;\n",
            "defined" : "symbol_c * return_type_symbol = &search_constant_type_c::%s_type_name;\n"%fdecl["outputs"][0][1].lower(),
            }.get(result_type_rule, "symbol_c * return_type_symbol = %s;\n"%result_type_rule)
        
        if not do_type_search_only:
            if code_gen[0] is not None:
                res += "function_type_prefix = %s;\n"%{"return_type" : "return_type_symbol"}.get(code_gen[0], "(symbol_c*)(new pragma_c(\"%s\"))"%code_gen[0])
            if code_gen[2] is not None:
                res += "function_type_suffix = %s_symbol;\n"%{"common_type" : "last_type"}.get(code_gen[2], code_gen[2])
            
            any_common = reduce(lambda x, y: {"ANY": lambda x: x,
                                          "ANY_BIT": lambda x: {"ANY": y, "ANY_NUM": y}.get(y, x),
                                          "ANY_NUM": lambda x: {"ANY": y}.get(y, x),
                                          "ANY_REAL": lambda x: {"ANY": y, "ANY_NUM": y}.get(y, x)}.get(x, y), 
                                [paramtype for paramname,paramtype,unused in fdecl["inputs"]], "BOOL")
            
            first = True
            for list, test_type, default_type in [(["ANY", "ANY_NUM"], "integer", "lint"),
                                                  (["ANY_BIT"], "integer", "lword"),
                                                  (["ANY", "ANY_REAL"], "real", "lreal")]:
            
                if any_common in list:
                    if not first:
                        res += "else "
                    first = False
                    res += """if (search_expression_type->is_literal_%s_type(function_type_suffix))
    function_type_suffix = &search_constant_type_c::%s_type_name;
"""%(test_type, default_type)
        
            res += "break;\n"
        else:
            res += "return return_type_symbol;\n"
        
        return res.replace('\n','\n'+indent)

def get_default_input_type(fdecls):
    if type(fdecls) != type(tuple()) and len(fdecls) == 1:
        ParamTypes = fdecls.values()[0]
        if len(ParamTypes) == 1:
            ParamType_name, ParamType_value = ParamTypes.items()[0]
            if not ParamType_name.startswith("ANY") and type(ParamType_value) == type(tuple()):
                return "&search_constant_type_c::%s_type_name" % ParamType_name.lower()
    return "NULL"
    
###################################################################
###                                                             ###
###                           MAIN                              ###
###                                                             ###
###################################################################

"""
Reorganize std_decl from structure.py
into a nested dictionnary structure (i.e. a tree):
"{fname : {IN[0]paramname : {IN[0]paramtype : {IN[1]paraname : {IN[1]paramtype : {... : {IN[N]paraname : {IN[N]paramtype : (fdecl,)}}}}}}"
Keep ptrack of original declaration order in a 
separated list called official_order
"""
std_fdecls = {}
official_order = []
for section in std_decl:
    for fdecl in section["list"]:
        if len(official_order)==0 or fdecl["name"] not in official_order:
            official_order.append(fdecl["name"])
        # store all func by name in a dict
        std_fdecls_fdecl_name = std_fdecls.get(fdecl["name"], {})
        current = std_fdecls_fdecl_name
        for i in fdecl["inputs"]:
            current[i[0]] = current.get(i[0], {})
            current = current[i[0]]
            last = current
            current[i[1]] = current.get(i[1], {})
            current = current[i[1]]
        last[i[1]]=(fdecl,)
        std_fdecls[fdecl["name"]] = std_fdecls_fdecl_name

###################################################################

"""
Generate the long enumeration of std function types
"""
function_type_decl =  matiec_header + """
typedef enum {
"""
for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    function_type_decl += "    function_"+fname.lower()+",\n"

function_type_decl += """    function_none
} function_type_t;
"""
###################################################################
"""
Generate the funct that return enumerated according function name
"""
get_function_type_decl = matiec_header + """
function_type_t get_function_type(identifier_c *function_name) {
"""
for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    get_function_type_decl += """
if (!strcasecmp(function_name->value, "%s"))
    return function_%s;
"""%(fname,fname.lower())

get_function_type_decl += """
    else return function_none;
}

"""
###################################################################
"""
Generate the part of generate_c_st_c::visit(function_invocation)
that is responsible to generate C code for std lib calls.
"""
st_code_gen = matiec_header + """
switch(current_function_type){
"""

for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    st_code_gen += """
/****
 *%s
 */
    case function_%s :
    {
        symbol_c *last_type_symbol = %s;
"""    %(fname, fname.lower(), get_default_input_type(fdecls))
    indent =  "    "

    st_code_gen += recurse_and_indent(fdecls, indent).replace('\n','\n    ')
    
    st_code_gen += """
    }/*function_%s*/
    break;
"""    %(fname.lower())
st_code_gen +=  """
    case function_none :
    ERROR;
}
"""

###################################################################
"""
Generate the part of generate_c_il_c::visit(il_function_call)
that is responsible to generate C code for std lib calls.
"""
il_code_gen = matiec_header + """
switch(current_function_type){
"""

for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    il_code_gen += """
/****
 *%s
 */
    case function_%s :
    {
        symbol_c *last_type_symbol = %s;
"""    %(fname, fname.lower(), get_default_input_type(fdecls))
    indent =  "    "

    il_code_gen += recurse_and_indent(fdecls, indent, do_il=True).replace('\n','\n    ')
    
    il_code_gen += """
    }/*function_%s*/
    break;
"""    %(fname.lower())
il_code_gen +=  """
    case function_none :
    ERROR;
}
"""

###################################################################
"""
Generate the part of search_expression_type_c::visit(function_invocation)
that is responsible of returning type symbol for function invocation.
"""
search_type_code = matiec_header + """

void *search_expression_type_c::compute_standard_function_default(function_invocation_c *st_symbol = NULL, il_formal_funct_call_c *il_symbol = NULL) {
  function_type_t current_function_type;
  function_call_param_iterator_c *tmp_function_call_param_iterator;
  if (st_symbol != NULL && il_symbol == NULL) {
    current_function_type = get_function_type((identifier_c *)st_symbol->function_name);
    tmp_function_call_param_iterator = new function_call_param_iterator_c(st_symbol);
  }
  else if (st_symbol == NULL && il_symbol != NULL) {
    current_function_type = get_function_type((identifier_c *)il_symbol->function_name);
    tmp_function_call_param_iterator = new function_call_param_iterator_c(il_symbol);
  }
  else
    ERROR;
  function_call_param_iterator_c function_call_param_iterator(*tmp_function_call_param_iterator);
  search_expression_type_c* search_expression_type = this;

  switch(current_function_type){
"""

for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    search_type_code += """
/****
 *%s
 */
    case function_%s :
    {
        symbol_c *last_type_symbol = %s;
"""    %(fname, fname.lower(), get_default_input_type(fdecls))
    indent =  "    "

    search_type_code += recurse_and_indent(fdecls, indent, True).replace('\n','\n    ')
    
    search_type_code += """
    }/*function_%s*/
    break;
"""    %(fname.lower())
search_type_code += """
    case function_none :
    ERROR;
  }
  return NULL;
}

void *search_expression_type_c::compute_standard_function_il(il_function_call_c *symbol, symbol_c *param_data_type) {
  
  function_type_t current_function_type = get_function_type((identifier_c *)symbol->function_name);
  function_call_param_iterator_c function_call_param_iterator(symbol);  
  search_expression_type_c* search_expression_type = this;

  switch(current_function_type){
"""

for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    search_type_code += """
/****
 *%s
 */
    case function_%s :
    {
        symbol_c *last_type_symbol = %s;
"""    %(fname, fname.lower(), get_default_input_type(fdecls))
    indent =  "    "

    search_type_code += recurse_and_indent(fdecls, indent, True, True).replace('\n','\n    ')
    
    search_type_code += """
    }/*function_%s*/
    break;
"""    %(fname.lower())
search_type_code += """
    case function_none :
    ERROR;
  }
  return NULL;
}
"""

###################################################################
###################################################################
###################################################################
"""
Generate the standard_function_names[] for inclusion in bizon generated code
"""
standard_function_names = matiec_header + """
const char *standard_function_names[] = {
"""
for fname, fdecls in [ (fname,std_fdecls[fname]) for fname in official_order ]:
    standard_function_names += "\""+fname+"\",\n"
standard_function_names += """
/* end of array marker! Do not remove! */
NULL
};

"""

###################################################################
###################################################################
###################################################################
"""
Generate the C implementation of the IEC standard function library.
"""
iec_std_lib_generated = matiec_lesser_header + """

/* Macro that expand to subtypes */
"""
for typename, parenttypename in TypeHierarchy_list:
    if (typename.startswith("ANY")):
        iec_std_lib_generated += "#define " + typename + "(DO)"
        for typename2, parenttypename2 in TypeHierarchy_list:
            if(parenttypename2 == typename):
                if(typename2.startswith("ANY")):
                    iec_std_lib_generated +=  " " + typename2 + "(DO)"
                else:
                    iec_std_lib_generated +=  " DO(" + typename2 + ")"
        iec_std_lib_generated +=  "\n"
    else:
        break

# Now, print that out, or write to files from sys.argv
for path, name, ext in file_list :
    fd = open(os.path.join(sys.argv[1], path, name+'.'+ext),'w')
    fd.write(eval(name))
    fd.close()
    
#print "/* Code to eventually paste in iec_std_lib.h if type hierarchy changed */"
#print "/* you also have to change iec_std_lib.h according to new types        */\n\n"
#print iec_std_lib_generated
