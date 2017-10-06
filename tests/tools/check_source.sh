#!/bin/sh
# -*- coding: utf-8 -*-

# This file is part of Beremiz, a Integrated Development Environment for
# programming IEC 61131-3 automates supporting plcopen standard and CanFestival.
#
# Copyright (C) 2017: Andrey Skvortsov
#
# See COPYING file for copyrights details.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


exit_code=0
set_exit_error()
{
    if [ $exit_code -eq 0 ]; then
       exit_code=1
    fi
}


compile_checks()
{
    echo "Syntax checking..."
    py_files=$(find . -name '*.py')

    # remove compiled Python files
    find . -name '*.pyc' -exec rm -f {} \;

    for i in $py_files; do
        # echo $i
        python -m py_compile $i
        if [ $? -ne 0 ]; then
            echo "Syntax error in $i"
            set_exit_error
        fi
    done
}

# pep8 was renamed to pycodestyle
# detect existed version
pep8_detect()
{
    test -n $pep8 && (which pep8 > /dev/null) && pep8="pep8"
    test -n $pep8 && (which pycodestyle > /dev/null) && pep8="pycodestyle"
    if [ -z $pep8 ]; then
        echo "pep8/pycodestyle is not found"
        set_exit_error
    fi
}

pep8_checks_default()
{
    echo "Check basic code-style problems for PEP-8"

    test -n $pep8 && pep8_detect
    test -z $pep8 && return

    user_ignore=
    # user_ignore=$user_ignore,E265  # E265 block comment should start with '# '
    user_ignore=$user_ignore,E501  # E501 line too long (80 > 79 characters)

    # ignored by default,
    default_ignore=
    default_ignore=$default_ignore,E121  # E121 continuation line under-indented for hanging indent
    default_ignore=$default_ignore,E123  # E123 closing bracket does not match indentation of opening bracket’s line
    default_ignore=$default_ignore,E126  # E126 continuation line over-indented for hanging indent
    default_ignore=$default_ignore,E133  # E133 closing bracket is missing indentation
    default_ignore=$default_ignore,E226  # E226 missing whitespace around arithmetic operator
    default_ignore=$default_ignore,E241  # E241 multiple spaces after ':'
    default_ignore=$default_ignore,E242  # E242 tab after ‘,’
    default_ignore=$default_ignore,E704  # E704 multiple statements on one line (def)
    default_ignore=$default_ignore,W503  # W503 line break occurred before a binary operator
    ignore=$user_ignore,$default_ignore

    # $pep8 --ignore $ignore --exclude build ./
    $pep8 --max-line-length 300 --exclude build ./
    if [ $? -ne 0 ]; then
        set_exit_error
    fi
}


pep8_checks_selected()
{
    echo "Check basic code-style problems for PEP-8 (selective)"

    test -n $pep8 && pep8_detect
    test -z $pep8 && return

    # select checks:
    user_select=
    user_select=$user_select,W291   # W291 trailing whitespace
    user_select=$user_select,E401   # E401 multiple imports on one line
    user_select=$user_select,E265   # E265 block comment should start with '# '
    user_select=$user_select,E228   # E228 missing whitespace around modulo operator
    user_select=$user_select,W293   # W293 blank line contains whitespace
    user_select=$user_select,E302   # E302 expected 2 blank lines, found 1
    user_select=$user_select,E261   # E261 at least two spaces before inline comment
    user_select=$user_select,E271   # E271 multiple spaces after keyword
    user_select=$user_select,E231   # E231 missing whitespace after ','
    user_select=$user_select,E303   # E303 too many blank lines (2)
    user_select=$user_select,E225   # E225 missing whitespace around operator
    user_select=$user_select,E711   # E711 comparison to None should be 'if cond is not None:'
    user_select=$user_select,E251   # E251 unexpected spaces around keyword / parameter equals
    user_select=$user_select,E227   # E227 missing whitespace around bitwise or shift operator
    user_select=$user_select,E202   # E202 whitespace before ')'
    user_select=$user_select,E201   # E201 whitespace after '{'
    user_select=$user_select,W391   # W391 blank line at end of file
    user_select=$user_select,E305   # E305 expected 2 blank lines after class or function definition, found X
    user_select=$user_select,E306   # E306 expected 1 blank line before a nested definition, found X
    user_select=$user_select,E703   # E703 statement ends with a semicolon
    user_select=$user_select,E701   # E701 multiple statements on one line (colon)
    user_select=$user_select,E221   # E221 multiple spaces before operator
    user_select=$user_select,E741   # E741 ambiguous variable name 'l'
    user_select=$user_select,E111   # E111 indentation is not a multiple of four
    user_select=$user_select,E222   # E222 multiple spaces after operator
    user_select=$user_select,E712   # E712 comparison to True should be 'if cond is True:' or 'if cond:'
    user_select=$user_select,E262   # E262 inline comment should start with '# '
    user_select=$user_select,E203   # E203 whitespace before ','
    user_select=$user_select,E731   # E731 do not assign a lambda expression, use a def
    user_select=$user_select,W601   # W601 .has_key() is deprecated, use 'in'
    user_select=$user_select,E502   # E502 the backslash is redundant between brackets
    user_select=$user_select,W602   # W602 deprecated form of raising exception
    user_select=$user_select,E129   # E129 visually indented line with same indent as next logical line
    user_select=$user_select,E127   # E127 continuation line over-indented for visual indent
    user_select=$user_select,E128   # E128 continuation line under-indented for visual indent
    user_select=$user_select,E125   # E125 continuation line with same indent as next logical line
    user_select=$user_select,E114   # E114 indentation is not a multiple of four (comment)
    user_select=$user_select,E211   # E211 whitespace before '['
    user_select=$user_select,W191   # W191 indentation contains tabs
    user_select=$user_select,E101   # E101 indentation contains mixed spaces and tabs
    user_select=$user_select,E124   # E124 closing bracket does not match visual indentation
    user_select=$user_select,E272   # E272 multiple spaces before keyword
    user_select=$user_select,E713   # E713 test for membership should be 'not in'
    user_select=$user_select,E122   # E122 continuation line missing indentation or outdented
    user_select=$user_select,E131   # E131 continuation line unaligned for hanging indent
    user_select=$user_select,E721   # E721 do not compare types, use 'isinstance()'
    user_select=$user_select,E115   # E115 expected an indented block (comment)
    user_select=$user_select,E722   # E722 do not use bare except'
    user_select=$user_select,E266   # E266 too many leading '#' for block comment
    user_select=$user_select,E402   # E402 module level import not at top of file
    user_select=$user_select,W503   # W503 line break before binary operator

    $pep8 --select $user_select --exclude=build .
    if [ $? -ne 0 ]; then
        set_exit_error
    fi
}

