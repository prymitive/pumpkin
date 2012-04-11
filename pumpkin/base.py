# -*- coding: utf-8 -*-
'''
Created on 2009-06-11
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


import logging
try:
    # this is python >=2.5 module
    from functools import wraps
except ImportError:
    # so in case of <2.5 fallback to this backported code (taken from django)
    from pumpkin.contrib.backports import wraps

from pumpkin.debug import PUMPKIN_LOGLEVEL
from pumpkin.fields import Field, StringListField
from pumpkin import exceptions
from pumpkin import resource

logging.basicConfig(level=PUMPKIN_LOGLEVEL)
log = logging.getLogger(__name__)


def run_hooks(func):
    """Hooks decorator, it runs hooks for given method.
    """
    @wraps(func)
    def hook(*args, **kwargs):
        model = args[0]
        pre_name = '_hook_pre_%s' % func.__name__
        post_name = '_hook_post_%s' % func.__name__

        # run pre hook if present
        if getattr(model, pre_name, None) is not None:
            log.debug("Running pre hook '%s' on '%s'" % (pre_name, model))
            hook_call = getattr(model, pre_name)
            hook_call()
            log.debug("Pre hook finished")

        # run real method
        ret = func(*args, **kwargs)

        # run post hook if present
        if getattr(model, post_name, None) is not None:
            log.debug("Running post hook '%s' on '%s'" % (post_name, model))
            hook_call = getattr(model, post_name)
            hook_call()
            log.debug("Post hook finished")
        return ret
    return hook


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

                # we check if custom validate method is present, if so we
                # override fields validate reference
                validate_name = '_%s_validate' % key
                if validate_name in adict.keys():
                    value._validator = adict[validate_name]

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


class _Model(object):
    """This class represents LDAP object
    """
    __metaclass__ = _model
    object_class = StringListField('objectClass', readonly=True)

    @classmethod
    def _get_fields(cls):
        """Returns dict with fields name -> instance mappings
        """
        ret = cls._fields
        for base in cls.__bases__:
            for (name, instance) in base._fields.items():
                if name not in ret.keys():
                    ret[name] = instance
        return ret

    @classmethod
    def private_classes(cls):
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

    @classmethod
    def ldap_attributes(cls, lazy=True):
        """Get list of ldap attributes used by model
        """
        if lazy:
            return [ref.attr for ref in cls._get_fields().values()]
        else:
            ret = []
            for field in cls._get_fields().values():
                if not field.lazy:
                    ret.append(field.attr)
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
            return self.private_classes()


    def __init__(self, directory, dn=None, attrs={}):
        """Model constructor. You need to pass directory instance reference,
        it will be used for contacting LDAP database, dn is distinguished name
        of object that will be mapped to Model instance, if dn is None then
        empty instance will be created

        @param directory: LDAP directory instance used for lookups
        @param dn: LDAP object distinguished name
        @param attrs: dict with already fetch attributes, used when creating
        model instance from LDAP search, must contain all non-lazy attributes,
        missing non-lazy attributes will be set to None
        """
        # can't use attrs kwarg because all model instances will use same
        # reference
        self._storage = {}
        for (attr, value) in attrs.items():
            self._store_attr(attr, value)
        if attrs != {}:
            for instance in self._get_fields().values():
                if not self._isstored(instance.attr):
                    if not instance.lazy:
                        self._store_attr(instance.attr, None)

        if dn:
            if isinstance(dn, unicode):
                self._dn = dn
            else:
                self._dn = unicode(dn, 'utf-8')
        else:
            self._dn = None

        # used when changing object dn
        self._olddn = None

        self.directory = directory

        self._validate_rdn_fields()
        self._validate_schema()

        if dn == None:
            self._empty = True
            self._parent = self.directory.get_basedn()
        else:
            self._empty = False
            self._parent = None

            self.update(missing_only=True)
            self._validate_object_class()

    def _validate_schema(self):
        """Checks if all model fields are present in schema
        """
        # skip checks if we got catch all model type (like models.DN) or the model is using extensibleObject
        if 'extensibleObject' not in self.private_classes() and self._object_class_ != [] and self._rdn_ != []:
            (must, may) = self.directory.get_schema_attrs(self.__class__)

            for (field, instance) in self._get_fields().items():
                # check if all non read-only attributes can be stored
                if not instance.readonly and instance.validate_schema and instance.attr not in must + may:
                    raise exceptions.SchemaValidationError(
"""Can't store '%s' field with LDAP attribute '%s' using current schema and \
object classes: %s, all available attrs: %s""" % (
                        field, instance.attr, self.private_classes(), must + may
                        )
                    )

    def _validate_object_class(self):
        """Checks if passed object dn matches our model. To do so we check if
        all object classes defined in model are present in object.
        """
        for oc in self.private_classes():
            if oc not in self.object_class:
                if self.directory._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                    if oc in ['securityPrincipal']:
                        continue #Active Directory treats these classes as being allowed, even when not in the schema
                raise exceptions.ModelNotMatched(
                    "Object with dn %s does not have %s object class" % (
                        self.dn,
                        oc
                    )
                )

    def _validate_rdn_fields(self):
        """Checks if all rdn fields are defined
        """
        for name in self.rdn_fields():
            if name not in self._get_fields():
                raise exceptions.InvalidModel(
                    "RDN field '%s' is missing from model" % name)

    def _isstored(self, attr):
        """Checks if given attribute is stored in local instance storage
        """
        if attr in self._storage.keys():
            return True
        else:
            return False

    def _ldap_dn(self):
        """Return current object dn in LDAP, always returns dn that should be
        used for searches, dn can change when setting new parent dn or setting
        new value to rdn attributes so we need this
        """
        if self._olddn:
            return self._olddn
        else:
            return self.dn

    def _store_attr(self, attr, value):
        """Store attribute in local storage
        """
        log.debug("Storing attribute '%s' with value '%s'" % (attr, value))
        self._storage[attr] = value

    def _get_attr(self, attr, binary=False):
        """Get attribute from LDAP database for current object
        @param attr: attribute name
        """
        if self._isstored(attr):
            value = self._storage.get(attr)
            log.debug("Returning localy stored value '%s' for attribute '%s'" % (
                value, attr))
            if self.directory._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                if value in [[], '']:
                    return None
            return value
        elif self.isnew():
            return None
        else:
            # if we got binary transfer, we need to append ';binary' to
            # attribute name
            if binary:
                attribute = '%s;binary' % attr
            else:
                attribute = attr
            # if object got renamed we must keep searching using old dn until
            # save()
            value = self.directory.get_attr(self._ldap_dn(), attribute)
            self._store_attr(attr, value)
            return value

    def _set_attr(self, attr, value):
        """Set attribute value in local storage, it will be saved to LDAP after
        calling save()

        @param attr: attribute name
        @param value: new value for attribute
        """
        if attr in self.rdn_attrs() and not self.isnew():
            # we are setting new value to attribute that is part of object rdn
            # we handle it this way
            # 1. store current object dn
            # 2. set rdn attribute to new value
            # 3. check during save() if we got old dn, if true rename object
            # before actual save()
            if self._olddn is None:
                self._olddn = self.dn
                self._parent = self.get_parent()
        self._store_attr(attr, value)

    def _del_attr(self, attr):
        """Remove attribue from object, we set it's value to None and it will
        be removed from LDAP after calling save()
        """
        self._store_attr(attr, None)

    def _generate_rdn(self):
        """Generate new object RDN using _rdn_ fields
        """
        ret = ''
        for (name, instance) in self._get_fields().items():
            if name in self.rdn_fields():
                # _rdn_ attribute can hold a list of values so we always make
                #it a list
                if isinstance(getattr(self, name), list):
                    values = getattr(self, name)
                else:
                    values = [getattr(self, name)]

                # for each attribute value we create rdn part and append it
                for value in values:
                    if self.directory._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                        #AD prefers the rdn 'key' to be in uppercase.
                        rdn_part = '%s=%s' % (instance.attr.upper(), value)
                    else:
                        rdn_part = '%s=%s' % (instance.attr, value)

                    if ret != '':
                        ret = '%s+%s' % (ret, rdn_part)
                    else:
                        ret = rdn_part
        return ret

    def _get_field_attr(self, field):
        """Get field attribute name for search, it appends ';binary' to
        attribute names if field has binary mode set.
        """
        if field.binary:
            return '%s;binary' % field.attr
        else:
            return field.attr

    def get_attributes(self, all=True):
        """Returns dict with object attributes, values will be in
        LDAP format (list of str). All readonly fields will be skipped, lazy
        fields that are not stored in local storage (not set to new value or
        not fetched from LDAP) will be skipped.

        @ivar all: if True return all attributes, even not set, if False return
        only attributes with not None value.
        """
        # we need to make sure that objectClass is set
        record = {
            'objectClass': self._get_fields()['object_class'].encode2str(
                self.object_class),
        }
        for field in self._get_fields().values():
            if field.readonly:
                # we don't save readonly fields
                continue
            if field.lazy:
                # if field is lazy and all=False check if field value is stored
                # and if it is stored save it, otherwise skip it from save()
                if not self._isstored(field.attr):
                    continue
            value = self._get_attr(field.attr)
            if (value is not None or all) and field.attr not in record.keys():
                record[self._get_field_attr(field)] = value
        return record

    @run_hooks
    def update(self, missing_only=False, force=False):
        """Fetch all non-lazy fields from LDAP
        @param missing_only: fetch only attributes that are not present in local
        storage
        @param force: force fetching all attributes, even lazy
        """
        if missing_only and not force:
            # fetch only missing fields (not present in self._storage)
            ldap_attrs = []
            for instance in self._get_fields().values():
                if not self._isstored(instance.attr):
                    ldap_attrs.append(self._get_field_attr(instance))
        else:
            # fetch all fields
            ldap_attrs = [self._get_field_attr(ref) for ref in self._get_fields().values()]

        # remove lazy fields
        if not force:
            for instance in self._get_fields().values():
                if instance.lazy:
                    if instance.attr in ldap_attrs:
                        ldap_attrs.remove(instance.attr)
                        log.debug("Lazy attribute: '%s'" % instance.attr)
                    if '%s;binary' % instance.attr in ldap_attrs:
                        ldap_attrs.remove('%s;binary' % instance.attr)
                        log.debug("Lazy attribute: '%s;binary'" % instance.attr)

        log.debug("Updating attrs '%s' for '%s'" % (ldap_attrs, self.dn))
        if ldap_attrs != []:
            for (attr, value) in self.directory.get_attrs(
                self._ldap_dn(), ldap_attrs).items():
                self._store_attr(attr, value)

    def isnew(self):
        """Returns True if instance is new and not yet written to LDAP
        """
        return self._empty

    def rdn_fields(self):
        """Model attributes used as rdn
        """
        if not isinstance(self._rdn_, list):
            return [self._rdn_]
        else:
            return self._rdn_

    def rdn_attrs(self):
        """LDAP attributes used as rdn
        """
        return [self._get_fields()[name].attr for name in self.rdn_fields()]

    def missing_fields(self):
        """Check if all attributes required by schema are set
        """
        ret = []
        (must, may) = self.directory.get_schema_attrs(self.__class__)
        for (name, instance) in self._get_fields().items():
            for attr in must:
                if instance.attr == attr:
                    if getattr(self, name) is None:
                        ret.append(name)
        return ret

    def get_parent(self):
        """Return parent object dn.
        """
        if self._parent:
            return self._parent
        else:
            return ','.join(self.dn.split(',')[1:])

    @run_hooks
    def save(self):
        """Save object into LDAP, if instance in new it will add object
        to LDAP, update self._rdn and mark it non-empty, if instance is
        non-empty it will write all attributes to LDAP
        """
        if self.missing_fields() != []:
            raise exceptions.FieldValueMissing(
                "Can't save when required fields are missing: %s" %
                self.missing_fields())

        if self.isnew():
            # when adding new object we need data dict without None values
            record = self.get_attributes(all=False)
            log.debug("Adding new object to LDAP: '%s'" % self.dn)
            if self.directory._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                if 'objectClass' in record and 'securityPrincipal' in record['objectClass']:
                    record['objectClass'].remove('securityPrincipal')
                    #In AD this is one of those implicit object classes
            self.directory.add_object(self.dn, record)
            self._empty = False
        else:

            if self._olddn and self._olddn != self.dn:
                log.debug("Rename object from '%s' to '%s'" % (self._olddn, self.dn))
                self.directory.rename(
                    self._olddn,
                    self._generate_rdn(),
                    parent = self._parent
                )
                self._olddn = None
                self._parent = ','.join(self.dn.split(',')[1:])
                log.debug("Parent after save '%s'" % self._parent)

            record = self.get_attributes(all=True)
            log.debug("Save attributes for '%s': %s" % (self.dn, record))

            if self.directory._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                #AD doesn't let you set these, and it was renamed earlier
                for i in self.rdn_attrs():
                    if i in record:
                        del record[i]

                #AD also doesn't let you set these
                for i in ['objectClass', 'objectGUID']:
                    if i in record:
                        del record[i]

                #AD doesn't like empty modlists
                if len(record) != 0:
                    self.directory.set_attrs(self.dn, record)

                #Update GUID from ldap next time its requested
                if 'objectGUID' in self._storage:
                    del self._storage['objectGUID']
            else:
                self.directory.set_attrs(self.dn, record)





    @run_hooks
    def delete(self, recursive=False):
        """Delete object from LDAP
        """
        log.debug("Deleting '%s' recursive=%s" % (self.dn, recursive))
        if self.isnew():
            raise exceptions.DeleteOnNew("Can't delete empty object")
        else:
            # we got recursive delete so we first delete all children objects
            if recursive:
                for instance in self.directory.search(
                    Model, basedn=self.dn, skip_basedn=True, recursive=False):
                    instance.delete(recursive=recursive)
            self.directory.delete(self.dn)
            self._empty = True
            self._dn = None

    def set_parent(self, parent_dn):
        """Set parrent object dn, required when creating new object, can also
        be used to move object aroudn LDAP tree.
        """
        # save old dn becouse we will need that during save()
        if self._olddn is None and not self.isnew():
            self._olddn = self.dn
        self._parent = parent_dn

    def dn():
        doc = "Object distinguished name"
        def fget(self):
            # If object is new or was renamed we got _parent so we generate new
            # dn else we return _dn (dn from constructor)
            if self._parent:
                return '%s,%s' % (self._generate_rdn(), self._parent)
            elif self._dn:
                return self._dn
        return locals()
    dn = property(**dn())

    @run_hooks
    def passwd(self, oldpass, newpass):
        """Change LDAP password
        """
        #TODO add check if object has password field or implement PasswordField
        self.directory.passwd(self._ldap_dn(), oldpass, newpass)

    def get_children(self, model=None, recursive=True):
        """Return list of children objects

        .. attribute:: model

           model used for search, it defaults to
           :class:`~pumpkin.base.Model` which will match all objects, if custom
           model is passed it will only return children matching model.

        .. attribute:: recursive

           if recursive is True we will get all objects from current object
           subtree, if it is False, only objects which are located directly
           under current object will be returned.
        """
        return self.directory.search(
            model, self.dn, recursive=recursive, skip_basedn=True)


class Model(_Model):
    """Base model, it has only dn field and is used for example to remove any
    object from LDAP without knowing it's model type. All defines models should
    inherit from this class.
    """
    _object_class_ = []
    _rdn_ = []
