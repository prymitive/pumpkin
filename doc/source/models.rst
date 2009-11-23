Working with models
===================

Philosophy
----------

Models are used to map LDAP objects and into python object instances, this is
why pumpkin is desribes itself as *LDAP ORM (without R)*, the *R* is missing
because there are no relations involved.

Model definiton
---------------

Each models is composed as class based on :class:`~pumpkin.base.Model` class.
Example::

   from pumpkin.base import Model
   
   class MyModel(Model):
     """This is my custom model"""

It must define this required elements:

* list of LDAP object classes that it will use. To define it we must create
  *_object_class_* attribute for each model. This attribute holds list of
  containing LDAP object class names. Example::

     _object_class_ = ['posixAccount', 'inetOrgPerson']

* rdn field or list of fields, those fields will be used as naming attributes
  when saving objects to LDAP. To define it we must create *_rdn_* attribute for
  each model. This attribue holds a string or list of strings containg model
  field names (se below for information about fields). Example::

     _rdn_ = 'login'

* list of field definitons. Each field is defined as a attribute created from
  one of fields classes. We need to pass LDAP attribute name that will be mapped
  to this field as first argument, followed by available keywords (see fields
  api docs for current list). Example::

     from pumpkin.fields import StringField, IntegerField
     login = StringField('uid')
     id = IntegerField('uidNumber')

Rules for model definitions
---------------------------

* We use LDAP server schema to store objects and their attributes so each model
  must follow server schema.
* Models are not schema redefiniton, define them as You need (as long as they
  are following schema).
* Mix object classes defined in server schema to get what You need, don't create
  every model for every object class.
* Searching for model means searching for objects that are defined using all
  object classes listed in model, this means that if You define two models::

    ModelA(Model):
      _object_class_ = ['class1', 'class2']

    ModelB(Model):
      _object_class_ = ['class1']

  doing search in LDAP for ModelB objects will also return ModelA objects mapped
  to ModelB class, keep that in mind.

Defining simple model
---------------------

We will create model that maps into *posixGroup* object class:

>>> class PosixGroup(Model):
>>>   _object_class_ = 'posixGroup'
>>>   _rdn_ = 'name'
>>>   name = StringField('cn')
>>>   gid = IntegerField('gidNumber')
>>>   members = IntegerListField('memberUid')

Using hooks
-----------

Hooks allows to run any code before or after calling one of those methods:

  * :meth:`~pumpkin.base.Model.update`
  * :meth:`~pumpkin.base.Model.save`
  * :meth:`~pumpkin.base.Model.delete`
  * :meth:`~pumpkin.base.Model.passwd`

They are used in :class:`~pumpkin.models.PosixGroup` to keep members gid field 
(mapped to gidNumber attribute) in sync. To create a hook we need to create
a method named '_hook_{pre,post}_{method}', for example to create hook what will
be run after :meth:`~pumpkin.base.Model.delete` we need to define:

  >>> class MyModel(Model):
  >>>   def _hook_post_delete(self)
  >>>     [do something]