flake8_checks()
{
    echo "Check for problems using flake8 ..."

    which flake8 > /dev/null
    if [ $? -ne 0 ]; then
        echo "flake8 is not found"
        set_exit_error
        return
    fi

    flake8 --max-line-length=300  --exclude=build --builtins="_" ./
    if [ $? -ne 0 ]; then
        set_exit_error
    fi
}

pylint_checks()
{
    echo "Check for problems using pylint ..."

    which pylint > /dev/null
    if [ $? -ne 0 ]; then
        echo "pylint is not found"
        set_exit_error
        return
    fi

    export PYTHONPATH="$PWD/../CanFestival-3/objdictgen":$PYTHONPATH

    disable=
    disable=$disable,C0103        # invalid-name
    disable=$disable,C0111        # missing-docstring
    disable=$disable,W0703        # broad-except
    disable=$disable,C0326        # bad whitespace
    disable=$disable,C0301        # Line too long
    disable=$disable,C0302        # Too many lines in module
    disable=$disable,W0511        # fixme
    disable=$disable,W0110        # (deprecated-lambda) map/filter on lambda could be replaced by comprehension
    disable=$disable,W1401        # (anomalous-backslash-in-string) Anomalous backslash in string: '\.'. String constant might be missing an r prefix.

    enable=
    enable=$enable,E1601          # print statement used
    enable=$enable,C0325          # (superfluous-parens) Unnecessary parens after keyword    
    enable=$enable,W0404          # reimported module    
    enable=$enable,C0411          # (wrong-import-order) standard import "import x" comes before "import y"
    enable=$enable,W0108          # (unnecessary-lambda) Lambda may not be necessary
    enable=$enable,C0412          # (ungrouped-imports) Imports from package X are not grouped
    enable=$enable,C0321          # (multiple-statements) More than one statement on a single line
    enable=$enable,W0231          # (super-init-not-called) __init__ method from base class is not called
    enable=$enable,W0105          # (pointless-string-statement) String statement has no effect    
    enable=$enable,W0311          # (bad-indentation) Bad indentation. Found 16 spaces, expected 12
    enable=$enable,W0101          # (unreachable) Unreachable code
    enable=$enable,E0102          # (function-redefined) method already defined
    enable=$enable,W0602          # (global-variable-not-assigned) Using global for 'X' but no assignment is done
    enable=$enable,W0612          # (unused-variable) Unused variable 'X'
    enable=$enable,W0611          # (unused-import), Unused import connectors

    # enable=$enable,W0403        # relative import
    # enable=$enable,W0622        # (redefined-builtin) Redefining built-in
    # enable=$enable,C1001        # (old-style-class) Old-style class defined. Problem with PyJS
    # enable=

    options=
    options="$options --rcfile=.pylint"
    # options="$options --py3k"   # report errors for Python 3 porting

    if [ -n "$enable" ]; then
        options="$options --disable=all"
        options="$options --enable=$enable"
    else
        options="$options --disable=$disable"
    fi
    # echo $options

    find ./ -name '*.py' | grep -v '/build/' | xargs pylint $options 
    if [ $? -ne 0 ]; then
        set_exit_error
    fi
}

main()
{
    compile_checks
    pep8_checks_default
    # pep8_checks_selected
    # flake8_checks
    pylint_checks
    exit $exit_code
}

main
