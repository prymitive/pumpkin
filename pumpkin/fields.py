# -*- coding: utf-8 -*-
'''
Created on 2009-06-08
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


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
    def __init__(self, name, **kwargs):
        """Constructor
        @param name: field name

        @ivar readonly: mark field as read-only
        @ivar default: field will always return this value (instead of getting
        value from LDAP) if field is also set as readonly (optional)
        """
        self.attr = name
        self.readonly = kwargs.get('readonly', False)
        self.default = kwargs.get('default', None)
        self.lazy = kwargs.get('lazy', False)

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
        value = instance._get_attr(self.attr)
        if value is None:
            return None
        else:
            return self.decode2local(value, instance=instance)

    def fset(self, instance, value):
        """Write attribute value using model instance
        """
        if value is None:
            self.fdel(instance)
        else:
            value = self.validate(value)
            instance._set_attr(self.attr, self.encode2str(value, instance=instance))

    def fdel(self, instance):
        """Delete attribute using model instance
        """
        instance._del_attr(self.attr)

class StringListField(Field):
    """List of unicode values
    """
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
            raise ValueError, "Not a list of unicode values"

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
    def validate(self, values):
        """Check if new value is a list of int values
        """
        if isinstance(values, list):
            values = unique_list(values)
            for value in values:
                if not isinstance(value, int):
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
    def validate(self, values):
        """Check if new value is int
        """
        if isinstance(values, int):
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
