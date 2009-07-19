# -*- coding: utf-8 -*-
'''
Created on 2009-07-12
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


def present(attr):
    """Will match only objects with *attr* atribute set
    """
    return '(%s=*)' % attr

def eq(attr, value):
    """Will match only objects with *attr* atribute value set to *value*
    """
    return '(%s=%s)' % (attr, value)

def startswith(attr, value):
    """Will match only objects with *attr* attribute set to string that starts
    with *value* substring
    """
    return '(%s=*%s)' % (attr, value)

def endswith(attr, value):
    """Will match only objects with *attr* attribute set to string that ends
    with *value* substring
    """
    return '(%s=%s*)' % (attr, value)

def contains(attr, value):
    """Will match only objects with *attr* attribute set to string that contains
    with *value* substring
    """
    return '(%s=*%s*)' % (attr, value)


def _make_op(prefix, parts):
    """Operator maker, used to create operators
    """
    ret = '(%s' % prefix
    for part in parts:
        ret += part
    ret += ')'
    return ret

def opand(*args):
    """And operator, ale given matches must be succesfull
    """
    return _make_op('&', args)

def opor(*args):
    """Or operator, at least one given match must be succesfull
    """
    return _make_op('|', args)

def opnot(*args):
    """Not operator, none of given matches can be succesfull, they all must fail
    """
    return _make_op('!', args)
