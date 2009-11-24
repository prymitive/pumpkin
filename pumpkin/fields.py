# -*- coding: utf-8 -*-
'''
Created on 2009-06-08
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


import time
import datetime
import logging
import copy

from pumpkin.debug import PUMPKIN_LOGLEVEL


logging.basicConfig(level=PUMPKIN_LOGLEVEL)
log = logging.getLogger(__name__)


def unique_list(values):
    """Strip all reapeted values in list
    """
    ret = set(values)
    return list(ret)


def check_singleval(name, values):
    """Check if field with single valued type is mapped to multi valued
    attribute
    """
    if not isinstance(values, list):
        raise TypeError('Values for %s are not a list: %s' % (name, values))
    if len(values) > 1:
        raise TypeError(
            """Field named %s expects single valued entry 
            but %d entries found""" % (name, len(values))
        )


def get_singleval(value):
    """Returns single value
    """
    if value is None:
        return None
    elif isinstance(value, list):
        return value[0]
    else:
        raise Exception('Value not a list or None: %s' % value)


class Field(object):
    """Base field with get and set methods
    """
    # default value to return if attribute is not set in LDAP, passing
    # 'default' kwarg passed to __init__() will override this
    default = None

    def __init__(self, name, **kwargs):
        """Constructor
        @param name: field name

        @ivar readonly: mark field as read-only
        @ivar default: default value to return if LDAP attribute for this field
        is not set, it will override fields self._default value, defaults
        to None, this is used mostly to return '[]' when *ListField is empty
        @ivar lazy: don't fetch attribute value from LDAP until needed, usefull
        for big binary attributes like 'jpegPhoto'
        @ivar binary: field requires binary transfer (for example
        'userCertificate' attribute needs this
        """
        self.attr = name
        self.readonly = kwargs.get('readonly', False)
        self.lazy = kwargs.get('lazy', False)
        self.binary = kwargs.get('binary', False)

        if kwargs.has_key('default'):
            self.default = kwargs.get('default')
            log.debug("New default value '%s' for field '%s'" % (
                self.default, self.attr))

    def decode2local(self, values, instance=None):
        """Returns field value decoded to local field type, if field represents
           value of integer type attribute than the value that we got from LDAP
           will be converted to int.
           This base field is just returning value as is (str).        
        """
        return values

    def encode2str(self, values, instance=None):
        """Returns field value encoded to type that is parsable by python-ldap
           (list of str values). If any field is storing attribute value
           in format other then list of str values, than we need to define
           encode2str() function that will convert it to proper format.
           This base field is just returning values as is (str).
        """
        if values is None:
            raise Exception('LDAP value is None')
        elif not isinstance(values, list):
            return [values]
        else:
            return values

    def validate(self, values):
        """Check if new value is valid, raise exception if not, return final
        value if it passes test so it can also modify value. This stub always
        passes, each field must implement it's own validate method.
        """
        return values

    def fget(self, instance):
        """Base fget function implementation, it reads attribute value(s)
           using model instance
        """
        value = instance._get_attr(self.attr, binary=self.binary)
        if value is None:
            log.debug("Field '%s' value is None, returning default '%s'" % (
                self.attr, self.default))
            return copy.deepcopy(self.default)
        else:
            return self.decode2local(value, instance=instance)

    def fset(self, instance, value):
        """Write attribute value using model instance
        """
        if value is None:
            self.fdel(instance)
        else:
            value = self.validate(value)
            instance._set_attr(self.attr, self.encode2str(
                value, instance=instance))

    def fdel(self, instance):
        """Delete attribute using model instance
        """
        instance._del_attr(self.attr)

class StringListField(Field):
    """List of unicode values
    """
    default = []

    def validate(self, values):
        """Check if new value is a list of unicode values
        """
        if isinstance(values, list):
            values = unique_list(values)
            for value in values:
                if not isinstance(value, unicode):
                    raise ValueError, "Not a unicode value: %s" % value
            return values
        else:
            raise ValueError, "Not a list of unicode values: '%s'" % values

    def decode2local(self, values, instance=None):
        """Returns list of unicode values
        """
        return [unicode(item, 'utf-8') for item in values]

    def encode2str(self, values, instance=None):
        """Returns list of str value
        """
        return [item.encode('utf-8') for item in values]


class StringField(StringListField):
    """Unicode string
    """
    default = None

    def validate(self, values):
        """Check if new value is unicode
        """
        if isinstance(values, unicode):
            return values
        else:
            raise ValueError, "Not a unicode value: %s" % values

    def encode2str(self, values, instance=None):
        """Returns str value
        """
        return StringListField.encode2str(self, [values])

    def decode2local(self, values, instance=None):
        """Return unicode value
        """
        check_singleval(self.attr, values)
        return get_singleval(StringListField.decode2local(self, values))


class IntegerListField(Field):
    """List of integer values
    """
    default = []

    def validate(self, values):
        """Check if new value is a list of int values
        """
        if isinstance(values, list):
            values = unique_list(values)
            for value in values:
                if not isinstance(value, (int, long)):
                    raise ValueError, "Not a int value: %s" % value
            return values
        else:
            raise ValueError, "Not a list of int values: %s" % values

    def decode2local(self, values, instance=None):
        """Returns list of int
        """
        return [int(item) for item in values]

    def encode2str(self, values, instance=None):
        """Returns list of str values
        """
        return [str(item) for item in values]


class IntegerField(IntegerListField):
    """Int value
    """
    default = None

    def validate(self, values):
        """Check if new value is int
        """
        if isinstance(values, (int, long)):
            return values
        else:
            raise ValueError("Not a int value: %s" % values)

    def encode2str(self, values, instance=None):
        """Returns str value
        """
        return IntegerListField.encode2str(self, [values])

    def decode2local(self, values, instance=None):
        """Returns int value
        """
        check_singleval(self.attr, values)
        return get_singleval(IntegerListField.decode2local(self, values))


class BooleanField(Field):
    """Boolean field
    """
    def __init__(self, name, **kwargs):
        """
        @ivar true: str representing True, this str will be saved to LDAP if
        field value is True, default 'True'
        @ivar flase: str representing False, this str will be saved to LDAP if
        field value is False, default 'False'
        """
        Field.__init__(self, name, **kwargs)
        self.true = kwargs.get('true', 'True')
        self.false = kwargs.get('false', 'False')

    def validate(self, values):
        """Check if value is True or False
        """
        if values in [True, False]:
            return values
        else:
            raise ValueError("Not a boolean value: %s" % values)

    def encode2str(self, values, instance=None):
        """Returns str self.true or self.false
        """
        if values:
            return [self.true]
        else:
            return [self.false]

    def decode2local(self, values, instance=None):
        """Returns True or False
        """
        check_singleval(self.attr, values)
        if get_singleval(values) == self.true:
            return True
        elif get_singleval(values) == self.false:
            return False
        else:
            raise ValueError("Unknown value '%s', not '%s' or '%s'" % (
                values, self.true, self.false))


class BinaryField(Field):
    """Single valued binary field
    """
    def decode2local(self, values, instance=None):
        """Return single value
        """
        check_singleval(self.attr, values)
        return get_singleval(values)


class DatetimeField(Field):
    """Single valued datetime field
    """
    def validate(self, values):
        """Check if value is valid datetime instance
        """
        if isinstance(values, datetime.datetime):
            return values
        else:
            raise ValueError("Not a datatime value: %s" % values)

    def encode2str(self, values, instance=None):
        """Return str values
        """
        return [str(int(time.mktime(values.timetuple())))]

    def decode2local(self, values, instance=None):
        """Return datetime instance
        """
        check_singleval(self.attr, values)
        return datetime.datetime.fromtimestamp(float(get_singleval(values)))


class DictField(Field):
    """Dictionary field with only unicode values.
    """
    def __init__(self, name, **kwargs):
        """Adds 'separator' kwarg
        """
        Field.__init__(self, name, **kwargs)
        self.delimiter = kwargs.get('delimiter', "|")


    def validate(self, values):
        """Check if value is valid dict instance
        """
        if isinstance(values, dict):
            for value in values.values():
                if not isinstance(value, unicode):
                    raise ValueError("'%s' is not a unicode value, DictField \
                can only store items with unicode values." % value)
            return values
        else:
            raise ValueError("Not a dict value: %s" % values)

    def encode2str(self, values, instance=None):
        """Return str values
        """
        return ['%s%s%s' % (
            k.encode("utf-8"),
            self.delimiter,
            v.encode("utf-8")) for (k,v) in values.items()
        ]

    def decode2local(self, values, instance=None):
        """Return dict instance
        """
        return dict((i.split(self.delimiter)) for i in values)
