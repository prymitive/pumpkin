# -*- coding: utf-8 -*-
'''
Created on 2009-06-11
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


from functools import partial

import ldap.dn

from fields import Field
from fields import StringListField


class _model(type):
    """Metaclass for Model. We parse Model instance namespace looking for Field
    instances, every found instance is added to Model instance as a property.
    Each field can have custom fset and fget functions, they are defined
    as a function named _%field_{fset, fget}, where %field is name of the field.
    
    Example:
    class User(Model):
        uid = StringField('uid')
    this will define Your custom Model with uid field that will be mapped
    to 'uid' attribute in LDAP database.
    
    Example custom fget function for uid field above:
        def uid_fget(self):
            return 'Custom value'
    """

    def __init__(cls, name, bases, adict):
        """Parse Model namespace and create properties from fields
        """
        cls._fields = {}
        for (key, value) in adict.items():
            # we look only for Field type objects
            if isinstance(value, Field):
                # we check if custom fdel function is defined
                fdel_name = '_%s_fdel' % key
                if fdel_name in adict.keys():
                    fdel_func = adict[fdel_name]
                else:
                    fdel_func = value.fdel

                # we check if custom fget function is defined for this Field
                fget_name = '_%s_fget' % key
                if fget_name in adict.keys():
                    fget_func = adict[fget_name]
                else:
                    fget_func = value.fget
    
                # we check if custom fset is also present, but only for 
                # non-readonly Fields
                if not value.readonly:
                    fset_name = '_%s_fset' % key
                    if fset_name in adict.keys():
                        fset_func = adict[fset_name]
                    else:
                        fset_func = value.fset
                else:
                    fset_func = None
                    # partial is needed so we won't get any scope problems
                    # because value changes on every iteration
                    if value.default:
                        fget_func = partial(lambda self, x: x.default, x=value)
    
                setattr(cls, key, property(
                    fget=fget_func,
                    fset=fset_func,
                    fdel=fdel_func,
                    )
                )

                # we store { field_name: field_instance }
                cls._fields[key] = value

    def __getattribute__(cls, name):
        """Intercept getattr() calls and return Field attribute name instead
        of property
        """
        # start with currents class _fields
        fields = super(_model, cls).__getattribute__('_fields')

        # if we are getattr'ing _fields then we return it right away
        if name == '_fields':
            return fields

        # we get _fields from every class in __bases__ and append it to fields
        for base in super(_model, cls).__getattribute__('__bases__'):
            try:
                base_fields = super(_model, base).__getattribute__('_fields')
                for (field, instance) in base_fields.items():
                    if field not in fields.keys():
                        fields[field] = instance
            except:
                pass

        if name in fields.keys():
            for (field, instance) in fields.items():
                if field == name:
                    return instance.attr
        else:
            return super(_model, cls).__getattribute__(name)


class Model(object):
    """This class represents LDAP object
    """
    __metaclass__ = _model
    object_class = StringListField('objectClass', readonly=True)

    @classmethod
    def get_private_classes(cls):
        """Get list of models private classes
        """
        # first get current class _object_class_
        if cls._object_class_ is not None:
            ret = cls._object_class_
        else:
            ret = []

        # _object_class_ can be str or list, if it's str we make it a list
        if not isinstance(ret, list):
            ret = [ret]

        # get _object_class_ from every base class and append it to list
        for base in cls.__bases__:
            pclasses = getattr(base, '_object_class_', [])
            if not isinstance(pclasses, list):
                pclasses = [pclasses]
            for pclass in pclasses:
                if pclass not in ret:
                    ret.append(pclass)
        return ret

    def _object_class_fget(self):
        """Custom fget for getting objectClass, for new object it will return
        _object_class_, for storred objects it will return
        actual objectClass value from LDAP
        """
        if self._get_attr('objectClass'):
            # we got value in local storage, return it
            return self._get_fields()['object_class'].fget(self)
        else:
            # we got new, empty object, return default objectClass
            return self.get_private_classes()


    def __init__(self, directory, dn=None, attrs={}):
        """Model constructor. You need to pass directory instance reference,
        it will be used for contacting LDAP database, dn is distinguished name
        of object that will be mapped to Model instance, if dn is None then
        empty instance will be created
        
        @param directory: LDAP directory instance used for lookups
        @param dn: LDAP object distinguished name
        @param attrs: dict with already fetch attributes, used when creating
        model instance from LDAP search

        @ivar rdn: object relative distinguished name
        @ivar location: object location 
        @ivar dn: full object distinguished name (rdn + location)
        """
        # can't use attrs kwarg becouse all model instances will use same reference
        self._storage = {}
        for (attr, value) in attrs.items():
            self._store_attr(attr, value)

        # list of dn attrs generated from dn str
        self._rdn_attrs = None
        # location part of dn
        self._location = None
        
        self._directory = directory

        self._validate_rdn()
        self._validate_model_fields()

        if dn == None:
            self._empty = True
        else:
            self._empty = False

            self._rdn_attrs = ldap.dn.str2dn(dn)
            self._rdn = ldap.dn.dn2str([self._rdn_attrs[0]])
            self._location = ldap.dn.dn2str(self._rdn_attrs[1:])

            self.update(missing_only=True)
            self._validate_object_class()

    def _validate_model_fields(self):
        """Checks if all model fields are present in schema
        """
        (must, may) = self._directory.get_schema_attrs(self.__class__)

        for (field, instance) in self._get_fields().items():
             if instance.attr not in must + may:
                 raise Exception(
"""Can't store '%s' field with LDAP attribute '%s' using current schema and \
object classes: %s, all available attrs: %s""" % (
                    field, instance.attr, self.get_private_classes(), must + may
                    )
                )

    def _validate_object_class(self):
        """Checks if passed object dn matches our model. To do so we check if
        all object classes defined in model are present in object.
        """
        for oc in self.get_private_classes():
            if oc not in self.object_class:
                raise TypeError(
                    "Object with dn %s does not have %s object class" % (self.dn, oc)
                )

    def _validate_rdn(self):
        """Checks if all rdn fields are defined
        """
        for name in self.get_rdn_fields():
            if name not in self._get_fields():
                raise Exception("RDN field '%s' is missing from model" % name)

    def _isstored(self, attr):
        """Checks if given attribute is stored in local instance storage
        """
        if attr in self._storage.keys():
            return True
        else:
            return False

    def _store_attr(self, attr, value):
        """Store attribute in local storage
        """
        self._storage[attr] = value

    def _get_attr(self, attr):
        """Get attribute from LDAP database for current object
        @param attr: attribute name
        """
        if self._isstored(attr):
            return self._storage.get(attr)
        elif self.isnew():
            return None
        else:
            value = self._directory.get_attr(self.dn, attr)
            self._store_attr(attr, value)
            return value

    def _set_attr(self, attr, value):
        """Set attribute value in local storage, it will be saved to LDAP after
        calling save()
        
        @param attr: attribute name
        @param value: new value for attribute
        """
        if attr in self.get_rdn_attrs():
            pass
            #TODO rdn rename on set
        self._store_attr(attr, value)

    def _del_attr(self, attr):
        """Remove attribue from object, we set it's value to None and it will
        be removed from LDAP after calling save()
        """
        self._store_attr(attr, None)

    def get_attributes(self):
        """Returns dict with all attributes that are set, values will be in LDAP
        format (list of str)
        """
        # we need to make sure that objectClass is set
        record = {
            'objectClass': self._get_fields()['object_class'].encode2str(
                self.object_class),
        }
        for (attr, value) in self._storage.items():
            if attr not in record.keys():
                record[attr] = value
        return record

    def update(self, missing_only=False, force=False):
        """Fetch all non-lazy fields from LDAP
        @param missing_only: fetch only attributes that are not present in local
        storage
        @param force: force fetching all attributes, even lazy
        """
        if missing_only and not force:
            ldap_attrs = []
            for instance in self._get_fields().values():
                if not self._isstored(instance.attr):
                    ldap_attrs.append(instance.attr)
        else:
            ldap_attrs = self._get_fields().values()

        # remove lazy fields
        if not force:
            for instance in self._get_fields().values():
                if instance.lazy and instance.attr in ldap_attrs:
                    ldap_attrs.remove(instance.attr)

        if ldap_attrs != []:
            for (attr, value) in self._directory.get_attrs(self.dn, ldap_attrs).items():
                self._store_attr(attr, value)

    def isnew(self):
        """Returns True if instance is new and not yet written to LDAP
        """
        return self._empty

    def _get_fields(self):
        """Returns dict with fields name -> instance mappings
        """
        ret = self._fields
        for base in self.__class__.__bases__:
            for (name, instance) in base._fields.items():
                if name not in ret.keys():
                    ret[name] = instance
        return ret

    def get_rdn_fields(self):
        """Model attributes used as rdn
        """
        if not isinstance(self._rdn_, list):
            return [self._rdn_]
        else:
            return self._rdn_

    def get_rdn_attrs(self):
        """LDAP attributes used as rdn
        """
        return [self._get_fields()[name].attr for name in self.get_rdn_fields()]

    def dn():
        doc = "Object distinguished name"        
        def fget(self):
            return '%s,%s' % (self.rdn, self.location)
        return locals()
    dn = property(**dn())

    def rdn():
        doc = """Object relative disinguished name. For every attribute present
        in models _rdn_ list, we get it value for current model and join 
        it using '+'.
        """
        def fget(self):
            if not self.isnew():
                return self._rdn
            else:
                ret = ''
                for (name, instance) in self._get_fields().items():
                    if name in self.get_rdn_fields():
                        rdn_part = '%s=%s' % (instance.attr, getattr(self, name))
                        if ret != '':
                            ret = '+'.join(ret, rdn_part)
                        else:
                            ret = rdn_part
                return ret
        return locals()
    rdn = property(**rdn())

    def location():
        doc = "Object location" 
        def fget(self):
            return self._location
        def fset(self, new_location):
            if self.isnew():
                self._location = new_location
            else:
                self.move(new_location)

        return locals()
    location = property(**location())

    def set_password(self, oldpass, newpass):
        """Change current object password in LDAP database

        @param oldpass: old password
        @param newpass: new password
        """
        # FIXME refactor to save()?
        if self.isnew():
            raise Exception, "Can't change password on empty object"
        else:
            self._directory.passwd(self.dn, oldpass, newpass)
        
    def rename(self, newrdn):
        """Rename object
        @param newdn: new relative distinguished name for current object
        """
        # FIXME refactor to save()?
        if self.isnew():
            raise Exception, "Can't rename empty object"
        else:
            self._directory.modrdn_s(self.dn, newrdn)

    def move(self, new_location):
        """Move current object to new location
        """
        self._rdn, self._location = self._directory.move(
            self.dn, self.rdn, new_location)

    def get_missing_fields(self):
        """Check if all attributes required by schema are set
        """
        ret = []
        (must, may) = self._directory.get_schema_attrs(self.__class__)
        for (name, instance) in self._get_fields().items():
            for attr in must:
                if instance.attr == attr:
                    if getattr(self, name) is None:
                        ret.append(name)
        return ret

    def save(self):
        """Save object into LDAP, if instance in new it will add object
        to LDAP, update self._rdn and mark it non-empty, if instance is
        non-empty it will write all attributes to LDAP
        """
        missing = self.get_missing_fields()
        if missing != []:
            raise Exception(
                "Can't save when required fields are missing: %s" % missing)
        
        record = self.get_attributes()
        if self.isnew():
            if self.location is None:
                raise Exception('Location not set')

            self._directory.add_object(self.dn, record)
            self._rdn = self.rdn
            self._empty = False
        else:
            self._directory.set_attrs(self.dn, record)

    def delete(self):
        """Delete object from LDAP
        """
        if self.isnew():
            raise Exception, "Can't delete empty object"
        else:
            self._directory.delete(self.dn)
