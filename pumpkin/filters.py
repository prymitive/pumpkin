# -*- coding: utf-8 -*-
'''
Created on 2009-07-12
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


try:
    # this is python >=2.5 module
    from functools import wraps
except ImportError:
    # so in case of <2.5 fallback to this backported code (taken from django)
    from pumpkin.contrib.backports import wraps


def unicode2str(func):
    """Convert all unicode args to str
    """
    @wraps(func)
    def newfunc( * args, ** kwargs):
        nargs = []
        for arg in args:
            if isinstance(arg, unicode):
                nargs.append(arg.encode('utf-8'))
            else:
                nargs.append(arg)

        nkwargs = {}
        for (kwarg, value) in kwargs.items():
            if isinstance(value, unicode):
                nkwargs[kwarg] = value.encode('utf-8')
            else:
                nkwargs[kwarg] = value

        return func( *nargs, **nkwargs)
    return newfunc


@unicode2str
def present(attr):
    """Will match only objects with *attr* atribute set
    """
    return '(%s=*)' % attr

@unicode2str
def eq(attr, value):
    """Will match only objects with *attr* atribute value set to *value*
    """
    return '(%s=%s)' % (attr, value)

@unicode2str
def startswith(attr, value):
    """Will match only objects with *attr* attribute set to string that starts
    with *value* substring
    """
    return '(%s=%s*)' % (attr, value)

@unicode2str
def endswith(attr, value):
    """Will match only objects with *attr* attribute set to string that ends
    with *value* substring
    """
    return '(%s=*%s)' % (attr, value)

@unicode2str
def contains(attr, value):
    """Will match only objects with *attr* attribute set to string that contains
    with *value* substring
    """
    return '(%s=*%s*)' % (attr, value)


@unicode2str
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
